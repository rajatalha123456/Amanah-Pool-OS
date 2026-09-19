from django.db import migrations


MODEL_REGISTRY_SEED = (
    ("shariah_copilot", "1.0"),
    ("allocation_anomaly_detector", "1.0"),
    ("reconciliation_copilot", "1.0"),
)


def seed_models(apps, schema_editor):
    AIModelRegistry = apps.get_model("ai_agents", "AIModelRegistry")
    for model_name, version in MODEL_REGISTRY_SEED:
        AIModelRegistry.objects.get_or_create(
            model_name=model_name,
            defaults={"version": version, "status": "active"},
        )


def unseed_models(apps, schema_editor):
    AIModelRegistry = apps.get_model("ai_agents", "AIModelRegistry")
    AIModelRegistry.objects.filter(
        model_name__in=[model_name for model_name, _ in MODEL_REGISTRY_SEED]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("ai_agents", "0001_initial")]

    operations = [migrations.RunPython(seed_models, unseed_models)]
