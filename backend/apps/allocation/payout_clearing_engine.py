"""
Core-Banking Clearing & Raast / 1LINK Payout Batch (SIMULATED RAILS)

Batches are persisted (PayoutBatchRecord) and built from real signed allocation
lines and participant beneficiary data. The *rails* are simulated: no message is
transmitted to Raast/1LINK and no money moves; every batch and result carries
mode = "SIMULATION" until a real switch integration exists.
BRD Module 14 / Screen 35: Payout Execution Engine & Clearing Rails

Implements:
1. Automated Batch Generation from Certified Allocation Runs / Period Close
2. 5-Gate Pre-Disbursement Verification (Fatwa Seal, MOD-97 IBAN, FBR ATL Tax, SBP Liquidity, Maker-Checker)
3. ISO 20022 pacs.008.001.08 XML clearing feed generation for SBP Raast switch
4. Real-time Clearing & Settlement Simulation with 1LINK & Raast clearing response handling
5. Automatic Contra-Accounting GL Voucher generation to clear pool profit payable liabilities
"""

import hashlib
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from django.utils import timezone
from django.db import transaction



MODE_SIMULATION = "SIMULATION"


def _validate_pakistan_iban(iban: str) -> bool:
    """Validates Pakistani 24-character IBAN using MOD-97 algorithm."""
    clean = iban.replace(" ", "").upper()
    if len(clean) != 24 or not clean.startswith("PK"):
        return False
    # Reorder: move 4 initial characters to end
    reordered = clean[4:] + clean[:4]
    # Replace letters with 10-35
    numeric_str = ""
    for ch in reordered:
        if ch.isalpha():
            numeric_str += str(ord(ch) - 55)
        elif ch.isdigit():
            numeric_str += ch
        else:
            return False
    return int(numeric_str) % 97 == 1


class PayoutClearingEngine:
    """Enterprise Clearing & Settlement Controller for SBP Raast and 1LINK rails."""

    @classmethod
    def get_or_create_batch_for_run(cls, allocation_run, tenant, force_regenerate=False):
        from apps.allocation.models import PayoutBatchRecord

        existing = PayoutBatchRecord._base_manager.filter(
            tenant_id=allocation_run.tenant_id, allocation_run_id=allocation_run.id
        ).first()
        if existing is not None:
            if not force_regenerate:
                return existing.payload
            if existing.status not in ("draft", "validated"):
                raise ValueError(
                    f"A batch in status '{existing.status}' can no longer be regenerated."
                )
        if allocation_run.status != "signed":
            raise ValueError("Payout batches can only be built from a signed allocation run.")

        pool = allocation_run.pool
        value_date = allocation_run.value_date
        batch_code = f"BATCH-SBP-CLR-{pool.code}-{value_date.strftime('%Y%m')}-01"

        # Read allocation lines from allocation run
        from apps.allocation.models import AllocationLine

        # One payment per participant account that earned a profit. Beneficiary
        # details come from the participant record; class-level (legacy) lines
        # have no beneficiary and so produce no payment.
        lines = list(
            AllocationLine._base_manager.filter(allocation_run=allocation_run, account__isnull=False)
            .select_related("account__participant")
            .order_by("participant_class", "account__account_number")
        )
        recipients = []
        for line in lines:
            participant = line.account.participant
            if line.allocated_amount <= 0:
                continue
            recipients.append(
                {
                    "name": participant.full_name,
                    "cnic": participant.cnic_ntn,
                    "iban": participant.iban,
                    "bank_name": participant.bank_name,
                    "bic": participant.bic,
                    "participant_class": line.participant_class,
                    "tax_status": participant.tax_status,
                    "zakat_exempt": participant.zakat_exempt,
                    "default_channel": participant.default_channel,
                    "profit": line.allocated_amount,
                }
            )

        transactions = []
        total_gross = Decimal("0.00")
        total_wht = Decimal("0.00")
        total_zakat = Decimal("0.00")
        total_net = Decimal("0.00")

        for idx, dep in enumerate(recipients, start=1):
            p_class = dep["participant_class"]
            base_share = Decimal(dep["profit"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # WHT rate: Filer 15%, Non-Filer 30% (FBR / SBP Income Tax Ordinance)
            wht_rate = Decimal("0.15") if dep["tax_status"] == "filer" else Decimal("0.30")
            wht_amount = (base_share * wht_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Zakat: 2.5% if not exempt
            zakat_amount = Decimal("0.00")
            if not dep["zakat_exempt"]:
                zakat_amount = (base_share * Decimal("0.025")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            net_payout = base_share - wht_amount - zakat_amount
            total_gross += base_share
            total_wht += wht_amount
            total_zakat += zakat_amount
            total_net += net_payout

            txn_ref = f"RAAST-{value_date.strftime('%y%m')}-{str(idx).zfill(4)}"
            
            transactions.append({
                "id": str(uuid.uuid4()),
                "txn_ref": txn_ref,
                "beneficiary_name": dep["name"],
                "cnic_ntn": dep["cnic"],
                "iban": dep["iban"],
                "bank_name": dep["bank_name"],
                "bic": dep["bic"],
                "participant_class": p_class,
                "gross_profit": float(base_share),
                "tax_status": dep["tax_status"],
                "wht_rate_pct": float(wht_rate * 100),
                "wht_amount": float(wht_amount),
                "zakat_exempt": dep["zakat_exempt"],
                "zakat_amount": float(zakat_amount),
                "net_payout": float(net_payout),
                "routing_channel": dep["default_channel"],  # raast, one_link, ibt
                "status": "PENDING",  # PENDING, QUEUED, DISPATCHED, SETTLED, FAILED
                "iban_valid": _validate_pakistan_iban(dep["iban"]),
                "clearing_rrn": None,
                "latency_ms": None,
                "response_code": None,
                "settled_at": None,
            })

        # Calculate batch Merkle root / SHA-256 seal
        hash_seed = f"{batch_code}:{total_gross}:{total_net}:{len(transactions)}"
        batch_hash = f"MERKLE-CLR-{hashlib.sha256(hash_seed.encode()).hexdigest().upper()[:32]}"
        iso_msg_id = f"RAAST/NOVU/{value_date.strftime('%Y%m%d')}/{str(uuid.uuid4())[:8].upper()}"

        batch_obj = {
            "batch_id": str(uuid.uuid4()),
            "batch_code": batch_code,
            "allocation_run_id": str(allocation_run.id),
            "pool_id": str(pool.id),
            "pool_name": pool.name,
            "pool_code": pool.code,
            "period_month": value_date.strftime("%B %Y"),
            "value_date": value_date.isoformat(),
            "status": "draft",  # draft, validated, authorized, dispatched, settled, partially_settled
            "total_records": len(transactions),
            "total_gross_profit": float(total_gross),
            "total_wht_deducted": float(total_wht),
            "total_zakat_deducted": float(total_zakat),
            "total_net_disbursed": float(total_net),
            "batch_hash": batch_hash,
            "iso_msg_id": iso_msg_id,
            # The batch is prepared on behalf of whoever created the allocation run.
            "maker_email": allocation_run.created_by.email if allocation_run.created_by else None,
            "checker_email": None,
            "authorized_at": None,
            "dispatched_at": None,
            "settled_at": None,
            "journal_batch_id": None,
            "gates_verified": False,
            "gate_results": {},
            "mode": MODE_SIMULATION,
            "tenant_id": str(allocation_run.tenant_id),
            "transactions": transactions,
        }

        cls._persist(batch_obj)
        return batch_obj

    @classmethod
    def _persist(cls, batch_obj):
        """Saves the batch document (one record per allocation run)."""
        from apps.allocation.models import PayoutBatchRecord

        PayoutBatchRecord._base_manager.update_or_create(
            tenant_id=batch_obj["tenant_id"],
            allocation_run_id=batch_obj["allocation_run_id"],
            defaults={
                "batch_code": batch_obj["batch_code"],
                "status": batch_obj["status"],
                "payload": batch_obj,
            },
        )
        return batch_obj

    @classmethod
    def verify_pre_disbursement_gates(cls, batch_obj, tenant):
        """Runs the 5 Pre-Disbursement Compliance Gates required by SBP."""
        transactions = batch_obj["transactions"]

        # Gate 1: the pool's contract must be backed by an approved, in-force Shariah decision.
        from apps.pools.models import Pool
        from apps.products.shariah import shariah_decision_for

        pool = Pool._base_manager.get(id=batch_obj["pool_id"])
        decision = shariah_decision_for(pool)
        has_fatwa_seal = decision is not None
        latest_fatwa_code = decision.decision_code if decision else "NONE"

        # Gate 2: MOD-97 IBAN checksum (format check only - no bank directory lookup).
        invalid_ibans = [t for t in transactions if not t.get("iban_valid")]
        gate2_passed = len(invalid_ibans) == 0 and len(transactions) > 0

        # Gate 3: withholding applied at the statutory rate for the filer status recorded on
        # each participant (the FBR Active Taxpayer List itself is not integrated).
        gate3_passed = all(
            (t["tax_status"] == "filer" and t["wht_rate_pct"] == 15.0) or
            (t["tax_status"] == "non_filer" and t["wht_rate_pct"] == 30.0)
            for t in transactions
        )

        # Gate 4: settlement-account liquidity. There is no live SBP/nostro balance feed, so the
        # balance comes from configuration (PAYOUT_SETTLEMENT_ACCOUNT_BALANCE); if it is not
        # configured the gate fails rather than assuming funds.
        from django.conf import settings

        configured_balance = getattr(settings, "PAYOUT_SETTLEMENT_ACCOUNT_BALANCE", None)
        if configured_balance is None:
            sbp_clearing_available = None
            gate4_passed = False
        else:
            sbp_clearing_available = float(configured_balance)
            gate4_passed = sbp_clearing_available >= batch_obj["total_net_disbursed"]

        # Gate 5: Maker-Checker Role Separation
        # Prepared by maker, ready for checker authorization
        gate5_passed = bool(batch_obj.get("maker_email"))

        all_passed = has_fatwa_seal and gate2_passed and gate3_passed and gate4_passed and gate5_passed

        gate_results = {
            "gate_1_fatwa_seal": {
                "name": "SBP Shariah Fatwa Quorum Seal",
                "passed": has_fatwa_seal,
                "details": (
                    f"Approved Shariah decision backing the pool contract: {latest_fatwa_code}"
                    if has_fatwa_seal
                    else "No approved, in-force Shariah decision is linked to this pool's contract."
                ),
                "status": "PASS" if has_fatwa_seal else "FAIL",
            },
            "gate_2_iban_integrity": {
                "name": "PK MOD-97 IBAN Checksum Integrity",
                "passed": gate2_passed,
                "details": (
                    f"All {len(transactions)} recipient IBANs pass the MOD-97 checksum"
                    if gate2_passed
                    else (f"{len(invalid_ibans)} invalid IBAN(s)" if transactions else "Batch has no payable recipients.")
                ),
                "status": "PASS" if gate2_passed else "FAIL",
            },
            "gate_3_tax_withholding": {
                "name": "FBR Withholding Tax (WHT) Statutory Rate Compliance",
                "passed": gate3_passed,
                "details": "Filer (15%) and non-filer (30%) rates applied per the recorded participant status; ATL not integrated.",
                "status": "PASS" if gate3_passed else "FAIL",
            },
            "gate_4_settlement_liquidity": {
                "name": "SBP RTGS & Raast Nostro Settlement Liquidity",
                "passed": gate4_passed,
                "details": (
                    "No settlement-account balance is configured (PAYOUT_SETTLEMENT_ACCOUNT_BALANCE); liquidity cannot be confirmed."
                    if sbp_clearing_available is None
                    else f"Configured settlement balance PKR {sbp_clearing_available:,.2f} vs PKR {batch_obj['total_net_disbursed']:,.2f} to pay (no live balance feed)."
                ),
                "status": "PASS" if gate4_passed else "FAIL",
            },
            "gate_5_dual_authorization": {
                "name": "Dual Authorization Maker-Checker Gate",
                "passed": gate5_passed,
                "details": f"Prepared by Pool Operations Maker ({batch_obj['maker_email']}). Awaiting CFO/Checker authorization.",
                "status": "READY" if gate5_passed else "FAIL",
            },
        }

        batch_obj["gates_verified"] = all_passed
        batch_obj["gate_results"] = gate_results
        if all_passed and batch_obj["status"] == "draft":
            batch_obj["status"] = "validated"

        return cls._persist(batch_obj)

    @classmethod
    def authorize_batch(cls, batch_obj, checker_user):
        """Checker authorization required prior to dispatch."""
        if not batch_obj.get("gates_verified"):
            raise ValueError("All 5 Pre-Disbursement Gates must be verified before authorization.")
        if batch_obj.get("maker_email") == checker_user.email:
            raise ValueError("Maker-Checker violation: The user who created the batch cannot authorize it.")

        if batch_obj.get("status") != "validated":
            raise ValueError(f"Only a validated batch can be authorized (current status: {batch_obj.get('status')}).")

        batch_obj["status"] = "authorized"
        batch_obj["checker_email"] = checker_user.email
        batch_obj["authorized_at"] = timezone.now().isoformat()
        return cls._persist(batch_obj)

    @classmethod
    def simulate_dispatch(cls, batch_obj, inject_edge_case=False):
        """
        Simulates live dispatch across SBP Raast Instant, 1LINK 1IBFT, and Intra-Bank rails.
        If inject_edge_case=True, injects 1 simulated return (pacs.002 AC04 Dormant Account)
        to demonstrate suspense GL liability handling.
        """
        import random
        now = timezone.now()
        batch_obj["dispatched_at"] = now.isoformat()
        batch_obj["status"] = "dispatched"

        txns = batch_obj["transactions"]
        settled_count = 0
        failed_count = 0

        for idx, txn in enumerate(txns):
            # Simulate realistic response times
            channel = txn["routing_channel"]
            if channel == "raast":
                latency = random.randint(70, 180)  # 70-180ms Raast Instant
            elif channel == "one_link":
                latency = random.randint(300, 650)  # 300-650ms 1IBFT
            else:
                latency = random.randint(20, 45)   # Internal GL Transfer

            # Edge case injection on 7th transaction if requested
            if inject_edge_case and idx == 6:
                txn["status"] = "FAILED"
                txn["clearing_rrn"] = f"NACK-SBP-RAAST-{str(uuid.uuid4())[:12].upper()}"
                txn["latency_ms"] = latency
                txn["response_code"] = "AC04"  # SBP ISO 20022 Return: Account Closed or Dormant
                txn["settled_at"] = None
                failed_count += 1
            else:
                txn["status"] = "SETTLED"
                txn["clearing_rrn"] = f"RRN-{now.strftime('%Y%m%d')}-{random.randint(10000000, 99999999)}"
                txn["latency_ms"] = latency
                txn["response_code"] = "ACTC"  # Accepted Technical Validation / Settled
                txn["settled_at"] = now.isoformat()
                settled_count += 1

        batch_obj["settled_at"] = now.isoformat()
        batch_obj["status"] = "partially_settled" if failed_count > 0 else "settled"
        batch_obj["settled_records"] = settled_count
        batch_obj["failed_records"] = failed_count
        batch_obj["mode"] = MODE_SIMULATION  # nothing was transmitted; the results above are simulated

        return cls._persist(batch_obj)

    @classmethod
    def post_contra_accounting_voucher(cls, batch_obj, tenant, user):
        """
        Creates balanced JournalBatch & JournalEntries in the double-entry accounting ledger:
        Dr. 2101-001 - Pool Depositor Profit Payable Liability (Gross Profit)
        Cr. 2102-005 - FBR Withholding Tax Payable (WHT Deductions)
        Cr. 1001-002 - SBP Raast / 1LINK Settlement Clearing Account (Net Settled)
        Cr. 2109-099 - Unclaimed / Suspended Profit Liability (Any Failed/Returned)
        """
        from apps.accounting.models import JournalBatch, JournalEntry, JournalBatchStatus, JournalEntryType
        from apps.pools.models import Pool

        if batch_obj.get("journal_batch_id"):
            raise ValueError("The contra voucher for this batch has already been posted.")

        pool = Pool._base_manager.get(id=batch_obj["pool_id"])
        total_gross = Decimal(str(batch_obj["total_gross_profit"])).quantize(Decimal("0.01"))
        total_wht = Decimal(str(batch_obj["total_wht_deducted"])).quantize(Decimal("0.01"))
        total_zakat = Decimal(str(batch_obj["total_zakat_deducted"])).quantize(Decimal("0.01"))

        # Calculate settled net vs failed net
        settled_net = Decimal("0.00")
        failed_net = Decimal("0.00")

        for txn in batch_obj["transactions"]:
            net_amt = Decimal(str(txn["net_payout"])).quantize(Decimal("0.01"))
            if txn["status"] == "SETTLED":
                settled_net += net_amt
            else:
                failed_net += net_amt

        # Balanced double-entry
        total_debit = sum(
            (Decimal(str(t["gross_profit"])).quantize(Decimal("0.01")) for t in batch_obj["transactions"]),
            Decimal("0.00"),
        )
        total_credit = total_wht + total_zakat + settled_net + failed_net

        # Adjust any rounding penny to ensure absolute ledger equality
        diff = total_debit - total_credit
        if diff != Decimal("0.00"):
            settled_net += diff
            total_credit += diff

        with transaction.atomic():
            jb = JournalBatch.objects.create(
                tenant=tenant,
                pool=pool,
                batch_date=date.today(),
                total_debit=total_debit,
                total_credit=total_credit,
                status=JournalBatchStatus.POSTED,
                posted_by=user if user.is_authenticated else None,
            )

            # 1. Dr. the same per-class Depositor Payable control accounts that the signed
            #    allocation run credited, so the liability clears exactly.
            gross_by_class = {}
            for txn in batch_obj["transactions"]:
                gross_by_class[txn["participant_class"]] = gross_by_class.get(
                    txn["participant_class"], Decimal("0.00")
                ) + Decimal(str(txn["gross_profit"])).quantize(Decimal("0.01"))
            for participant_class in sorted(gross_by_class):
                JournalEntry.objects.create(
                    tenant=tenant,
                    batch=jb,
                    account_name=f"Depositor Payable - {participant_class}",
                    entry_type=JournalEntryType.DEBIT,
                    amount=gross_by_class[participant_class],
                )

            # 2. Cr. FBR Withholding Tax Payable
            if total_wht > Decimal("0.00"):
                JournalEntry.objects.create(
                    tenant=tenant,
                    batch=jb,
                    account_name="2102-005 Federal Board of Revenue Withholding Tax Payable",
                    entry_type=JournalEntryType.CREDIT,
                    amount=total_wht,
                )

            # 3. Cr. Central Zakat Collection Fund
            if total_zakat > Decimal("0.00"):
                JournalEntry.objects.create(
                    tenant=tenant,
                    batch=jb,
                    account_name="2102-009 Central Zakat Collection Account (Ministry of Religious Affairs)",
                    entry_type=JournalEntryType.CREDIT,
                    amount=total_zakat,
                )

            # 4. Cr. SBP Raast / 1LINK Settlement Clearing Account
            if settled_net > Decimal("0.00"):
                JournalEntry.objects.create(
                    tenant=tenant,
                    batch=jb,
                    account_name="1001-002 SBP Raast RTGS & 1LINK Settlement Clearing Account",
                    entry_type=JournalEntryType.CREDIT,
                    amount=settled_net,
                )

            # 5. Cr. Unclaimed / Suspended Profit Liability (if any rejected)
            if failed_net > Decimal("0.00"):
                JournalEntry.objects.create(
                    tenant=tenant,
                    batch=jb,
                    account_name="2109-099 Suspense / Unclaimed Depositor Profit Liability (Dormant Accounts)",
                    entry_type=JournalEntryType.CREDIT,
                    amount=failed_net,
                )

        batch_obj["journal_batch_id"] = str(jb.id)
        batch_obj["contra_voucher_code"] = f"JV-{jb.batch_date.strftime('%Y%m')}-{str(jb.id)[:8].upper()}"
        return cls._persist(batch_obj)

    @classmethod
    def generate_iso20022_pacs008_xml(cls, batch_obj):
        """
        Generates standard ISO 20022 pacs.008.001.08 XML payload
        (FIToFICustomerCreditTransfer) for submission to SBP Raast switch.
        """
        now_iso = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!-- SIMULATION: generated for review only; not transmitted to any switch -->',
            '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
            '  <FIToFICstmrCdtTrf>',
            '    <GrpHdr>',
            f'      <MsgId>{batch_obj["iso_msg_id"]}</MsgId>',
            f'      <CreDtTm>{now_iso}</CreDtTm>',
            f'      <NbOfTxs>{batch_obj["total_records"]}</NbOfTxs>',
            f'      <CtrlSum>{batch_obj["total_net_disbursed"]:.2f}</CtrlSum>',
            '      <SttlmInf>',
            '        <SttlmMtd>CLRG</SttlmMtd>',
            '        <ClrSys>',
            '          <Prtry>SBP_RAAST_RTGS</Prtry>',
            '        </ClrSys>',
            '      </SttlmInf>',
            '      <InstgAgt>',
            '        <FinInstnId>',
            '          <BICFI>NOVUPKKA</BICFI>',
            '          <Nm>Novu Islamic Banking Corporation</Nm>',
            '        </FinInstnId>',
            '      </InstgAgt>',
            '      <InstdAgt>',
            '        <FinInstnId>',
            '          <BICFI>SBPKPKKA</BICFI>',
            '          <Nm>State Bank of Pakistan Core Raast Switch</Nm>',
            '        </FinInstnId>',
            '      </InstdAgt>',
            '    </GrpHdr>',
        ]

        for txn in batch_obj["transactions"]:
            lines.extend([
                '    <CdtTrfTxInf>',
                '      <PmtId>',
                f'        <EndToEndId>{txn["txn_ref"]}</EndToEndId>',
                f'        <UETR>{txn["id"]}</UETR>',
                '      </PmtId>',
                '      <IntrBkSttlmAmt Ccy="PKR">' f'{txn["net_payout"]:.2f}' '</IntrBkSttlmAmt>',
                f'      <IntrBkSttlmDt>{batch_obj["value_date"]}</IntrBkSttlmDt>',
                '      <Dbtr>',
                f'        <Nm>Mudarabah Pool - {batch_obj["pool_name"]}</Nm>',
                '      </Dbtr>',
                '      <DbtrAcct>',
                '        <Id>',
                f'          <Othr><Id>GL-2101-001</Id></Othr>',
                '        </Id>',
                '      </DbtrAcct>',
                '      <DbtrAgt>',
                '        <FinInstnId><BICFI>NOVUPKKA</BICFI></FinInstnId>',
                '      </DbtrAgt>',
                '      <CdtrAgt>',
                f'        <FinInstnId><BICFI>{txn["bic"]}</BICFI><Nm>{txn["bank_name"]}</Nm></FinInstnId>',
                '      </CdtrAgt>',
                '      <Cdtr>',
                f'        <Nm>{txn["beneficiary_name"]}</Nm>',
                f'        <Id><OrgId><AnyBIC>{txn["cnic_ntn"]}</AnyBIC></OrgId></Id>',
                '      </Cdtr>',
                '      <CdtrAcct>',
                '        <Id>',
                f'          <IBAN>{txn["iban"]}</IBAN>',
                '        </Id>',
                '      </CdtrAcct>',
                '      <RmtInf>',
                f'        <Ustrd>Mudarabah Profit Distribution {batch_obj["period_month"]} [WHT Paid: PKR {txn["wht_amount"]:.2f}]</Ustrd>',
                '      </RmtInf>',
                '    </CdtTrfTxInf>',
            ])

        lines.extend([
            '  </FIToFICstmrCdtTrf>',
            '</Document>',
        ])

        return "\n".join(lines)
