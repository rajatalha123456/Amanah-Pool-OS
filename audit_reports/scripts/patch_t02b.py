ROOT = "backend/apps/"

def rd(p): return open(ROOT + p, encoding="utf-8").read()
def wr(p, s): open(ROOT + p, "w", encoding="utf-8").write(s)
def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)

s = rd("governance/config_changes.py")
s = sub(s, "def submit_change(*, kind, serializer, request, instance=None):\n    \"\"\"Called by a configuration endpoint after its serializer validated the proposal.\"\"\"\n    reason = str(request.data.get(\"change_reason\") or \"\").strip()",
        "def submit_change(*, kind, serializer, request, instance=None, data=None):\n    \"\"\"Called by a configuration endpoint after its serializer validated the proposal.\"\"\"\n    data = request.data if data is None else data\n    reason = str(data.get(\"change_reason\") or \"\").strip()")
s = sub(s, "payload = {name: _plain(request.data[name]) for name in fields if name in request.data}",
        "payload = {name: _plain(data[name]) for name in fields if name in data}")
wr("governance/config_changes.py", s)

s = rd("products/serializers.py")
s = sub(s, '''        read_only_fields = ("id", "tenant", "created_at", "updated_at")
''', '''        read_only_fields = ("id", "tenant", "created_at", "updated_at")

    # Only one rule pack is the tenant's default; making another one the default (when its approved change is applied)
    # takes the flag away from the previous one in the same step.
    def _single_default(self, instance):
        if instance.is_default:
            JurisdictionRulePack._base_manager.filter(tenant_id=instance.tenant_id).exclude(pk=instance.pk).update(is_default=False)

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._single_default(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._single_default(instance)
        return instance
''') if False else s
wr("products/serializers.py", s)
print("ok")
