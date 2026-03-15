"""api/demo_runner.py — Synthetic demo mode for FraudGen.

Runs in a background thread and gradually populates RunState with realistic
hardcoded data, simulating a live pipeline execution without calling the Claude API.

Usage (from api/main.py):
    from api.demo_runner import run_demo
    thread = threading.Thread(target=run_demo, args=(run_state, variant_count), daemon=True)
    thread.start()

    # Instant "load with data" mode — completes in ~2s and writes all output files:
    thread = threading.Thread(
        target=run_demo,
        args=(run_state, variant_count),
        kwargs={"instant": True, "folder_path_out": folder_path},
        daemon=True,
    )
"""
from __future__ import annotations

import csv
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pipeline.run_state import (
    AgentStatus,
    CellStatus,
    RunState,
    TraceEvent,
    VariantSummary,
)
from models.variant import ScoredVariant, Transaction

_OUTPUT_BASE = Path(__file__).parent.parent / "app" / "output" / "runs"
_CACHE_DIR   = Path(__file__).parent.parent / ".trace_cache"


# ---------------------------------------------------------------------------
# Cache loader — reads real Claude-generated data from .trace_cache/
# ---------------------------------------------------------------------------

def _load_cache() -> dict | None:
    """
    Try to load real pipeline output from .trace_cache/.

    Returns a dict with keys: orchestrator, personas, variants
    or None if the cache is absent or unreadable.
    """
    orch_path     = _CACHE_DIR / "orchestrator.json"
    personas_path = _CACHE_DIR / "personas.json"
    if not orch_path.exists() or not personas_path.exists():
        return None
    try:
        orch    = json.loads(orch_path.read_text(encoding="utf-8"))
        personas = json.loads(personas_path.read_text(encoding="utf-8"))
        if isinstance(personas, dict):          # handle {personas: [...]} wrapper
            personas = personas.get("personas", personas)
        variants = []
        for vf in sorted(_CACHE_DIR.glob("variant_cell_*.json")):
            try:
                variants.append(json.loads(vf.read_text(encoding="utf-8")))
            except Exception:
                pass
        if not personas or not orch.get("variation_dimensions"):
            return None
        return {"orchestrator": orch, "personas": personas, "variants": variants}
    except Exception:
        return None


class _OrchestratorStub:
    """Minimal stand-in so the /matrix endpoint can read .variation_dimensions."""
    def __init__(self, dimensions: list) -> None:
        self.variation_dimensions = dimensions


def _cells_from_orchestrator(orch: dict) -> list[CellStatus]:
    """
    Build a ~12-cell coverage grid from the orchestrator's variation_dimensions.
    Uses the first 3 dimensions; takes the first 3, 2, 2 example values respectively.
    """
    dims = orch.get("variation_dimensions", [])
    if len(dims) < 3:
        return _build_cells()   # fall back to hardcoded

    def vals(dim: dict, n: int) -> list[str]:
        return (dim.get("example_values") or [])[:n]

    d1 = [(dims[0]["name"], v) for v in vals(dims[0], 3)]
    d2 = [(dims[1]["name"], v) for v in vals(dims[1], 2)]
    d3 = [(dims[2]["name"], v) for v in vals(dims[2], 2)]

    cells = []
    personas_cycle = _PERSONA_CYCLE   # reuse hardcoded cycle; overwritten later if cache loaded
    idx = 0
    for n1, v1 in d1:
        for n2, v2 in d2:
            for n3, v3 in d3:
                pid, pname = personas_cycle[idx % len(personas_cycle)]
                cells.append(CellStatus(
                    cell_id=f"cell_{idx:02d}",
                    dimension_values={n1: v1, n2: v2, n3: v3},
                    assigned_persona_id=pid,
                    assigned_persona_name=pname,
                    status="empty",
                ))
                idx += 1
    return cells


def _persona_stub_from_cache(raw: dict) -> "_PersonaStub":
    """Normalise a cached persona dict to what the frontend Persona type expects."""
    return _PersonaStub({
        "persona_id":       raw.get("persona_id", ""),
        "name":             raw.get("name", "Unknown"),
        "risk_tolerance":   raw.get("risk_tolerance", raw.get("risk_level", "mid")),
        "resources":        raw.get("resources", ""),
        "geographic_scope": raw.get("geographic_scope", ""),
        "evasion_targets":  raw.get("evasion_targets", []),
        "description":      raw.get("backstory", raw.get("description", "")),
    })


def _scored_variant_from_cache(raw: dict, realism: float, distinct: float) -> ScoredVariant | None:
    """
    Build a ScoredVariant from a cached raw variant dict, adding fake critic scores.
    Returns None on validation failure (logged by caller).
    """
    try:
        txns = [Transaction(**t) for t in raw.get("transactions", [])]
        return ScoredVariant(
            variant_id=raw["variant_id"],
            fraud_type=raw["fraud_type"],
            persona_id=raw["persona_id"],
            strategy_description=raw.get("strategy_description", ""),
            variant_parameters=raw["variant_parameters"],
            transactions=txns,
            evasion_techniques=raw.get("evasion_techniques", []),
            fraud_indicators_present=raw.get("fraud_indicators_present", []),
            realism_score=realism,
            distinctiveness_score=distinct,
            persona_consistency=True,
            passed=True,
            feedback="High realism — accurately models known regulatory evasion patterns and behavioral signatures.",
        )
    except Exception:
        return None


# Critic scores to assign to cached variants (one pair per variant file found)
_CACHE_CRITIC_SCORES = [
    (8.7, 8.9),
    (9.1, 8.6),
    (8.4, 9.2),
    (8.8, 8.3),
]


# ---------------------------------------------------------------------------
# Static demo personas
# ---------------------------------------------------------------------------

_PERSONAS = [
    {
        "persona_id": "p_viktor",
        "name": "Viktor Sorokin",
        "risk_tolerance": "high",
        "resources": "Eastern European organized crime network, unregulated crypto exchanges, money service businesses",
        "geographic_scope": "International",
        "evasion_targets": ["KYC checks", "CTR thresholds", "velocity alerts"],
        "description": "Organized crime affiliate with a multi-country mule network and deep ties to unregulated crypto infrastructure.",
    },
    {
        "persona_id": "p_maria",
        "name": "Maria Chen",
        "risk_tolerance": "mid",
        "resources": "Shell companies, business bank accounts, bookkeeping front",
        "geographic_scope": "Domestic + cross-border",
        "evasion_targets": ["SARs", "AML transaction monitoring", "CTRs"],
        "description": "Former bookkeeper who layers transactions through a chain of seemingly legitimate small businesses.",
    },
    {
        "persona_id": "p_james",
        "name": "James Okafor",
        "risk_tolerance": "mid",
        "resources": "Social media reach, student networks, gig-economy accounts",
        "geographic_scope": "Domestic (multi-city)",
        "evasion_targets": ["Account linking analysis", "device fingerprinting"],
        "description": "Operates a mule recruitment ring via encrypted messaging apps targeting financially vulnerable individuals.",
    },
    {
        "persona_id": "p_sandra",
        "name": "Sandra Kowalski",
        "risk_tolerance": "low",
        "resources": "Single personal bank account, limited cash",
        "geographic_scope": "Local",
        "evasion_targets": ["None — unwitting participant"],
        "description": "Unwitting mule recruited via fake job advertisement; unaware she is participating in fraud.",
    },
    {
        "persona_id": "p_derek",
        "name": "Derek Liu",
        "risk_tolerance": "high",
        "resources": "VPN infrastructure, synthetic identity toolkit, automated scripting",
        "geographic_scope": "International",
        "evasion_targets": ["Device fingerprinting", "IP geolocation checks", "biometric verification"],
        "description": "Tech-savvy operator using synthetic identities and automation to orchestrate high-volume micro-transaction layering.",
    },
]

# ---------------------------------------------------------------------------
# Coverage grid dimensions (3 × 2 × 2 = 12 cells)
# ---------------------------------------------------------------------------

_DIM_HOP   = ["3-hop", "5-hop", "7-hop"]
_DIM_TIME  = ["same-day", "randomized"]
_DIM_EXTR  = ["crypto", "wire"]

_PERSONA_CYCLE = [
    ("p_viktor", "Viktor Sorokin"),
    ("p_maria",  "Maria Chen"),
    ("p_james",  "James Okafor"),
    ("p_sandra", "Sandra Kowalski"),
    ("p_derek",  "Derek Liu"),
]


def _build_cells() -> list[CellStatus]:
    cells = []
    idx = 0
    for hop in _DIM_HOP:
        for timing in _DIM_TIME:
            for extraction in _DIM_EXTR:
                pid, pname = _PERSONA_CYCLE[idx % len(_PERSONA_CYCLE)]
                cells.append(CellStatus(
                    cell_id=f"cell_{idx:02d}",
                    dimension_values={"hop_count": hop, "timing": timing, "extraction_method": extraction},
                    assigned_persona_id=pid,
                    assigned_persona_name=pname,
                    status="empty",
                ))
                idx += 1
    return cells


# ---------------------------------------------------------------------------
# Hardcoded synthetic variants
# ---------------------------------------------------------------------------

def _txn(
    role: str, amount: float, channel: str, merchant: str,
    sender: str, receiver: str, offset_hrs: float = 0.0,
) -> dict:
    """Build a transaction dict."""
    ts = f"2026-03-10T{9 + int(offset_hrs):02d}:{int((offset_hrs % 1) * 60):02d}:00Z"
    is_fraud = role != "cover_activity"
    return dict(
        transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
        timestamp=ts,
        amount=amount,
        sender_account_id=sender,
        receiver_account_id=receiver,
        merchant_category=merchant,
        channel=channel,
        is_fraud=is_fraud,
        fraud_role=role,
    )


_DEMO_VARIANTS: list[dict] = [
    # Variant 0 — 3-hop same-day crypto (Viktor)
    {
        "variant_id": "var_001",
        "fraud_type": "layered mule account network",
        "persona_id": "p_viktor",
        "strategy_description": "Viktor's crew moves $48k through three same-day ACH hops then converts to BTC via an OTC broker, exploiting same-day settlement windows before overnight batch reconciliation catches the pattern.",
        "variant_parameters": {"hop_count": 3, "timing": "same-day", "extraction_method": "crypto", "topology": "linear", "amount_logic": "structured_below_10k"},
        "evasion_techniques": ["structuring below $10k CTR threshold", "same-day settlement exploit", "OTC crypto conversion"],
        "fraud_indicators_present": ["rapid successive transfers", "round-number structuring", "crypto off-ramp"],
        "realism_score": 8.7,
        "distinctiveness_score": 8.2,
        "persona_consistency": True,
        "passed": True,
        "feedback": "High realism — amounts correctly structured below CTR threshold; timing sequence plausible within same-day ACH windows.",
        "transactions": [
            _txn("placement",    9800.0,  "ACH",    "wire_transfer",         "acct_SRC_001", "acct_M1_001", 0.0),
            _txn("cover_activity", 124.5, "card",   "grocery",               "acct_M1_001",  "acct_MERCH_A", 0.5),
            _txn("hop_1_of_3",   9600.0,  "ACH",    "wire_transfer",         "acct_M1_001",  "acct_M2_001", 1.0),
            _txn("hop_2_of_3",   9400.0,  "ACH",    "wire_transfer",         "acct_M2_001",  "acct_M3_001", 2.5),
            _txn("hop_3_of_3",   9200.0,  "Zelle",  "peer_to_peer",          "acct_M3_001",  "acct_OTC_001", 4.0),
            _txn("extraction",   9100.0,  "crypto", "cryptocurrency_exchange","acct_OTC_001", "wallet_BTC_vk1", 5.0),
        ],
    },
    # Variant 1 — 5-hop randomized wire (Maria)
    {
        "variant_id": "var_002",
        "fraud_type": "layered mule account network",
        "persona_id": "p_maria",
        "strategy_description": "Maria's shell company network receives a $95k business wire, splits into five sub-transfers across shell entities over three days with random timing, then consolidates for a final international wire to an offshore account.",
        "variant_parameters": {"hop_count": 5, "timing": "randomized", "extraction_method": "wire", "topology": "fan-out-then-merge", "amount_logic": "split_and_merge"},
        "evasion_techniques": ["business account cover", "random inter-day delays", "offshore wire to low-scrutiny jurisdiction"],
        "fraud_indicators_present": ["large incoming wire split into sub-transfers", "multiple shell entities", "rapid account opening"],
        "realism_score": 9.1,
        "distinctiveness_score": 8.5,
        "persona_consistency": True,
        "passed": True,
        "feedback": "Excellent structural realism; fan-out-then-merge topology is distinctively different from linear chains.",
        "transactions": [
            _txn("placement",    95000.0, "wire",   "wire_transfer",   "acct_SRC_002", "acct_SHELL_A", 0.0),
            _txn("hop_1_of_5",  18000.0,  "ACH",    "wire_transfer",   "acct_SHELL_A", "acct_M4_001", 2.0),
            _txn("hop_2_of_5",  19500.0,  "ACH",    "wire_transfer",   "acct_SHELL_A", "acct_M5_001", 2.3),
            _txn("hop_3_of_5",  21000.0,  "ACH",    "wire_transfer",   "acct_SHELL_A", "acct_M6_001", 6.0),
            _txn("hop_4_of_5",  17500.0,  "ACH",    "wire_transfer",   "acct_SHELL_A", "acct_M7_001", 8.5),
            _txn("hop_5_of_5",  16000.0,  "wire",   "wire_transfer",   "acct_M4_001",  "acct_SHELL_B", 24.0),
            _txn("cover_activity", 3200.0,"ACH",    "payroll",         "acct_SHELL_B", "acct_EMPLOYEE_01", 25.0),
            _txn("extraction",  88000.0,  "wire",   "international_wire","acct_SHELL_B","acct_OFFSHORE_001", 26.0),
        ],
    },
    # Variant 2 — 3-hop randomized crypto (James)
    {
        "variant_id": "var_003",
        "fraud_type": "layered mule account network",
        "persona_id": "p_james",
        "strategy_description": "James's student mule network uses Zelle for rapid sub-$3k hops between personal accounts, with 12–36 hour random gaps, before cashing out via a peer crypto platform.",
        "variant_parameters": {"hop_count": 3, "timing": "randomized", "extraction_method": "crypto", "topology": "linear", "amount_logic": "micro_structured"},
        "evasion_techniques": ["micro-structuring under $3k", "student/young-adult account profiles", "randomized timing to avoid velocity rules"],
        "fraud_indicators_present": ["Zelle to multiple new contacts", "young account holders", "crypto off-ramp"],
        "realism_score": 7.9,
        "distinctiveness_score": 8.8,
        "persona_consistency": True,
        "passed": True,
        "feedback": "Distinct micro-structuring pattern; student demographic angle is novel and realistic.",
        "transactions": [
            _txn("placement",    2900.0,  "Zelle",  "peer_to_peer",          "acct_SRC_003", "acct_STU_001", 0.0),
            _txn("hop_1_of_3",   2750.0,  "Zelle",  "peer_to_peer",          "acct_STU_001", "acct_STU_002", 12.0),
            _txn("hop_2_of_3",   2700.0,  "Zelle",  "peer_to_peer",          "acct_STU_002", "acct_STU_003", 36.0),
            _txn("hop_3_of_3",   2650.0,  "crypto", "cryptocurrency_exchange","acct_STU_003", "acct_PEER_EXCH", 48.0),
            _txn("extraction",   2580.0,  "crypto", "cryptocurrency_exchange","acct_PEER_EXCH","wallet_BTC_jm1", 49.0),
        ],
    },
    # Variant 3 — 5-hop same-day wire (Sandra — unwitting)
    {
        "variant_id": "var_004",
        "fraud_type": "layered mule account network",
        "persona_id": "p_sandra",
        "strategy_description": "Sandra unwittingly forwards $14k she received from a 'remote job' directly to another mule, within hours. The funds move through two more hops the same day before a wire extraction.",
        "variant_parameters": {"hop_count": 5, "timing": "same-day", "extraction_method": "wire", "topology": "linear", "amount_logic": "pass_through_minus_fee"},
        "evasion_techniques": ["unwitting mule reduces behavioral red flags", "same-day pass-through", "employment cover story"],
        "fraud_indicators_present": ["large inbound from unknown sender", "immediate outbound forwarding", "account opened recently"],
        "realism_score": 8.3,
        "distinctiveness_score": 7.6,
        "persona_consistency": True,
        "passed": True,
        "feedback": "Unwitting mule angle adds realism; pass-through timing is consistent with same-day ACH windows.",
        "transactions": [
            _txn("placement",    14200.0, "ACH",   "wire_transfer",   "acct_SRC_004", "acct_SANDRA", 0.0),
            _txn("hop_1_of_5",   14000.0, "ACH",   "wire_transfer",   "acct_SANDRA",  "acct_M8_001", 1.5),
            _txn("hop_2_of_5",   13800.0, "Zelle", "peer_to_peer",    "acct_M8_001",  "acct_M9_001", 2.5),
            _txn("hop_3_of_5",   13500.0, "ACH",   "wire_transfer",   "acct_M9_001",  "acct_M10_001", 3.5),
            _txn("hop_4_of_5",   13200.0, "ACH",   "wire_transfer",   "acct_M10_001", "acct_M11_001", 5.0),
            _txn("hop_5_of_5",   13000.0, "wire",  "wire_transfer",   "acct_M11_001", "acct_CONSOL_001", 6.0),
            _txn("cover_activity", 45.99, "card",  "restaurant",      "acct_SANDRA",  "acct_MERCH_B", 4.0),
            _txn("extraction",   12700.0, "wire",  "international_wire","acct_CONSOL_001","acct_OFFSHORE_002", 7.5),
        ],
    },
    # Variant 4 — 7-hop randomized crypto (Derek)
    {
        "variant_id": "var_005",
        "fraud_type": "layered mule account network",
        "persona_id": "p_derek",
        "strategy_description": "Derek's automated toolkit rotates $220k through 7 synthetic-identity accounts with randomized inter-hop delays of 4–72 hours, mimicking organic spending. Final extraction routes to a non-custodial wallet via a privacy coin swap.",
        "variant_parameters": {"hop_count": 7, "timing": "randomized", "extraction_method": "crypto", "topology": "linear", "amount_logic": "noise_injected"},
        "evasion_techniques": ["synthetic identity accounts", "behavioral noise injection", "privacy coin swap for extraction", "VPN-masked IP per account"],
        "fraud_indicators_present": ["consistent account creation pattern", "all accounts <90 days old", "privacy coin usage"],
        "realism_score": 9.3,
        "distinctiveness_score": 9.0,
        "persona_consistency": True,
        "passed": True,
        "feedback": "Outstanding structural complexity; 7-hop chain with noise injection is maximally distinct from simpler variants.",
        "transactions": [
            _txn("placement",    29800.0,  "wire",   "wire_transfer",          "acct_SRC_005", "acct_SYN_001", 0.0),
            _txn("cover_activity", 78.40,  "card",   "streaming_subscription", "acct_SYN_001", "acct_MERCH_C", 1.0),
            _txn("hop_1_of_7",   29200.0,  "ACH",    "wire_transfer",          "acct_SYN_001", "acct_SYN_002", 4.0),
            _txn("hop_2_of_7",   28600.0,  "ACH",    "wire_transfer",          "acct_SYN_002", "acct_SYN_003", 12.0),
            _txn("cover_activity", 142.99, "card",   "electronics",            "acct_SYN_002", "acct_MERCH_D", 15.0),
            _txn("hop_3_of_7",   28100.0,  "Zelle",  "peer_to_peer",           "acct_SYN_003", "acct_SYN_004", 24.0),
            _txn("hop_4_of_7",   27800.0,  "ACH",    "wire_transfer",          "acct_SYN_004", "acct_SYN_005", 48.0),
            _txn("hop_5_of_7",   27400.0,  "ACH",    "wire_transfer",          "acct_SYN_005", "acct_SYN_006", 72.0),
            _txn("hop_6_of_7",   26900.0,  "ACH",    "wire_transfer",          "acct_SYN_006", "acct_SYN_007", 96.0),
            _txn("hop_7_of_7",   26400.0,  "crypto", "cryptocurrency_exchange","acct_SYN_007", "acct_DEX_001", 100.0),
            _txn("extraction",   25800.0,  "crypto", "privacy_coin_swap",      "acct_DEX_001", "wallet_XMR_dk1", 101.0),
        ],
    },
    # Variant 5 — 7-hop same-day wire (Viktor)
    {
        "variant_id": "var_006",
        "fraud_type": "layered mule account network",
        "persona_id": "p_viktor",
        "strategy_description": "A high-velocity same-day sweep: $180k enters through an MSB-adjacent account at 08:00, passes through 7 pre-staged mule accounts in under 6 hours, and exits via a SWIFT wire before the bank's end-of-day review.",
        "variant_parameters": {"hop_count": 7, "timing": "same-day", "extraction_method": "wire", "topology": "linear", "amount_logic": "high_velocity_sweep"},
        "evasion_techniques": ["pre-staged accounts", "intra-day sweep before review window", "MSB account cover"],
        "fraud_indicators_present": ["abnormal velocity", "sequential same-hour transfers", "large SWIFT outbound"],
        "realism_score": 8.9,
        "distinctiveness_score": 8.1,
        "persona_consistency": True,
        "passed": True,
        "feedback": "Intra-day timing constraint is accurately modeled against real-day ACH cutoff windows.",
        "transactions": [
            _txn("placement",    180000.0, "wire",  "wire_transfer",    "acct_SRC_006", "acct_MSB_001", 0.0),
            _txn("hop_1_of_7",   176000.0, "wire",  "wire_transfer",    "acct_MSB_001", "acct_MV1_001", 0.5),
            _txn("hop_2_of_7",   172000.0, "ACH",   "wire_transfer",    "acct_MV1_001", "acct_MV2_001", 1.0),
            _txn("hop_3_of_7",   168000.0, "ACH",   "wire_transfer",    "acct_MV2_001", "acct_MV3_001", 1.5),
            _txn("hop_4_of_7",   165000.0, "ACH",   "wire_transfer",    "acct_MV3_001", "acct_MV4_001", 2.0),
            _txn("hop_5_of_7",   162000.0, "wire",  "wire_transfer",    "acct_MV4_001", "acct_MV5_001", 2.5),
            _txn("hop_6_of_7",   159000.0, "wire",  "wire_transfer",    "acct_MV5_001", "acct_MV6_001", 3.5),
            _txn("hop_7_of_7",   156000.0, "wire",  "wire_transfer",    "acct_MV6_001", "acct_CONSOL_002", 4.5),
            _txn("extraction",   155000.0, "wire",  "international_wire","acct_CONSOL_002","acct_OFFSHORE_003", 5.5),
        ],
    },
    # Variant 6 — 5-hop randomized crypto (Maria)
    {
        "variant_id": "var_007",
        "fraud_type": "layered mule account network",
        "persona_id": "p_maria",
        "strategy_description": "Maria's bookkeeping cover: payroll-like ACH credits to 5 'employee' accounts, each holding funds 1–4 days before forwarding to a consolidation account, which then converts to USDC and bridges offshore.",
        "variant_parameters": {"hop_count": 5, "timing": "randomized", "extraction_method": "crypto", "topology": "fan-in", "amount_logic": "payroll_cover"},
        "evasion_techniques": ["payroll timing mimicry", "employee account cover", "stablecoin extraction via DeFi bridge"],
        "fraud_indicators_present": ["multiple same-day payroll credits", "funds immediately re-forwarded", "DeFi bridge activity"],
        "realism_score": 8.4,
        "distinctiveness_score": 9.2,
        "persona_consistency": True,
        "passed": True,
        "feedback": "Payroll cover is highly novel; stablecoin bridge extraction is distinct from all other variants. Top distinctiveness score.",
        "transactions": [
            _txn("placement",    42000.0, "ACH",    "payroll",                 "acct_SHELL_C", "acct_EMP_001", 0.0),
            _txn("placement",    38500.0, "ACH",    "payroll",                 "acct_SHELL_C", "acct_EMP_002", 0.1),
            _txn("placement",    41000.0, "ACH",    "payroll",                 "acct_SHELL_C", "acct_EMP_003", 0.2),
            _txn("cover_activity", 890.0,"card",    "grocery",                 "acct_EMP_001", "acct_MERCH_E", 8.0),
            _txn("hop_1_of_5",   41500.0,"ACH",     "wire_transfer",           "acct_EMP_001", "acct_CONSOL_003", 24.0),
            _txn("hop_2_of_5",   37900.0,"ACH",     "wire_transfer",           "acct_EMP_002", "acct_CONSOL_003", 48.0),
            _txn("hop_3_of_5",   40300.0,"ACH",     "wire_transfer",           "acct_EMP_003", "acct_CONSOL_003", 72.0),
            _txn("hop_4_of_5",   115000.0,"wire",   "wire_transfer",           "acct_CONSOL_003","acct_DEFI_001", 73.0),
            _txn("hop_5_of_5",   113000.0,"crypto", "cryptocurrency_exchange", "acct_DEFI_001","wallet_USDC_mc1", 73.5),
            _txn("extraction",   112000.0,"crypto", "defi_bridge",             "wallet_USDC_mc1","wallet_OFFSHORE_mc1", 74.0),
        ],
    },
]

_AGENT_IDS = ["A1", "A2", "A3"]

_EVENT_TEMPLATES = [
    "Orchestrator decomposed fraud description into {dims} variation dimensions",
    "PersonaGenerator creating {n} distinct criminal profiles",
    "Persona '{name}' generated — risk: {risk}",
    "Agent {agent} starting variant {var} ({params})",
    "Agent {agent} — Step 1/4: Persona analysis for {var}",
    "Agent {agent} — Step 2/4: Network topology planning for {var}",
    "Agent {agent} — Step 3/4: Participant profile generation for {var}",
    "Agent {agent} — Step 4/4: Transaction sequence construction for {var}",
    "Critic evaluated {var}: realism={r:.1f}, distinctiveness={d:.1f} → {'APPROVED' if True else 'REJECTED'}",
    "Coverage cell {cell} marked complete — {var} assigned",
]


# ---------------------------------------------------------------------------
# Main demo runner
# ---------------------------------------------------------------------------

def run_demo(
    run_state: RunState,
    variant_count: int = 7,
    instant: bool = False,
    folder_path_out: list[str] | None = None,
) -> None:
    """
    Populate run_state with synthetic demo data.

    instant=False  — streams over ~35s (nice for LiveMonitor demo)
    instant=True   — completes in ~2s and writes all output files to disk
                     (folder_path_out[0] is set so dataset/export endpoints work)

    Designed to be run in a background thread.
    """
    def _sleep(t: float) -> None:
        time.sleep(0.05 if instant else t)

    # ------------------------------------------------------------------
    # Source data — prefer real Claude-generated cache, fall back to hardcoded
    # ------------------------------------------------------------------
    cache = _load_cache()

    if cache:
        # Real orchestrator output → dimensions + cells
        orch_data      = cache["orchestrator"]
        raw_personas   = cache["personas"]
        cached_variants = cache["variants"]
        cells = _cells_from_orchestrator(orch_data)

        # Patch cell persona assignments from real personas
        persona_ids   = [p.get("persona_id", f"P-{i:02d}") for i, p in enumerate(raw_personas)]
        persona_names = [p.get("name", f"Persona {i}") for i, p in enumerate(raw_personas)]
        for i, cell in enumerate(cells):
            pid   = persona_ids[i % len(persona_ids)]
            pname = persona_names[i % len(persona_names)]
            cell.assigned_persona_id   = pid
            cell.assigned_persona_name = pname

        # Build variant list from cache, cycling if variant_count > cache size
        # Fall back to hardcoded only when cache has no variants at all
        cache_svs: list[dict] = []
        for raw_vd, (r, d) in zip(cached_variants, _CACHE_CRITIC_SCORES):
            cache_svs.append({**raw_vd, "_realism": r, "_distinct": d})

        if cache_svs:
            # Cycle through cached variants with fresh IDs to hit variant_count
            while len(cache_svs) < variant_count:
                idx = len(cache_svs) % len(cached_variants)
                r, d = _CACHE_CRITIC_SCORES[len(cache_svs) % len(_CACHE_CRITIC_SCORES)]
                new_id = f"V-{uuid.uuid4().hex[:6].upper()}"
                cache_svs.append({**cached_variants[idx], "variant_id": new_id, "_realism": r, "_distinct": d})
            variant_dicts = cache_svs[:max(1, variant_count)]
        else:
            # Cache exists (personas/orchestrator) but no variant files — use hardcoded variants
            variant_dicts = [{"_hardcoded": True, **v}
                             for v in _DEMO_VARIANTS[:max(1, min(variant_count, len(_DEMO_VARIANTS)))]]

        # Name map for the event log — cache personas only
        persona_name_map = {p.get("persona_id", ""): p.get("name", "") for p in raw_personas}

        dim_names = [d.get("name", "") for d in orch_data.get("variation_dimensions", [])]
        dim_count = len(dim_names)
    else:
        # No cache — use fully hardcoded data
        orch_data      = None
        raw_personas   = None
        cached_variants = []
        cells = _build_cells()
        variant_dicts  = [{"_hardcoded": True, **v}
                          for v in _DEMO_VARIANTS[:max(1, min(variant_count, len(_DEMO_VARIANTS)))]]
        persona_name_map = {p["persona_id"]: p["name"] for p in _PERSONAS}
        dim_count = 3

    # ------------------------------------------------------------------
    # Phase 1 — Orchestrating
    # ------------------------------------------------------------------
    run_state.set_phase("orchestrating")
    run_state.variants_total = len(variant_dicts)
    run_state.log_event("Orchestrator received fraud description — beginning dimension decomposition")
    _sleep(0.8)

    if cache and orch_data:
        dims = orch_data.get("variation_dimensions", [])
        run_state.set_orchestrator_output(_OrchestratorStub(dims))
        run_state.log_event(f"Orchestrator identified {dim_count} variation dimensions via extended thinking")
        _sleep(0.6)
        for dim in dims[:5]:   # log first 5 dimensions with their descriptions
            run_state.log_event(f"  Dimension: {dim['name']} — {dim.get('description','')[:80]}…")
            _sleep(0.3)
        if len(dims) > 5:
            run_state.log_event(f"  … and {len(dims) - 5} additional dimensions")
    else:
        run_state.log_event("Orchestrator decomposed description into 3 variation dimensions: hop_count, timing, extraction_method")

    _sleep(0.6)
    run_state.log_event(f"CellGenerator produced {len(cells)} coverage cells")
    _sleep(0.4)

    for cell in cells:
        run_state.upsert_cell(cell)

    # ------------------------------------------------------------------
    # Phase 2 — Persona generation
    # ------------------------------------------------------------------
    run_state.set_phase("personas")

    if cache and raw_personas:
        n_personas = len(raw_personas)
        run_state.log_event(f"PersonaGenerator creating {n_personas} criminal profiles")
        _sleep(0.5)
        for p in raw_personas:
            _sleep(0.5)
            run_state.personas.append(_persona_stub_from_cache(p))
            risk = p.get("risk_tolerance", p.get("risk_level", "mid"))
            scope = p.get("geographic_scope", "unknown")
            run_state.log_event(f"Persona '{p['name']}' generated — risk: {risk}, scope: {scope}")
    else:
        run_state.log_event(f"PersonaGenerator creating {len(_PERSONAS)} criminal profiles")
        _sleep(0.5)
        for p in _PERSONAS:
            _sleep(0.5)
            run_state.personas.append(_PersonaStub(p))
            run_state.log_event(f"Persona '{p['name']}' generated — risk: {p['risk_tolerance']}, scope: {p['geographic_scope']}")

    _sleep(0.3)

    # ------------------------------------------------------------------
    # Phase 3 — Variant generation
    # ------------------------------------------------------------------
    run_state.set_phase("generating")
    run_state.log_event("Beginning variant generation — dispatching agent pool")

    approved_svs: list[ScoredVariant] = []

    for i, vd in enumerate(variant_dicts):
        if run_state.control_signal == "stop":
            break

        while run_state.control_signal == "pause":
            time.sleep(0.5)

        agent_id = _AGENT_IDS[i % len(_AGENT_IDS)]
        cell = cells[i % len(cells)]
        params_str = ", ".join(f"{k}={v}" for k, v in list(cell.dimension_values.items())[:3])

        cell.status = "in_progress"
        run_state.upsert_cell(cell)

        variant_id_preview = vd.get("variant_id", f"var_{i:03d}")
        persona_id_preview = vd.get("persona_id", "unknown")

        run_state.upsert_agent(AgentStatus(
            agent_id=agent_id,
            cell_id=cell.cell_id,
            variant_id=variant_id_preview,
            persona_name=persona_name_map.get(persona_id_preview, "Unknown"),
            status="running",
            current_step=1,
            total_steps=4,
            step_name="Persona analysis",
            attempt=1,
            max_attempts=3,
            tokens_used=0,
            cost_usd=0.0,
        ))

        run_state.log_event(f"Agent {agent_id} → {variant_id_preview} | {params_str}")

        # Build per-step detail payloads from cached or hardcoded variant data
        persona_dict = None
        if cache and raw_personas:
            persona_dict = next(
                (p for p in raw_personas if p.get("persona_id") == persona_id_preview),
                raw_personas[0] if raw_personas else None
            )

        step_details = [
            # Step 1 — Persona analysis
            {
                "persona_id":       persona_id_preview,
                "persona_name":     persona_name_map.get(persona_id_preview, "Unknown"),
                **({"backstory": persona_dict["backstory"][:400]} if persona_dict and "backstory" in persona_dict else {}),
                **({"timeline_pressure": persona_dict["timeline_pressure"]} if persona_dict and "timeline_pressure" in persona_dict else {}),
                **({"evasion_targets": persona_dict.get("evasion_targets", [])} if persona_dict else {}),
                **({"resources": persona_dict.get("resources", "")[:200]} if persona_dict else {}),
            },
            # Step 2 — Network topology planning
            {
                "cell_assignment":    cell.dimension_values,
                "variant_parameters": vd.get("variant_parameters", {}),
                "strategy_summary":   (vd.get("strategy_description") or "")[:300],
            },
            # Step 3 — Participant profile generation
            {
                "evasion_techniques":     vd.get("evasion_techniques", []),
                "unique_account_ids":     list({t["sender_account_id"] for t in vd.get("transactions", [])} |
                                               {t["receiver_account_id"] for t in vd.get("transactions", [])}),
            },
            # Step 4 — Transaction sequence construction
            {
                "transaction_count": len(vd.get("transactions", [])),
                "transactions":      vd.get("transactions", [])[:12],   # first 12 to keep payload readable
                "fraud_indicators":  vd.get("fraud_indicators_present", []),
            },
        ]

        step_names = [
            "Persona analysis",
            "Network topology planning",
            "Participant profile generation",
            "Transaction sequence construction",
        ]
        step_delays = [0.9, 1.0, 0.9, 1.2]

        for step_i, (step_name, delay, detail_payload) in enumerate(
            zip(step_names, step_delays, step_details), start=1
        ):
            _sleep(delay)
            run_state.log_event(f"Agent {agent_id} — Step {step_i}/4: {step_name} [{variant_id_preview}]")

            # Emit a structured TraceEvent so the Execution Trace tab populates
            run_state.add_trace_event(TraceEvent(
                event_id=f"ev_{uuid.uuid4().hex[:10]}",
                ts=datetime.now(timezone.utc).isoformat(),
                agent_id=agent_id,
                variant_id=variant_id_preview,
                step=step_i,
                step_name=step_name,
                attempt=1,
                status="done",
                description=f"Step {step_i}/4 complete",
                score=None,
                detail=detail_payload,
            ))

            run_state.upsert_agent(AgentStatus(
                agent_id=agent_id,
                cell_id=cell.cell_id,
                variant_id=variant_id_preview,
                persona_name=persona_name_map.get(persona_id_preview, "Unknown"),
                status="running",
                current_step=step_i,
                total_steps=4,
                step_name=step_name,
                attempt=1,
                max_attempts=3,
                tokens_used=step_i * 1800,
                cost_usd=round(step_i * 0.012, 4),
            ))

        if vd.get("_hardcoded"):
            # Build from hardcoded static data
            try:
                txns = [Transaction(**t) for t in vd["transactions"]]
                sv = ScoredVariant(
                    variant_id=vd["variant_id"],
                    fraud_type=vd["fraud_type"],
                    persona_id=vd["persona_id"],
                    strategy_description=vd["strategy_description"],
                    variant_parameters=vd["variant_parameters"],
                    transactions=txns,
                    evasion_techniques=vd["evasion_techniques"],
                    fraud_indicators_present=vd["fraud_indicators_present"],
                    realism_score=vd["realism_score"],
                    distinctiveness_score=vd["distinctiveness_score"],
                    persona_consistency=vd["persona_consistency"],
                    passed=vd["passed"],
                    feedback=vd["feedback"],
                )
            except Exception as exc:
                run_state.add_error(f"Demo variant build failed: {exc}")
                continue
            realism   = vd["realism_score"]
            distinct  = vd["distinctiveness_score"]
        else:
            # Build from cached Claude-generated data
            sv = _scored_variant_from_cache(vd, vd["_realism"], vd["_distinct"])
            if sv is None:
                run_state.add_error(f"Cache variant build failed for {vd.get('variant_id')}")
                continue
            realism  = vd["_realism"]
            distinct = vd["_distinct"]

        run_state.add_scored_variant(sv)
        approved_svs.append(sv)

        run_state.log_event(
            f"Critic scored {sv.variant_id}: "
            f"realism={realism:.1f}, "
            f"distinctiveness={distinct:.1f} → APPROVED"
        )
        run_state.add_cost(round(0.048 + i * 0.003, 4))

        summary = VariantSummary(
            variant_id=sv.variant_id,
            persona_name=persona_name_map.get(sv.persona_id, sv.persona_id),
            parameters_summary=params_str,
            critic_score=round((realism + distinct) / 2, 2),
            status="approved",
            strategy_description=sv.strategy_description[:200],
            completed_at=datetime.now(timezone.utc).isoformat(),
            realism_score=realism,
            distinctiveness_score=distinct,
            attempt_count=1,
            passed=True,
        )
        run_state.update_variant(summary)

        cell.status = "completed"
        cell.critic_score = summary.critic_score
        cell.variant_id = vd["variant_id"]
        run_state.upsert_cell(cell)

        run_state.upsert_agent(AgentStatus(
            agent_id=agent_id,
            cell_id=cell.cell_id,
            variant_id=sv.variant_id,
            persona_name=summary.persona_name,
            status="done",
            current_step=4,
            total_steps=4,
            step_name="Complete",
            attempt=1,
            max_attempts=3,
            tokens_used=7200,
            cost_usd=round(0.048 + i * 0.003, 4),
            last_score=summary.critic_score,
        ))

        run_state.log_event(f"Coverage cell {cell.cell_id} marked complete — {sv.variant_id} approved")

    # ------------------------------------------------------------------
    # Phase 4 — Write output files (instant mode) then complete
    # ------------------------------------------------------------------
    if instant and folder_path_out is not None and approved_svs:
        try:
            folder = _write_demo_files(approved_svs, persona_name_map, run_state,
                                       raw_personas=raw_personas)
            folder_path_out[0] = folder
            run_state.log_event(f"Output files written to {folder}")
        except Exception as exc:
            run_state.add_error(f"Demo file write failed: {exc}")

    run_state.log_event("All variants processed — pipeline complete")
    run_state.mark_complete()


# ---------------------------------------------------------------------------
# Output file writer for instant mode
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "transaction_id", "timestamp", "amount", "sender_account_id",
    "receiver_account_id", "merchant_category", "channel", "is_fraud",
    "fraud_role", "variant_id", "persona_id", "persona_name", "fraud_type",
    "realism_score", "distinctiveness_score",
]


def _write_demo_files(
    approved_svs: list[ScoredVariant],
    persona_name_map: dict[str, str],
    run_state: RunState,
    raw_personas: list[dict] | None = None,
) -> str:
    """Write dataset.csv, dataset.json, personas.json, variants.json, run_summary.json."""
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    folder = str(_OUTPUT_BASE / f"run_{timestamp}")
    os.makedirs(folder, exist_ok=True)

    # dataset.csv
    rows = []
    for sv in approved_svs:
        pname = persona_name_map.get(sv.persona_id, sv.persona_id)
        for txn in sv.transactions:
            rows.append({
                "transaction_id": txn.transaction_id,
                "timestamp": txn.timestamp,
                "amount": txn.amount,
                "sender_account_id": txn.sender_account_id,
                "receiver_account_id": txn.receiver_account_id,
                "merchant_category": txn.merchant_category,
                "channel": txn.channel,
                "is_fraud": txn.is_fraud,
                "fraud_role": txn.fraud_role,
                "variant_id": sv.variant_id,
                "persona_id": sv.persona_id,
                "persona_name": pname,
                "fraud_type": sv.fraud_type,
                "realism_score": sv.realism_score,
                "distinctiveness_score": sv.distinctiveness_score,
            })

    csv_path = os.path.join(folder, "dataset.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # dataset.json
    _write_json(os.path.join(folder, "dataset.json"), {
        "variants": [
            {
                "variant_id": sv.variant_id,
                "fraud_type": sv.fraud_type,
                "persona_id": sv.persona_id,
                "persona_name": persona_name_map.get(sv.persona_id, sv.persona_id),
                "strategy_description": sv.strategy_description,
                "variant_parameters": sv.variant_parameters,
                "realism_score": sv.realism_score,
                "distinctiveness_score": sv.distinctiveness_score,
                "evasion_techniques": sv.evasion_techniques,
                "fraud_indicators_present": sv.fraud_indicators_present,
                "transactions": [t.model_dump() for t in sv.transactions],
            }
            for sv in approved_svs
        ]
    })

    # personas.json — use real cached personas if available, else hardcoded
    _write_json(os.path.join(folder, "personas.json"), raw_personas if raw_personas else _PERSONAS)

    # variants.json
    _write_json(os.path.join(folder, "variants.json"), [
        {
            "variant_id": sv.variant_id,
            "fraud_type": sv.fraud_type,
            "persona_id": sv.persona_id,
            "persona_name": persona_name_map.get(sv.persona_id, sv.persona_id),
            "strategy_description": sv.strategy_description,
            "variant_parameters": sv.variant_parameters,
            "realism_score": sv.realism_score,
            "distinctiveness_score": sv.distinctiveness_score,
            "passed": sv.passed,
            "feedback": sv.feedback,
            "evasion_techniques": sv.evasion_techniques,
            "fraud_indicators_present": sv.fraud_indicators_present,
        }
        for sv in approved_svs
    ])

    # run_summary.json
    scores = [(sv.realism_score + sv.distinctiveness_score) / 2 for sv in approved_svs]
    _write_json(os.path.join(folder, "run_summary.json"), {
        "variant_count": len(approved_svs),
        "mean_critic_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "coverage_saturation_pct": round(len(approved_svs) / 12 * 100, 1),
        "persona_count": len({sv.persona_id for sv in approved_svs}),
        "total_transactions": sum(len(sv.transactions) for sv in approved_svs),
        "run_duration_seconds": round(run_state.elapsed_s, 1),
        "total_cost_usd": round(run_state.total_cost_usd, 4),
        "revisions_count": run_state.revisions_count,
        "rejections_count": run_state.rejections_count,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })

    # config.json (minimal) — use first variant's fraud_type from cache if available
    fraud_desc = (
        approved_svs[0].fraud_type
        if approved_svs and approved_svs[0].fraud_type
        else "Demo run — layered mule account network"
    )
    _write_json(os.path.join(folder, "config.json"), {
        "fraud_description": fraud_desc,
        "variant_count": len(approved_svs),
        "demo_mode": True,
    })

    return folder


def _write_json(path: str, data: object) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Minimal persona stub (duck-types the Pydantic Persona model for API reads)
# ---------------------------------------------------------------------------

class _PersonaStub:
    """Lightweight stand-in so get_personas() can call .model_dump()."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self) -> dict:
        return self._data
