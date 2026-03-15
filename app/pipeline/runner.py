"""Async pipeline runner — coordinates all agents and drives a full run end to end."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from agents.critic import CriticAgent
from agents.fraud_constructor import FraudConstructorAgent
from agents.orchestrator import OrchestratorAgent
from agents.persona_generator import PersonaGeneratorAgent
from models.persona import Persona
from models.run_config import RunConfig
from models.variant import ScoredVariant
from pipeline.cell_generator import generate_cells
from pipeline.coverage_matrix import CoverageMatrix
from pipeline.output_handler import OutputHandler
from pipeline.run_state import CellStatus, RunState, VariantSummary
from utils.schema_validator import validate_raw_variant

logger = logging.getLogger(__name__)


def _check_cell_persona_conflict(cell: dict, persona: Persona) -> str:
    """Return a non-empty conflict description if cell and persona are irreconcilable."""
    dim = cell.get("dimension_values", {})
    conflicts: list[str] = []

    hop_count = dim.get("hop_count")
    if hop_count is not None:
        try:
            if persona.operational_scale == "small" and int(hop_count) > 4:
                conflicts.append(
                    f"cell hop_count={hop_count} but persona.operational_scale='small' (max 4 hops)"
                )
        except (ValueError, TypeError):
            pass

    extraction = str(dim.get("extraction_method", "")).lower()
    resources = persona.resources.lower()
    if "crypto" in extraction and ("no crypto" in resources or "crypto_capability\": false" in resources):
        conflicts.append(
            f"cell extraction_method='{extraction}' but persona.resources states no crypto capability"
        )

    geographic = str(dim.get("geographic_spread", dim.get("primary_payment_rail", ""))).lower()
    if any(w in geographic for w in ("international", "cross-border", "swift")) and (
        "no international" in resources or "domestic only" in resources
    ):
        conflicts.append(
            f"cell geographic_spread='{geographic}' but persona.resources states no international reach"
        )

    return "; ".join(conflicts)


async def _stop_monitor(
    run_state: RunState,
    tasks: list[asyncio.Task],
    poll_interval: float = 0.5,
) -> None:
    """Cancel all pending tasks as soon as a stop signal is detected."""
    while True:
        if run_state.control_signal == "stop":
            for t in tasks:
                if not t.done():
                    t.cancel()
            return
        if all(t.done() for t in tasks):
            return
        await asyncio.sleep(poll_interval)


class PipelineRunner:
    """Coordinates the full pipeline from RunConfig to output files on disk.

    Runs entirely inside an asyncio event loop.  The caller is expected to
    start a background thread with ``threading.Thread(target=asyncio.run,
    args=(runner.run(config, run_state),))``.
    """

    async def run(
        self,
        config: RunConfig,
        run_state: RunState,
        personas_out: list | None = None,
        approved_variants_out: list | None = None,
    ) -> str:
        """Execute a full pipeline run.

        Parameters
        ----------
        config:
            All settings for this run.
        run_state:
            Shared state object that the console polls for live updates.
        personas_out:
            If provided, will be extended with the generated Persona objects so
            the caller can pass them to OutputHandler for a richer personas.json.
        approved_variants_out:
            If provided, this list is used as the approved_variants accumulator
            instead of a fresh internal list.  This lets the caller (e.g. the
            Streamlit session state) hold a live reference to the same list and
            observe variants as they are approved in real time.

        Returns
        -------
        str
            Absolute path of the run output folder.
        """
        run_start_time = datetime.now(tz=timezone.utc)

        # ------------------------------------------------------------------
        # Demo mode guard — cap cells and force fidelity level 3
        # ------------------------------------------------------------------
        if config.demo_mode:
            config = config.model_copy(update={"fidelity_level": 3})

        # ------------------------------------------------------------------
        # Step 1 — Orchestrate
        # ------------------------------------------------------------------
        run_state.set_phase("Orchestrating")
        run_state.log_event("Orchestrator -> Claude [thinking mode] decomposing fraud description...")
        orchestrator_output = await OrchestratorAgent().run(config)
        run_state.log_event(
            f"Orchestrator done: {len(orchestrator_output.variation_dimensions)} dimensions discovered"
        )
        run_state.set_orchestrator_output(orchestrator_output)

        # Generate coverage cells deterministically from dimensions
        target_cells = min(config.variant_count, 12) if config.demo_mode else config.variant_count
        cells: list[dict] = generate_cells(
            dimensions=orchestrator_output.variation_dimensions,
            target_count=target_cells,
            suggested_persona_count=orchestrator_output.suggested_persona_count,
        )
        run_state.log_event(f"CellGenerator: {len(cells)} cells from Cartesian product of dimensions")

        # ------------------------------------------------------------------
        # Step 2 — Build coverage matrix
        # ------------------------------------------------------------------
        matrix = CoverageMatrix(
            orchestrator_output.variation_dimensions,
            cells,
        )

        # ------------------------------------------------------------------
        # Step 3 — Generate personas
        # ------------------------------------------------------------------
        run_state.set_phase("Generating personas")
        run_state.log_event(f"PersonaGenerator -> Claude generating {orchestrator_output.suggested_persona_count} personas...")
        personas: list[Persona] = await PersonaGeneratorAgent().run(
            config.fraud_description, config
        )
        run_state.log_event(f"PersonaGenerator done: {len(personas)} personas — {', '.join(p.name for p in personas)}")
        run_state.set_personas(personas)

        if personas_out is not None:
            personas_out.extend(personas)

        # ------------------------------------------------------------------
        # Step 4 — Set totals and start variant generation
        # ------------------------------------------------------------------
        run_state.variants_total = len(cells)

        run_state.set_phase("Generating variants")
        run_state.log_event(
            f"Spawning {len(cells)} variant tasks "
            f"(max {config.max_parallel} parallel, {config.max_revisions} revision(s) allowed)"
        )

        semaphore = asyncio.Semaphore(config.max_parallel)
        approved_variants: list[ScoredVariant] = (
            approved_variants_out if approved_variants_out is not None else []
        )
        approved_lock = asyncio.Lock()

        tasks = [
            asyncio.create_task(self._process_cell(
                cell=cell,
                personas=personas,
                matrix=matrix,
                config=config,
                run_state=run_state,
                semaphore=semaphore,
                approved_variants=approved_variants,
                approved_lock=approved_lock,
                extra_feedback="",
            ))
            for cell in cells
        ]

        monitor = asyncio.create_task(_stop_monitor(run_state, tasks))
        _first_results = await asyncio.gather(*tasks, return_exceptions=True)
        monitor.cancel()
        for _r in _first_results:
            if isinstance(_r, BaseException) and not isinstance(_r, asyncio.CancelledError):
                run_state.add_error(f"Unhandled task exception: {_r}")
                logger.exception("Unhandled task exception in gather", exc_info=_r)

        # ------------------------------------------------------------------
        # Step 5 — Stop check after first pass
        # ------------------------------------------------------------------
        if run_state.control_signal == "stop":
            logger.info("Stop signal received — skipping second pass and writing output.")
        elif config.auto_second_pass:
            # ------------------------------------------------------------------
            # Step 6 — Optional second pass for underrepresented cells
            # ------------------------------------------------------------------
            saturation = matrix.check_saturation()
            if saturation < 0.6:
                underrepresented = matrix.get_underrepresented_cells()
                if underrepresented:
                    run_state.log_event(
                        f"Second pass: coverage {saturation*100:.0f}% — "
                        f"retrying {len(underrepresented)} underrepresented cells"
                    )
                    logger.info(
                        "Coverage saturation %.1f%% — running second pass on %d cells.",
                        saturation * 100,
                        len(underrepresented),
                    )
                    second_pass_tasks = [
                        asyncio.create_task(self._process_cell(
                            cell=cell,
                            personas=personas,
                            matrix=matrix,
                            config=config,
                            run_state=run_state,
                            semaphore=semaphore,
                            approved_variants=approved_variants,
                            approved_lock=approved_lock,
                            extra_feedback=(
                                "Focus on underrepresented variant space — "
                                "be structurally different from common patterns"
                            ),
                        ))
                        for cell in underrepresented
                    ]
                    monitor2 = asyncio.create_task(_stop_monitor(run_state, second_pass_tasks))
                    _second_results = await asyncio.gather(*second_pass_tasks, return_exceptions=True)
                    monitor2.cancel()
                    for _r in _second_results:
                        if isinstance(_r, BaseException) and not isinstance(_r, asyncio.CancelledError):
                            run_state.add_error(f"Unhandled second-pass task exception: {_r}")
                            logger.exception("Unhandled second-pass task exception", exc_info=_r)

        # ------------------------------------------------------------------
        # Step 7 — Compile dataset
        # ------------------------------------------------------------------
        run_state.set_phase("Compiling dataset")

        folder_path = OutputHandler().write_run_output(
            approved_variants=approved_variants,
            run_config=config,
            run_state=run_state,
            run_start_time=run_start_time,
        )

        # ------------------------------------------------------------------
        # Step 8 — Mark complete
        # ------------------------------------------------------------------
        run_state.log_event(
            f"RUN COMPLETE — {run_state.variants_completed} variants "
            f"({run_state.rejections_count} rejected, {run_state.revisions_count} revised) "
            f"| total cost=${run_state.total_cost_usd:.4f}"
        )
        run_state.mark_complete()

        return folder_path

    # ------------------------------------------------------------------
    # Private: per-cell coroutine
    # ------------------------------------------------------------------

    async def _process_cell(
        self,
        cell: dict,
        personas: list[Persona],
        matrix: CoverageMatrix,
        config: RunConfig,
        run_state: RunState,
        semaphore: asyncio.Semaphore,
        approved_variants: list[ScoredVariant],
        approved_lock: asyncio.Lock,
        extra_feedback: str = "",
    ) -> None:
        """Run the fraud_constructor → validator → critic loop for one coverage cell.

        All exceptions are caught internally — a failure here never propagates to
        the caller or crashes other concurrent tasks.
        """
        cell_id: str = cell["cell_id"]

        async with semaphore:
            # ----------------------------------------------------------------
            # Control signal check — before doing any work
            # ----------------------------------------------------------------
            if run_state.control_signal == "stop":
                return

            while run_state.control_signal == "pause":
                await asyncio.sleep(0.5)
                if run_state.control_signal == "stop":
                    return

            # ----------------------------------------------------------------
            # Claim the cell in the coverage matrix
            # ----------------------------------------------------------------
            claimed = matrix.assign_cell(
                cell_id=cell_id,
                agent_id=str(id(asyncio.current_task())),
            )
            if claimed is None:
                # Cell already taken by another task (race condition) — skip silently.
                return

            # ----------------------------------------------------------------
            # Resolve persona
            # ----------------------------------------------------------------
            slot = cell.get("persona_slot", 0)
            if personas:
                slot = max(0, min(int(slot), len(personas) - 1))
                persona = personas[slot]
            else:
                # No personas available — reject the cell and exit.
                matrix.reject_cell(cell_id)
                run_state.add_error(
                    f"Cell {cell_id}: no personas available, skipping."
                )
                return

            # ----------------------------------------------------------------
            # Pre-check: detect irreconcilable cell/persona conflicts before
            # burning API calls on attempts that will always fail persona_consistency
            # ----------------------------------------------------------------
            conflict = _check_cell_persona_conflict(cell, persona)
            if conflict:
                run_state.log_event(
                    f"{cell_id}: CONFLICT SKIP — {conflict} (irreconcilable, skipping)"
                )
                run_state.add_error(f"Cell {cell_id}: irreconcilable cell/persona conflict — {conflict}")
                matrix.reject_cell(cell_id)
                return

            run_state.upsert_cell(CellStatus(
                cell_id=cell_id,
                dimension_values=cell.get("dimension_values", {}),
                assigned_persona_id=getattr(persona, "persona_id", ""),
                assigned_persona_name=persona.name,
                status="in_progress",
            ))
            run_state.increment_active()

            # Log cell start with dimension parameters
            dim_vals = cell.get("dimension_values", {})
            dim_summary = ", ".join(f"{k}={v}" for k, v in list(dim_vals.items())[:4])
            run_state.log_event(f"{cell_id}: START — {dim_summary} | persona={persona.name}")

            # ----------------------------------------------------------------
            # Track cost before entering the attempt loop
            # ----------------------------------------------------------------
            # We create dedicated agent instances per cell so their LLMClient
            # token counters are isolated.  This lets us compute the cost delta
            # per cell by reading cost_usd after all calls complete.
            constructor = FraudConstructorAgent()
            critic_agent = CriticAgent()

            feedback: str = extra_feedback
            passed_this_cell = False
            attempt_count = 0
            max_attempts = config.max_revisions + 1  # e.g. max_revisions=2 → 3 total attempts

            try:
                for attempt in range(max_attempts):
                    attempt_count = attempt + 1

                    # Check stop signal between attempts
                    if run_state.control_signal == "stop":
                        break

                    # ----------------------------------------------------------
                    # Fraud constructor
                    # ----------------------------------------------------------
                    run_state.log_event(
                        f"{cell_id}: FraudConstructor [attempt {attempt_count}/{max_attempts}] "
                        f"persona={persona.name}"
                    )
                    try:
                        raw_variant, persona_ok, consistency_notes = await constructor.run(
                            persona=persona,
                            cell_assignment=cell,
                            critic_feedback=feedback,
                            on_step=lambda msg, _cid=cell_id: run_state.log_event(f"{_cid}: {msg}"),
                        )
                    except Exception as exc:
                        err_msg = (
                            f"Cell {cell_id} attempt {attempt_count}: "
                            f"FraudConstructor error — {exc}"
                        )
                        logger.error(err_msg)
                        run_state.add_error(err_msg)
                        # Constructor errors are transient — allow retry if attempts remain
                        feedback = str(exc)
                        continue

                    # ----------------------------------------------------------
                    # Schema validation (hard fail — no retry on bad structure)
                    # ----------------------------------------------------------
                    validated, validation_error = validate_raw_variant(raw_variant.model_dump())
                    if validated is None:
                        err_msg = (
                            f"Cell {cell_id} attempt {attempt_count}: "
                            f"Schema validation failed — {validation_error}"
                        )
                        logger.error(err_msg)
                        run_state.add_error(err_msg)
                        run_state.log_event(f"{cell_id}: Schema validation FAILED — {str(validation_error)[:80]}")
                        # Hard fail: break immediately, reject cell
                        break
                    txn_count = len(validated.transactions) if hasattr(validated, "transactions") else "?"
                    run_state.log_event(f"{cell_id}: Schema validation OK — {txn_count} transactions")

                    # ----------------------------------------------------------
                    # Critic evaluation
                    # ----------------------------------------------------------
                    run_state.log_event(f"{cell_id}: Critic -> Claude evaluating variant...")
                    if not persona_ok:
                        run_state.log_event(f"{cell_id}: persona_consistency=False — {consistency_notes}")
                    try:
                        scored = await critic_agent.run(
                            variant=validated,
                            persona=persona,
                            persona_consistency=persona_ok,
                            critic_floor=config.critic_floor,
                        )
                    except Exception as exc:
                        err_msg = (
                            f"Cell {cell_id} attempt {attempt_count}: "
                            f"CriticAgent error — {exc}"
                        )
                        logger.error(err_msg)
                        run_state.add_error(err_msg)
                        feedback = str(exc)
                        continue

                    avg_score = round((scored.realism_score + scored.distinctiveness_score) / 2.0, 1)
                    if scored.passed:
                        run_state.log_event(
                            f"{cell_id}: Critic PASS score={avg_score} "
                            f"(realism={scored.realism_score} distinct={scored.distinctiveness_score})"
                        )
                        # --------------------------------------------------------
                        # Approved — record the variant
                        # --------------------------------------------------------
                        async with approved_lock:
                            approved_variants.append(scored)
                        run_state.add_scored_variant(scored)

                        matrix.complete_cell(cell_id, variant_id=scored.variant_id)
                        run_state.upsert_cell(CellStatus(
                            cell_id=cell_id,
                            dimension_values=cell.get("dimension_values", {}),
                            assigned_persona_id=getattr(persona, "persona_id", ""),
                            assigned_persona_name=persona.name,
                            status="completed",
                            attempt_count=attempt_count,
                            critic_score=avg_score,
                            variant_id=scored.variant_id,
                        ))

                        # Build a human-readable parameters summary
                        params = scored.variant_parameters
                        hop_count = params.get("hop_count", "?")
                        topology = params.get("topology", "?")
                        extraction = params.get("extraction_method", "?")
                        geo = params.get("geographic_spread", "?")
                        params_summary = (
                            f"{hop_count}-hop {topology}, "
                            f"{extraction} extraction, {geo}"
                        )

                        status = "revised" if attempt_count > 1 else "approved"
                        summary = VariantSummary(
                            variant_id=scored.variant_id,
                            persona_name=persona.name,
                            parameters_summary=params_summary,
                            critic_score=round(
                                (scored.realism_score + scored.distinctiveness_score) / 2.0, 2
                            ),
                            status=status,
                            strategy_description=scored.strategy_description[:200],
                            completed_at=datetime.now(tz=timezone.utc).isoformat(),
                            realism_score=scored.realism_score,
                            distinctiveness_score=scored.distinctiveness_score,
                            attempt_count=attempt_count,
                            passed=True,
                        )
                        run_state.update_variant(summary)
                        passed_this_cell = True
                        break

                    else:
                        # --------------------------------------------------------
                        # Failed — prepare feedback for next attempt
                        # --------------------------------------------------------
                        run_state.log_event(
                            f"{cell_id}: Critic FAIL score={avg_score} — "
                            f"{scored.feedback[:80] if scored.feedback else 'no feedback'}"
                        )
                        if not scored.persona_consistency:
                            feedback = (
                                f"PERSONA CONSISTENCY FAILURE: {consistency_notes} "
                                "Do NOT change the cell assignment parameters. "
                                "Adapt the persona's behavior to work within the cell's "
                                "structural constraints instead."
                            )
                        else:
                            feedback = scored.feedback
                        logger.info(
                            "Cell %s attempt %d rejected by critic: %s",
                            cell_id,
                            attempt_count,
                            feedback[:120],
                        )

                # ----------------------------------------------------------------
                # After attempt loop — reject cell if nothing passed
                # ----------------------------------------------------------------
                if not passed_this_cell:
                    matrix.reject_cell(cell_id)
                    run_state.upsert_cell(CellStatus(
                        cell_id=cell_id,
                        dimension_values=cell.get("dimension_values", {}),
                        assigned_persona_id=getattr(persona, "persona_id", ""),
                        assigned_persona_name=persona.name,
                        status="failed",
                        attempt_count=attempt_count,
                    ))
                    logger.warning(
                        "Cell %s permanently rejected after %d attempt(s).",
                        cell_id,
                        attempt_count,
                    )
                    # Log a rejected variant summary so the console can surface it
                    summary = VariantSummary(
                        variant_id=f"REJECTED-{cell_id}",
                        persona_name=persona.name,
                        parameters_summary=f"cell {cell_id} — all attempts failed",
                        critic_score=0.0,
                        status="rejected",
                        strategy_description="",
                        completed_at=datetime.now(tz=timezone.utc).isoformat(),
                        passed=False,
                        attempt_count=attempt_count,
                    )
                    run_state.update_variant(summary)

            except asyncio.CancelledError:
                raise  # propagate cancellation to the event loop
            except Exception as exc:
                # Catch-all: isolate any unexpected exception
                err_msg = f"Cell {cell_id}: unexpected error — {exc}"
                logger.exception(err_msg)
                run_state.add_error(err_msg)
                matrix.reject_cell(cell_id)

            finally:
                # ----------------------------------------------------------------
                # Accumulate cost from this cell's agent instances
                # ----------------------------------------------------------------
                cell_cost = 0.0
                for _agent_obj in (constructor, critic_agent):
                    try:
                        cell_cost += _agent_obj._client.cost_usd
                    except AttributeError:
                        pass
                run_state.add_cost(cell_cost)
                if cell_cost > 0:
                    run_state.log_event(f"{cell_id}: DONE — cell cost=${cell_cost:.4f} | run total=${run_state.total_cost_usd:.4f}")

                # Always decrement — balances the single increment_active() above.
                run_state.decrement_active()

                # ----------------------------------------------------------------
                # Cost cap check — signal stop if exceeded
                # ----------------------------------------------------------------
                if run_state.total_cost_usd >= config.cost_cap_usd:
                    if run_state.control_signal != "stop":
                        run_state.set_control("stop")
                        run_state.add_error(
                            f"Cost cap of ${config.cost_cap_usd} reached. Stopping run."
                        )
                        logger.warning(
                            "Cost cap $%.2f reached (current: $%.4f). Run stopped.",
                            config.cost_cap_usd,
                            run_state.total_cost_usd,
                        )
