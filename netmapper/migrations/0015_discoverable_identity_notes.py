from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("netmapper", "0014_networkscanrecord"),
    ]

    operations = [
        migrations.AddField(
            model_name="discoverable",
            name="identity_notes",
            field=models.TextField(
                blank=True,
                help_text="Stored Nmap/SNMP identity observations from network scans.",
            ),
        ),
    ]
