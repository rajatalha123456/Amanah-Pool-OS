"""Mandatory contract parameters per contract type (BRD 5 / 6.1)."""

# BRD 5 (Contract): type/version, Rab-ul-Maal, Mudarib/partner/agent, PSR, Wakalah fee and loss basis. These are the
# parameters a template of each contract type must state before the Shariah Board can approve it (BRD 6.1 step 2).
PARTY_CLAUSES = [
    {"key": "rab_ul_maal", "label": "Rab-ul-Maal (capital provider)", "description": "Who provides the capital."},
    {"key": "mudarib", "label": "Mudarib (manager)", "description": "Who manages the capital for a share of profit."},
    {"key": "partners", "label": "Partners", "description": "The Musharakah partners and how capital is contributed."},
    {"key": "principal", "label": "Principal", "description": "On whose behalf the agent acts."},
    {"key": "agent", "label": "Agent (Wakil)", "description": "Who acts as agent."},
    {"key": "wakalah_fee", "label": "Wakalah fee", "description": "The agent's fixed, disclosed fee."},
    {"key": "parties", "label": "Lender and borrower", "description": "Who lends and who borrows under the Qard."},
]
MANDATORY_PARAMETERS = {
    "mudarabah_unrestricted": ["rab_ul_maal", "mudarib", "profit_ratio", "loss_bearing_clause"],
    "mudarabah_restricted": ["rab_ul_maal", "mudarib", "profit_ratio", "loss_bearing_clause"],
    "musharakah": ["partners", "profit_ratio", "loss_bearing_clause"],
    "wakalah": ["principal", "agent", "wakalah_fee", "loss_bearing_clause"],
    "qard": ["parties", "late_payment_policy"],
}


def missing_parameters(template):
    clauses = template.clauses if isinstance(template.clauses, dict) else {}
    return [key for key in MANDATORY_PARAMETERS.get(template.contract_type, []) if not str(clauses.get(key) or "").strip()]
