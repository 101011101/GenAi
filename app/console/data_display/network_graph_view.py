"""
Network graph visualization for the fraud data generation console.

Renders mule network graphs side by side using NetworkX + Matplotlib.
Falls back gracefully if dependencies are not installed.
No LLM calls or agent imports.
"""
from __future__ import annotations

import math
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------
try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    _MPL_AVAILABLE = True
except ImportError:
    _MPL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_transactions(variant: Any) -> list[dict]:
    """Extract transactions from a variant object or dict."""
    if variant is None:
        return []
    if isinstance(variant, dict):
        txns = variant.get("transactions", [])
    else:
        txns = getattr(variant, "transactions", [])

    result = []
    for t in txns:
        if isinstance(t, dict):
            result.append(t)
        else:
            result.append(t.__dict__ if hasattr(t, "__dict__") else {})
    return result


def _get_critic_score(variant: Any) -> float:
    """Return the best available critic score for a variant."""
    if variant is None:
        return 0.0
    if isinstance(variant, dict):
        return float(
            variant.get("realism_score")
            or variant.get("critic_score")
            or variant.get("score", 0.0)
        )
    return float(
        getattr(variant, "realism_score", None)
        or getattr(variant, "critic_score", None)
        or 0.0
    )


def _get_variant_id(variant: Any) -> str:
    if isinstance(variant, dict):
        return str(variant.get("variant_id", "?"))
    return str(getattr(variant, "variant_id", "?"))


def _get_hop_count(variant: Any) -> int:
    """Extract hop_count from variant_parameters for structural diversity selection."""
    if isinstance(variant, dict):
        params = variant.get("variant_parameters", {})
    else:
        params = getattr(variant, "variant_parameters", {}) or {}
    return int(params.get("hop_count", 0))


def _select_diverse_variants(variants: list, max_n: int = 4) -> list:
    """
    Select up to max_n variants with highest critic scores from structurally
    distinct hop_count buckets.
    """
    if not variants:
        return []

    # Sort by critic score descending
    scored = sorted(variants, key=_get_critic_score, reverse=True)

    selected: list = []
    used_hops: set = set()

    # First pass: prefer different hop counts
    for v in scored:
        hc = _get_hop_count(v)
        if hc not in used_hops:
            selected.append(v)
            used_hops.add(hc)
        if len(selected) >= max_n:
            break

    # Second pass: fill remaining slots from top-scored
    for v in scored:
        if len(selected) >= max_n:
            break
        if v not in selected:
            selected.append(v)

    return selected[:max_n]


def _build_graph(transactions: list[dict]) -> "nx.DiGraph":
    """Build a directed NetworkX graph from transaction dicts."""
    G = nx.DiGraph()
    for txn in transactions:
        sender = txn.get("sender_account_id", "?")
        receiver = txn.get("receiver_account_id", "?")
        amount = float(txn.get("amount", 1.0))
        is_fraud = bool(txn.get("is_fraud", True))
        fraud_role = txn.get("fraud_role", "")
        G.add_edge(
            sender,
            receiver,
            amount=amount,
            is_fraud=is_fraud,
            fraud_role=fraud_role,
        )
    return G


def _assign_node_colors(G: "nx.DiGraph", transactions: list[dict]) -> dict[str, str]:
    """
    Assign colors to nodes based on their role in the fraud chain.
      - First sender (source of funds) → blue
      - Last receiver (extraction) → red
      - Cover activity accounts → gray
      - All others (mule middle accounts) → orange
    """
    # Determine which accounts are purely cover activity
    cover_accounts: set[str] = set()
    fraud_accounts: set[str] = set()
    for txn in transactions:
        if txn.get("fraud_role", "").startswith("cover"):
            cover_accounts.add(txn.get("sender_account_id", ""))
            cover_accounts.add(txn.get("receiver_account_id", ""))
        else:
            fraud_accounts.add(txn.get("sender_account_id", ""))
            fraud_accounts.add(txn.get("receiver_account_id", ""))

    # Nodes only in cover activity
    pure_cover = cover_accounts - fraud_accounts

    # The originator is a sender that never appears as a receiver in fraud txns
    fraud_receivers = {
        txn.get("receiver_account_id", "")
        for txn in transactions
        if not txn.get("fraud_role", "").startswith("cover")
    }
    fraud_senders = {
        txn.get("sender_account_id", "")
        for txn in transactions
        if not txn.get("fraud_role", "").startswith("cover")
    }
    originators = fraud_senders - fraud_receivers

    # Extraction accounts are receivers that never appear as senders in fraud txns
    extractors = fraud_receivers - fraud_senders

    colors: dict[str, str] = {}
    for node in G.nodes():
        if node in pure_cover:
            colors[node] = "#888888"  # gray
        elif node in originators:
            colors[node] = "#3498DB"  # blue
        elif node in extractors:
            colors[node] = "#E74C3C"  # red
        else:
            colors[node] = "#E67E22"  # orange (mule)
    return colors


def _draw_variant_graph(
    ax: "matplotlib.axes.Axes",
    variant: Any,
    transactions: list[dict],
) -> None:
    """Draw a single variant's transaction network on a Matplotlib Axes."""
    G = _build_graph(transactions)
    if len(G.nodes()) == 0:
        ax.text(0.5, 0.5, "No transactions", ha="center", va="center", color="white")
        ax.set_facecolor("#0E1117")
        ax.axis("off")
        return

    node_colors_map = _assign_node_colors(G, transactions)
    node_list = list(G.nodes())
    node_colors = [node_colors_map.get(n, "#E67E22") for n in node_list]

    # Layout
    try:
        pos = nx.spring_layout(G, seed=42, k=1.5)
    except Exception:
        pos = nx.circular_layout(G)

    # Edge properties
    fraud_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("is_fraud", True)
    ]
    cover_edges = [
        (u, v) for u, v, d in G.edges(data=True) if not d.get("is_fraud", True)
    ]

    # Edge widths proportional to log(amount)
    def _edge_width(u: str, v: str) -> float:
        amt = G[u][v].get("amount", 1.0)
        return max(0.5, math.log1p(amt) / 3.0)

    fraud_widths = [_edge_width(u, v) for u, v in fraud_edges]
    cover_widths = [_edge_width(u, v) for u, v in cover_edges]

    ax.set_facecolor("#0E1117")

    nx.draw_networkx_nodes(
        G, pos, nodelist=node_list, node_color=node_colors,
        node_size=300, ax=ax, alpha=0.9,
    )
    nx.draw_networkx_labels(
        G, pos, labels={n: n[-4:] for n in node_list},
        font_size=6, font_color="white", ax=ax,
    )
    if fraud_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=fraud_edges, width=fraud_widths,
            edge_color="#E74C3C", arrows=True, ax=ax,
            arrowsize=12, connectionstyle="arc3,rad=0.1",
        )
    if cover_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=cover_edges, width=cover_widths,
            edge_color="#666666", arrows=True, ax=ax,
            style="dashed", arrowsize=8,
        )

    vid = _get_variant_id(variant)
    score = _get_critic_score(variant)
    ax.set_title(
        f"{vid}  ·  score {score:.1f}",
        color="white", fontsize=8, pad=4,
    )
    ax.axis("off")


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_network_graphs(variants: list | None) -> None:
    """
    Render 3-4 mule network graphs side by side.

    Parameters
    ----------
    variants : list | None
        List of ScoredVariant / RawVariant objects or dicts.
        Handles None and empty list gracefully.
    """
    st.markdown("**Network Graph View**")

    if not _NX_AVAILABLE or not _MPL_AVAILABLE:
        st.info(
            "Install networkx and matplotlib for network graph visualization.\n"
            "  pip install networkx matplotlib"
        )
        return

    if not variants:
        st.caption("Network graphs will appear here once variants are generated.")
        return

    try:
        selected = _select_diverse_variants(variants, max_n=4)
        if not selected:
            st.caption("No variants available for graph rendering.")
            return

        n = len(selected)
        fig, axes = plt.subplots(1, n, figsize=(5 * n, 5))
        fig.patch.set_facecolor("#0E1117")

        if n == 1:
            axes = [axes]

        for ax, variant in zip(axes, selected):
            transactions = _get_transactions(variant)
            _draw_variant_graph(ax, variant, transactions)

        # Legend
        legend_handles = [
            mpatches.Patch(color="#3498DB", label="Originator"),
            mpatches.Patch(color="#E67E22", label="Mule"),
            mpatches.Patch(color="#E74C3C", label="Extractor"),
            mpatches.Patch(color="#888888", label="Cover"),
        ]
        fig.legend(
            handles=legend_handles,
            loc="lower center",
            ncol=4,
            framealpha=0.3,
            facecolor="#1A1F2E",
            labelcolor="white",
            fontsize=8,
        )

        plt.tight_layout(rect=[0, 0.06, 1, 1])
        st.pyplot(fig)
        plt.close(fig)

    except Exception as exc:
        st.warning(f"Graph rendering encountered an issue: {exc}")
