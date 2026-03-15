"""Deterministic variant constraint checker.

Replaces the LLM step-5 self-review in FraudConstructorAgent.
All checks are pure Python — no LLM calls.
"""
from __future__ import annotations

from datetime import datetime, timezone


def check_variant_constraints(
    variant_data: dict,
    persona_analysis: dict,
    network_plan: dict,
    rail_constraints: dict,
) -> list[str]:
    """Check a generated variant against hard constraints.

    Parameters
    ----------
    variant_data:
        The step-4 output dict (same schema as _SELF_REVIEW_SCHEMA).
    persona_analysis:
        Step-1 output dict; must contain a "constraint_audit" sub-dict.
    network_plan:
        Step-2 output dict (used for topology consistency check).
    rail_constraints:
        Loaded payment_rail_constraints.json dict.

    Returns
    -------
    list[str]
        Violation descriptions. Empty list means all checks passed.
    """
    violations: list[str] = []
    audit = persona_analysis.get("constraint_audit", {})
    transactions: list[dict] = variant_data.get("transactions", [])
    fraud_ids: set[str] = set(variant_data.get("fraud_account_ids", []))
    params: dict = variant_data.get("variant_parameters", {})

    # ------------------------------------------------------------------
    # 1. Hop count ≤ max_hop_count
    # ------------------------------------------------------------------
    max_hops = audit.get("max_hop_count")
    actual_hops = params.get("hop_count")
    if max_hops is not None and actual_hops is not None:
        try:
            if int(actual_hops) > int(max_hops):
                violations.append(
                    f"hop_count={actual_hops} exceeds constraint_audit.max_hop_count={max_hops}"
                )
        except (ValueError, TypeError):
            pass

    # ------------------------------------------------------------------
    # 2. Crypto channel/extraction when crypto_allowed=false
    # ------------------------------------------------------------------
    if audit.get("crypto_allowed") is False:
        for txn in transactions:
            if "crypto" in str(txn.get("channel", "")).lower():
                violations.append(
                    f"txn {txn.get('transaction_id')}: channel='{txn['channel']}' "
                    "violates constraint_audit.crypto_allowed=false"
                )
                break
        if "crypto" in str(params.get("extraction_method", "")).lower():
            violations.append(
                f"extraction_method='{params['extraction_method']}' "
                "violates constraint_audit.crypto_allowed=false"
            )

    # ------------------------------------------------------------------
    # 3. International routing when international_allowed=false
    # ------------------------------------------------------------------
    if audit.get("international_allowed") is False:
        geo = str(params.get("geographic_spread", "")).lower()
        if any(w in geo for w in ("international", "cross-border", "swift", "offshore")):
            violations.append(
                f"geographic_spread='{params['geographic_spread']}' "
                "violates constraint_audit.international_allowed=false"
            )

    # ------------------------------------------------------------------
    # 4. Allowed channels
    # ------------------------------------------------------------------
    allowed_channels = audit.get("allowed_channels")
    if allowed_channels:
        allowed_lower = {str(c).lower() for c in allowed_channels}
        for txn in transactions:
            ch = str(txn.get("channel", "")).lower()
            if ch and ch not in allowed_lower:
                violations.append(
                    f"txn {txn.get('transaction_id')}: channel='{txn['channel']}' "
                    f"not in constraint_audit.allowed_channels"
                )

    # ------------------------------------------------------------------
    # 5. Inter-hop timing gaps (min/max)
    # ------------------------------------------------------------------
    min_interval = audit.get("min_timing_interval_hrs")
    max_interval = audit.get("max_timing_interval_hrs")
    if min_interval is not None or max_interval is not None:
        fraud_txns = [
            t for t in transactions
            if t.get("sender_account_id") in fraud_ids
            or t.get("receiver_account_id") in fraud_ids
        ]
        sorted_fraud = _sort_by_timestamp(fraud_txns)
        for i in range(1, len(sorted_fraud)):
            prev_ts = _parse_ts(sorted_fraud[i - 1].get("timestamp", ""))
            curr_ts = _parse_ts(sorted_fraud[i].get("timestamp", ""))
            if prev_ts is None or curr_ts is None:
                continue
            gap_hrs = (curr_ts - prev_ts).total_seconds() / 3600.0
            tid = sorted_fraud[i].get("transaction_id", f"txn[{i}]")
            if min_interval is not None and gap_hrs < float(min_interval):
                violations.append(
                    f"txn {tid}: inter-hop gap {gap_hrs:.2f}h < "
                    f"min_timing_interval_hrs={min_interval}"
                )
            if max_interval is not None and gap_hrs > float(max_interval):
                violations.append(
                    f"txn {tid}: inter-hop gap {gap_hrs:.2f}h > "
                    f"max_timing_interval_hrs={max_interval}"
                )

    # ------------------------------------------------------------------
    # 6. ACH minimum settlement gap (1h floor)
    # ------------------------------------------------------------------
    sorted_all = _sort_by_timestamp(transactions)
    for i in range(1, len(sorted_all)):
        prev = sorted_all[i - 1]
        if str(prev.get("channel", "")).upper() != "ACH":
            continue
        curr = sorted_all[i]
        prev_ts = _parse_ts(prev.get("timestamp", ""))
        curr_ts = _parse_ts(curr.get("timestamp", ""))
        if prev_ts and curr_ts:
            gap_hrs = (curr_ts - prev_ts).total_seconds() / 3600.0
            if gap_hrs < 1.0:
                violations.append(
                    f"txn {curr.get('transaction_id')}: follows ACH txn "
                    f"{prev.get('transaction_id')} with only {gap_hrs:.2f}h gap "
                    "(ACH minimum settlement is 1h)"
                )

    # ------------------------------------------------------------------
    # 7. Zelle per-transaction limit
    # ------------------------------------------------------------------
    zelle_max = float(
        rail_constraints.get("Zelle", {}).get("max_per_transaction", 2500)
    )
    for txn in transactions:
        if str(txn.get("channel", "")).lower() == "zelle":
            try:
                amt = float(txn.get("amount", 0))
                if amt > zelle_max:
                    violations.append(
                        f"txn {txn.get('transaction_id')}: Zelle amount ${amt:,.2f} "
                        f"exceeds per-transaction limit ${zelle_max:,.0f}"
                    )
            except (ValueError, TypeError):
                pass

    # ------------------------------------------------------------------
    # 8. Cover activity count vs cover_activity field value
    # ------------------------------------------------------------------
    cover_level = str(params.get("cover_activity", "none")).lower()
    cover_count = sum(
        1 for t in transactions
        if t.get("sender_account_id") not in fraud_ids
        and t.get("receiver_account_id") not in fraud_ids
    )
    if cover_level == "none" and cover_count > 0:
        violations.append(
            f"cover_activity='none' but {cover_count} cover transaction(s) present"
        )
    elif cover_level == "low" and cover_count == 0:
        violations.append(
            "cover_activity='low' requires ≥1 cover transaction but found 0"
        )
    elif cover_level == "high" and cover_count < 4:
        violations.append(
            f"cover_activity='high' requires ≥4 cover transactions but found {cover_count}"
        )

    return violations


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_ts(ts_str: str) -> datetime | None:
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _sort_by_timestamp(transactions: list[dict]) -> list[dict]:
    def _key(t: dict) -> datetime:
        ts = _parse_ts(t.get("timestamp", ""))
        return ts if ts is not None else datetime.max.replace(tzinfo=timezone.utc)
    return sorted(transactions, key=_key)
