import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger("apps")

CONTRACT_ANALYZER_PROMPT = """You are the AI Contract Analyzer for Amanah Pool OS, an institutional Islamic banking system.
Your job is to analyze the provided Islamic financial contract or legal clauses and extract the parameters into a strictly valid JSON object.

Extract these exact fields:
1. "contract_type": one of ["mudarabah_unrestricted", "mudarabah_restricted", "musharakah", "wakalah", "qard"]
2. "name_suggestion": a clean recommended title (e.g. "Unrestricted Mudarabah Term Deposit Charter v1.0")
3. "depositor_psr": number percentage (e.g. 70.0), or null if not applicable
4. "mudarib_psr": number percentage (e.g. 30.0), or null if not applicable
5. "wakalah_fee_percentage": number (e.g. 1.5) or null
6. "profit_calculation_frequency": e.g. "Daily funds, monthly distribution"
7. "loss_absorption_mechanism": 1-2 sentence description of who absorbs capital loss
8. "prohibited_terms_detected": list of strings (e.g. ["Capital guarantee clause violates AAOIFI Mudarabah Standard 13", "Fixed interest uplift prohibited"]), empty list [] if clean.
9. "shariah_verdict": "COMPLIANT" if clean, or "CONTAINS_POTENTIAL_VIOLATIONS" if prohibited terms found.
10. "confidence_score": number between 0.0 and 1.0 (e.g. 0.96)
11. "clauses": list of extracted clause objects: [{"clause_code": "CL-01", "clause_title": "...", "content": "..."}]

CONTRACT TEXT TO ANALYZE:
{contract_text}

Respond ONLY with the JSON object. Do not include markdown code block syntax (like ```json), commentary, or extra text.
"""

def analyze_contract_text(contract_text: str, tenant_code: str, user_id: str = "") -> dict:
    prompt = CONTRACT_ANALYZER_PROMPT.replace("{contract_text}", contract_text)
    
    # We call the copilot service's direct LLM or generate
    copilot_url = f"{settings.SHARIAH_COPILOT_BASE_URL}/query/ask"
    headers = {
        "X-Internal-Key": settings.SHARIAH_COPILOT_INTERNAL_KEY,
        "X-User-Id": str(user_id) or "contract-analyzer",
        "X-User-Role": "shariah_reviewer",
        # Retrieval stays inside the caller's own tenant (BR-010).
        "X-Tenant-Id": tenant_code,
    }
    
    # Alternatively call Copilot's raw LLM or use fallbacks
    try:
        response = requests.post(
            copilot_url,
            headers=headers,
            json={"user_id": "analyzer", "question": prompt, "filters": {}},
            timeout=45
        )
        if response.ok:
            data = response.json()
            summary = data.get("research_summary", "")
            # If summary contains JSON or raw data
            try:
                # Find JSON substring if wrapped
                start = summary.find("{")
                end = summary.rfind("}")
                if start != -1 and end != -1:
                    return _with_review_flags(json.loads(summary[start:end+1]), source="shariah_copilot_llm")
            except Exception:
                pass
    except Exception as exc:
        logger.warning(f"Copilot direct analysis call failed: {exc}")

    # Fallback when the AI service is unavailable or returns nothing usable: a plain
    # keyword screen. It never guesses commercial terms (PSR, fees, clauses) and always
    # routes to a human (BRD Section 9: low confidence routes to human).
    text_lower = contract_text.lower()
    c_type = None
    if "restricted mudarabah" in text_lower or ("restricted" in text_lower and "mudarabah" in text_lower):
        c_type = "mudarabah_restricted"
    elif "mudarabah" in text_lower:
        c_type = "mudarabah_unrestricted"
    elif "musharakah" in text_lower:
        c_type = "musharakah"
    elif "wakalah" in text_lower:
        c_type = "wakalah"
    elif "qard" in text_lower:
        c_type = "qard"

    prohibited = []
    if "guarantee" in text_lower and ("capital" in text_lower or "profit" in text_lower):
        prohibited.append("Possible capital/profit guarantee wording - needs Shariah review.")
    if "interest" in text_lower or "late payment fee" in text_lower:
        prohibited.append("Possible interest / late-payment fee wording - needs Shariah review.")

    return _with_review_flags(
        {
            "contract_type": c_type,
            "name_suggestion": None,
            "depositor_psr": None,
            "mudarib_psr": None,
            "wakalah_fee_percentage": None,
            "profit_calculation_frequency": None,
            "loss_absorption_mechanism": None,
            "prohibited_terms_detected": prohibited,
            "shariah_verdict": "CONTAINS_POTENTIAL_VIOLATIONS" if prohibited else "REQUIRES_HUMAN_REVIEW",
            "confidence_score": 0.2,
            "clauses": [],
        },
        source="keyword_screen_fallback",
    )


def _with_review_flags(result: dict, source: str) -> dict:
    """Every AI output carries its source, confidence and whether a human must review it (BR-009)."""
    try:
        confidence = float(result.get("confidence_score"))
    except (TypeError, ValueError):
        confidence = 0.0
    result["confidence_score"] = confidence
    result["source"] = source
    result["requires_human_review"] = confidence < 0.8 or source != "shariah_copilot_llm"
    result["disclaimer"] = "AI-assisted extraction only; it is not a Shariah ruling and must be confirmed by a qualified reviewer."
    return result
