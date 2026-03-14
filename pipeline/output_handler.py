from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from models.output_record import OutputRecord
from models.variant import ScoredVariant
from pipeline.run_state import RunState

# Base directory for all run output — relative to this file's location so it
# works regardless of where the process is started from.
_OUTPUT_BASE = Path(__file__).parent.parent / "output" / "runs"


class OutputHandler:
    """
    Writes pipeline output to disk.

    Two usage patterns:

    1. Batch (up to ~100 variants): call write_run_output() once at the end of
       a run.  All six files are written together.

    2. Incremental (1000+ variants): call append_variant() after each variant
       completes to keep memory flat, then call write_run_output() at the end
       with approved_variants=[] to write the remaining non-CSV files.  The CSV
       is already on disk from the incremental appends; write_run_output() will
       not overwrite it when approved_variants is empty.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_run_output(
        self,
        approved_variants: list[ScoredVariant],
        run_config,
        run_state: RunState,
        run_start_time: datetime | None = None,
        coverage_saturation_pct: float = 0.0,
    ) -> str:
        """
        Write all six output files for a completed run.

        Parameters
        ----------
        approved_variants:
            List of ScoredVariant objects that passed the critic.
        run_config:
            The RunConfig for this run (Pydantic model).
        run_state:
            The RunState for this run.
        run_start_time:
            When the run started (UTC).  Used to compute run_duration_seconds.
            Defaults to now if not provided (duration will be ~0s).

        Returns
        -------
        str
            Absolute path of the run folder that was created.
        """
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_folder = str(_OUTPUT_BASE / f"run_{timestamp}")
        os.makedirs(run_folder, exist_ok=True)

        all_records: list[OutputRecord] = []
        for variant in approved_variants:
            all_records.extend(self._variant_to_output_records(variant))

        # 1. config.json
        self._write_json(
            os.path.join(run_folder, "config.json"),
            run_config.model_dump(),
        )

        # 2. personas.json
        unique_persona_ids: dict[str, dict] = {}
        for variant in approved_variants:
            pid = variant.persona_id
            if pid not in unique_persona_ids:
                # Store whatever persona metadata is embedded in the variant.
                # The full Persona object is held by the runner; here we extract
                # what is available from the variant itself.
                unique_persona_ids[pid] = {"persona_id": pid}
        self._write_json(
            os.path.join(run_folder, "personas.json"),
            list(unique_persona_ids.values()),
        )

        # 3. variants.json
        variants_data = [self._scored_variant_to_dict(v) for v in approved_variants]
        self._write_json(
            os.path.join(run_folder, "variants.json"),
            variants_data,
        )

        # 4. dataset.csv — flat tabular, one row per transaction
        csv_path = os.path.join(run_folder, "dataset.csv")
        if all_records:
            df = self._records_to_dataframe(all_records)
            df.to_csv(csv_path, index=False)
        else:
            # Write an empty CSV with column headers so the file always exists.
            pd.DataFrame(columns=self._output_record_columns()).to_csv(csv_path, index=False)

        # 5. dataset.json — nested structure
        dataset_json = {
            "variants": [
                {
                    **self._scored_variant_to_dict(v),
                    "transactions": [t.model_dump() for t in v.transactions],
                }
                for v in approved_variants
            ]
        }
        self._write_json(os.path.join(run_folder, "dataset.json"), dataset_json)

        # 6. run_summary.json
        now = datetime.now(tz=timezone.utc)
        if run_start_time is None:
            run_duration_seconds = 0.0
        else:
            run_duration_seconds = (now - run_start_time).total_seconds()

        critic_scores = [
            (v.realism_score + v.distinctiveness_score) / 2.0
            for v in approved_variants
        ]
        mean_critic_score = (
            sum(critic_scores) / len(critic_scores) if critic_scores else 0.0
        )

        saturation_pct = coverage_saturation_pct

        run_summary = {
            "variant_count": len(approved_variants),
            "mean_critic_score": round(mean_critic_score, 3),
            "coverage_saturation_pct": saturation_pct,
            "persona_count": len(unique_persona_ids),
            "total_transactions": len(all_records),
            "run_duration_seconds": round(run_duration_seconds, 1),
            "total_cost_usd": round(run_state.total_cost_usd, 4),
            "revisions_count": run_state.revisions_count,
            "rejections_count": run_state.rejections_count,
            "timestamp": now.isoformat(),
        }
        self._write_json(os.path.join(run_folder, "run_summary.json"), run_summary)

        return run_folder

    def append_variant(self, variant: ScoredVariant, run_folder: str) -> None:
        """
        Incrementally append one variant's transactions to the run's CSV.

        Opens the file in append mode so the full dataset is never held in
        memory.  If the file does not yet exist, writes the header row first.

        Intended for large runs (1000+ variants) where writing all records at
        the end would consume too much RAM.
        """
        csv_path = os.path.join(run_folder, "dataset.csv")
        records = self._variant_to_output_records(variant)
        if not records:
            return

        df = self._records_to_dataframe(records)
        write_header = not os.path.exists(csv_path)
        df.to_csv(csv_path, mode="a", index=False, header=write_header)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _variant_to_output_records(self, variant: ScoredVariant) -> list[OutputRecord]:
        """
        Flatten a ScoredVariant into one OutputRecord per transaction.

        Each record carries both the transaction fields and the variant/persona
        metadata required by the labeled dataset schema.
        """
        critic_scores = {
            "realism": variant.realism_score,
            "distinctiveness": variant.distinctiveness_score,
            "passed": variant.passed,
        }
        records: list[OutputRecord] = []
        for txn in variant.transactions:
            record = OutputRecord(
                # Transaction fields
                transaction_id=txn.transaction_id,
                timestamp=txn.timestamp,
                amount=txn.amount,
                sender_account_id=txn.sender_account_id,
                receiver_account_id=txn.receiver_account_id,
                merchant_category=txn.merchant_category,
                channel=txn.channel,
                is_fraud=txn.is_fraud,
                fraud_role=txn.fraud_role,
                # Variant / persona metadata
                variant_id=variant.variant_id,
                persona_id=variant.persona_id,
                persona_name="",  # populated downstream when Persona objects are available
                fraud_type=variant.fraud_type,
                variant_parameters=variant.variant_parameters,
                # Critic evaluation
                critic_scores=critic_scores,
            )
            records.append(record)
        return records

    def _records_to_dataframe(self, records: list[OutputRecord]) -> pd.DataFrame:
        """Convert a list of OutputRecord objects to a flat DataFrame."""
        rows = []
        for rec in records:
            row = rec.model_dump()
            # Flatten nested dicts so CSV stays flat/tabular.
            vp = row.pop("variant_parameters", {}) or {}
            cs = row.pop("critic_scores", {}) or {}
            for k, v in vp.items():
                row[f"param_{k}"] = v
            for k, v in cs.items():
                row[f"critic_{k}"] = v
            rows.append(row)
        return pd.DataFrame(rows)

    def _output_record_columns(self) -> list[str]:
        """Return column names for an empty header-only CSV."""
        base = list(OutputRecord.model_fields.keys())
        # Remove dict fields; they will be expanded by _records_to_dataframe.
        base = [c for c in base if c not in ("variant_parameters", "critic_scores")]
        return base

    @staticmethod
    def _scored_variant_to_dict(variant: ScoredVariant) -> dict:
        """Serialize a ScoredVariant to a plain dict (without transactions list)."""
        d = variant.model_dump()
        # Transactions are written separately in dataset.json; strip them from
        # the top-level variants.json entry to avoid duplication.
        d.pop("transactions", None)
        return d

    @staticmethod
    def _write_json(path: str, data: Any) -> None:
        """Write data to a JSON file with 2-space indentation."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
