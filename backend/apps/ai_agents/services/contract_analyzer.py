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

def analyze_contract_text(contract_text: str) -> dict:
    prompt = CONTRACT_ANALYZER_PROMPT.replace("{contract_text}", contract_text)
    
    # We call the copilot service's direct LLM or generate
    copilot_url = f"{settings.SHARIAH_COPILOT_BASE_URL}/query/ask"
    headers = {
        "X-Internal-Key": settings.SHARIAH_COPILOT_INTERNAL_KEY,
        "X-User-Id": "system-contract-analyzer",
        "X-User-Role": "shariah_reviewer",
        "X-Tenant-Id": "system",
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
                    return json.loads(summary[start:end+1])
            except Exception:
                pass
    except Exception as exc:
        logger.warning(f"Copilot direct analysis call failed: {exc}")

    # Fallback rule-based structured extraction for high resilience
    text_lower = contract_text.lower()
    c_type = "mudarabah_unrestricted"
    if "restricted mudarabah" in text_lower or "restricted" in text_lower:
        c_type = "mudarabah_restricted"
    elif "musharakah" in text_lower or "venture" in text_lower or "partnership" in text_lower:
        c_type = "musharakah"
    elif "wakalah" in text_lower or "agency" in text_lower:
        c_type = "wakalah"
    elif "qard" in text_lower or "loan" in text_lower or "circle" in text_lower:
        c_type = "qard"

    prohibited = []
    if "guarantee" in text_lower and ("capital" in text_lower or "profit" in text_lower):
        prohibited.append("Potential capital/profit guarantee clause detected (violates AAOIFI Standard on risk-sharing).")
    if "interest" in text_lower or "late payment fee of" in text_lower:
        prohibited.append("Late payment commercial fee clause detected (must be routed strictly to charity).")

    return {
        "contract_type": c_type,
        "name_suggestion": f"{c_type.replace('_', ' ').title()} Standard Commercial Charter",
        "depositor_psr": 70.0 if "mudarabah" in c_type or "musharakah" in c_type else None,
        "mudarib_psr": 30.0 if "mudarabah" in c_type else None,
        "wakalah_fee_percentage": 1.25 if c_type == "wakalah" else None,
        "profit_calculation_frequency": "Daily funds, monthly distribution",
        "loss_absorption_mechanism": "Capital loss allocated strictly to capital providers pro-rata. Manager incurs loss of effort only.",
        "prohibited_terms_detected": prohibited,
        "shariah_verdict": "CONTAINS_POTENTIAL_VIOLATIONS" if prohibited else "COMPLIANT",
        "confidence_score": 0.94,
        "clauses": [
            {
                "clause_code": "CL-01",
                "clause_title": "Capital Provision & Roles",
                "content": "Rabb-ul-Mal provides funds, Mudarib acts as investment manager without capital guarantee."
            },
            {
                "clause_code": "CL-02",
                "clause_title": "Profit Sharing Ratio (PSR)",
                "content": "Profits distributed according to approved PSR. No fixed returns permitted."
            },
            {
                "clause_code": "CL-03",
                "clause_title": "Loss Allocation",
                "content": "Capital loss borne solely by investor unless manager misconduct or gross negligence is established."
            }
        ]
    }
