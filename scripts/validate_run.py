#!/usr/bin/env python3
"""Validate the output of a FraudGen pipeline run.

Usage:
    python scripts/validate_run.py output/runs/run_20260314_153045
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Allow imports from project root when run as a script.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from models.run_config import RunConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Expected files in every run folder
# ---------------------------------------------------------------------------
EXPECTED_FILES = [
    "config.json",
    "personas.json",
    "variants.json",
    "dataset.csv",
    "dataset.json",
    "run_summary.json",
]

SCORED_VARIANT_REQUIRED = {
    "variant_id",
    "fraud_type",
    "persona_id",
    "strategy_description",
    "variant_parameters",
    "realism_score",
    "distinctiveness_score",
    "persona_consistency",
    "label_correctness",
    "passed",
    "feedback",
}

TRANSACTION_REQUIRED = {
    "transaction_id",
    "timestamp",
    "amount",
    "sender_account_id",
    "receiver_account_id",
    "merchant_category",
    "channel",
    "is_fraud",
    "fraud_role",
}

RUN_SUMMARY_KEYS = {
    "variant_count": int,
    "mean_critic_score": (int, float),
    "coverage_saturation_pct": (int, float),
    "persona_count": int,
    "total_transactions": int,
    "run_duration_seconds": (int, float),
    "total_cost_usd": (int, float),
    "revisions_count": int,
    "rejections_count": int,
    "timestamp": str,
}

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

class CheckResult:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []  # (status, name, detail)

    def ok(self, name: str, detail: str = "") -> None:
        self.results.append(("PASS", name, detail))

    def fail(self, name: str, detail: str = "") -> None:
        self.results.append(("FAIL", name, detail))

    def warn(self, name: str, detail: str = "") -> None:
        self.results.append(("WARN", name, detail))

    def print_report(self) -> int:
        """Print a checklist and return exit code (0 = all pass, 1 = any fail)."""
        markers = {"PASS": "\u2705", "FAIL": "\u274c", "WARN": "\u26a0\ufe0f"}
        passes = fails = warns = 0
        for status, name, detail in self.results:
            suffix = f"  ({detail})" if detail else ""
            print(f"  {markers[status]} {status}  {name}{suffix}")
            if status == "PASS":
                passes += 1
            elif status == "FAIL":
                fails += 1
            else:
                warns += 1

        print()
        print(f"Summary: {passes} passed, {fails} failed, {warns} warnings")
        return 1 if fails > 0 else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> object:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _parse_iso(ts: str) -> datetime | None:
    """Try to parse an ISO-8601 timestamp string."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


_HOP_RE = re.compile(r"^hop_(\d+)_of_(\d+)$")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_file_presence(run_dir: Path, cr: CheckResult) -> bool:
    all_present = True
    for fname in EXPECTED_FILES:
        if (run_dir / fname).exists():
            cr.ok(f"file exists: {fname}")
        else:
            cr.fail(f"file exists: {fname}", "missing")
            all_present = False
    return all_present


def check_config_schema(run_dir: Path, cr: CheckResult) -> RunConfig | None:
    try:
        data = _load_json(run_dir / "config.json")
        cfg = RunConfig(**data)
        cr.ok("config.json schema (RunConfig)")
        return cfg
    except Exception as exc:
        cr.fail("config.json schema (RunConfig)", str(exc))
        return None


def check_variants_schema(run_dir: Path, cr: CheckResult) -> list[dict] | None:
    try:
        variants = _load_json(run_dir / "variants.json")
        assert isinstance(variants, list), "variants.json must be a JSON array"
        for i, v in enumerate(variants):
            missing = SCORED_VARIANT_REQUIRED - set(v.keys())
            if missing:
                cr.fail(f"variants.json[{i}] schema", f"missing keys: {missing}")
                return None
        cr.ok("variants.json schema", f"{len(variants)} variants")
        return variants
    except Exception as exc:
        cr.fail("variants.json schema", str(exc))
        return None


def check_dataset_json_schema(run_dir: Path, cr: CheckResult) -> dict | None:
    try:
        data = _load_json(run_dir / "dataset.json")
        assert isinstance(data, dict) and "variants" in data, "must have 'variants' key"
        for i, v in enumerate(data["variants"]):
            assert "transactions" in v, f"variant {i} missing 'transactions'"
            for j, t in enumerate(v["transactions"]):
                missing = TRANSACTION_REQUIRED - set(t.keys())
                if missing:
                    cr.fail(f"dataset.json variants[{i}].transactions[{j}]", f"missing: {missing}")
                    return None
        cr.ok("dataset.json schema", f"{len(data['variants'])} variants")
        return data
    except Exception as exc:
        cr.fail("dataset.json schema", str(exc))
        return None


def check_dataset_csv(run_dir: Path, cr: CheckResult) -> list[dict] | None:
    """Parse dataset.csv and return rows as list of dicts (or None on failure)."""
    try:
        with open(run_dir / "dataset.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            rows = list(reader)

        base_cols = {
            "transaction_id", "timestamp", "amount", "sender_account_id",
            "receiver_account_id", "merchant_category", "channel", "is_fraud",
            "fraud_role", "variant_id", "persona_id", "persona_name", "fraud_type",
        }
        missing = base_cols - set(columns)
        if missing:
            cr.fail("dataset.csv base columns", f"missing: {missing}")
            return None

        has_param = any(c.startswith("param_") for c in columns)
        has_critic = any(c.startswith("critic_") for c in columns)
        if not has_param:
            cr.warn("dataset.csv param_* columns", "no param_ columns found")
        if not has_critic:
            cr.warn("dataset.csv critic_* columns", "no critic_ columns found")

        cr.ok("dataset.csv parseable", f"{len(rows)} rows, {len(columns)} columns")
        return rows
    except Exception as exc:
        cr.fail("dataset.csv parseable", str(exc))
        return None


def check_run_summary(run_dir: Path, cr: CheckResult) -> dict | None:
    try:
        summary = _load_json(run_dir / "run_summary.json")
        assert isinstance(summary, dict), "must be a JSON object"
        for key, expected_type in RUN_SUMMARY_KEYS.items():
            if key not in summary:
                cr.fail("run_summary.json keys", f"missing key: {key}")
                return None
            if not isinstance(summary[key], expected_type):
                cr.fail("run_summary.json types", f"{key}: expected {expected_type}, got {type(summary[key]).__name__}")
                return None
        cr.ok("run_summary.json schema", f"{len(summary)} keys")
        return summary
    except Exception as exc:
        cr.fail("run_summary.json schema", str(exc))
        return None


# --- Referential integrity ---

def check_referential_integrity(
    variants: list[dict],
    personas_data: list[dict],
    dataset_json: dict,
    csv_rows: list[dict],
    cr: CheckResult,
) -> None:
    persona_ids_in_file = {p["persona_id"] for p in personas_data}
    persona_ids_in_variants = {v["persona_id"] for v in variants}
    missing = persona_ids_in_variants - persona_ids_in_file
    if missing:
        cr.fail("persona_id refs (variants -> personas.json)", f"missing: {missing}")
    else:
        cr.ok("persona_id refs (variants -> personas.json)")

    variant_ids_json = {v["variant_id"] for v in variants}
    variant_ids_csv = {row["variant_id"] for row in csv_rows} if csv_rows else set()
    csv_extra = variant_ids_csv - variant_ids_json
    csv_missing = variant_ids_json - variant_ids_csv
    if csv_extra:
        cr.fail("variant_id refs (csv -> variants.json)", f"csv has extra: {csv_extra}")
    elif csv_missing:
        cr.warn("variant_id refs (csv -> variants.json)", f"csv missing (may be ok if 0 txns): {csv_missing}")
    else:
        cr.ok("variant_id refs (csv <-> variants.json)")

    # Transaction counts: dataset.csv vs dataset.json
    csv_counts: dict[str, int] = Counter(row["variant_id"] for row in csv_rows) if csv_rows else {}
    json_counts: dict[str, int] = {}
    for v in dataset_json.get("variants", []):
        json_counts[v["variant_id"]] = len(v.get("transactions", []))

    mismatches = []
    for vid in set(csv_counts) | set(json_counts):
        c = csv_counts.get(vid, 0)
        j = json_counts.get(vid, 0)
        if c != j:
            mismatches.append(f"{vid}: csv={c} json={j}")
    if mismatches:
        cr.fail("txn counts (csv vs dataset.json)", "; ".join(mismatches[:5]))
    else:
        cr.ok("txn counts (csv vs dataset.json)")


# --- Transaction consistency ---

def check_transaction_consistency(dataset_json: dict, cr: CheckResult) -> None:
    all_ok = True
    any_variant_no_fraud = False

    for v in dataset_json.get("variants", []):
        vid = v.get("variant_id", "?")
        txns = v.get("transactions", [])

        # Amounts > 0
        for t in txns:
            if t.get("amount", 0) <= 0:
                cr.fail(f"amount > 0 [{vid}]", f"txn {t.get('transaction_id')} amount={t.get('amount')}")
                all_ok = False
                break

        # Timestamps valid ISO and ordered for fraud txns
        fraud_txns = [t for t in txns if t.get("is_fraud")]
        if not fraud_txns:
            any_variant_no_fraud = True
            cr.fail(f"at least 1 fraud txn [{vid}]", "no fraud transactions")
            all_ok = False
            continue

        timestamps_valid = True
        parsed_ts: list[tuple[int, datetime]] = []
        for i, t in enumerate(fraud_txns):
            dt = _parse_iso(t.get("timestamp", ""))
            if dt is None:
                cr.fail(f"ISO timestamp [{vid}]", f"txn {t.get('transaction_id')}: {t.get('timestamp')}")
                timestamps_valid = False
                all_ok = False
                break
            parsed_ts.append((i, dt))

        if timestamps_valid and len(parsed_ts) > 1:
            for k in range(1, len(parsed_ts)):
                if parsed_ts[k][1] < parsed_ts[k - 1][1]:
                    cr.fail(f"fraud txn timestamp order [{vid}]", "timestamps not in order")
                    all_ok = False
                    break

        # Hop chain connectivity
        hop_txns: list[tuple[int, int, dict]] = []
        for t in fraud_txns:
            role = t.get("fraud_role", "")
            m = _HOP_RE.match(role)
            if m:
                hop_txns.append((int(m.group(1)), int(m.group(2)), t))

        if hop_txns:
            hop_txns.sort(key=lambda x: x[0])
            for k in range(1, len(hop_txns)):
                prev_receiver = hop_txns[k - 1][2].get("receiver_account_id")
                curr_sender = hop_txns[k][2].get("sender_account_id")
                if prev_receiver != curr_sender:
                    cr.fail(
                        f"hop chain connectivity [{vid}]",
                        f"hop {hop_txns[k-1][0]}->hop {hop_txns[k][0]}: "
                        f"receiver {prev_receiver} != sender {curr_sender}",
                    )
                    all_ok = False
                    break

    if all_ok:
        cr.ok("transaction consistency (amounts, timestamps, hops)")
    if any_variant_no_fraud:
        pass  # already reported per-variant


# --- Critic score sanity ---

def check_critic_scores(variants: list[dict], config: RunConfig | None, summary: dict | None, cr: CheckResult) -> None:
    all_ok = True
    scores: list[float] = []

    for v in variants:
        realism = v.get("realism_score", 0)
        distinct = v.get("distinctiveness_score", 0)

        if not (1.0 <= realism <= 10.0):
            cr.fail("critic score range", f"{v.get('variant_id')}: realism_score={realism}")
            all_ok = False
        if not (1.0 <= distinct <= 10.0):
            cr.fail("critic score range", f"{v.get('variant_id')}: distinctiveness_score={distinct}")
            all_ok = False

        avg = (realism + distinct) / 2.0
        scores.append(avg)

        if config and v.get("passed"):
            if avg < config.critic_floor:
                cr.fail(
                    "passed variant meets critic_floor",
                    f"{v.get('variant_id')}: avg={avg:.2f} < floor={config.critic_floor}",
                )
                all_ok = False

    if all_ok:
        cr.ok("critic scores in range & passed variants meet floor")

    # Mean check
    if summary and scores:
        actual_mean = sum(scores) / len(scores)
        reported_mean = summary.get("mean_critic_score", 0)
        if abs(actual_mean - reported_mean) > 0.01:
            cr.fail(
                "mean_critic_score matches actual",
                f"reported={reported_mean}, actual={actual_mean:.3f}",
            )
        else:
            cr.ok("mean_critic_score matches actual", f"{reported_mean}")


# --- Coverage diversity ---

def check_coverage_diversity(variants: list[dict], cr: CheckResult) -> None:
    if not variants:
        cr.warn("coverage diversity", "no variants to check")
        return

    param_keys = ["hop_count", "topology", "extraction_method"]
    distinct: dict[str, set] = {k: set() for k in param_keys}
    for v in variants:
        params = v.get("variant_parameters", {}) or {}
        for k in param_keys:
            val = params.get(k)
            if val is not None:
                distinct[k].add(str(val))

    detail_parts = []
    for k in param_keys:
        detail_parts.append(f"{k}={len(distinct[k])}")

    total_distinct = sum(len(s) for s in distinct.values())
    if total_distinct <= len(param_keys):
        cr.warn("coverage diversity", f"low diversity: {', '.join(detail_parts)}")
    else:
        cr.ok("coverage diversity", ", ".join(detail_parts))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def validate_run(run_dir: Path) -> int:
    cr = CheckResult()
    print(f"Validating run: {run_dir}\n")

    # 1. File presence
    if not check_file_presence(run_dir, cr):
        print()
        return cr.print_report()

    # 2. Schema validation
    config = check_config_schema(run_dir, cr)

    variants = check_variants_schema(run_dir, cr)

    dataset_json = check_dataset_json_schema(run_dir, cr)

    csv_rows = check_dataset_csv(run_dir, cr)

    summary = check_run_summary(run_dir, cr)

    # Load personas for referential integrity
    try:
        personas_data = _load_json(run_dir / "personas.json")
    except Exception:
        personas_data = []

    # 3. Referential integrity
    if variants is not None and csv_rows is not None and dataset_json is not None:
        check_referential_integrity(variants, personas_data, dataset_json, csv_rows, cr)

    # 4. Transaction consistency
    if dataset_json is not None:
        check_transaction_consistency(dataset_json, cr)

    # 5. Critic score sanity
    if variants is not None:
        check_critic_scores(variants, config, summary, cr)

    # 6. Coverage diversity
    if variants is not None:
        check_coverage_diversity(variants, cr)

    print()
    return cr.print_report()


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <run_folder_path>")
        sys.exit(2)

    run_dir = Path(sys.argv[1])
    if not run_dir.is_dir():
        print(f"Error: {run_dir} is not a directory")
        sys.exit(2)

    exit_code = validate_run(run_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
