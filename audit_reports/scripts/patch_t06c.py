ROOT = "backend/apps/investments/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new, count=1):
    assert old in s, old[:90]
    return s.replace(old, new, count)


s = rd("test_distribution.py")
s = sub(s, "from .distribution import calculate_distribution\n",
        "from .ceremony_helpers import release_distribution\nfrom .distribution import calculate_distribution\n")
s = sub(s, '        self.shariah = self._user("board", UserRole.SHARIAH_BOARD)\n',
        '        self.shariah = self._user("board", UserRole.SHARIAH_BOARD)\n        self.signatory = self._user("signatory", UserRole.AUTHORIZED_SIGNATORY)\n')
s = sub(s, '''        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return run_id''', '''        response = release_distribution(self, base)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return run_id''')
s = sub(s, '''        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_overlapping''', '''        # the independent check re-derives the hash, so a tampered run never reaches the Shariah review
        self.assertEqual(release_distribution(self, base).status_code, status.HTTP_400_BAD_REQUEST)

    def test_overlapping''')
s = sub(s, '''        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_closed_period''', '''        self.assertEqual(release_distribution(self, base).status_code, status.HTTP_400_BAD_REQUEST)

    def test_closed_period''')
s = sub(s, '''        self.authenticate(self.checker)
        approved = self.client.post(new_base + "approve/")''', '''        approved = release_distribution(self, new_base)''')
s += '''

class DistributionCeremonyTests(MudarabahBase):
    """BRD 6.3: finance checker and Shariah reviewer approve; release by someone who is neither maker nor checker."""

    def _submitted(self):
        run_id = self.create_run().data["id"]
        base = reverse("distribution-run-detail", args=[run_id])
        self.authenticate(self.maker)
        self.client.post(base + "submit-for-checking/")
        return run_id, base

    def test_one_person_cannot_release_a_distribution(self):
        _, base = self._submitted()
        for user in (self.checker, self.shariah, self.maker, self.pm):
            self.authenticate(user)
            self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_403_FORBIDDEN, user.role)
        self.authenticate(self.signatory)
        # even the right role cannot skip the earlier stages
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_stages_must_run_in_order_with_the_right_roles(self):
        _, base = self._submitted()
        self.authenticate(self.shariah)
        self.assertEqual(self.client.post(base + "shariah-sign-off/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.authenticate(self.signatory)
        self.assertEqual(self.client.post(base + "check/").status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "check/").status_code, status.HTTP_200_OK)
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "shariah-sign-off/", {}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.shariah)
        self.assertEqual(self.client.post(base + "shariah-sign-off/", {"note": "ok"}, format="json").status_code, status.HTTP_200_OK)
        self.authenticate(self.signatory)
        released = self.client.post(base + "approve/")
        self.assertEqual(released.status_code, status.HTTP_200_OK, released.data)
        self.assertEqual(released.data["status"], "signed")
        self.assertEqual(str(released.data["released_by"]), str(self.signatory.id))
        self.assertEqual(str(released.data["shariah_signed_off_by"]), str(self.shariah.id))

    def test_a_second_release_of_the_same_run_is_refused(self):
        _, base = self._submitted()
        self.assertEqual(release_distribution(self, base).status_code, status.HTTP_200_OK)
        self.authenticate(self.signatory)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JournalBatch.objects.filter(investment_run_id=base.rstrip("/").split("/")[-1]).count(), 1)
'''
wr("test_distribution.py", s)

s = rd("test_musharakah_wakalah.py")
s = sub(s, "from .test_distribution import END, START, MudarabahBase\n",
        "from .ceremony_helpers import release_distribution\nfrom .test_distribution import END, START, MudarabahBase\n")
s = sub(s, '''        self.authenticate(self.checker)
        self.assertEqual(self.client.post(new_base + "approve/").status_code, status.HTTP_200_OK)''',
        '''        self.assertEqual(release_distribution(self, new_base).status_code, status.HTTP_200_OK)''')
# two stale-run tests: the block happens at release, after the earlier stages
s = sub(s, '''        self.raise_case()
        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")''', '''        self.raise_case()
        response = release_distribution(self, base)''')
s = sub(s, '''        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("negligence determinations"''', '''        response = release_distribution(self, base)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("negligence determinations"''')
wr("test_musharakah_wakalah.py", s)
print("ok")
