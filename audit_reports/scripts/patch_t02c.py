ROOT = "backend/apps/"

def rd(p): return open(ROOT + p, encoding="utf-8").read()
def wr(p, s): open(ROOT + p, "w", encoding="utf-8").write(s)
def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)

s = rd("products/serializers.py")
i = s.index("class JurisdictionRulePackSerializer")
j = s.index('        read_only_fields = ("id", "tenant", "created_at", "updated_at")\n', i) + len('        read_only_fields = ("id", "tenant", "created_at", "updated_at")\n')
add = '''
    # Only one rule pack is the tenant's default: when a change that makes another pack the default is applied, the
    # flag is taken away from the previous one in the same step.
    def _single_default(self, instance):
        if instance.is_default:
            JurisdictionRulePack._base_manager.filter(tenant_id=instance.tenant_id).exclude(pk=instance.pk).update(
                is_default=False
            )

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._single_default(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._single_default(instance)
        return instance
'''
s = s[:j] + add + s[j:]
wr("products/serializers.py", s)

s = rd("products/views.py")
a = s.index('    @action(detail=True, methods=["post"])\n    def activate(self, request, pk=None):')
b = s.index("        return Response(self.get_serializer(pack).data)", a) + len("        return Response(self.get_serializer(pack).data)")
new = '''    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Making a pack active / the tenant default changes what governs every pool: it is proposed, not applied."""
        from apps.governance.config_changes import submit_change
        from apps.governance.models import ConfigChangeKind
        from apps.governance.views import ConfigChangeRequestSerializer

        pack = self.get_object()
        data = {
            "is_active": True,
            "is_default": bool(request.data.get("is_default", False)),
            "change_reason": request.data.get("change_reason"),
        }
        serializer = self.get_serializer(pack, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        change = submit_change(
            kind=ConfigChangeKind.RULE_PACK, serializer=serializer, request=request, instance=pack, data=data
        )
        return Response(ConfigChangeRequestSerializer(change).data, status=202)'''
s = s[:a] + new + s[b:]
wr("products/views.py", s)
print("ok")
