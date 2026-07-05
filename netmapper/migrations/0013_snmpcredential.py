import django.core.serializers.json
from django.db import migrations, models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ("netmapper", "0012_alter_arptableentry_unique_together_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SnmpCredential",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "custom_field_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "version",
                    models.CharField(
                        choices=[("v2c", "SNMP v2c")],
                        default="v2c",
                        max_length=10,
                    ),
                ),
                ("community", models.TextField(blank=True)),
                ("port", models.PositiveIntegerField(default=161)),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        through="extras.TaggedItem", to="extras.Tag"
                    ),
                ),
            ],
            options={
                "verbose_name": "SNMP credential",
                "verbose_name_plural": "SNMP credentials",
                "ordering": ["name"],
                "unique_together": {("name",)},
            },
        ),
    ]
