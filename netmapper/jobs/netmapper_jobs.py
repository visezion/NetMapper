"""Script used to manually import Discoverables."""  # pylint: disable=invalid-name

__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from datetime import date, timedelta
import re
import traceback
import netaddr

from django.conf import settings
from django.utils import timezone

from dcim.models import Site, DeviceRole, Interface, Device
from ipam.models import IPAddress
from extras.scripts import (
    Script,
    ChoiceVar,
    ObjectVar,
    MultiObjectVar,
    TextVar,
    BooleanVar,
    IntegerVar,
    StringVar,
)
from utilities.forms.widgets import APISelect, APISelectMultiple

from netmapper.models import (
    Discoverable as Discoverable_m,
    Credential as Credential_m,
    NetworkScanRecord as NetworkScanRecord_m,
    NetworkScanStatusChoices,
    SnmpVersionChoices,
    SnmpCredential as SnmpCredential_m,
    DiscoveryLog as DiscoveryLog_m,
    ArpTableEntry as ArpTableEntry_m,
    MacAddressTableEntry as MacAddressTableEntry_m,
)
from netmapper.utils import (
    log_ingest,
    normalize_interface_label,
    normalize_hostname,
    spawn_script,
)
from netmapper.schemas import discoverable
from netmapper.tasks import discovery
from netmapper.dictionaries import (
    DiscoveryModeChoices,
    DeviceImageChoices,
    FilterModeChoices,
)
from netmapper.network_discovery import (
    build_scan_plan,
    candidate_to_summary,
    merge_identity_note,
    normalize_snmp_communities,
    scan_host_candidates,
)
from netmapper.scan_ingestion import (
    candidate_requires_generic_seed,
    seed_device_from_scan_candidate,
)

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netmapper", {})
NORNIR_LOG = PLUGIN_SETTINGS.get("NORNIR_LOG")
MAX_INGESTED_LOGS = PLUGIN_SETTINGS.get("MAX_INGESTED_LOGS")
DISCOVERY_BATCH_SIZE = max(1, PLUGIN_SETTINGS.get("DISCOVERY_BATCH_SIZE", 10))
NMAP_EXECUTABLE = PLUGIN_SETTINGS.get("NMAP_EXECUTABLE", "nmap")
SNMPGET_EXECUTABLE = PLUGIN_SETTINGS.get("SNMPGET_EXECUTABLE", "snmpget")
NMAP_HOST_TIMEOUT = PLUGIN_SETTINGS.get("NMAP_HOST_TIMEOUT", 30)
SNMP_FALLBACK_MAX_HOSTS = PLUGIN_SETTINGS.get("SNMP_FALLBACK_MAX_HOSTS", 256)
SNMP_TIMEOUT = PLUGIN_SETTINGS.get("SNMP_TIMEOUT", 2)
SUBNET_SCAN_MAX_HOSTS = PLUGIN_SETTINGS.get("SUBNET_SCAN_MAX_HOSTS", 4096)
PLUGIN_API_BASE = "/api/plugins/netmapper"
CREDENTIAL_API_URL = f"{PLUGIN_API_BASE}/credential/"
SNMP_CREDENTIAL_API_URL = f"{PLUGIN_API_BASE}/snmpcredential/"
DISCOVERABLE_API_URL = f"{PLUGIN_API_BASE}/discoverable/"


def _normalize_filters(raw_filters):
    """Return a clean filter list from a comma-separated string."""
    if not raw_filters:
        return []
    return [item.strip() for item in raw_filters.split(",") if item.strip()]


def _spawn_discovery_batch(
    script_handler,
    discoverables,
    filters=None,
    filter_type="exclude",
):
    """Run discovery on a batch and queue a follow-up job if needed."""
    if not discoverables:
        script_handler.log_failure("No discoverables selected")
        return ""

    filters = filters or []
    current_batch = discoverables[:DISCOVERY_BATCH_SIZE]
    remaining_batch = discoverables[DISCOVERY_BATCH_SIZE:]
    current_addresses = [str(discoverable_o.address) for discoverable_o in current_batch]

    if remaining_batch:
        script_handler.log_info(
            f"Processing {len(current_batch)} discoverables now and queuing "
            f"{len(remaining_batch)} more in a follow-up job"
        )
        spawn_script(
            "Discover",
            post_data={
                "discoverables": remaining_batch,
                "undiscovered_only": False,
                "filters": ",".join(filters),
                "filter_type": filter_type,
            },
            user=script_handler.request.user,
        )

    return discovery(
        current_addresses,
        script_handler=script_handler,
        filters=filters,
        filter_type=filter_type,
    )


def _ensure_selected_discoverables_enabled(script_handler, discoverables):
    """Enable explicitly selected discoverables before running discovery."""
    updated_addresses = []
    for discoverable_o in discoverables or []:
        if discoverable_o.discoverable:
            continue
        discoverable_o.discoverable = True
        discoverable_o.save(update_fields=["discoverable", "last_updated"])
        updated_addresses.append(str(discoverable_o.address))

    if updated_addresses:
        script_handler.log_info(
            "Enabled discoverable flag for explicitly selected devices: "
            + ", ".join(updated_addresses)
        )


class CreateDeviceRole(Script):
    """Script used to create DeviceRole used in Diagram.

    DeviceRole.slug is used to draw the icon in diagrams.
    """

    class Meta:
        """Script metadata."""

        name = "Create device roles"
        description = "Add device roles based on available PNG."
        commit_default = True

    def run(self, data, commit):
        """Start the script."""
        icons = DeviceImageChoices()
        for key, value in icons:
            try:
                DeviceRole.objects.get(slug=key)
                self.log_info(f"DeviceRole {key} found")
            except DeviceRole.DoesNotExist:  # pylint: disable=no-member
                self.log_warning(f"Created DeviceRole {key}")
                DeviceRole.objects.create(name=value, slug=key)


class AddDiscoverable(Script):
    """Script used to generate AddDiscoverable."""

    class Meta:
        """Script metadata."""

        name = "Add and discover"
        description = "Add comma separated IP addresses and discover them."
        commit_default = True

    # Credentials
    credential = ObjectVar(
        model=Credential_m,
        description="Credential used to discover.",
        required=True,
        widget=APISelect(api_url=CREDENTIAL_API_URL),
    )

    # Discovery mode
    mode = ChoiceVar(
        choices=DiscoveryModeChoices.CHOICES,
        description="Discovery mode",
        required=True,
    )

    # Site
    site = ObjectVar(
        model=Site,
        description="Site associated with discovered devices",
        required=True,
    )

    # IP addresses to be discovered
    ip_addresses = TextVar(
        description="IP addresses separated by comma or space",
        required=True,
    )

    # Filter (include/exclude commands)
    filters = StringVar(
        description="Filter command based on words separated by comma (e.g. mac,route).",
        required=False,
    )
    filter_type = ChoiceVar(
        choices=FilterModeChoices.CHOICES,
        description="Filter type",
        required=True,
        default="exclude",
    )

    def run(self, data, commit):
        """Start the script."""
        discoverable_ip_addresses = []
        discoverable_objects = []

        if not commit:
            self.log_warning("Commit not set, using dry-run mode")

        credential_o = data.get("credential")
        mode = data.get("mode")
        site_o = data.get("site")
        ip_addresses = re.split(" |,|\n", data.get("ip_addresses"))

        filters = _normalize_filters(data.get("filters"))
        filter_type = data.get("filter_type")

        # Parse IP addresses
        for ip_address in ip_addresses:
            ip_address = ip_address.strip()
            if not ip_address:
                # Skip empty string
                continue

            try:
                netaddr.IPAddress(ip_address)
            except netaddr.core.AddrFormatError:
                # Skip invalid IP address
                self.log_warning(f"Skipping invalid IP address {ip_address}")
                continue

            # Create or get Discoverable
            discoverable_o, created = discoverable.get_or_create(
                address=ip_address,
                site_id=site_o.pk,
                mode=mode,
                credential_id=credential_o.pk,
                discoverable=True,
            )
            if created:
                self.log_info(
                    f"Created new discoverable with IP address {discoverable_o.address}"
                )
            else:
                self.log_info(
                    f"Using existing discoverable with IP address {discoverable_o.address}"
                )

            discoverable_ip_addresses.append(discoverable_o.address)
            discoverable_objects.append(discoverable_o)

        if not discoverable_ip_addresses:
            self.log_failure("No valid IP address to discover")
            return ""

        self.log_info(f"Starting discovery on {', '.join(discoverable_ip_addresses)}")
        output = _spawn_discovery_batch(
            self,
            discoverable_objects,
            filters=filters,
            filter_type=filter_type,
        )

        self.log_info("Discovery completed")
        log_qs = DiscoveryLog_m.objects.filter(ingested=False, parsed=True)
        self.log_info(f"{len(log_qs)} logs to be ingested")

        return output


class ScanNetwork(Script):
    """Seed discoverables from a subnet/range using Nmap and optional SNMP."""

    class Meta:
        """Script metadata."""

        name = "Scan subnet or range"
        description = (
            "Use Nmap to find live hosts, enrich them with SNMP identity, create "
            "or update discoverables, and queue the full NetMapper discovery and "
            "ingest workflow."
        )
        commit_default = True

    credential = ObjectVar(
        model=Credential_m,
        description=(
            "Optional login credential attached to created discoverables. "
            "Leave empty for SNMP-only scans."
        ),
        required=False,
        widget=APISelect(api_url=CREDENTIAL_API_URL),
    )
    default_mode = ChoiceVar(
        choices=DiscoveryModeChoices.CHOICES,
        description="Fallback discovery mode when SNMP cannot infer a platform.",
        required=True,
    )
    site = ObjectVar(
        model=Site,
        description="Site associated with responsive hosts.",
        required=True,
    )
    targets = TextVar(
        description=(
            "IP addresses, CIDRs, or full IP ranges separated by comma, space, or newline."
        ),
        required=True,
    )
    snmp_credential = ObjectVar(
        model=SnmpCredential_m,
        description=(
            "Optional stored SNMP credential used for platform inference. "
            "When selected, it overrides the manual SNMP fields below."
        ),
        required=False,
        widget=APISelect(api_url=SNMP_CREDENTIAL_API_URL),
    )
    snmp_community = StringVar(
        description=(
            "Optional manual SNMP v2c community used to infer platform identity "
            "when no stored SNMP credential is selected."
        ),
        required=False,
    )
    snmp_port = IntegerVar(
        description="SNMP UDP port used for identity probes.",
        required=False,
        default=161,
    )
    snmp_version = ChoiceVar(
        choices=SnmpVersionChoices.choices,
        description="SNMP protocol version used for identity probes.",
        required=True,
        default=SnmpVersionChoices.V2C,
    )
    discover_now = BooleanVar(
        description="Queue the normal NetMapper discovery workflow after seeding hosts.",
        required=False,
        default=True,
    )
    overwrite_mode = BooleanVar(
        description="Allow inferred/fallback mode to overwrite an existing discoverable mode.",
        required=False,
        default=False,
    )
    store_identity_notes = BooleanVar(
        description="Store Nmap/SNMP identity details in discoverable comments.",
        required=False,
        default=True,
    )
    max_hosts = IntegerVar(
        description="Safety cap for the total number of IPs covered by the request.",
        required=False,
        default=SUBNET_SCAN_MAX_HOSTS,
    )
    nmap_host_timeout = IntegerVar(
        description="Per-host Nmap timeout in seconds.",
        required=False,
        default=NMAP_HOST_TIMEOUT,
    )
    snmp_timeout = IntegerVar(
        description="SNMP timeout in seconds for each responsive host.",
        required=False,
        default=SNMP_TIMEOUT,
    )
    filters = StringVar(
        description="Filter command based on words separated by comma (e.g. mac,route).",
        required=False,
    )
    filter_type = ChoiceVar(
        choices=FilterModeChoices.CHOICES,
        description="Filter type for the queued discovery job.",
        required=True,
        default="exclude",
    )
    scan_record_id = IntegerVar(
        description="Internal record ID used by the Network Scan UI.",
        required=False,
        default=0,
    )

    @staticmethod
    def _save_scan_record(scan_record, **kwargs):
        """Persist scan record changes when a history object is attached."""
        if not scan_record:
            return
        for field, value in kwargs.items():
            setattr(scan_record, field, value)
        scan_record.save()

    @staticmethod
    def _get_placeholder_credential():
        """Return a reusable placeholder credential for SNMP-only scans."""
        credential_o, _ = Credential_m.objects.get_or_create(
            name="SNMP Scan Placeholder",
            defaults={
                "username": "",
                "password": "",
                "enable_password": "",
                "verify_cert": True,
            },
        )
        return credential_o

    @staticmethod
    def _create_scan_record(data, plan, credential, discover_now, dry_run=False):
        """Create a scan history record for direct script execution."""
        return NetworkScanRecord_m.objects.create(
            site=data["site"],
            credential=credential,
            snmp_credential=data.get("snmp_credential"),
            default_mode=data["default_mode"],
            targets=data["targets"],
            normalized_targets=plan.normalized_targets,
            invalid_targets=plan.invalid_targets,
            filters=data.get("filters") or "",
            filter_type=data.get("filter_type") or "",
            discover_now=bool(discover_now),
            overwrite_mode=bool(data.get("overwrite_mode")),
            dry_run=dry_run,
            store_identity_notes=data.get("store_identity_notes", True),
            max_hosts=data.get("max_hosts") or SUBNET_SCAN_MAX_HOSTS,
            nmap_host_timeout=data.get("nmap_host_timeout") or NMAP_HOST_TIMEOUT,
            snmp_timeout=data.get("snmp_timeout") or SNMP_TIMEOUT,
            estimated_host_count=plan.estimated_host_count,
            status=NetworkScanStatusChoices.QUEUED,
            summary={
                "current_stage": "queued",
                "current_stage_label": "Queued",
                "status_message": "Scan request created and waiting for a worker.",
                "progress_percent": 0,
                "created_from": "extras_script",
            },
        )

    def _update_scan_progress(
        self,
        scan_record,
        *,
        stage,
        status_message,
        progress=None,
        extra_summary=None,
        persist_status=None,
    ):
        """Store human-readable stage progress in the scan record summary."""
        if not scan_record:
            return
        summary = dict(scan_record.summary or {})
        summary.update(
            {
                "current_stage": stage,
                "current_stage_label": stage.replace("_", " ").title(),
                "status_message": status_message,
            }
        )
        if progress is not None:
            summary["progress_percent"] = int(progress)
        if extra_summary:
            summary.update(extra_summary)
        fields = {
            "summary": summary,
        }
        if persist_status:
            fields["status"] = persist_status
        self._save_scan_record(scan_record, **fields)

    def _log_candidate_identity(self, candidate):
        """Write a concise identity summary for a responsive host."""
        identity_fragments = []
        if candidate.host.hostname:
            identity_fragments.append(f"nmap hostname={candidate.host.hostname}")
        if candidate.host.vendor:
            identity_fragments.append(f"vendor={candidate.host.vendor}")
        if candidate.snmp_metadata and candidate.snmp_metadata.sys_name:
            identity_fragments.append(f"snmp sysName={candidate.snmp_metadata.sys_name}")
        if candidate.snmp_metadata and candidate.snmp_metadata.sys_descr:
            identity_fragments.append(f"snmp sysDescr={candidate.snmp_metadata.sys_descr}")
        if candidate.inferred_mode:
            identity_fragments.append(f"inferred mode={candidate.inferred_mode}")
        if candidate.inferred_role:
            role_text = candidate.inferred_role
            if candidate.role_confidence:
                role_text += f" ({candidate.role_confidence})"
            identity_fragments.append(f"suggested role={role_text}")
        if identity_fragments:
            self.log_info(f"{candidate.host.address}: {'; '.join(identity_fragments)}")

    def run(self, data, commit):
        """Scan a subnet/range, create discoverables, and optionally discover them."""
        scan_record = None
        plan = None
        try:
            if not commit:
                self.log_warning("Commit not set, using dry-run mode")

            credential_o = data.get("credential")
            site_o = data.get("site")
            default_mode = data.get("default_mode")
            overwrite_mode = data.get("overwrite_mode")
            discover_now = data.get("discover_now")
            store_identity_notes = data.get("store_identity_notes", True)
            scan_record_id = data.get("scan_record_id") or 0
            filters = _normalize_filters(data.get("filters"))
            filter_type = data.get("filter_type")
            snmp_credential = data.get("snmp_credential")
            credential_requested = credential_o is not None
            if not credential_requested:
                credential_o = self._get_placeholder_credential()
            effective_discover_now = bool(discover_now and credential_requested)
            if discover_now and not credential_requested:
                self.log_warning(
                    "No login credential supplied. Running SNMP-only scan and skipping "
                    "queued CLI discovery."
                )

            snmp_community = (data.get("snmp_community") or "").strip()
            snmp_port = data.get("snmp_port") or 161
            snmp_version = data.get("snmp_version") or SnmpVersionChoices.V2C
            if snmp_credential:
                snmp_community = snmp_credential.get_secrets().get("community") or ""
                snmp_port = snmp_credential.port
                snmp_version = snmp_credential.version
            snmp_communities = normalize_snmp_communities(
                snmp_community,
                fallback_communities=["public"] if snmp_community else None,
            )

            plan = build_scan_plan(
                data.get("targets"),
                data.get("max_hosts") or SUBNET_SCAN_MAX_HOSTS,
            )

            if scan_record_id:
                scan_record = NetworkScanRecord_m.objects.filter(pk=scan_record_id).first()
            if not scan_record:
                scan_record = self._create_scan_record(
                    data,
                    plan,
                    credential=credential_o,
                    discover_now=effective_discover_now,
                )

            self._save_scan_record(
                scan_record,
                status=NetworkScanStatusChoices.RUNNING,
                started_at=timezone.now(),
            )
            self._update_scan_progress(
                scan_record,
                stage="planning",
                status_message="Validating scan targets and safety limits.",
                progress=5,
            )

            for invalid_target in plan.invalid_targets:
                self.log_warning(f"Skipping invalid target {invalid_target}")

            if not plan.normalized_targets:
                self._save_scan_record(
                    scan_record,
                    status=NetworkScanStatusChoices.FAILED,
                    finished_at=timezone.now(),
                    error="No valid targets were supplied",
                    normalized_targets=plan.normalized_targets,
                    invalid_targets=plan.invalid_targets,
                    estimated_host_count=plan.estimated_host_count,
                )
                self.log_failure("No valid targets were supplied")
                return ""

            if plan.exceeds_max_hosts:
                error = (
                    f"Requested scan covers {plan.estimated_host_count} IPs which exceeds "
                    f"the safety cap of {plan.max_hosts}"
                )
                self._save_scan_record(
                    scan_record,
                    status=NetworkScanStatusChoices.FAILED,
                    finished_at=timezone.now(),
                    error=error,
                    normalized_targets=plan.normalized_targets,
                    invalid_targets=plan.invalid_targets,
                    estimated_host_count=plan.estimated_host_count,
                )
                self.log_failure(error)
                return ""

            self.log_info(
                f"Scanning {len(plan.normalized_targets)} target specs covering approximately "
                f"{plan.estimated_host_count} IPs"
            )
            self._update_scan_progress(
                scan_record,
                stage="nmap_scan",
                status_message="Running Nmap reachability scan.",
                progress=15,
                extra_summary={
                    "responsive_hosts_count": 0,
                    "normalized_target_count": len(plan.normalized_targets),
                },
            )

            try:
                candidates = scan_host_candidates(
                    plan.normalized_targets,
                    default_mode=default_mode,
                    snmp_community=snmp_communities,
                    snmp_port=snmp_port,
                    snmp_version=snmp_version,
                    host_timeout=data.get("nmap_host_timeout") or NMAP_HOST_TIMEOUT,
                    snmp_timeout=data.get("snmp_timeout") or SNMP_TIMEOUT,
                    nmap_executable=NMAP_EXECUTABLE,
                    snmp_executable=SNMPGET_EXECUTABLE,
                    snmp_fallback_max_hosts=SNMP_FALLBACK_MAX_HOSTS,
                )
            except RuntimeError as exc:
                self._save_scan_record(
                    scan_record,
                    status=NetworkScanStatusChoices.FAILED,
                    finished_at=timezone.now(),
                    error=str(exc),
                    normalized_targets=plan.normalized_targets,
                    invalid_targets=plan.invalid_targets,
                    estimated_host_count=plan.estimated_host_count,
                )
                self.log_failure(str(exc))
                return ""

            self._update_scan_progress(
                scan_record,
                stage="snmp_enrichment",
                status_message=(
                    "Nmap completed. Evaluating SNMP identity and role suggestions."
                ),
                progress=45,
                extra_summary={
                    "responsive_hosts_count": len(candidates),
                },
            )

            if not candidates:
                self._save_scan_record(
                    scan_record,
                    status=NetworkScanStatusChoices.COMPLETED,
                    finished_at=timezone.now(),
                    normalized_targets=plan.normalized_targets,
                    invalid_targets=plan.invalid_targets,
                    estimated_host_count=plan.estimated_host_count,
                    responsive_hosts_count=0,
                    created_count=0,
                    updated_count=0,
                    reused_count=0,
                    snmp_failures_count=0,
                    summary={
                        "discover_now": discover_now,
                        "filters": filters,
                        "filter_type": filter_type,
                        "responsive_hosts_count": 0,
                    },
                    results=[],
                    error="",
                )
                self.log_warning("Nmap did not find any responsive hosts")
                return ""

            created_count = 0
            updated_count = 0
            reused_count = 0
            snmp_failures_count = 0
            seeded_device_count = 0
            scan_discoverables = []
            result_rows = []

            for candidate in candidates:
                if candidate.snmp_failed:
                    snmp_failures_count += 1
                    self.log_warning(
                        f"{candidate.host.address}: SNMP identity probe failed "
                        f"({candidate.snmp_metadata.error})"
                    )

                discoverable_o = Discoverable_m.objects.filter(
                    address=candidate.host.address
                ).first()
                if discoverable_o:
                    change_list = []
                    if credential_requested and discoverable_o.credential_id != credential_o.pk:
                        discoverable_o.credential = credential_o
                        change_list.append("credential")
                    if discoverable_o.site_id != site_o.pk:
                        discoverable_o.site = site_o
                        change_list.append("site")
                    if not discoverable_o.discoverable:
                        discoverable_o.discoverable = True
                        change_list.append("discoverable")
                    if overwrite_mode and discoverable_o.mode != candidate.selected_mode:
                        discoverable_o.mode = candidate.selected_mode
                        change_list.append("mode")
                    if store_identity_notes:
                        merged_notes = merge_identity_note(
                            discoverable_o.identity_notes,
                            candidate.identity_note,
                        )
                        if merged_notes != (discoverable_o.identity_notes or ""):
                            discoverable_o.identity_notes = merged_notes
                            change_list.append("identity_notes")

                    if change_list:
                        discoverable_o.save()
                        updated_count += 1
                        self.log_info(
                            f"Updated discoverable {discoverable_o.address} ({', '.join(change_list)})"
                        )
                    else:
                        reused_count += 1
                        self.log_info(f"Reusing discoverable {discoverable_o.address}")
                else:
                    discoverable_o, _ = discoverable.get_or_create(
                        address=candidate.host.address,
                        site_id=site_o.pk,
                        mode=candidate.selected_mode,
                        credential_id=credential_o.pk,
                        discoverable=True,
                    )
                    if store_identity_notes and candidate.identity_note:
                        discoverable_o.identity_notes = merge_identity_note(
                            discoverable_o.identity_notes,
                            candidate.identity_note,
                        )
                        discoverable_o.save()
                    created_count += 1
                    self.log_info(
                        f"Created discoverable {discoverable_o.address} using mode "
                        f"{candidate.selected_mode}"
                    )

                if candidate_requires_generic_seed(candidate):
                    seeded_device_count += 1
                    device_o, device_created = seed_device_from_scan_candidate(
                        discoverable_o,
                        candidate,
                    )
                    action = "Created" if device_created else "Updated"
                    self.log_info(
                        f"{action} generic NetBox device {device_o.name} from scan identity "
                        f"for {candidate.host.address}"
                    )
                else:
                    scan_discoverables.append(discoverable_o)
                self._log_candidate_identity(candidate)
                result_rows.append(candidate_to_summary(candidate))

            self.log_info(
                f"Scan complete: {created_count} created, {updated_count} updated, {reused_count} reused"
            )
            self._update_scan_progress(
                scan_record,
                stage="seed_discoverables",
                status_message="Responsive hosts have been converted into discoverables.",
                progress=70,
                extra_summary={
                    "responsive_hosts_count": len(candidates),
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "reused_count": reused_count,
                    "snmp_failures_count": snmp_failures_count,
                    "seeded_device_count": seeded_device_count,
                },
            )

            summary = {
                "discover_now": effective_discover_now,
                "discover_now_requested": bool(discover_now),
                "filters": filters,
                "filter_type": filter_type,
                "responsive_hosts_count": len(candidates),
                "snmp_failures_count": snmp_failures_count,
                "seeded_device_count": seeded_device_count,
            }

            if not effective_discover_now:
                summary.update(
                    {
                        "current_stage": "completed",
                        "current_stage_label": "Completed",
                        "status_message": "Scan finished without queued CLI discovery.",
                        "progress_percent": 100,
                    }
                )
                self._save_scan_record(
                    scan_record,
                    status=NetworkScanStatusChoices.COMPLETED,
                    finished_at=timezone.now(),
                    normalized_targets=plan.normalized_targets,
                    invalid_targets=plan.invalid_targets,
                    estimated_host_count=plan.estimated_host_count,
                    responsive_hosts_count=len(candidates),
                    created_count=created_count,
                    updated_count=updated_count,
                    reused_count=reused_count,
                    snmp_failures_count=snmp_failures_count,
                    summary=summary,
                    results=result_rows,
                    error="",
                )
                return ""

            self._update_scan_progress(
                scan_record,
                stage="queue_discovery",
                status_message=(
                    "Queueing NetMapper device discovery and ingestion for responsive hosts."
                ),
                progress=85,
                extra_summary={
                    "queued_discovery_count": len(scan_discoverables),
                },
            )
            output = _spawn_discovery_batch(
                self,
                scan_discoverables,
                filters=filters,
                filter_type=filter_type,
            )
            summary["queued_discovery_count"] = len(scan_discoverables)
            summary.update(
                {
                    "current_stage": "completed",
                    "current_stage_label": "Completed",
                    "status_message": "Scan finished and downstream discovery jobs were queued.",
                    "progress_percent": 100,
                }
            )
            self._save_scan_record(
                scan_record,
                status=NetworkScanStatusChoices.COMPLETED,
                finished_at=timezone.now(),
                normalized_targets=plan.normalized_targets,
                invalid_targets=plan.invalid_targets,
                estimated_host_count=plan.estimated_host_count,
                responsive_hosts_count=len(candidates),
                created_count=created_count,
                updated_count=updated_count,
                reused_count=reused_count,
                snmp_failures_count=snmp_failures_count,
                summary=summary,
                results=result_rows,
                error="",
            )
            self.log_info("Queued NetMapper discovery for responsive hosts")
            return output
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"
            traceback_text = traceback.format_exc()
            if scan_record:
                self._update_scan_progress(
                    scan_record,
                    stage="failed",
                    status_message=error_message,
                    progress=100,
                )
            self._save_scan_record(
                scan_record,
                status=NetworkScanStatusChoices.FAILED,
                finished_at=timezone.now(),
                error=f"{error_message}\n\n{traceback_text}",
                normalized_targets=plan.normalized_targets if plan else [],
                invalid_targets=plan.invalid_targets if plan else [],
                estimated_host_count=plan.estimated_host_count if plan else 0,
            )
            self.log_failure(error_message)
            raise


class Discover(Script):
    """Script used to start discovery."""

    class Meta:
        """Script metadata."""

        name = "Discover"
        description = "Start discovery on one, many or all discoverables."
        commit_default = True

    # Discoverable
    discoverables = MultiObjectVar(
        model=Discoverable_m,
        query_params={"discoverable": True},  # An API filterset must exists
        description="Devices to be discovered (leave empty to discover everything).",
        required=False,
        widget=APISelectMultiple(api_url=DISCOVERABLE_API_URL),
    )

    # Ingested?
    undiscovered_only = BooleanVar(
        description="Undiscovered devices only (the above setting is ignored).",
        required=False,
        default=True,
    )

    # Filter (include/exclude commands)
    filters = StringVar(
        description="Filter command based on words separated by comma (e.g. mac,route).",
        required=False,
    )
    filter_type = ChoiceVar(
        choices=FilterModeChoices.CHOICES,
        description="Filter type",
        required=True,
        default="exclude",
    )

    def run(self, data, commit):
        """Start the script."""
        # Filtering out discoverable=False is done at Nornir inventory level.
        discoverables = data.get("discoverables")
        filters = _normalize_filters(data.get("filters"))
        filter_type = data.get("filter_type")

        if data.get("undiscovered_only"):
            # Get only undiscovered IP addresses
            discoverables = discoverable.get_list(
                last_discovered_at__isnull=True, discoverable=True
            )
            discoverable_ip_addresses = [
                str(discoverable_o.address) for discoverable_o in discoverables
            ]
            self.log_info(
                f"Starting first discovery on {', '.join(discoverable_ip_addresses)}"
            )
        elif discoverables:
            _ensure_selected_discoverables_enabled(self, discoverables)
            discoverable_ip_addresses = [
                str(discoverable_o.address) for discoverable_o in discoverables
            ]
            self.log_info(
                f"Starting discovery on {', '.join(discoverable_ip_addresses)}"
            )
        else:
            discoverables = discoverable.get_list(discoverable=True)
            discoverable_ip_addresses = [
                str(discoverable_o.address) for discoverable_o in discoverables
            ]
            self.log_info("Starting discovery on all IP addresses")

        if not discoverables:
            self.log_failure("No discoverables selected")
            return ""

        output = _spawn_discovery_batch(
            self,
            list(discoverables),
            filters=filters,
            filter_type=filter_type,
        )

        self.log_info("Discovery completed")
        log_qs = DiscoveryLog_m.objects.filter(ingested=False, parsed=True)
        self.log_info(f"{len(log_qs)} logs to be ingested")

        return output


class Ingest(Script):
    """Script used to start ingestion."""

    class Meta:
        """Script metadata."""

        name = "Ingest"
        description = (
            "Start data ingestion (automatically triggered after a discovery)."
        )
        commit_default = True

    # Discoverable
    discoverables = MultiObjectVar(
        model=Discoverable_m,
        description="Limit ingestion to selected discoverables.",
        required=False,
        widget=APISelectMultiple(api_url=DISCOVERABLE_API_URL),
    )

    # Ingested?
    re_ingest = BooleanVar(
        description="Force re-ingestion.",
        required=False,
    )

    # Maximum logs to ingest
    max_ingested_logs = IntegerVar(
        description="Maximum logs to ingest before spawning another job",
        required=False,
        default=MAX_INGESTED_LOGS,
    )

    def run(self, data, commit):
        """Start the script."""
        log_list = data.get("log_list") if data.get("log_list") else []
        # Jobs spaned by discovery script don't have max_ingested_logs via POST
        max_ingested_logs = (
            data.get("max_ingested_logs")
            if data.get("max_ingested_logs")
            else MAX_INGESTED_LOGS
        )

        if log_list:
            # This is a spawned (child) job, get remaining logs
            self.log_info("This is a child ingest job")
            log_list_qs = DiscoveryLog_m.objects.filter(id__in=log_list).order_by(
                "order"
            )
        else:
            # This is the parent job, get all logs to be ingested
            self.log_info("This is the parent ingest job")
            log_list_qs = DiscoveryLog_m.objects.filter(
                supported=True, parsed=True
            ).order_by("order")
            if not data.get("re_ingest"):
                # Filter out logs already ingested
                log_list_qs = log_list_qs.filter(ingested=False)
            if data.get("discoverables"):
                log_list_qs = log_list_qs.filter(
                    discoverable__in=data.get("discoverables")
                )
            log_list = log_list_qs.values_list("id", flat=True)

        # Always limit max number of ingested logs to avoid timeout
        self.log_info(f"{len(log_list_qs)} logs to be ingested")
        if len(log_list) > max_ingested_logs:
            ingesting_log_qs = log_list_qs[:max_ingested_logs]
            self.log_info(f"Limiting ingesting to {max_ingested_logs} logs")
        else:
            ingesting_log_qs = log_list_qs

        for log in ingesting_log_qs:
            msg = (
                f" log {log.id} with command {log.command} on device {log.discoverable}"
            )
            if log.ingested:
                self.log_info(f"Reingesting {msg}")
            else:
                self.log_info(f"Ingesting {msg}")
            try:
                log_ingest(log)
            except ValueError as exc:
                self.log_failure(str(exc))

        if len(log_list) > max_ingested_logs:
            # Need to span another job
            remaining_log_list = log_list[max_ingested_logs:]
            data["log_list"] = remaining_log_list
            self.log_info(f"Spawning a new job to inget {len(remaining_log_list)} logs")
            spawn_script("Ingest", post_data=data, user=self.request.user)


class Purge(Script):
    """Script used to delete old data."""

    class Meta:
        """Script metadata."""

        name = "Purge"
        description = "Delete old logs, ARP table entries, MAC Address table entries."
        commit_default = True

    # Minimum days to delete
    days = IntegerVar(
        description="Minimum age in days to delete",
        required=True,
        default=90,
    )

    def run(self, data, commit):
        """Start the script."""
        today = date.today()
        today_minus_x = today - timedelta(days=data.get("days"))

        discoverylogs_qs = DiscoveryLog_m.objects.filter(created__lt=today_minus_x)
        arpentries_qs = ArpTableEntry_m.objects.filter(last_updated__lt=today_minus_x)
        macaddressentries_qs = MacAddressTableEntry_m.objects.filter(
            last_updated__lt=today_minus_x
        )
        orphan_arpentries_qs = ArpTableEntry_m.objects.filter(
            interface__ip_addresses__isnull=True
        )

        self.log_info(f"Deleting entries updated before f{today_minus_x}")
        self.log_info(f"Deleting {len(discoverylogs_qs)} discovery logs")
        if discoverylogs_qs:
            discoverylogs_qs.delete()
        self.log_info(f"Deleting {len(arpentries_qs)} ARP table entries")
        if arpentries_qs:
            arpentries_qs.delete()
        self.log_info(f"Deleting {len(macaddressentries_qs)} MAC address table entries")
        if macaddressentries_qs:
            macaddressentries_qs.delete()
        self.log_info(f"Deleting {len(orphan_arpentries_qs)} orphan ARP table entries")
        if orphan_arpentries_qs:
            orphan_arpentries_qs.delete()
        self.log_info("Purge completed")


class IPAMFromARP(Script):
    """Create IP Address on IPAM based on ARP table."""

    class Meta:
        """Script metadata."""

        name = "Update IPAM from ARP tables"
        description = (
            "Create IP Address on IPAM based on ARP table. Should be started after "
            + "VRFIpPrefixIntegrityCheck report."
        )
        commit_default = True

    def run(self, data, commit):
        """For each ARP, check if an IPAddress exist and create it if it doesn't.

        ARPTableEntry.Interface.IPAddress.VRF must be equal to Prefix.VRF.
        """
        for arptableentry_o in ArpTableEntry_m.objects.exclude(
            interface__ip_addresses__isnull=True
        ):
            try:
                interface_vrf_o = arptableentry_o.interface.ip_addresses.first().vrf
                # IP address with prefixlen built from ARP table and associated interface
                address = str(arptableentry_o.ip_address.ip)
                prefixlen = (
                    arptableentry_o.interface.ip_addresses.filter(
                        address__net_contains_or_equals=address
                    )
                    .first()
                    .address.prefixlen
                )
                ip_address = f"{address}/{prefixlen}"
            except AttributeError:
                self.log_failure(
                    f"IP address not found on interface {arptableentry_o.interface}, maybe "
                    + "some ingestion script has failed",
                )
                continue

            # Query for the IP address in the IPAM
            ipaddresses_qs = IPAddress.objects.filter(
                vrf=interface_vrf_o, address=ip_address
            )
            if not ipaddresses_qs:
                IPAddress.objects.create(address=ip_address, vrf=interface_vrf_o)
                self.log_info(
                    f"IP address {ip_address} with VRF {interface_vrf_o} added in IPAM",
                )


class FixData(Script):
    """Fix Device names and Interface labels."""

    class Meta:
        """Script metadata."""

        name = "Fix Netbox data"
        description = (
            "Fix Netbox data to be used with NetMapper (Device names, Interface labels)."
        )
        commit_default = True

    def run(self, data, commit):
        """Test and fix Netbox data."""
        # Test Device name
        device_qs = Device.objects.all()
        for device_o in device_qs:
            name = device_o.name
            new_name = normalize_hostname(name)

            if name == new_name:
                self.log_info(f"{device_o} has name {new_name}")
            else:
                self.log_warning(f"Renaming device {device_o} to {new_name}")
                device_o.name = new_name
                device_o.save()

        # Test Interface name/label integrity
        interface_qs = Interface.objects.all()
        for interface_o in interface_qs:
            name = interface_o.name
            new_label = normalize_interface_label(name)

            if interface_o.label == new_label:
                self.log_info(f"{interface_o} has label {new_label}")
            else:
                self.log_warning(
                    f"Renaming label {interface_o.label} to {new_label} for interface {interface_o}"
                )
                interface_o.label = new_label
                interface_o.save()
