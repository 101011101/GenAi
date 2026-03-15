"""
debug_pipeline.py — Interactive step-through runner for the FraudGen pipeline.

Runs each pipeline stage manually, pretty-prints the output, then waits for
your confirmation before moving to the next stage.

Stage outputs are cached to .debug_cache/ so you can resume from where you
left off without re-running earlier stages.

Usage:
    python3 debug_pipeline.py

Controls at each pause:
    Enter       → continue to next stage
    s / skip    → skip this cell and go to the next one (variant loop only)
    q / quit    → exit immediately
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Ensure project root is on sys.path
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.critic import CriticAgent
from agents.fraud_constructor import FraudConstructorAgent
from agents.orchestrator import OrchestratorAgent, OrchestratorOutput
from agents.persona_generator import PersonaGeneratorAgent
from models.persona import Persona
from models.run_config import RunConfig
from utils.schema_validator import validate_raw_variant

# ---------------------------------------------------------------------------
# Config — edit these to change what the debug run targets
# ---------------------------------------------------------------------------
DEBUG_CONFIG = RunConfig(
    fraud_description=(
        "Layered 3-hop mule account network, burst withdrawal pattern, "
        "domestic transfers only. Criminal organization uses recruited "
        "account holders to move stolen funds rapidly before extraction."
    ),
    variant_count=4,       # keep small for debug
    fidelity_level=3,
    persona_count=2,
    max_parallel=1,
    critic_floor=6.0,      # lower floor so debug runs pass more easily
    max_revisions=1,
)

# How many cells to process in the variant loop (set to None for all)
DEBUG_CELL_LIMIT = 2

# Cache directory
_CACHE_DIR = _ROOT / ".debug_cache"
_CACHE_ORCHESTRATOR = _CACHE_DIR / "orchestrator.json"
_CACHE_PERSONAS = _CACHE_DIR / "personas.json"


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_DIM    = "\033[2m"


def _hr(char: str = "─", width: int = 72) -> str:
    return char * width


def _header(title: str) -> None:
    print(f"\n{_BOLD}{_CYAN}{_hr('═')}{_RESET}")
    print(f"{_BOLD}{_CYAN}  {title}{_RESET}")
    print(f"{_BOLD}{_CYAN}{_hr('═')}{_RESET}\n")


def _section(title: str) -> None:
    print(f"\n{_BOLD}{_YELLOW}{_hr()}{_RESET}")
    print(f"{_BOLD}{_YELLOW}  {title}{_RESET}")
    print(f"{_BOLD}{_YELLOW}{_hr()}{_RESET}\n")


def _ok(msg: str) -> None:
    print(f"{_GREEN}✔  {msg}{_RESET}")


def _info(msg: str) -> None:
    print(f"{_DIM}   {msg}{_RESET}")


def _err(msg: str) -> None:
    print(f"{_RED}✘  {msg}{_RESET}")


def _cached(msg: str) -> None:
    print(f"{_CYAN}⚡  {msg} (loaded from cache){_RESET}")


def _dump(obj: object, indent: int = 2) -> None:
    """Pretty-print a dict/list/Pydantic model."""
    if hasattr(obj, "model_dump"):
        data = obj.model_dump()
    else:
        data = obj
    print(json.dumps(data, indent=indent, default=str))


def _pause(prompt: str = "") -> str:
    """Print a pause prompt and return the user's input (stripped, lowercase)."""
    msg = prompt or "Press Enter to continue, [s]kip cell, or [q]uit…"
    try:
        return input(f"\n{_BOLD}  ❯  {msg}  {_RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def _check_quit(response: str) -> None:
    if response in ("q", "quit", "exit"):
        print("Exiting debug run.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _save_cache(path: Path, data: object) -> None:
    _CACHE_DIR.mkdir(exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump()
    elif hasattr(data, "__dict__"):
        payload = data.__dict__
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _load_orchestrator_cache() -> OrchestratorOutput | None:
    if not _CACHE_ORCHESTRATOR.exists():
        return None
    try:
        raw = json.loads(_CACHE_ORCHESTRATOR.read_text(encoding="utf-8"))
        return OrchestratorOutput(
            variation_dimensions=raw.get("variation_dimensions", []),
            coverage_cells=raw.get("coverage_cells", []),
            suggested_persona_count=raw.get("suggested_persona_count", 5),
        )
    except Exception:
        return None


def _load_personas_cache() -> list[Persona] | None:
    if not _CACHE_PERSONAS.exists():
        return None
    try:
        raw = json.loads(_CACHE_PERSONAS.read_text(encoding="utf-8"))
        personas_list = raw if isinstance(raw, list) else raw.get("personas", [])
        return [Persona.model_validate(p) for p in personas_list]
    except Exception:
        return None


def _ask_use_cache(stage: str) -> bool:
    """Ask the user if they want to use a cached result for a stage."""
    resp = _pause(f"Cache found for {stage}. Use it? [Enter=yes, n=re-run]")
    _check_quit(resp)
    return resp not in ("n", "no", "r", "rerun", "re-run")


# ---------------------------------------------------------------------------
# Live timer helpers
# ---------------------------------------------------------------------------

async def _tick(label: str) -> None:
    """Background task: rewrite the current line with elapsed seconds every 0.5s."""
    start = time.perf_counter()
    while True:
        elapsed = int(time.perf_counter() - start)
        print(f"\r  {_DIM}→ {label}  {elapsed}s…{_RESET}   ", end="", flush=True)
        await asyncio.sleep(0.5)


def make_on_step() -> tuple[callable, callable]:
    """Return (on_step callback, cleanup fn).

    on_step fires at each step boundary:
      - label ending in '— running…' → start live timer
      - label ending in 's)' (done)   → cancel timer, print final line
    cleanup cancels any still-running timer (call after the constructor returns).
    """
    _task: list[asyncio.Task | None] = [None]

    def _cancel() -> None:
        if _task[0] is not None and not _task[0].done():
            _task[0].cancel()
            _task[0] = None
            print()  # move past the timer line

    def on_step(label: str) -> None:
        _cancel()
        if "— done" in label:
            print(f"  {_DIM}→ {label}{_RESET}")
        else:
            # Start a new live ticker for this step
            _task[0] = asyncio.create_task(_tick(label.replace(" — running…", "")))

    return on_step, _cancel


# ---------------------------------------------------------------------------
# Main async runner
# ---------------------------------------------------------------------------

async def main() -> None:
    _header("FraudGen — Pipeline Step-Through Debugger")
    print(f"  Fraud description : {DEBUG_CONFIG.fraud_description[:80]}…")
    print(f"  Variant count     : {DEBUG_CONFIG.variant_count}")
    print(f"  Persona count     : {DEBUG_CONFIG.persona_count}")
    print(f"  Cell limit        : {DEBUG_CELL_LIMIT}")
    print(f"  Critic floor      : {DEBUG_CONFIG.critic_floor}")
    print(f"  Cache dir         : {_CACHE_DIR}")

    resp = _pause("Ready to start? Press Enter or [q]uit")
    _check_quit(resp)

    # -----------------------------------------------------------------------
    # STAGE 1 — Orchestrator
    # -----------------------------------------------------------------------
    _section("STAGE 1 / 4  —  OrchestratorAgent")

    orchestrator_output: OrchestratorOutput | None = None
    cached_orch = _load_orchestrator_cache()
    if cached_orch is not None and _ask_use_cache("Stage 1 (Orchestrator)"):
        orchestrator_output = cached_orch
        _cached(f"Orchestrator: {len(orchestrator_output.coverage_cells)} cells, "
                f"{len(orchestrator_output.variation_dimensions)} dimensions")
    else:
        _info("Calling Claude with extended thinking to decompose the fraud description…")
        orchestrator_output = await OrchestratorAgent().run(DEBUG_CONFIG)
        _save_cache(_CACHE_ORCHESTRATOR, orchestrator_output)
        _ok("Cached orchestrator output to .debug_cache/orchestrator.json")

    _ok(f"Orchestrator: {len(orchestrator_output.coverage_cells)} cells "
        f"across {len(orchestrator_output.variation_dimensions)} dimensions")
    _ok(f"Suggested persona count: {orchestrator_output.suggested_persona_count}")

    print(f"\n{_BOLD}Variation dimensions:{_RESET}")
    for dim in orchestrator_output.variation_dimensions:
        print(f"  • {dim.get('name')}: {dim.get('description', '')[:60]}")

    print(f"\n{_BOLD}Coverage cells (first 6):{_RESET}")
    for cell in orchestrator_output.coverage_cells[:6]:
        dims = cell.get("dimension_values", {})
        dims_str = ", ".join(f"{k}={v}" for k, v in list(dims.items())[:3])
        print(f"  [{cell['cell_id']}]  slot={cell['persona_slot']}  {dims_str}")
    if len(orchestrator_output.coverage_cells) > 6:
        print(f"  … and {len(orchestrator_output.coverage_cells) - 6} more")

    print(f"\n{_BOLD}Full orchestrator output:{_RESET}")
    _dump(orchestrator_output.__dict__)

    resp = _pause()
    _check_quit(resp)

    # -----------------------------------------------------------------------
    # STAGE 2 — Persona Generator
    # -----------------------------------------------------------------------
    _section("STAGE 2 / 4  —  PersonaGeneratorAgent")

    personas: list[Persona] | None = None
    cached_personas = _load_personas_cache()
    if cached_personas is not None and _ask_use_cache("Stage 2 (Personas)"):
        personas = cached_personas
        _cached(f"Loaded {len(personas)} personas")
    else:
        _info(f"Generating {orchestrator_output.suggested_persona_count} criminal personas…")
        personas = await PersonaGeneratorAgent().run(
            DEBUG_CONFIG.fraud_description, DEBUG_CONFIG
        )
        _save_cache(_CACHE_PERSONAS, [p.model_dump() for p in personas])
        _ok("Cached personas to .debug_cache/personas.json")

    _ok(f"Personas ready: {len(personas)}")
    for p in personas:
        print(f"\n  {_BOLD}[{p.persona_id}] {p.name}{_RESET}  risk={p.risk_tolerance}")
        print(f"  {_DIM}{p.backstory[:100]}…{_RESET}" if len(p.backstory) > 100 else f"  {_DIM}{p.backstory}{_RESET}")

    print(f"\n{_BOLD}Full persona objects:{_RESET}")
    for p in personas:
        _dump(p)
        print()

    resp = _pause()
    _check_quit(resp)

    # -----------------------------------------------------------------------
    # STAGE 3 + 4 — FraudConstructor → Critic (per cell)
    # -----------------------------------------------------------------------
    cells = orchestrator_output.coverage_cells
    if DEBUG_CELL_LIMIT is not None:
        cells = cells[:DEBUG_CELL_LIMIT]

    approved: list = []

    for cell_idx, cell in enumerate(cells):
        cell_id = cell["cell_id"]

        # Resolve persona
        slot = max(0, min(int(cell.get("persona_slot", 0)), len(personas) - 1))
        persona = personas[slot]

        _section(f"STAGE 3 / 4  —  FraudConstructorAgent  [{cell_id}]  ({cell_idx + 1}/{len(cells)})")
        _info(f"Cell: {json.dumps(cell.get('dimension_values', {}), default=str)}")
        _info(f"Persona: {persona.name} ({persona.persona_id})")

        # Per-cell variant cache
        cell_cache_path = _CACHE_DIR / f"variant_{cell_id}.json"
        raw_variant = None

        if cell_cache_path.exists():
            resp = _pause(f"Cache found for variant {cell_id}. Use it? [Enter=yes, n=re-run]")
            _check_quit(resp)
            if resp not in ("n", "no", "r", "rerun"):
                try:
                    from models.variant import RawVariant
                    raw_variant = RawVariant.model_validate(
                        json.loads(cell_cache_path.read_text(encoding="utf-8"))
                    )
                    _cached(f"Variant {raw_variant.variant_id} loaded")
                except Exception as e:
                    _err(f"Cache load failed ({e}), re-running constructor…")
                    raw_variant = None

        if raw_variant is None:
            on_step, _cleanup = make_on_step()

            print()
            try:
                raw_variant = await FraudConstructorAgent().run(
                    persona=persona,
                    cell_assignment=cell,
                    on_step=on_step,
                )
                _cleanup()
                _save_cache(cell_cache_path, raw_variant)
                _ok(f"Cached variant to .debug_cache/variant_{cell_id}.json")
            except Exception as exc:
                _cleanup()
                _err(f"FraudConstructor failed: {exc}")
                resp = _pause("Press Enter to continue to next cell, [s]kip, or [q]uit")
                _check_quit(resp)
                continue

        _ok(f"FraudConstructor complete — variant_id={raw_variant.variant_id}")
        _ok(f"Transactions generated: {len(raw_variant.transactions)}")
        print(f"\n{_BOLD}Raw variant output:{_RESET}")
        _dump(raw_variant)

        resp = _pause("Variant generated. Continue to schema validation? ([s]kip cell, [q]uit)")
        _check_quit(resp)
        if resp in ("s", "skip"):
            continue

        # -------------------------------------------------------------------
        # Schema validation
        # -------------------------------------------------------------------
        _section(f"STAGE 3b  —  Schema Validator  [{cell_id}]")

        validated, validation_error = validate_raw_variant(raw_variant.model_dump())
        if validated is None:
            _err(f"Schema validation FAILED: {validation_error}")
            resp = _pause("Press Enter to continue to next cell, or [q]uit")
            _check_quit(resp)
            continue
        else:
            _ok("Schema validation PASSED")

        resp = _pause("Continue to Critic? ([s]kip cell, [q]uit)")
        _check_quit(resp)
        if resp in ("s", "skip"):
            continue

        # -------------------------------------------------------------------
        # Critic
        # -------------------------------------------------------------------
        _section(f"STAGE 4 / 4  —  CriticAgent  [{cell_id}]")
        _info(f"Critic floor: realism≥{DEBUG_CONFIG.critic_floor}, distinctiveness≥6.0")

        try:
            scored = await CriticAgent().run(
                variant=validated,
                persona=persona,
                critic_floor=DEBUG_CONFIG.critic_floor,
            )
        except Exception as exc:
            _err(f"CriticAgent failed: {exc}")
            resp = _pause("Press Enter to continue to next cell, or [q]uit")
            _check_quit(resp)
            continue

        avg = round((scored.realism_score + scored.distinctiveness_score) / 2.0, 1)
        status_color = _GREEN if scored.passed else _RED
        status_label = "PASS ✔" if scored.passed else "FAIL ✘"

        print(f"\n  {status_color}{_BOLD}Critic: {status_label}{_RESET}")
        print(f"  Realism           : {scored.realism_score}")
        print(f"  Distinctiveness   : {scored.distinctiveness_score}")
        print(f"  Avg score         : {avg}")
        print(f"  Persona consistent: {scored.persona_consistency}")
        print(f"  Label correct     : {scored.label_correctness}")
        if scored.feedback:
            print(f"\n  {_DIM}Feedback: {scored.feedback[:200]}{_RESET}")

        if scored.passed:
            approved.append(scored)
            _ok(f"Variant {scored.variant_id} approved and added to dataset.")
        else:
            _err(f"Variant {scored.variant_id} rejected by critic.")

        resp = _pause("Continue to next cell? ([q]uit to exit)")
        _check_quit(resp)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    _header("Debug Run Complete")
    _ok(f"Cells processed : {len(cells)}")
    _ok(f"Approved        : {len(approved)}")
    _ok(f"Rejected        : {len(cells) - len(approved)}")

    if approved:
        print(f"\n{_BOLD}Approved variant IDs:{_RESET}")
        for v in approved:
            print(f"  • {v.variant_id}  score={round((v.realism_score + v.distinctiveness_score) / 2, 1)}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
