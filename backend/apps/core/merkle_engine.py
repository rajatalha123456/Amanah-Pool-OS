"""
Tamper-evident hash chain for the AuditLog (BRD Section 14: "Append-only audit
events; tamper-evident evidence hashes").

Every AuditLog row is sealed when it is written (AuditLog.save): it receives a
per-tenant `sequence` number, the previous row's `entry_hash` as `prev_hash`,
and its own `entry_hash` = SHA-256 over its content and `prev_hash`. The hashes
are stored, so verification compares what the database holds *now* against what
was sealed *then*:

* editing a stored row changes its recomputed hash         -> CONTENT_ALTERED
* editing a row and re-hashing it breaks the next link     -> CHAIN_BROKEN
* deleting a row in the middle leaves a sequence gap       -> MISSING_ENTRIES

Limit (inherent to any hash chain): deleting the newest rows cannot be detected
from the database alone. Anchor `current_merkle_root` outside the database
(evidence bundle, regulator filing) to close that gap.

Rows written before sealing was introduced have no hash; they are reported as
`unsealed_legacy_entries` and are not part of the verified chain.
"""

import copy
import hashlib
import json
from datetime import timezone as dt_timezone

from django.utils import timezone

GENESIS_BLOCK_HASH = "GENESIS"


def _deterministic_json(data) -> str:
    """Serializes a changes payload to a deterministic, sorted JSON string."""
    if data is None:
        return ""
    return json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))


def _utc_iso(value) -> str:
    return value.astimezone(dt_timezone.utc).isoformat() if value else ""


def compute_entry_hash(entry, prev_hash=None) -> str:
    """SHA-256 over the entry's content and the hash of the previous entry."""
    prev_hash = entry.prev_hash if prev_hash is None else prev_hash
    parts = [
        str(entry.sequence),
        str(entry.id),
        str(entry.tenant_id or ""),
        str(entry.actor_id or ""),
        entry.action,
        entry.model_name,
        entry.object_id,
        _deterministic_json(entry.changes),
        entry.reason or "",
        entry.ip_address or "",
        _utc_iso(entry.created_at),
        prev_hash,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


# Kept for callers that referred to the old name.
compute_audit_leaf_hash = compute_entry_hash


class MerkleAuditEngine:
    """Verification of the sealed AuditLog chain."""

    @classmethod
    def _walk(cls, entries, tamper=None):
        """
        Walks sealed entries in sequence order and checks every link.

        `tamper` = (entry_id, new_changes) alters that entry *in memory only* so
        the real verification can be demonstrated; nothing is written.
        """

        expected_sequence = None
        previous_hash = GENESIS_BLOCK_HASH
        blocks = []
        problems = []

        for entry in entries:
            if tamper and str(entry.id) == str(tamper[0]):
                entry = copy.copy(entry)
                entry.changes = tamper[1]

            issues = []
            if expected_sequence is not None and entry.sequence != expected_sequence:
                issues.append("MISSING_ENTRIES")
            if entry.prev_hash != previous_hash and expected_sequence is not None:
                issues.append("CHAIN_BROKEN")
            recomputed = compute_entry_hash(entry)
            if recomputed != entry.entry_hash:
                issues.append("CONTENT_ALTERED")

            block = {
                "height": entry.sequence,
                "entry_id": str(entry.id),
                "timestamp": entry.created_at.isoformat() if entry.created_at else None,
                "actor_email": entry.actor.email if entry.actor else "System Automated",
                "actor_role": getattr(entry.actor, "role", "system") if entry.actor else "system",
                "action": entry.action,
                "model_name": entry.model_name,
                "object_id": entry.object_id,
                "reason": entry.reason or "",
                "ip_address": entry.ip_address or "",
                "leaf_hash": recomputed,
                "rolling_merkle_root": entry.entry_hash,
                "is_tampered": bool(issues),
                "tamper_detected_at_this_block": bool(issues),
                "issues": issues,
                "field_diffs": cls.extract_field_diffs(entry.changes),
            }
            blocks.append(block)
            if issues:
                problems.append(
                    {
                        "height": entry.sequence,
                        "entry_id": str(entry.id),
                        "action": entry.action,
                        "model_name": entry.model_name,
                        "issues": issues,
                        "tamper_evidence": ", ".join(issues),
                    }
                )

            previous_hash = entry.entry_hash
            expected_sequence = entry.sequence + 1

        return blocks, problems, previous_hash

    @classmethod
    def _sealed_entries(cls, queryset):
        return list(
            queryset.filter(sequence__isnull=False).select_related("actor", "tenant").order_by("sequence")
        )

    @classmethod
    def verify_merkle_chain(cls, queryset):
        """
        Verifies the whole sealed chain of `queryset` (callers pass one tenant's
        entries, unfiltered, so continuity can be checked).
        """

        entries = cls._sealed_entries(queryset)
        legacy_count = queryset.filter(sequence__isnull=True).count()
        blocks, problems, tip = cls._walk(entries)

        return {
            "status": "VERIFIED" if not problems else "TAMPER_DETECTED",
            "simulation": False,
            "total_blocks": len(blocks),
            "tampered_count": len(problems),
            "unsealed_legacy_entries": legacy_count,
            "genesis_block_hash": GENESIS_BLOCK_HASH,
            "current_merkle_root": tip if blocks else GENESIS_BLOCK_HASH,
            "verified_at": timezone.now().isoformat(),
            "chain_blocks": list(reversed(blocks)),  # newest first for the UI
            "tampered_blocks": problems,
            "note": (
                "Anchor current_merkle_root outside the database to also detect deletion of the newest entries."
            ),
        }

    @classmethod
    def simulate_tamper_detection(cls, queryset, target_height=None):
        """
        Demonstration for auditors: alters one entry's content *in memory only*
        and runs the real verification, which flags it. No stored data changes.
        """

        entries = cls._sealed_entries(queryset)
        if not entries:
            result = cls.verify_merkle_chain(queryset)
            result["simulation"] = True
            return result

        if target_height is None:
            target = entries[len(entries) // 2]
        else:
            target = next((e for e in entries if e.sequence == target_height), entries[-1])

        altered = dict(target.changes or {})
        altered["tampered_unauthorized_override"] = "SIMULATED_OUT_OF_BAND_EDIT"
        blocks, problems, tip = cls._walk(entries, tamper=(target.id, altered))

        return {
            "status": "TAMPER_DETECTED" if problems else "VERIFIED",
            "simulation": True,
            "total_blocks": len(blocks),
            "tampered_count": len(problems),
            "broken_at_block_height": problems[0]["height"] if problems else None,
            "genesis_block_hash": GENESIS_BLOCK_HASH,
            "compromised_merkle_root": tip,
            "verified_at": timezone.now().isoformat(),
            "chain_blocks": list(reversed(blocks)),
            "tampered_blocks": problems,
            "note": "SIMULATION: one entry was altered in memory to demonstrate detection. No stored data was changed.",
        }

    @classmethod
    def extract_field_diffs(cls, changes):
        """
        Parses changes JSON into structured before/after field comparisons.
        Handles both {"field": {"before": X, "after": Y}} and {"field": new_val} forms.
        """
        if not isinstance(changes, dict) or not changes:
            return []

        diffs = []
        for field, val in changes.items():
            if isinstance(val, dict) and ("before" in val or "after" in val):
                before = val.get("before", "—")
                after = val.get("after", "—")
            else:
                before = "—"
                after = val

            diffs.append({"field": field, "before": str(before), "after": str(after)})
        return diffs
