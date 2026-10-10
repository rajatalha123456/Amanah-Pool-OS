from django.test import TestCase

from apps.tenants.models import Tenant

from .audit import log_action
from .merkle_engine import GENESIS_BLOCK_HASH, MerkleAuditEngine, compute_entry_hash
from .models import AuditLog


class AuditHashChainTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Chain A", code="CHAIN-A", data_residency="PK")
        self.other = Tenant.objects.create(name="Chain B", code="CHAIN-B", data_residency="PK")
        for i in range(5):
            log_action(
                tenant=self.tenant, actor=None, action="create", model_name="Pool",
                object_id=f"pool-{i}", changes={"name": f"Pool {i}", "amount": i},
            )
        log_action(tenant=self.other, actor=None, action="create", model_name="Pool", object_id="x", changes={})

    def chain(self):
        return AuditLog.objects.filter(tenant=self.tenant)

    def test_entries_are_sealed_into_a_per_tenant_chain(self):
        entries = list(self.chain().order_by("sequence"))
        self.assertEqual([e.sequence for e in entries], [1, 2, 3, 4, 5])
        self.assertEqual(entries[0].prev_hash, GENESIS_BLOCK_HASH)
        for previous, current in zip(entries, entries[1:]):
            self.assertEqual(current.prev_hash, previous.entry_hash)
        for entry in entries:
            self.assertEqual(entry.entry_hash, compute_entry_hash(entry))
        # The other tenant has its own chain starting at 1.
        self.assertEqual(AuditLog.objects.get(tenant=self.other).sequence, 1)

    def test_intact_chain_verifies(self):
        result = MerkleAuditEngine.verify_merkle_chain(self.chain())
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["total_blocks"], 5)
        self.assertEqual(result["tampered_count"], 0)
        self.assertFalse(result["simulation"])

    def test_editing_a_stored_row_is_detected(self):
        target = self.chain().get(sequence=3)
        AuditLog.objects.filter(pk=target.pk).update(changes={"name": "Pool 2", "amount": 999999})
        result = MerkleAuditEngine.verify_merkle_chain(self.chain())
        self.assertEqual(result["status"], "TAMPER_DETECTED")
        self.assertEqual([b["height"] for b in result["tampered_blocks"]], [3])
        self.assertIn("CONTENT_ALTERED", result["tampered_blocks"][0]["issues"])

    def test_rehashing_an_edited_row_still_breaks_the_next_link(self):
        target = self.chain().get(sequence=3)
        target.changes = {"name": "forged"}
        forged_hash = compute_entry_hash(target)
        AuditLog.objects.filter(pk=target.pk).update(changes=target.changes, entry_hash=forged_hash)
        result = MerkleAuditEngine.verify_merkle_chain(self.chain())
        self.assertEqual(result["status"], "TAMPER_DETECTED")
        self.assertEqual([b["height"] for b in result["tampered_blocks"]], [4])
        self.assertIn("CHAIN_BROKEN", result["tampered_blocks"][0]["issues"])

    def test_deleting_a_middle_row_is_detected(self):
        AuditLog.objects.filter(tenant=self.tenant, sequence=2).delete()
        result = MerkleAuditEngine.verify_merkle_chain(self.chain())
        self.assertEqual(result["status"], "TAMPER_DETECTED")
        self.assertIn("MISSING_ENTRIES", result["tampered_blocks"][0]["issues"])

    def test_legacy_unsealed_rows_are_reported_not_verified(self):
        AuditLog.objects.create(
            tenant=self.tenant, action="old", model_name="X", object_id="1",
            entry_hash="legacy-placeholder", sequence=None,
        )
        result = MerkleAuditEngine.verify_merkle_chain(self.chain())
        self.assertEqual(result["unsealed_legacy_entries"], 1)
        self.assertEqual(result["status"], "VERIFIED")

    def test_tamper_simulation_is_in_memory_only(self):
        before = list(self.chain().order_by("sequence").values_list("entry_hash", "changes"))
        result = MerkleAuditEngine.simulate_tamper_detection(self.chain())
        self.assertTrue(result["simulation"])
        self.assertEqual(result["status"], "TAMPER_DETECTED")
        self.assertEqual(before, list(self.chain().order_by("sequence").values_list("entry_hash", "changes")))
        self.assertEqual(MerkleAuditEngine.verify_merkle_chain(self.chain())["status"], "VERIFIED")
