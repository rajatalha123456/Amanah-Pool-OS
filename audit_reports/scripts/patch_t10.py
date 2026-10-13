ROOT = "backend/"

def rd(p): return open(ROOT + p, encoding="utf-8").read()
def wr(p, s): open(ROOT + p, "w", encoding="utf-8").write(s)
def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)

s = rd("apps/allocation/serializers.py")
s = sub(s, '''        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate(self, attrs):
        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        participant_class = attrs.get(''', '''        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate_weightage(self, value):
        # A weightage multiplies the balance; zero or negative would remove or reverse a class's share of the profit.
        if value <= 0:
            raise serializers.ValidationError("The weightage must be greater than zero.")
        return value

    def validate(self, attrs):
        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        participant_class = attrs.get(''')
wr("apps/allocation/serializers.py", s)

s = rd("apps/allocation/models.py")
s = sub(s, '''    status = models.CharField(
        max_length=20, choices=WeightageBandStatus.choices, default=WeightageBandStatus.DRAFT
    )

    def __str__(self):
        return f"{self.pool.name} - {self.participant_class} ({self.weightage})"''', '''    status = models.CharField(
        max_length=20, choices=WeightageBandStatus.choices, default=WeightageBandStatus.DRAFT
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(weightage__gt=0), name="weightage_band_positive"),
        ]

    def __str__(self):
        return f"{self.pool.name} - {self.participant_class} ({self.weightage})"''')
wr("apps/allocation/models.py", s)

s = rd("config/urls.py")
s = sub(s, '''from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
''', '''from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
''')
s = s.rstrip() + '''

# The Django admin edits tables directly, bypassing the maker-checker rules of the API. It is a development tool only:
# it is mounted when DEBUG is on, or when ENABLE_DJANGO_ADMIN is set explicitly.
if settings.DEBUG or getattr(settings, "ENABLE_DJANGO_ADMIN", False):
    urlpatterns.insert(0, path("admin/", admin.site.urls))
'''
wr("config/urls.py", s)
s = rd("config/settings/base.py")
s = sub(s, 'DEBUG = config("DEBUG", default=False, cast=bool)\n', 'DEBUG = config("DEBUG", default=False, cast=bool)\n# Off unless asked for: the admin bypasses the API\'s approval rules (see config/urls.py).\nENABLE_DJANGO_ADMIN = config("ENABLE_DJANGO_ADMIN", default=False, cast=bool)\n')
wr("config/settings/base.py", s)
print("ok")
