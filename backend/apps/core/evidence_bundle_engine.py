"""
Regulatory Evidence Bundle Builder
BRD Screen Inventory: AI & Assurance Screen 7 / Screen 39 ("Evidence bundle builder")

Compiles a sealed evidence package for a pool and period from recorded data
only. Nothing is defaulted or invented: when a piece of evidence does not
exist the artifact says `available: false`, and `verified` is true only when
a real check on the stored data passes (hash recomputation, balanced journal,
certified period, intact audit chain, ...). The master seal is a SHA-256 over
the artifact hashes, so any later change to the compiled bundle is detectable.

Artifacts
  ART-01 Shariah decision backing the pool contract and its quorum votes
  ART-02 Period close checklist / certification
  ART-03 Signed allocation run (inputs, rules used, outputs, calculation hash)
  ART-04 Journal batches posted for the run
  ART-05 Payout clearing batch (rails are SIMULATED - flagged in the artifact)
  ART-06 Concentration-risk scorecard
  ART-07 Reconciliation record
  ART-08 Audit trail chain verification (tamper-evident hash chain)
"""

import hashlib
import io
import json
import zipfile
from datetime import datetime

from django.utils import timezone


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_of(data) -> str:
    return _sha256(json.dumps(data, sort_keys=True, default=str))


def _artifact(meta, verified):
    meta = dict(meta)
    meta["verified"] = bool(verified)
    return {"meta": meta, "hash": _hash_of(meta), "verified": bool(verified)}


def _missing(artifact_id, name, reason):
    return _artifact({"artifact_id": artifact_id, "name": name, "available": False, "reason": reason}, False)


class EvidenceBundleEngine:
    """Compiles and seals evidence bundles from recorded data."""

    @classmethod
    def compile_bundle(cls, pool_id: str, period_date: str, audit_type: str, user, tenant):
        from apps.accounting.models import JournalBatch, ReconciliationBatch
        from apps.allocation.engine import compute_run_hash
        from apps.allocation.models import AllocationRun, AllocationRunStatus, PayoutBatchRecord
        from apps.core.merkle_engine import MerkleAuditEngine
        from apps.core.models import AuditLog
        from apps.pools.concentration_engine import run_concentration_risk_analysis
        from apps.pools.models import PeriodCloseChecklist, Pool
        from apps.products.shariah import shariah_decision_for

        try:
            target_date = datetime.strptime(period_date, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValueError("period_date must be a valid date in YYYY-MM-DD format.")

        # Tenant-scoped lookup: a pool of another tenant is simply not found.
        pool = Pool._base_manager.filter(id=pool_id, tenant=tenant).first()
        if pool is None:
            raise ValueError("Pool not found.")

        period_month_str = target_date.strftime("%B %Y")
        bundle_id = f"EVID-{pool.code}-{target_date.strftime('%Y%m')}-{audit_type[:4].upper()}"
        artifacts = []

        # ART-01 - Shariah decision backing the pool contract
        decision = pool.product.contract_template.shariah_decision
        if decision is None:
            artifacts.append(_missing("ART-01-SHARIAH-DECISION", "Shariah decision and quorum attestation",
                                      "The pool's contract template has no linked Shariah decision."))
        else:
            in_force = shariah_decision_for(pool) is not None
            artifacts.append(
                _artifact(
                    {
                        "artifact_id": "ART-01-SHARIAH-DECISION",
                        "name": "Shariah decision and quorum attestation",
                        "available": True,
                        "decision_code": decision.decision_code,
                        "title": decision.title,
                        "status": decision.status,
                        "in_force": in_force,
                        "effective_date": decision.effective_date.isoformat(),
                        "expiry_date": decision.expiry_date.isoformat() if decision.expiry_date else None,
                        "approved_at": decision.approved_at.isoformat() if decision.approved_at else None,
                        "quorum_votes": [
                            {
                                "scholar_name": vote.scholar_name,
                                "scholar_title": vote.scholar_title,
                                "vote": vote.decision_vote,
                                "digital_signature_hash": vote.digital_signature_hash,
                                "voted_at": vote.voted_at.isoformat() if vote.voted_at else None,
                            }
                            for vote in decision.quorum_votes.all()
                        ],
                    },
                    verified=in_force,
                )
            )

        # ART-02 - Period close
        closes = PeriodCloseChecklist._base_manager.filter(tenant=tenant, pool=pool)
        close = (
            closes.filter(period_start__lte=target_date, period_end__gte=target_date).order_by("-period_end").first()
        )
        if close is None:
            artifacts.append(_missing("ART-02-PERIOD-CLOSE", "Period close certification",
                                      f"No period close record covers {target_date}."))
        else:
            artifacts.append(
                _artifact(
                    {
                        "artifact_id": "ART-02-PERIOD-CLOSE",
                        "name": "Period close certification",
                        "available": True,
                        "period_start": close.period_start.isoformat(),
                        "period_end": close.period_end.isoformat(),
                        "status": close.status,
                        "checklist": close.checklist_data or {},
                        "certified_by": close.certified_by.email if close.certified_by else None,
                        "certified_at": close.certified_at.isoformat() if close.certified_at else None,
                        "decision_note": close.decision_note,
                    },
                    verified=close.status in ("certified", "locked"),
                )
            )

        # ART-03 - Signed allocation run covering the target date
        run = (
            AllocationRun._base_manager.filter(
                tenant=tenant, pool=pool, status=AllocationRunStatus.SIGNED,
                value_date__gte=target_date,
            )
            .order_by("value_date")
            .first()
        )
        if run is not None and run.effective_period_start > target_date:
            run = None
        if run is None:
            artifacts.append(_missing("ART-03-ALLOCATION", "Signed profit allocation run",
                                      f"No signed allocation run covers {target_date}."))
        else:
            lines = list(run.lines.select_related("account__participant"))
            hash_ok = bool(run.calculation_hash) and compute_run_hash(run) == run.calculation_hash
            artifacts.append(
                _artifact(
                    {
                        "artifact_id": "ART-03-ALLOCATION",
                        "name": "Signed profit allocation run",
                        "available": True,
                        "run_id": str(run.id),
                        "period_start": run.effective_period_start.isoformat(),
                        "period_end": run.value_date.isoformat(),
                        "gross_income": str(run.gross_income),
                        "direct_expenses": str(run.direct_expenses),
                        "distributable_amount": str(run.distributable_amount),
                        "depositor_pool_share": str(run.depositor_pool_share),
                        "mudarib_share": str(run.mudarib_share),
                        "per_amount": str(run.per_amount),
                        "irr_amount": str(run.irr_amount),
                        "rounding_residual": str(run.rounding_residual),
                        "config_snapshot": run.config_snapshot,
                        "calculation_hash": run.calculation_hash,
                        "hash_recomputes": hash_ok,
                        "maker": run.created_by.email if run.created_by else None,
                        "checker": run.checked_by.email if run.checked_by else None,
                        "shariah_signed_off_by": run.shariah_signed_off_by.email if run.shariah_signed_off_by else None,
                        "line_count": len(lines),
                        "lines": [
                            {
                                "account_number": line.account.account_number if line.account else None,
                                "participant": line.account.participant.full_name if line.account else None,
                                "participant_class": line.participant_class,
                                "average_funds": str(line.daily_funds),
                                "weightage": str(line.weightage),
                                "allocated_amount": str(line.allocated_amount),
                            }
                            for line in lines
                        ],
                    },
                    verified=hash_ok,
                )
            )

        # ART-04 - Journals posted for the run (and any reversals of it)
        if run is None:
            artifacts.append(_missing("ART-04-GL-JOURNALS", "Journal batches", "No signed allocation run in scope."))
        else:
            batches = list(
                JournalBatch._base_manager.filter(tenant=tenant, allocation_run=run)
                | JournalBatch._base_manager.filter(tenant=tenant, reverses_batch__allocation_run=run)
            )
            artifacts.append(
                _artifact(
                    {
                        "artifact_id": "ART-04-GL-JOURNALS",
                        "name": "Journal batches",
                        "available": bool(batches),
                        "batches": [
                            {
                                "id": str(batch.id),
                                "batch_date": batch.batch_date.isoformat(),
                                "total_debit": str(batch.total_debit),
                                "total_credit": str(batch.total_credit),
                                "is_balanced": batch.total_debit == batch.total_credit,
                                "reverses_batch": str(batch.reverses_batch_id) if batch.reverses_batch_id else None,
                                "entries": [
                                    {"account_name": e.account_name, "entry_type": e.entry_type, "amount": str(e.amount)}
                                    for e in batch.entries.all()
                                ],
                            }
                            for batch in batches
                        ],
                    },
                    verified=bool(batches) and all(b.total_debit == b.total_credit for b in batches),
                )
            )

        # ART-05 - Payout clearing batch (read-only: never created as a side effect)
        payout = (
            PayoutBatchRecord._base_manager.filter(tenant=tenant, allocation_run=run).first() if run else None
        )
        if payout is None:
            artifacts.append(_missing("ART-05-PAYOUT-CLEARING", "Payout clearing batch",
                                      "No payout batch has been prepared for the run."))
        else:
            batch = payout.payload
            artifacts.append(
                _artifact(
                    {
                        "artifact_id": "ART-05-PAYOUT-CLEARING",
                        "name": "Payout clearing batch",
                        "available": True,
                        "mode": batch.get("mode", "SIMULATION"),
                        "note": "Clearing rails are simulated; no funds moved through Raast/1LINK.",
                        "batch_code": batch.get("batch_code"),
                        "status": batch.get("status"),
                        "total_records": batch.get("total_records"),
                        "total_gross_profit": batch.get("total_gross_profit"),
                        "total_wht_deducted": batch.get("total_wht_deducted"),
                        "total_net_disbursed": batch.get("total_net_disbursed"),
                        "maker_email": batch.get("maker_email"),
                        "checker_email": batch.get("checker_email"),
                        "gates_verified": batch.get("gates_verified"),
                        "journal_batch_id": batch.get("journal_batch_id"),
                    },
                    verified=bool(batch.get("gates_verified")) and batch.get("mode") != "SIMULATION",
                )
            )

        # ART-06 - Concentration-risk scorecard
        concentration = run_concentration_risk_analysis(pool=pool)
        breaches = concentration.get("breach_summary", {}).get("breaches_count", 0)
        artifacts.append(
            _artifact(
                {
                    "artifact_id": "ART-06-CONCENTRATION-RISK",
                    "name": "Concentration-risk scorecard",
                    "available": True,
                    "total_portfolio_exposure": float(concentration.get("total_portfolio_exposure", 0.0)),
                    "asset_count": concentration.get("asset_count", 0),
                    "breaches_count": breaches,
                    "early_warnings_count": concentration.get("breach_summary", {}).get("early_warnings_count", 0),
                    "top_obligors": concentration.get("obligors", [])[:3],
                    "sector_concentrations": concentration.get("sectors", [])[:4],
                },
                verified=breaches == 0,
            )
        )

        # ART-07 - Reconciliation record
        recon = (
            ReconciliationBatch._base_manager.filter(
                tenant=tenant, pool=pool, reconciliation_date__lte=target_date
            )
            .order_by("-reconciliation_date")
            .first()
        )
        if recon is None:
            artifacts.append(_missing("ART-07-RECONCILIATION", "Reconciliation record",
                                      f"No reconciliation recorded on or before {target_date}."))
        else:
            artifacts.append(
                _artifact(
                    {
                        "artifact_id": "ART-07-RECONCILIATION",
                        "name": "Reconciliation record",
                        "available": True,
                        "reconciliation_date": recon.reconciliation_date.isoformat(),
                        "source_system": recon.source_system,
                        "total_records": recon.total_records,
                        "matched_records": recon.matched_records,
                        "exception_count": recon.exception_count,
                        "variance_amount": str(recon.variance_amount),
                        "status": recon.status,
                        "performed_by": recon.performed_by.email if recon.performed_by else None,
                    },
                    verified=recon.status in ("matched", "cleared") and recon.variance_amount == 0,
                )
            )

        # ART-08 - Audit trail chain verification
        chain = MerkleAuditEngine.verify_merkle_chain(AuditLog.objects.filter(tenant=tenant))
        artifacts.append(
            _artifact(
                {
                    "artifact_id": "ART-08-AUDIT-CHAIN",
                    "name": "Audit trail hash-chain verification",
                    "available": chain["total_blocks"] > 0,
                    "chain_status": chain["status"],
                    "sealed_entries": chain["total_blocks"],
                    "tampered_entries": chain["tampered_count"],
                    "unsealed_legacy_entries": chain["unsealed_legacy_entries"],
                    "current_merkle_root": chain["current_merkle_root"],
                    "verified_at": chain["verified_at"],
                    "note": chain["note"],
                },
                verified=chain["status"] == "VERIFIED" and chain["total_blocks"] > 0,
            )
        )

        master_seal = f"SEAL-SHA256:{_sha256(':'.join(a['hash'] for a in artifacts)).upper()}"
        available = [a for a in artifacts if a["meta"].get("available")]

        return {
            "bundle_id": bundle_id,
            "pool_id": str(pool.id),
            "pool_name": pool.name,
            "pool_code": pool.code,
            "period_month": period_month_str,
            "target_date": target_date.isoformat(),
            "audit_type": audit_type,
            "compiled_at": timezone.now().isoformat(),
            "compiled_by_email": user.email,
            "master_bundle_seal": master_seal,
            "artifacts_count": len(artifacts),
            "artifacts_available": len(available),
            "artifacts_verified": sum(1 for a in artifacts if a["verified"]),
            "all_verified": all(a["verified"] for a in artifacts),
            "artifacts": artifacts,
            "payout_batch_available": payout is not None,
            "xml_pacs008_available": payout is not None,
        }

    @classmethod
    def generate_zip_archive(cls, bundle_payload, tenant=None):
        """Builds the in-memory ZIP: manifest, dossier and one JSON per artifact."""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("00_AUDIT_MANIFEST.json", json.dumps(bundle_payload, indent=2, default=str))

            dossier = [
                "# EVIDENCE DOSSIER",
                f"**Bundle:** `{bundle_payload['bundle_id']}`",
                f"**Pool:** {bundle_payload['pool_name']} ({bundle_payload['pool_code']})",
                f"**Period:** {bundle_payload['period_month']}",
                f"**Audit type:** {bundle_payload['audit_type']}",
                f"**Compiled:** {bundle_payload['compiled_at']} by {bundle_payload['compiled_by_email']}",
                f"**Master seal:** `{bundle_payload['master_bundle_seal']}`",
                "",
                f"Artifacts available: {bundle_payload['artifacts_available']}/{bundle_payload['artifacts_count']} - "
                f"verified: {bundle_payload['artifacts_verified']}/{bundle_payload['artifacts_count']}",
                "",
                "Each artifact is verified only when a check on the stored data passes; "
                "missing evidence is reported as unavailable, not assumed.",
                "",
            ]
            for index, artifact in enumerate(bundle_payload["artifacts"], start=1):
                meta = artifact["meta"]
                state = "VERIFIED" if artifact["verified"] else ("NOT VERIFIED" if meta.get("available") else "UNAVAILABLE")
                dossier.append(f"## {index}. {meta['name']} (`{meta['artifact_id']}`) - {state}")
                dossier.append(f"- SHA-256: `{artifact['hash']}`")
                if meta.get("reason"):
                    dossier.append(f"- Reason: {meta['reason']}")
                dossier.append("")
            zip_file.writestr("01_DOSSIER.md", "\n".join(dossier))

            for artifact in bundle_payload["artifacts"]:
                zip_file.writestr(f"{artifact['meta']['artifact_id']}.json", json.dumps(artifact["meta"], indent=2, default=str))

            # ISO 20022 message of the persisted payout batch, if one exists (read-only).
            if bundle_payload.get("payout_batch_available") and tenant is not None:
                from apps.allocation.models import PayoutBatchRecord
                from apps.allocation.payout_clearing_engine import PayoutClearingEngine

                record = (
                    PayoutBatchRecord._base_manager.filter(
                        tenant=tenant, payload__pool_id=bundle_payload["pool_id"]
                    )
                    .order_by("-created_at")
                    .first()
                )
                if record is not None:
                    zip_file.writestr(
                        "06_PAYOUT_ISO20022_PACS008_SIMULATION.xml",
                        PayoutClearingEngine.generate_iso20022_pacs008_xml(record.payload),
                    )

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
