from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pools", "0003_balanceimportbatch_dailybalance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pool",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending_approval", "Pending Approval"),
                    ("approved", "Approved"),
                    ("open", "Open"),
                    ("allocation", "Allocation"),
                    ("closed", "Closed"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
    ]