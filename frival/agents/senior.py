"""
Senior Agent — Coordination Layer.

Programmatic rule engine (NOT an LLM call).
Combines Agent A (Technical) and Agent B (Fundamental) into a final decision.
"""

from typing import Dict, Any


def synthesize(
    technical: Dict[str, Any],
    fundamental: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Combine technical and fundamental agent verdicts into a final decision.

    Decision table:
        Technical | Fundamental | Result
        CONFIRM   | CONFIRM     | FIRED (HIGH confidence)
        CONFIRM   | NEUTRAL     | FIRED (MODERATE confidence)
        NEUTRAL   | CONFIRM     | FIRED (MODERATE confidence)
        REJECT    | *           | SHELVED (technical rejection)
        *         | REJECT      | SHELVED (fundamental veto — unconditional)
        NEUTRAL   | NEUTRAL     | SHELVED (ambiguous)

    Fundamental rejection always vetoes — this targets April-type macro shocks.

    Parameters
    ----------
    technical : dict from agents/technical.py
    fundamental : dict from agents/fundamental.py

    Returns
    -------
    dict with: final_decision, final_confidence, veto_reason, agents_summary
    """
    t_dec = technical.get("decision", "NEUTRAL")
    f_dec = fundamental.get("decision", "NEUTRAL")

    # Rule: Fundamental rejection is an unconditional veto
    if f_dec == "REJECT":
        return {
            "final_decision": "SHELVED",
            "final_confidence": None,
            "veto_reason": f"fundamental: {fundamental.get('justification', 'macro rejection')}",
            "agents_summary": f"Technical={t_dec}, Fundamental={f_dec} → vetoed by fundamental",
        }

    # Rule: Technical rejection
    if t_dec == "REJECT":
        return {
            "final_decision": "SHELVED",
            "final_confidence": None,
            "veto_reason": f"technical: {technical.get('justification', 'technical rejection')}",
            "agents_summary": f"Technical={t_dec}, Fundamental={f_dec} → vetoed by technical",
        }

    # Rule: Both confirm
    if t_dec == "CONFIRM" and f_dec == "CONFIRM":
        conf = "HIGH"
        return {
            "final_decision": "FIRED",
            "final_confidence": conf,
            "veto_reason": "",
            "agents_summary": f"Technical={t_dec}({technical.get('confidence','')}), Fundamental={f_dec}({fundamental.get('confidence','')}) → {conf}",
        }

    # Rule: One confirms, one neutral
    if t_dec == "CONFIRM" or f_dec == "CONFIRM":
        return {
            "final_decision": "FIRED",
            "final_confidence": "MODERATE",
            "veto_reason": "",
            "agents_summary": f"Technical={t_dec}, Fundamental={f_dec} → MODERATE (one agent neutral)",
        }

    # Rule: Both neutral — ambiguous
    return {
        "final_decision": "SHELVED",
        "final_confidence": None,
        "veto_reason": "ambiguous: both agents neutral",
        "agents_summary": f"Technical={t_dec}, Fundamental={f_dec} → ambiguous",
    }