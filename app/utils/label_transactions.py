"""Deterministic transaction labeler.

Given an unlabeled list of transaction dicts and a set of fraud_account_ids,
traces the transfer graph and stamps fraud_role + is_fraud on every transaction.

This removes the labeling responsibility from the LLM entirely. The LLM only
needs to declare which accounts are part of the fraud network; Python handles
the graph traversal and label assignment.

Label rules:
  placement     — receiver is in fraud network, sender is NOT (entry edge)
  hop_N_of_M    — both sender and receiver are in fraud network (internal edge)
                  N = BFS depth layer from entry nodes; M = max depth before exit
  extraction    — sender is in fraud network, receiver is NOT (exit edge)
  cover_activity — neither account is in fraud network (external edge)

  is_fraud=True  for placement, hop_*, extraction
  is_fraud=False for cover_activity
"""
from __future__ import annotations

from collections import deque


def label_transactions(
    transactions: list[dict],
    fraud_account_ids: set[str],
) -> list[dict]:
    """Stamp fraud_role and is_fraud on every transaction dict in-place.

    Parameters
    ----------
    transactions:
        List of transaction dicts. Each must have at least
        sender_account_id, receiver_account_id, timestamp.
        fraud_role and is_fraud are written (overwriting any existing values).
    fraud_account_ids:
        Set of account IDs that are part of the fraud network.
        All other accounts are treated as external (cover activity or victim).

    Returns
    -------
    The same list with fraud_role and is_fraud set on every transaction.
    """
    if not fraud_account_ids:
        for txn in transactions:
            txn["fraud_role"] = "cover_activity"
            txn["is_fraud"] = False
        return transactions

    # Sort by timestamp for deterministic BFS ordering
    sorted_txns = sorted(transactions, key=lambda t: t.get("timestamp", ""))

    # ------------------------------------------------------------------
    # Step 1: Classify each transaction into one of four buckets
    # ------------------------------------------------------------------
    entry_txn_ids: set[str] = set()    # placement candidates
    exit_txn_ids: set[str] = set()     # extraction candidates
    internal_txn_ids: set[str] = set() # hop candidates
    external_txn_ids: set[str] = set() # cover_activity candidates

    for txn in sorted_txns:
        sender_in = txn["sender_account_id"] in fraud_account_ids
        receiver_in = txn["receiver_account_id"] in fraud_account_ids
        tid = txn["transaction_id"]

        if not sender_in and receiver_in:
            entry_txn_ids.add(tid)
        elif sender_in and not receiver_in:
            exit_txn_ids.add(tid)
        elif sender_in and receiver_in:
            internal_txn_ids.add(tid)
        else:
            external_txn_ids.add(tid)

    # ------------------------------------------------------------------
    # Step 2: BFS to assign hop depth to internal transactions
    # ------------------------------------------------------------------
    # Build adjacency: fraud_account → list of (receiver_account, txn_id)
    # Only for internal edges (both endpoints in fraud network)
    adjacency: dict[str, list[tuple[str, str]]] = {acct: [] for acct in fraud_account_ids}
    for txn in sorted_txns:
        if txn["transaction_id"] in internal_txn_ids:
            adjacency.setdefault(txn["sender_account_id"], []).append(
                (txn["receiver_account_id"], txn["transaction_id"])
            )

    # Entry accounts: accounts that receive placement transactions
    entry_accounts: set[str] = set()
    for txn in sorted_txns:
        if txn["transaction_id"] in entry_txn_ids:
            entry_accounts.add(txn["receiver_account_id"])

    # BFS from all entry accounts simultaneously; track depth per txn_id
    txn_depth: dict[str, int] = {}
    visited_accounts: set[str] = set(entry_accounts)
    queue: deque[tuple[str, int]] = deque((acct, 0) for acct in entry_accounts)

    while queue:
        account, depth = queue.popleft()
        for next_account, txn_id in adjacency.get(account, []):
            if txn_id not in txn_depth:
                txn_depth[txn_id] = depth + 1
                if next_account not in visited_accounts:
                    visited_accounts.add(next_account)
                    queue.append((next_account, depth + 1))

    # Any internal txn not reached by BFS (isolated fraud edge): depth = 1
    for tid in internal_txn_ids:
        if tid not in txn_depth:
            txn_depth[tid] = 1

    max_depth = max(txn_depth.values()) if txn_depth else 0

    # ------------------------------------------------------------------
    # Step 3: Stamp labels
    # ------------------------------------------------------------------
    for txn in transactions:
        tid = txn["transaction_id"]

        if tid in external_txn_ids:
            txn["fraud_role"] = "cover_activity"
            txn["is_fraud"] = False

        elif tid in entry_txn_ids:
            txn["fraud_role"] = "placement"
            txn["is_fraud"] = True

        elif tid in exit_txn_ids:
            txn["fraud_role"] = "extraction"
            txn["is_fraud"] = True

        elif tid in internal_txn_ids:
            depth = txn_depth[tid]
            m = max_depth if max_depth > 0 else 1
            txn["fraud_role"] = f"hop_{depth}_of_{m}"
            txn["is_fraud"] = True

        else:
            # Fallback: transaction_id not found in any bucket (shouldn't happen)
            txn["fraud_role"] = "cover_activity"
            txn["is_fraud"] = False

    return transactions


def detect_topology(transactions: list[dict], fraud_account_ids: set[str]) -> str:
    """Detect chain/fan_out/hybrid from the actual transaction graph."""
    out_edges: dict[str, set[str]] = {}
    for txn in transactions:
        s = txn["sender_account_id"]
        r = txn["receiver_account_id"]
        if s in fraud_account_ids and r in fraud_account_ids:
            out_edges.setdefault(s, set()).add(r)

    if not out_edges:
        return "chain"

    has_fanout = any(len(v) > 1 for v in out_edges.values())
    has_chain_node = any(len(v) == 1 for v in out_edges.values())

    if has_fanout and has_chain_node:
        return "hybrid"
    elif has_fanout:
        return "fan_out"
    return "chain"
