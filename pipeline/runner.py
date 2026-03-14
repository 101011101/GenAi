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
from pipeline.coverage_matrix import CoverageMatrix
from pipeline.output_handler import OutputHandler
from pipeline.run_state import RunState, VariantSummary
from utils.schema_validator import validate_raw_variant

logger = logging.getLogger(__name__)


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
        matrix_out: list | None = None,
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
        # Demo mode guard — cap cells, force fidelity 3, use Haiku for speed
        # ------------------------------------------------------------------
        self._agent_model = "claude-haiku-4-5-20251001" if config.demo_mode else None
        if config.demo_mode:
            config = config.model_copy(update={"fidelity_level": 3})

        # ------------------------------------------------------------------
        # Step 1 — Orchestrate
        # ------------------------------------------------------------------
        run_state.set_phase("Orchestrating")
        orchestrator_output = await OrchestratorAgent().run(config)

        cells: list[dict] = orchestrator_output.coverage_cells

        # Demo mode: cap at 12 cells
        if config.demo_mode:
            cells = cells[:12]

        # ------------------------------------------------------------------
        # Step 2 — Build coverage matrix
        # ------------------------------------------------------------------
        matrix = CoverageMatrix(
            orchestrator_output.variation_dimensions,
            cells,
        )

        if matrix_out is not None:
            matrix_out.append(matrix)

        # ------------------------------------------------------------------
        # Step 3 — Generate personas
        # ------------------------------------------------------------------
        run_state.set_phase("Generating personas")
        personas: list[Persona] = await PersonaGeneratorAgent(model=self._agent_model).run(
            config.fraud_description, config
        )

        if personas_out is not None:
            personas_out.extend(personas)

        # ------------------------------------------------------------------
        # Step 4 — Set totals and start variant generation
        # ------------------------------------------------------------------
        run_state.variants_total = len(cells)

        run_state.set_phase("Generating variants")

        semaphore = asyncio.Semaphore(config.max_parallel)
        approved_variants: list[ScoredVariant] = (
            approved_variants_out if approved_variants_out is not None else []
        )
        approved_lock = asyncio.Lock()

        tasks = [
            self._process_cell(
                cell=cell,
                personas=personas,
                matrix=matrix,
                config=config,
                run_state=run_state,
                semaphore=semaphore,
                approved_variants=approved_variants,
                approved_lock=approved_lock,
                extra_feedback="",
            )
            for cell in cells
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

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
                    logger.info(
                        "Coverage saturation %.1f%% — running second pass on %d cells.",
                        saturation * 100,
                        len(underrepresented),
                    )
                    second_pass_tasks = [
                        self._process_cell(
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
                        )
                        for cell in underrepresented
                    ]
                    await asyncio.gather(*second_pass_tasks, return_exceptions=True)

        # ------------------------------------------------------------------
        # Step 7 — Compile dataset
        # ------------------------------------------------------------------
        run_state.set_phase("Compiling dataset")

        saturation = matrix.check_saturation()
        folder_path = OutputHandler().write_run_output(
            approved_variants=approved_variants,
            run_config=config,
            run_state=run_state,
            run_start_time=run_start_time,
            coverage_saturation_pct=round(saturation * 100, 1),
        )

        # ------------------------------------------------------------------
        # Step 8 — Mark complete
        # ------------------------------------------------------------------
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

            run_state.increment_active()

            # ----------------------------------------------------------------
            # Track cost before entering the attempt loop
            # ----------------------------------------------------------------
            # We create dedicated agent instances per cell so their LLMClient
            # token counters are isolated.  This lets us compute the cost delta
            # per cell by reading cost_usd after all calls complete.
            constructor = FraudConstructorAgent(model=self._agent_model)
            critic_agent = CriticAgent(model=self._agent_model)

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
                    try:
                        raw_variant = await constructor.run(
                            persona=persona,
                            cell_assignment=cell,
                            critic_feedback=feedback,
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
                        # Hard fail: break immediately, reject cell
                        break

                    # ----------------------------------------------------------
                    # Critic evaluation
                    # ----------------------------------------------------------
                    try:
                        scored = await critic_agent.run(
                            variant=validated,
                            persona=persona,
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

                    if scored.passed:
                        # --------------------------------------------------------
                        # Approved — record the variant
                        # --------------------------------------------------------
                        async with approved_lock:
                            approved_variants.append(scored)

                        matrix.complete_cell(cell_id, variant_id=scored.variant_id)

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
                        )
                        run_state.update_variant(summary)
                        passed_this_cell = True
                        break

                    else:
                        # --------------------------------------------------------
                        # Failed — prepare feedback for next attempt
                        # --------------------------------------------------------
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
                    )
                    run_state.update_variant(summary)

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
                cell_cost = constructor._client.cost_usd + critic_agent._client.cost_usd
                run_state.add_cost(cell_cost)

                # Decrement active count (update_variant also decrements, but only
                # on the approved path — decrement_active() handles the other paths).
                if not passed_this_cell:
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
