"""
Senior Agent — Coordination Layer.

Programmatic rule engine (NOT an LLM call).
Combines Agent A (Technical) and Agent B (Fundamental) into a final decision.
"""

from typing import Dict, Any


def synthesize(
    technical: Dict[str, Any],
    fundamental: Dict[str, Any],
    fundamental_reject_streak: int = 0,
) -> Dict[str, Any]:
    """
    Combine technical and fundamental agent verdicts into a final decision.

    Decision table:
        Technical | Fundamental | Result
        CONFIRM   | CONFIRM     | FIRED (HIGH confidence)
        CONFIRM   | NEUTRAL     | FIRED (MODERATE confidence)
        NEUTRAL   | CONFIRM     | FIRED (MODERATE confidence)
        REJECT    | *           | SHELVED (technical rejection)
        *         | REJECT      | SHELVED (fundamental veto — soft after 3 streaks)
        NEUTRAL   | NEUTRAL     | SHELVED (ambiguous)

    Soft-veto: after `fundamental_reject_streak` >= 3 consecutive fund-REJECTs
    on this pair, a HIGH-CONFIRM from Agent A can override the veto (FIRED, LOW confidence).
    """
    t_dec = technical.get("decision", "NEUTRAL")
    f_dec = fundamental.get("decision", "NEUTRAL")

    # Rule: Fundamental rejection — with soft-veto after 3 strikes
    if f_dec == "REJECT":
        if fundamental_reject_streak >= 3 and t_dec == "CONFIRM" and technical.get("confidence") == "HIGH":
            return {
                "final_decision": "FIRED",
                "final_confidence": "LOW",
                "veto_reason": "",
                "agents_summary": (
                    f"Technical={t_dec}(HIGH), Fundamental={f_dec} → FIRED "
                    f"(soft-veto active: Agent B rejected {fundamental_reject_streak}x consecutively)"
                ),
            }
        return {
            "final_decision": "SHELVED",
            "final_confidence": None,
            "veto_reason": f"fundamental: {fundamental.get('justification', 'macro rejection')}",
            "agents_summary": f"Technical={t_dec}, Fundamental={f_dec} → vetoed by fundamental (streak={fundamental_reject_streak})",
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


def synthesize_borderline(
    technical: Dict[str, Any],
    fundamental: Dict[str, Any],
    fundamental_reject_streak: int = 0,
) -> Dict[str, Any]:
    """
    Stricter synthesis for borderline-range signals. Same soft-veto rules apply.
    """
    t_dec = technical.get("decision", "NEUTRAL")
    f_dec = fundamental.get("decision", "NEUTRAL")

    # Rule: Fundamental rejection — with soft-veto after 3 strikes
    if f_dec == "REJECT":
        if fundamental_reject_streak >= 3 and t_dec == "CONFIRM" and technical.get("confidence") == "HIGH":
            return {
                "final_decision": "FIRED",
                "final_confidence": "LOW",
                "veto_reason": "",
                "agents_summary": (
                    f"[Borderline] Technical={t_dec}(HIGH), Fundamental={f_dec} → FIRED "
                    f"(soft-veto active: Agent B rejected {fundamental_reject_streak}x consecutively)"
                ),
            }
        return {
            "final_decision": "SHELVED",
            "final_confidence": None,
            "veto_reason": f"fundamental: {fundamental.get('justification', 'macro rejection')}",
            "agents_summary": f"[Borderline] Technical={t_dec}, Fundamental={f_dec} → vetoed by fundamental (streak={fundamental_reject_streak})",
        }

    # Rule: Technical rejection
    if t_dec == "REJECT":
        return {
            "final_decision": "SHELVED",
            "final_confidence": None,
            "veto_reason": f"technical: {technical.get('justification', 'technical rejection')}",
            "agents_summary": f"[Borderline] Technical={t_dec}, Fundamental={f_dec} → vetoed by technical",
        }

    # Rule: Both must CONFIRM — model is weak, agents carry the conviction
    if t_dec == "CONFIRM" and f_dec == "CONFIRM":
        return {
            "final_decision": "FIRED",
            "final_confidence": "MODERATE",
            "veto_reason": "",
            "agents_summary": f"[Borderline] Technical=CONFIRM, Fundamental=CONFIRM → FIRED (both agents overrode weak model)",
        }

    # Anything else: not enough conviction
    return {
        "final_decision": "SHELVED",
        "final_confidence": None,
        "veto_reason": f"borderline: both agents must confirm (got T={t_dec}, F={f_dec})",
        "agents_summary": f"[Borderline] Technical={t_dec}, Fundamental={f_dec} → insufficient for borderline entry",
    }