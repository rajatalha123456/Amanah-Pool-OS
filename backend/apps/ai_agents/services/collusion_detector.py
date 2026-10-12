"""
Circle relationship indicators for Risk & Compliance review (BRD Section 9: AI flags, humans decide).

Only recorded data is used:
  * two or more members paid into the same bank account (identical IBAN);
  * two or more members registered with the same e-mail address;
  * a member who has already received the pot and now has an overdue contribution.

These are indicators for a person to look into - not findings, accusations or AML conclusions. Nothing is
inferred, guessed or generated: if the data shows no shared details, nothing is flagged.

(The previous version invented CNIC prefixes, home addresses and bank branches from a hash of the member
reference and always reported the first three members as a "guarantee ring"; it was removed in the audit.)
"""

from collections import defaultdict

from django.utils import timezone

from apps.circles.models import ArrearsRecord, ArrearsStatus, CircleMember, Payout, PayoutStatus

DISCLAIMER = (
    "Indicators from recorded member details only. They are prompts for review by Risk & Compliance, "
    "not findings, and must not be used to accuse or penalise a member without investigation."
)


def detect_fraud_and_collusion_network(tenant, pool_id=None):
    members = CircleMember.objects.filter(tenant=tenant).select_related("pool")
    if pool_id:
        members = members.filter(pool_id=pool_id)
    members = list(members)

    paid_out = set(
        Payout.objects.filter(member__in=members, status=PayoutStatus.DISBURSED).values_list("member_id", flat=True)
    )
    overdue = set(
        ArrearsRecord.objects.filter(member__in=members, status=ArrearsStatus.OVERDUE).values_list("member_id", flat=True)
    )

    by_iban, by_email = defaultdict(list), defaultdict(list)
    for m in members:
        iban = (m.iban or "").replace(" ", "").upper()
        if iban:
            by_iban[iban].append(m)
        email = (m.email or "").strip().lower()
        if email:
            by_email[email].append(m)

    clusters, edges = [], []
    flags = defaultdict(list)

    def add_cluster(kind, severity, title, description, group):
        cluster_id = f"{kind}-{len(clusters) + 1:02d}"
        clusters.append({
            "cluster_id": cluster_id, "cluster_type": kind, "severity": severity, "title": title,
            "description": description, "members": [m.member_name for m in group],
            "recommended_action": "Review the member records and, if needed, raise an exception case.",
        })
        for a, b in zip(group, group[1:]):
            edges.append({
                "id": f"{cluster_id}-{a.id}-{b.id}", "source": str(a.id), "target": str(b.id),
                "type": kind, "label": title, "severity": severity,
                "color": "#ef4444" if severity == "HIGH" else "#f59e0b",
            })
        for m in group:
            flags[m.id].append(title)

    for iban, group in by_iban.items():
        if len(group) > 1:
            add_cluster(
                "SHARED_BANK_ACCOUNT", "HIGH", f"Same payout account ({len(group)} members)",
                f"Members {', '.join(m.member_reference for m in group)} have the same IBAN ending {iban[-4:]}.", group,
            )
    for email, group in by_email.items():
        if len(group) > 1:
            add_cluster(
                "SHARED_EMAIL", "MEDIUM", f"Same e-mail address ({len(group)} members)",
                f"Members {', '.join(m.member_reference for m in group)} share one registered e-mail address.", group,
            )
    for m in members:
        if m.id in paid_out and m.id in overdue:
            flags[m.id].append("Received the pot and now has an overdue contribution")

    nodes = []
    for m in members:
        member_flags = flags.get(m.id, [])
        nodes.append({
            "id": str(m.id), "label": m.member_name, "ref": m.member_reference, "pool": m.pool.name,
            "payout_position": m.payout_position, "is_paid_out": m.id in paid_out,
            "risk_score": min(100, 30 * len(member_flags)),
            "risk_tier": "REVIEW" if member_flags else "NONE",
            "flags": member_flags, "type": "MEMBER",
        })

    flagged = sum(1 for n in nodes if n["flags"])
    summary_lines = [f"- [{c['severity']}] {c['title']}: {c['description']}" for c in clusters]
    summary_lines += [
        f"- {n['ref']}: {'; '.join(n['flags'])}" for n in nodes
        if any("overdue" in f for f in n["flags"])
    ]
    return {
        "success": True,
        "overall_network_risk": min(100, 20 * len(clusters) + 10 * flagged),
        "risk_tier": "REVIEW" if clusters or flagged else "NONE",
        "cluster_count": len(clusters),
        "suspicious_member_count": flagged,
        "clusters": clusters,
        "graph": {"nodes": nodes, "edges": edges},
        "investigation_dossier": (
            f"Circle relationship indicators - generated {timezone.now():%Y-%m-%d %H:%M} UTC\n\n"
            + ("\n".join(summary_lines) if summary_lines else "No shared bank accounts, e-mail addresses or post-payout arrears found.")
            + f"\n\n{DISCLAIMER}"
        ),
        "disclaimer": DISCLAIMER,
    }
