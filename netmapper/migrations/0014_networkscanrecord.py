import django.core.serializers.json
from django.db import migrations, models
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0237_module_remove_local_context_data"),
        ("netmapper", "0013_snmpcredential"),
    ]

    operations = [
        migrations.CreateModel(
            name="NetworkScanRecord",
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
                (
                    "default_mode",
                    models.CharField(
                        choices=[
                            ("netmiko_alcatel_aos", "Alcatel AOS"),
                            ("netmiko_allied_telesis_awplus", "Allied Telesis AW+"),
                            ("netmiko_aruba_aoscx", "Aruba AOS-CX"),
                            ("netmiko_arista_eos", "Arista EOS"),
                            ("netmiko_cisco_asa", "Cisco ASA"),
                            ("netmiko_cisco_ios", "Cisco IOS"),
                            ("netmiko_cisco_nxos", "Cisco NX-OS"),
                            ("netmiko_cisco_xr", "Cisco XR"),
                            ("napalm_cisco_wlc_ssh", "Cisco Wireless Controller"),
                            ("napalm_huawei_vrp", "Huawei VRP"),
                            ("netmiko_hp_comware", "HP Comware"),
                            ("netmiko_hp_procurve", "HP Procurve"),
                            ("netmiko_linux", "Linux"),
                            ("netmiko_mikrotik_routeros", "MikroTik RouterOS"),
                            ("netmiko_rukus_fastiron", "Ruckus FastIron"),
                            ("netmiko_juniper_junos", "Juniper JunOS"),
                            ("napalm_panos", "Palo Alto Networks firewall (NAPALM)"),
                            ("xml_panw_ngfw", "Palo Alto Networks firewall (XML API)"),
                        ],
                        max_length=30,
                    ),
                ),
                ("targets", models.TextField()),
                ("normalized_targets", models.JSONField(blank=True, default=list)),
                ("invalid_targets", models.JSONField(blank=True, default=list)),
                ("filters", models.CharField(blank=True, max_length=255)),
                ("filter_type", models.CharField(blank=True, max_length=20)),
                ("discover_now", models.BooleanField(default=True)),
                ("overwrite_mode", models.BooleanField(default=False)),
                ("dry_run", models.BooleanField(default=False)),
                ("store_identity_notes", models.BooleanField(default=True)),
                ("max_hosts", models.PositiveIntegerField(default=4096)),
                ("nmap_host_timeout", models.PositiveIntegerField(default=30)),
                ("snmp_timeout", models.PositiveIntegerField(default=2)),
                ("estimated_host_count", models.PositiveIntegerField(default=0)),
                ("responsive_hosts_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("reused_count", models.PositiveIntegerField(default=0)),
                ("snmp_failures_count", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("job_id", models.CharField(blank=True, max_length=100)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("results", models.JSONField(blank=True, default=list)),
                ("error", models.TextField(blank=True)),
                (
                    "credential",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="netmapper.credential",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="+",
                        to="dcim.site",
                    ),
                ),
                (
                    "snmp_credential",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="+",
                        to="netmapper.snmpcredential",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        through="extras.TaggedItem", to="extras.Tag"
                    ),
                ),
            ],
            options={
                "verbose_name": "Network scan",
                "verbose_name_plural": "Network scans",
                "ordering": ["-created"],
            },
        ),
    ]
