"""
CBS EOD SFTP Daemon & Balance Ingestion Engine (BRD Module 6 & 14)

Simulates production automated midnight batch feeds from Core Banking Systems
(Temenos T24, Oracle Flexcube Islamic, Finastra Fusion Midas).
Features:
- SFTP Handshake & Remote Path File Polling
- SHA-256 Cryptographic Checksum Verification (Sidecar validation)
- Float Discrepancy & Clearing Variance Detection
- Preview of the balance file only: this simulation never writes DailyBalance rows, import batches or
  exception cases (real balances come in through Balance Import).
"""

import hashlib
import json
from datetime import date
from decimal import Decimal
from django.utils import timezone
from apps.core.audit import log_action
from apps.pools.models import (
    BalanceImportBatchStatus,
    Pool,
)


class CBSDaemonScenario:
    CLEAN = "clean"
    FLOAT_DISCREPANCY = "float_discrepancy"
    CHECKSUM_MISMATCH = "checksum_mismatch"


def simulate_cbs_sftp_ingestion(
    tenant,
    pool: Pool,
    value_date: date,
    cbs_vendor: str = "Temenos T24",
    scenario: str = CBSDaemonScenario.CLEAN,
    user=None,
):
    """
    Executes automated CBS balance feed ingestion via simulated secure SFTP daemon.
    """
    now = timezone.now()
    file_name = f"{tenant.code}_{pool.code}_EOD_BALANCES_{value_date.strftime('%Y%m%d')}.csv"
    sftp_remote_path = f"/var/sftp/cbs_feeds/{cbs_vendor.lower().replace(' ', '_')}/{file_name}"
    sftp_host = "sftp-eod.cbs.amanah-bank.internal:2222"

    # 1. Base participant balance breakdown
    # Realistic segment breakdown for Islamic Banking Pools
    base_balances = [
        {
            "account_no": "PK78AMAN0001092837401",
            "title": "Amanah Mudarabah Retail Cluster",
            "participant_class": "Retail Regular",
            "ledger_balance": Decimal("25000000.00"),
            "uncleared_float": Decimal("0.00"),
            "available_balance": Decimal("25000000.00"),
            "currency": "PKR",
            "branch_code": "0101 (Karachi Main)",
        },
        {
            "account_no": "PK12AMAN0009837461928",
            "title": "Amanah High-Yield Saver Cluster",
            "participant_class": "Premium Saver",
            "ledger_balance": Decimal("40250000.00"),
            "uncleared_float": Decimal("0.00"),
            "available_balance": Decimal("40250000.00"),
            "currency": "PKR",
            "branch_code": "0104 (Lahore Gulberg)",
        },
        {
            "account_no": "PK55AMAN0007625149302",
            "title": "Amanah Wealth Management HNW Segment",
            "participant_class": "HNW Depositor",
            "ledger_balance": Decimal("26000000.00"),
            "uncleared_float": Decimal("0.00"),
            "available_balance": Decimal("26000000.00"),
            "currency": "PKR",
            "branch_code": "0108 (Islamabad F-7)",
        },
        {
            "account_no": "PK91AMAN0003418902741",
            "title": "Corporate Treasury & Institutional Placement",
            "participant_class": "Corporate / Institutional",
            "ledger_balance": Decimal("29000000.00"),
            "uncleared_float": Decimal("0.00"),
            "available_balance": Decimal("29000000.00"),
            "currency": "PKR",
            "branch_code": "0100 (Treasury Central)",
        },
    ]

    # Inject scenario deviations
    sftp_logs = [
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: Initializing secure SSH handshake with {sftp_host}...",
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: Authenticated via ed25519 host key. SFTP subsystem v3 ready.",
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: Polling remote directory {sftp_remote_path}...",
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: File found: {file_name} (Size: 18.4 KB). Downloading sidecar checksum {file_name}.sha256...",
    ]

    total_ledger = Decimal("0.00")
    total_float = Decimal("0.00")
    total_available = Decimal("0.00")

    records_payload = []
    has_discrepancy = False

    if scenario == CBSDaemonScenario.FLOAT_DISCREPANCY:
        # Corporate segment has uncleared float and clearing hold discrepancy
        for item in base_balances:
            rec = dict(item)
            if rec["participant_class"] == "Corporate / Institutional":
                rec["uncleared_float"] = Decimal("1450000.00")
                rec["available_balance"] = rec["ledger_balance"] - rec["uncleared_float"]
                rec["discrepancy_note"] = "NIFT 2nd clearing float hold pending SBP settlement confirmation."
                has_discrepancy = True
            records_payload.append(rec)
    else:
        records_payload = [dict(item) for item in base_balances]

    for r in records_payload:
        total_ledger += r["ledger_balance"]
        total_float += r["uncleared_float"]
        total_available += r["available_balance"]

    # Generate SHA-256
    raw_payload_str = json.dumps(
        [
            {
                "account_no": r["account_no"],
                "ledger": str(r["ledger_balance"]),
                "available": str(r["available_balance"]),
                "class": r["participant_class"],
            }
            for r in records_payload
        ],
        sort_keys=True,
    )
    computed_sha256 = hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()

    sidecar_sha256 = computed_sha256
    if scenario == CBSDaemonScenario.CHECKSUM_MISMATCH:
        sidecar_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        sftp_logs.append(
            f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: CRITICAL CHECKSUM MISMATCH! Expected {sidecar_sha256}, calculated {computed_sha256}."
        )
        sftp_logs.append(
            f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: Ingestion aborted to protect pool integrity against payload tampering."
        )
        return {
            "success": False,
            "simulated": True,
            "status": "CHECKSUM_ERROR",
            "message": "Cryptographic SHA-256 sidecar checksum verification failed. Ingestion rejected.",
            "cbs_vendor": cbs_vendor,
            "file_name": file_name,
            "sftp_remote_path": sftp_remote_path,
            "computed_sha256": computed_sha256,
            "sidecar_sha256": sidecar_sha256,
            "sftp_logs": sftp_logs,
            "records": [],
            "batch": None,
        }

    sftp_logs.append(
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: SHA-256 Verified: {computed_sha256[:16]}... matches sidecar."
    )
    sftp_logs.append(
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: Ingesting {len(records_payload)} accounts. Parsing balances..."
    )

    # SIMULATION ONLY: nothing below touches DailyBalance, import batches or exception cases. The figures are
    # fixed demo values; feeding them into real pool data would distort profit allocation (audit finding).
    batch_status = BalanceImportBatchStatus.EXCEPTION if has_discrepancy else BalanceImportBatchStatus.BALANCED
    sftp_logs.append(
        f"[{now.strftime('%H:%M:%S.%f')[:-3]}] SFTP_DAEMON: SIMULATION - preview only, nothing was written to the pool."
    )

    log_action(
        tenant=tenant,
        actor=user,
        action="cbs_sftp_ingestion",
        model_name="BalanceImportBatch",
        object_id=file_name,
        changes={
            "cbs_vendor": cbs_vendor,
            "scenario": scenario,
            "sha256": computed_sha256,
            "total_records": len(records_payload),
            "total_ledger": str(total_ledger),
            "total_available": str(total_available),
            "total_float": str(total_float),
            "status": batch_status,
            "simulated_preview_only": True,
        },
    )

    return {
        "success": True,
        "simulated": True,
        "status": "BALANCED" if not has_discrepancy else "EXCEPTION",
        "message": (
            f"CBS EOD batch successfully ingested from {cbs_vendor}."
            if not has_discrepancy
            else f"CBS EOD batch ingested with float discrepancy alerts ({cbs_vendor})."
        ),
        "cbs_vendor": cbs_vendor,
        "file_name": file_name,
        "sftp_remote_path": sftp_remote_path,
        "computed_sha256": computed_sha256,
        "sidecar_sha256": sidecar_sha256,
        "sftp_logs": sftp_logs,
        "summary": {
            "total_records": len(records_payload),
            "matched_records": len(records_payload) - (1 if has_discrepancy else 0),
            "exception_count": 1 if has_discrepancy else 0,
            "total_ledger": float(total_ledger),
            "total_float": float(total_float),
            "total_available": float(total_available),
        },
        "records": [
            {
                "account_no": r["account_no"],
                "title": r["title"],
                "participant_class": r["participant_class"],
                "ledger_balance": float(r["ledger_balance"]),
                "uncleared_float": float(r["uncleared_float"]),
                "available_balance": float(r["available_balance"]),
                "currency": r["currency"],
                "branch_code": r["branch_code"],
                "status": "FLOAT_HOLD" if r["uncleared_float"] > 0 else "SETTLED",
                "discrepancy_note": r.get("discrepancy_note", ""),
            }
            for r in records_payload
        ],
        "batch": None,
        "note": "Simulation preview only - no balances were imported. Use Balance Import for real data.",
    }
