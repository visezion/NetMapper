"""Views, called by URLs."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

import logging
import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.conf import settings
from django.db.models import Count
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import FormView

from utilities.forms import BulkDeleteForm, ConfirmationForm
from utilities.htmx import htmx_partial
from utilities.permissions import get_permission_for_model
from utilities.views import get_viewname
from netbox.object_actions import (
    AddObject,
    BulkDelete,
    BulkEdit,
    BulkExport,
    BulkImport,
    ObjectAction,
)
from netbox.views import generic

from netmapper import models, tables, forms, filtersets, utils, topologies
from netmapper.credential_testing import (
    test_discovery_credential,
    test_snmp_credential,
)
from netmapper.network_discovery import (
    build_scan_plan,
    candidate_to_summary,
    scan_host_candidates,
)
from netmapper.job_tracking import reconcile_scan_record_job

try:
    PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netmapper", {})
except ImproperlyConfigured:
    PLUGIN_SETTINGS = {}


class BulkDiscoverAction(ObjectAction):
    """Bulk discovery action for Discoverable list views."""

    name = "bulk_discover"
    label = "Discover Selected"
    multi = True
    permissions_required = {"change"}
    template_name = "netmapper/buttons/bulk_discover.html"


class BulkIngestAction(ObjectAction):
    """Bulk ingest action for Discoverable list views."""

    name = "bulk_ingest"
    label = "Ingest Selected"
    multi = True
    permissions_required = {"change"}
    template_name = "netmapper/buttons/bulk_ingest.html"


#
# ARPEntry views
#


class ArpTableListView(generic.ObjectListView):
    """Summary view listing all ARP."""

    queryset = models.ArpTableEntry.objects.all().order_by(
        "interface__device__name", "interface__name", "ip_address"
    )
    table = tables.ArpTableEntryTable
    filterset = filtersets.ArpTableEntryFilterSet
    actions = (BulkExport,)


class ArpTableView(generic.ObjectView):
    """Detailed ARP table entry view."""

    queryset = models.ArpTableEntry.objects.all()

    def get_extra_context(self, request, instance):
        """Get associated ARP and MAC Address tables."""
        arp_table_qs = models.ArpTableEntry.objects.filter(
            ip_address=str(instance.ip_address)
        )
        arp_table = tables.ArpTableEntryTable(arp_table_qs)
        arp_table.configure(request)

        macaddress_table_qs = models.MacAddressTableEntry.objects.filter(
            mac_address=instance.mac_address
        )
        macaddress_table = tables.MacAddressTableEntryTable(macaddress_table_qs)
        macaddress_table.configure(request)

        return {
            "arp_table": arp_table,
            "macaddress_table": macaddress_table,
        }


#
# Credential views
#


class CredentialListView(generic.ObjectListView):
    """Summary view listing all Credential objects."""

    queryset = models.Credential.objects.annotate(
        discoverables_count=Count("discoverables")
    ).order_by("name")
    table = tables.CredentialTable
    filterset = filtersets.CredentialFilterSet
    actions = (AddObject, BulkImport, BulkDelete)


class CredentialView(generic.ObjectView):
    """Detailed Credential view."""

    queryset = models.Credential.objects.all()

    def get_extra_context(self, request, instance):
        """Get associated Discoverable obhects."""
        table = tables.DiscoverableTableWOLogCount(instance.discoverables.all())
        table.configure(request)

        return {
            "discoverables_table": table,
        }


class CredentialTestView(PermissionRequiredMixin, FormView):
    """Test a stored discovery credential against a target address."""

    form_class = forms.CredentialConnectionTestForm
    permission_required = "netmapper.view_credential"
    template_name = "netmapper/credential_test.html"

    def dispatch(self, request, *args, **kwargs):
        """Load the credential once for GET/POST handling."""
        self.credential = models.Credential.objects.get(pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Expose the credential and optional test result."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "credential": self.credential,
                "return_url": self.credential.get_absolute_url(),
            }
        )
        return context

    def form_valid(self, form):
        """Run the discovery credential test and display the result."""
        try:
            result = test_discovery_credential(
                self.credential,
                address=form.cleaned_data["address"],
                mode=form.cleaned_data["mode"],
                timeout=form.cleaned_data["timeout"] or 10,
            )
        except Exception as exc:  # pylint: disable=broad-except
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        context = self.get_context_data(form=form, test_result=result)
        return self.render_to_response(context)


class CredentialEditView(generic.ObjectEditView):
    """Edit Credential view."""

    queryset = models.Credential.objects.all()
    form = forms.CredentialForm


class CredentialDeleteView(generic.ObjectDeleteView):
    """Delete Credential view."""

    queryset = models.Credential.objects.all()
    default_return_url = "plugins:netmapper:credential_list"


class CredentialBulkImportView(generic.BulkImportView):
    """Bulk import Credential view."""

    queryset = models.Credential.objects.all()
    model_form = forms.CredentialCSVForm
    table = tables.CredentialTable


class CredentialBulkEditView(generic.BulkEditView):
    """Bulk edit Credential view."""

    queryset = models.Credential.objects.all()
    table = tables.CredentialTable
    default_return_url = "plugins:netmapper:credential_list"
    filterset = filtersets.CredentialFilterSet


class CredentialBulkDeleteView(generic.BulkDeleteView):
    """Bulk delete Credential view."""

    queryset = models.Credential.objects.all()
    table = tables.CredentialTable
    default_return_url = "plugins:netmapper:credential_list"
    filterset = filtersets.CredentialFilterSet


class SnmpCredentialListView(generic.ObjectListView):
    """Summary view listing stored SNMP credentials."""

    queryset = models.SnmpCredential.objects.all().order_by("name")
    table = tables.SnmpCredentialTable
    filterset = filtersets.SnmpCredentialFilterSet
    actions = (AddObject,)


class SnmpCredentialView(generic.ObjectView):
    """Detailed stored SNMP credential view."""

    queryset = models.SnmpCredential.objects.all()


class SnmpCredentialTestView(PermissionRequiredMixin, FormView):
    """Test a stored SNMP credential against a target address."""

    form_class = forms.SnmpCredentialConnectionTestForm
    permission_required = "netmapper.view_snmpcredential"
    template_name = "netmapper/snmpcredential_test.html"

    def dispatch(self, request, *args, **kwargs):
        """Load the SNMP credential once for GET/POST handling."""
        self.snmp_credential = models.SnmpCredential.objects.get(pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Expose the SNMP credential and optional test result."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "snmp_credential": self.snmp_credential,
                "return_url": self.snmp_credential.get_absolute_url(),
            }
        )
        return context

    def form_valid(self, form):
        """Run the SNMP credential test and display the result."""
        result = test_snmp_credential(
            self.snmp_credential,
            address=form.cleaned_data["address"],
            timeout=form.cleaned_data["timeout"] or 2,
        )
        if not result.get("success"):
            form.add_error(None, result.get("error"))
        context = self.get_context_data(form=form, test_result=result)
        return self.render_to_response(context)


class SnmpCredentialEditView(generic.ObjectEditView):
    """Edit stored SNMP credential view."""

    queryset = models.SnmpCredential.objects.all()
    form = forms.SnmpCredentialForm


class SnmpCredentialDeleteView(generic.ObjectDeleteView):
    """Delete stored SNMP credential view."""

    queryset = models.SnmpCredential.objects.all()
    default_return_url = "plugins:netmapper:snmpcredential-list"


class NetworkScanView(PermissionRequiredMixin, FormView):
    """Dedicated UI for subnet/range scans using stored SNMP credentials."""

    form_class = forms.NetworkScanForm
    permission_required = "netmapper.change_discoverable"
    template_name = "netmapper/network_scan.html"

    def get_success_url(self):
        """Redirect back to the scan page after submitting a job."""
        return reverse("plugins:netmapper:network_scan")

    def get_context_data(self, **kwargs):
        """Add standard template context."""
        context = super().get_context_data(**kwargs)
        recent_scans = list(models.NetworkScanRecord.objects.all()[:10])
        for scan_record in recent_scans:
            reconcile_scan_record_job(scan_record)
        recent_scans_table = tables.NetworkScanRecordTable(recent_scans)
        recent_scans_table.configure(self.request)
        context.update(
            {
                "title": "Network Scan",
                "return_url": reverse("plugins:netmapper:discoverable_list"),
                "recent_scans_table": recent_scans_table,
            }
        )
        return context

    def _build_scan_post_data(self, form):
        """Create the post_data payload expected by the script job."""
        snmp_credential = form.cleaned_data.get("snmp_credential")
        snmp_community = ""
        snmp_port = 161
        snmp_version = models.SnmpVersionChoices.V2C
        if snmp_credential:
            snmp_community = snmp_credential.get_secrets().get("community") or ""
            snmp_port = snmp_credential.port
            snmp_version = snmp_credential.version

        return {
            "credential": form.cleaned_data["credential"],
            "default_mode": form.cleaned_data["default_mode"],
            "site": form.cleaned_data["site"],
            "targets": form.cleaned_data["targets"],
            "snmp_community": snmp_community,
            "snmp_port": snmp_port,
            "snmp_version": snmp_version,
            "discover_now": form.cleaned_data["discover_now"],
            "overwrite_mode": form.cleaned_data["overwrite_mode"],
            "store_identity_notes": form.cleaned_data["store_identity_notes"],
            "max_hosts": form.cleaned_data["max_hosts"],
            "nmap_host_timeout": form.cleaned_data["nmap_host_timeout"],
            "snmp_timeout": form.cleaned_data["snmp_timeout"],
            "filters": form.cleaned_data["filters"],
            "filter_type": form.cleaned_data["filter_type"],
        }

    def _create_scan_record(self, form, plan, dry_run=False):
        """Persist a network scan history record."""
        return models.NetworkScanRecord.objects.create(
            site=form.cleaned_data["site"],
            credential=form.cleaned_data["credential"],
            snmp_credential=form.cleaned_data.get("snmp_credential"),
            default_mode=form.cleaned_data["default_mode"],
            targets=form.cleaned_data["targets"],
            normalized_targets=plan.normalized_targets,
            invalid_targets=plan.invalid_targets,
            filters=form.cleaned_data["filters"],
            filter_type=form.cleaned_data["filter_type"],
            discover_now=form.cleaned_data["discover_now"],
            overwrite_mode=form.cleaned_data["overwrite_mode"],
            dry_run=dry_run,
            store_identity_notes=form.cleaned_data["store_identity_notes"],
            max_hosts=form.cleaned_data["max_hosts"],
            nmap_host_timeout=form.cleaned_data["nmap_host_timeout"],
            snmp_timeout=form.cleaned_data["snmp_timeout"],
            estimated_host_count=plan.estimated_host_count,
            status=models.NetworkScanStatusChoices.QUEUED,
            summary={
                "current_stage": "queued",
                "current_stage_label": "Queued",
                "status_message": "Scan request created and waiting for a worker.",
                "progress_percent": 0,
            },
        )

    def _render_preview(self, form, plan, candidates=None, preview_error=None):
        """Render the page with preview or dry-run results."""
        preview_summary = None
        if candidates is not None:
            preview_summary = {
                "responsive_hosts_count": len(candidates),
                "snmp_failures_count": len([candidate for candidate in candidates if candidate.snmp_failed]),
                "results": [candidate_to_summary(candidate) for candidate in candidates[:25]],
            }
        context = self.get_context_data(
            form=form,
            preview_plan=plan,
            preview_summary=preview_summary,
            preview_error=preview_error,
        )
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """Support preview, dry-run, and queued execution from one form."""
        self.object = None
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)

        plan = build_scan_plan(
            form.cleaned_data["targets"],
            form.cleaned_data["max_hosts"],
        )

        if "_preview" in request.POST:
            return self._render_preview(form, plan)

        if plan.exceeds_max_hosts:
            form.add_error(
                "max_hosts",
                f"Requested scan covers {plan.estimated_host_count} IPs which exceeds the safety cap of {plan.max_hosts}.",
            )
            return self.form_invalid(form)

        if "_dry_run" in request.POST:
            post_data = self._build_scan_post_data(form)
            try:
                candidates = scan_host_candidates(
                    plan.normalized_targets,
                    default_mode=post_data["default_mode"],
                    snmp_community=post_data["snmp_community"],
                    snmp_port=post_data["snmp_port"],
                    snmp_version=post_data["snmp_version"],
                    host_timeout=post_data["nmap_host_timeout"],
                    snmp_timeout=post_data["snmp_timeout"],
                    snmp_fallback_max_hosts=PLUGIN_SETTINGS.get(
                        "SNMP_FALLBACK_MAX_HOSTS", 256
                    ),
                )
            except Exception as exc:  # pylint: disable=broad-except
                return self._render_preview(form, plan, preview_error=str(exc))

            record = self._create_scan_record(form, plan, dry_run=True)
            record.status = models.NetworkScanStatusChoices.COMPLETED
            record.started_at = timezone.now()
            record.finished_at = timezone.now()
            record.responsive_hosts_count = len(candidates)
            record.snmp_failures_count = len([candidate for candidate in candidates if candidate.snmp_failed])
            record.summary = {
                "preview_only": True,
                "current_stage": "completed",
                "current_stage_label": "Completed",
                "status_message": "Dry run completed successfully.",
                "progress_percent": 100,
                "responsive_hosts_count": record.responsive_hosts_count,
                "snmp_failures_count": record.snmp_failures_count,
            }
            record.results = [candidate_to_summary(candidate) for candidate in candidates]
            record.save()
            messages.success(
                request,
                f"Dry run completed successfully ({record.responsive_hosts_count} responsive hosts).",
            )
            return self._render_preview(form, plan, candidates=candidates)

        return self.form_valid(form, plan=plan)

    def form_valid(self, form, plan=None):
        """Queue the scan job using the stored SNMP credential, if supplied."""
        plan = plan or build_scan_plan(
            form.cleaned_data["targets"],
            form.cleaned_data["max_hosts"],
        )
        post_data = self._build_scan_post_data(form)
        record = self._create_scan_record(form, plan, dry_run=False)
        post_data["scan_record_id"] = record.pk

        try:
            job_id = utils.spawn_script("ScanNetwork", user=self.request.user, post_data=post_data)
        except Exception as exc:  # pylint: disable=broad-except
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        record.job_id = str(job_id)
        record.save(update_fields=["job_id", "last_updated"])

        messages.success(
            self.request,
            f"Network scan queued successfully (job ID {job_id}).",
        )
        return super().form_valid(form)


class NetworkScanRecordListView(generic.ObjectListView):
    """Summary view listing saved network scans."""

    queryset = models.NetworkScanRecord.objects.all()
    table = tables.NetworkScanRecordTable
    filterset = filtersets.NetworkScanRecordFilterSet
    filterset_form = forms.NetworkScanRecordFilterForm


class NetworkScanRecordView(generic.ObjectView):
    """Detailed saved network scan view."""

    queryset = models.NetworkScanRecord.objects.all()

    def get_extra_context(self, request, instance):
        """Expose summary data to the template."""
        job_health = reconcile_scan_record_job(instance)
        return {
            "summary_rows": instance.results[:50],
            "job_health": job_health,
            "auto_refresh": instance.status in {
                models.NetworkScanStatusChoices.QUEUED,
                models.NetworkScanStatusChoices.RUNNING,
            },
        }


#
# Diagram views
#


class DiagramListView(generic.ObjectListView):
    """Summary view listing all Diagram objects."""

    queryset = models.Diagram.objects.all().order_by("name")
    table = tables.DiagramTable


class DiagramView(generic.ObjectView):
    """Detailed Diagram view."""

    queryset = models.Diagram.objects.all()

    def get_extra_context(self, request, instance):
        """Get associated Diagram obhects from Interface queryset."""
        sites = list(instance.sites.all().values_list("id", flat=True))
        roles = list(instance.device_roles.all().values_list("id", flat=True))
        vrfs = list(instance.vrfs.all().values_list("id", flat=True))

        interface_qs = utils.get_diagram_interfaces(
            instance.mode,
            sites=sites,
            roles=roles,
            vrfs=vrfs,
            include_global_vrf=instance.include_global_vrf,
        )

        # Build and return the topology
        try:
            module = getattr(topologies, f"get_{instance.mode}_topology_data")
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                f"Get topology function not found for {instance.mode}"
            ) from exc
        topology_data = module(interface_qs, instance.details)
        topology_empty_message = None
        if not topology_data.get("nodes"):
            if instance.mode == "l2":
                topology_empty_message = (
                    "No cabled interfaces matched this diagram. "
                    "L2 diagrams only include interfaces attached to cables."
                )
            elif instance.mode == "l3":
                topology_empty_message = (
                    "No interfaces with IP addresses matched this diagram."
                )
            elif instance.mode == "site":
                topology_empty_message = (
                    "No inter-site cabled interfaces matched this diagram."
                )
            else:
                topology_empty_message = "No topology data matched this diagram."

        return {
            "topology_data": topology_data,
            "topology_details": instance.details,
            "topology_empty_message": topology_empty_message,
        }


class DiagramEditView(generic.ObjectEditView):
    """Edit Diagram view."""

    queryset = models.Diagram.objects.all()
    form = forms.DiagramForm


class DiagramDeleteView(generic.ObjectDeleteView):
    """Delete Diagram view."""

    queryset = models.Diagram.objects.all()
    default_return_url = "plugins:netmapper:diagram_list"


class DiagramExportView(generic.ObjectDeleteView):
    """
    Export a single object.

    Called from:
    * DiagramView clicking on the Export button on a specific Diagram.
    """

    queryset = models.Diagram.objects.all()

    def get(self, request, *args, **kwargs):
        """Download the log."""
        instance = self.get_object(**kwargs)
        sites = list(instance.sites.all().values_list("id", flat=True))
        roles = list(instance.device_roles.all().values_list("id", flat=True))
        vrfs = list(instance.vrfs.all().values_list("id", flat=True))

        interface_qs = utils.get_diagram_interfaces(
            instance.mode,
            sites=sites,
            roles=roles,
            vrfs=vrfs,
            include_global_vrf=instance.include_global_vrf,
        )

        # Build and return the topology
        try:
            module = getattr(topologies, f"get_{instance.mode}_drawio_topology")
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                f"Get DrawIO topology function not found for {instance.mode}"
            ) from exc
        drawio_xml = module(interface_qs, instance)

        response = HttpResponse(drawio_xml, content_type="application/xml")
        response["Content-Disposition"] = f"attachment; filename={instance.name}.drawio"
        return response


#
# Discoverable views
#


class DiscoverableListView(generic.ObjectListView):
    """Summary view listing all Discoverable objects."""

    queryset = models.Discoverable.objects.annotate(
        discoverylogs_count=Count("discoverylogs")
    ).order_by("device__name", "address")
    table = tables.DiscoverableTable
    actions = (
        AddObject,
        BulkImport,
        BulkExport,
        BulkEdit,
        BulkDelete,
        BulkDiscoverAction,
        BulkIngestAction,
    )
    template_name = "netmapper/discoverable_list.html"
    filterset = filtersets.DiscoverableFilterSet
    filterset_form = forms.DiscoverableListFilterForm

    def get_extra_context(self, request):
        """Expose action names for the custom bulk action template override."""
        return {
            "action_names": {action.name for action in self.get_permitted_actions(request.user)}
        }


class DiscoverableView(generic.ObjectView):
    """Detailed Discoverable view."""

    queryset = models.Discoverable.objects.annotate(
        discoverylogs_count=Count("discoverylogs")
    )

    def get_extra_context(self, request, instance):
        """Get associated DiscoveryLog obhects."""
        table = tables.DiscoveryLogTable(
            instance.discoverylogs.all().order_by("-created")
        )
        table.configure(request)

        return {
            "discoverylogs_table": table,
        }


class DiscoverableEditView(generic.ObjectEditView):
    """Edit Discoverable view."""

    queryset = models.Discoverable.objects.all()
    form = forms.DiscoverableForm


class DiscoverableDeleteView(generic.ObjectDeleteView):
    """Delete Discoverable view."""

    queryset = models.Discoverable.objects.all()
    default_return_url = "plugins:netmapper:discoverable_list"


class DiscoverableBulkImportView(generic.BulkImportView):
    """Bulk import Discoverable view."""

    queryset = models.Discoverable.objects.all()
    model_form = forms.DiscoverableCSVForm
    table = tables.DiscoverableTable


class DiscoverableBulkEditView(generic.BulkEditView):
    """Bulk edit Discoverable view."""

    queryset = models.Discoverable.objects.all()
    table = tables.DiscoverableTable
    form = forms.DiscoverableBulkEditForm


class DiscoverableBulkDeleteView(generic.BulkDeleteView):
    """Bulk delete Discoverable view."""

    queryset = models.Discoverable.objects.all()
    table = tables.DiscoverableTable
    default_return_url = "plugins:netmapper:discoverable_list"


class DiscoverableDiscoverView(generic.ObjectDeleteView):
    """
    Discover a single object.

    Called from:
    * DiscoverableListView clicking on the Discovery button on a specific Discoverable row.
    * DiscoverableView clicking on the Discovery button.
    """

    queryset = models.Discoverable.objects.all()
    template_name = "netmapper/discoverable_discover.html"

    def get_required_permission(self):
        """Check permissions."""
        return get_permission_for_model(self.queryset.model, "change")

    #
    # Request handlers
    #

    def get(self, request, *args, **kwargs):
        """Return the confirmation page."""
        obj = self.get_object(**kwargs)
        form = ConfirmationForm(initial=request.GET)

        # If this is an HTMX request, return only the rendered deletion form as modal content
        if htmx_partial(request):
            # Called from DiscoverableView
            viewname = get_viewname(self.queryset.model, action="discover")
            form_url = reverse(viewname, kwargs={"pk": obj.pk})
            return render(
                request,
                "netmapper/htmx/discover_form.html",
                {
                    "object": obj,
                    "object_type": self.queryset.model._meta.verbose_name,  # pylint: disable=protected-access
                    "form": form,
                    "form_url": form_url,
                    **self.get_extra_context(request, obj),
                },
            )

        # Called from DiscoverableViewList
        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        """Start the discovery on a single Discoverable."""
        logger = logging.getLogger("netbox.plugins.netmapper")
        obj = self.get_object(**kwargs)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            logger.debug("Form validation was successful")
            discoverables = [obj]

            # Starting discovery job on default queue (single Discoverable)
            msg = f"Starting discovery on {obj}"
            logger.info(msg)
            messages.success(request, msg)
            data = {
                "discoverables": discoverables,
            }
            utils.spawn_script("Discover", user=request.user, post_data=data)

            # return_url = form.cleaned_data.get("return_url")
            # if return_url and return_url.startswith("/"):
            #     return redirect(return_url)
            return redirect(self.get_return_url(request, obj))

        logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )


class DiscoverableIngestView(generic.ObjectDeleteView):
    """
    Ingest logs for a single discoverable.

    Called from:
    * DiscoverableListView clicking on the Ingest button on a specific Discoverable row.
    * DiscoverableView clicking on the Ingest button.
    """

    queryset = models.Discoverable.objects.all()
    template_name = "netmapper/discoverable_ingest.html"

    def get_required_permission(self):
        """Check permissions."""
        return get_permission_for_model(self.queryset.model, "change")

    def _get_ingestable_logs(self, queryset):
        """Return logs eligible for ingestion for the given discoverables."""
        return models.DiscoveryLog.objects.filter(
            discoverable__in=queryset,
            supported=True,
            parsed=True,
            ingested=False,
        )

    def _spawn_follow_up_job(self, request, queryset, ingestable_logs_count):
        """Start ingest now or discovery first when logs do not exist yet."""
        discoverables = list(queryset)
        if ingestable_logs_count:
            msg = (
                f"Starting ingest on {discoverables[0]} "
                f"({ingestable_logs_count} logs queued)"
            )
            messages.success(request, msg)
            utils.spawn_script(
                "Ingest",
                user=request.user,
                post_data={"discoverables": discoverables},
            )
            return

        msg = (
            f"No pending ingest logs exist for {discoverables[0]}. "
            "Starting discovery instead; ingestion will follow automatically "
            "when parsed logs are produced."
        )
        messages.info(request, msg)
        utils.spawn_script(
            "Discover",
            user=request.user,
            post_data={
                "discoverables": discoverables,
                "undiscovered_only": False,
            },
        )

    def get_extra_context(self, request, obj):
        """Expose ingestable log count to the templates."""
        ingestable_logs_count = self._get_ingestable_logs(
            self.queryset.filter(pk=obj.pk)
        ).count()
        return {"ingestable_logs_count": ingestable_logs_count}

    def get(self, request, *args, **kwargs):
        """Return the confirmation page."""
        obj = self.get_object(**kwargs)
        form = ConfirmationForm(initial=request.GET)

        if htmx_partial(request):
            viewname = get_viewname(self.queryset.model, action="ingest")
            form_url = reverse(viewname, kwargs={"pk": obj.pk})
            return render(
                request,
                "netmapper/htmx/ingest_form.html",
                {
                    "object": obj,
                    "object_type": self.queryset.model._meta.verbose_name,  # pylint: disable=protected-access
                    "form": form,
                    "form_url": form_url,
                    **self.get_extra_context(request, obj),
                },
            )

        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )

    def post(self, request, *args, **kwargs):
        """Start ingestion for a single discoverable."""
        logger = logging.getLogger("netbox.plugins.netmapper")
        obj = self.get_object(**kwargs)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            logger.debug("Form validation was successful")
            queryset = self.queryset.filter(pk=obj.pk)
            ingestable_logs_count = self._get_ingestable_logs(queryset).count()
            logger.info("Starting selected device processing on %s", obj)
            self._spawn_follow_up_job(request, queryset, ingestable_logs_count)
            return redirect(self.get_return_url(request, obj))

        logger.debug("Form validation failed")
        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                **self.get_extra_context(request, obj),
            },
        )


class DiscoverableBulkDiscoverView(generic.BulkDeleteView):
    """
    Disocver devices in bulk.

    Called from:
    * DiscoverableListView selecting Discoverable(s) and clicking on Disocver Selected button.
    """

    template_name = "netmapper/discoverable_bulk_discover.html"
    queryset = models.Discoverable.objects.prefetch_related("credential")
    filterset = None
    table = tables.DiscoverableTable
    default_return_url = "plugins:netmapper:discoverable_list"

    def get_required_permission(self):
        """Check permissions."""
        return get_permission_for_model(self.queryset.model, "change")

    def post(self, request, **kwargs):
        """Start the discovery."""
        logger = logging.getLogger("netbox.plugins.netmapper")
        model = self.queryset.model

        # Are we discovering *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            queryset = model.objects.all()
            pk_list = queryset.only("pk").values_list("pk", flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        if "_confirm" in request.POST:
            form = BulkDeleteForm(model, request.POST)
            if form.is_valid():
                logger.debug("Form validation was successful")
                queryset = self.queryset.filter(pk__in=pk_list)
                discovery_count = queryset.count()

                # Starting discovery job on default queue (list of Discoverable)
                msg = f"Starting discovery on {discovery_count} {model._meta.verbose_name_plural}"  # pylint: disable=protected-access
                logger.info(msg)
                messages.success(request, msg)
                data = {
                    "discoverables": list(queryset),
                }
                utils.spawn_script("Discover", user=request.user, post_data=data)

                return redirect(self.get_return_url(request))

            logger.debug("Form validation failed")

        else:
            form = BulkDeleteForm(
                model,
                initial={
                    "pk": pk_list,
                    "return_url": self.get_return_url(request),
                },
            )

        # Retrieve objects being deleted
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {model._meta.verbose_name_plural} were selected for discovery.",  # pylint: disable=protected-access
            )
            return redirect(self.get_return_url(request))

        return render(
            request,
            self.template_name,
            {
                "model": model,
                "form": form,
                "table": table,
                "return_url": self.get_return_url(request),
                **self.get_extra_context(request),
            },
        )


class DiscoverableBulkIngestView(generic.BulkDeleteView):
    """
    Ingest devices in bulk.

    Called from:
    * DiscoverableListView selecting Discoverable(s) and clicking on Ingest Selected button.
    """

    template_name = "netmapper/discoverable_bulk_ingest.html"
    queryset = models.Discoverable.objects.prefetch_related("credential")
    filterset = None
    table = tables.DiscoverableTable
    default_return_url = "plugins:netmapper:discoverable_list"

    def get_required_permission(self):
        """Check permissions."""
        return get_permission_for_model(self.queryset.model, "change")

    def _get_ingestable_logs(self, queryset):
        """Return logs eligible for ingestion for the given discoverables."""
        return models.DiscoveryLog.objects.filter(
            discoverable__in=queryset,
            supported=True,
            parsed=True,
            ingested=False,
        )

    def _spawn_follow_up_job(self, request, queryset, ingestable_logs_count):
        """Start ingest now or discovery first when no ingestable logs exist."""
        discoverables = list(queryset)
        device_count = len(discoverables)
        if ingestable_logs_count:
            msg = (
                f"Starting ingest on {device_count} devices "
                f"({ingestable_logs_count} logs queued)"
            )
            messages.success(request, msg)
            utils.spawn_script(
                "Ingest",
                user=request.user,
                post_data={"discoverables": discoverables},
            )
            return

        msg = (
            f"No pending ingest logs exist for the selected {device_count} devices. "
            "Starting discovery instead; ingestion will follow automatically "
            "when parsed logs are produced."
        )
        messages.info(request, msg)
        utils.spawn_script(
            "Discover",
            user=request.user,
            post_data={
                "discoverables": discoverables,
                "undiscovered_only": False,
            },
        )

    def post(self, request, **kwargs):
        """Start the ingestion."""
        logger = logging.getLogger("netbox.plugins.netmapper")
        model = self.queryset.model

        if request.POST.get("_all"):
            queryset = model.objects.all()
            pk_list = queryset.only("pk").values_list("pk", flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        if "_confirm" in request.POST:
            form = BulkDeleteForm(model, request.POST)
            if form.is_valid():
                logger.debug("Form validation was successful")
                queryset = self.queryset.filter(pk__in=pk_list)
                ingestable_logs_count = self._get_ingestable_logs(queryset).count()
                discovery_count = queryset.count()
                logger.info(
                    "Starting selected device processing on %s %s",
                    discovery_count,
                    model._meta.verbose_name_plural,  # pylint: disable=protected-access
                )
                self._spawn_follow_up_job(request, queryset, ingestable_logs_count)
                return redirect(self.get_return_url(request))

            logger.debug("Form validation failed")
        else:
            form = BulkDeleteForm(
                model,
                initial={
                    "pk": pk_list,
                    "return_url": self.get_return_url(request),
                },
            )

        queryset = self.queryset.filter(pk__in=pk_list)
        table = self.table(queryset, orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {model._meta.verbose_name_plural} were selected for ingest.",  # pylint: disable=protected-access
            )
            return redirect(self.get_return_url(request))

        return render(
            request,
            self.template_name,
            {
                "model": model,
                "form": form,
                "table": table,
                "return_url": self.get_return_url(request),
                "ingestable_logs_count": self._get_ingestable_logs(queryset).count(),
                **self.get_extra_context(request),
            },
        )


#
# DiscoveryLog views
#


class DiscoveryLogListView(generic.ObjectListView):
    """Summary view listing all DiscoveryLog objects."""

    queryset = models.DiscoveryLog.objects.all().order_by("-created")
    table = tables.DiscoveryLogTable
    filterset = filtersets.DiscoveryLogFilterSet
    filterset_form = forms.DiscoveryLogListFilterForm
    actions = (BulkDelete,)


class DiscoveryLogView(generic.ObjectView):
    """Detailed DiscoveryLog view."""

    queryset = models.DiscoveryLog.objects.all()


class DiscoveryLogDeleteView(generic.ObjectDeleteView):
    """Delete DiscoveryLog view."""

    queryset = models.DiscoveryLog.objects.all()
    default_return_url = "plugins:netmapper:discoverylog_list"


class DiscoveryLogExportView(generic.ObjectView):
    """
    Export a single object.

    Called from:
    * DiscoveryLogView clicking on the Discovery button on a specific Discoverable.
    """

    queryset = models.DiscoveryLog.objects.all()

    def get(self, request, **kwargs):
        """Download the log."""
        instance = self.get_object(**kwargs)
        data = utils.export_log(instance)
        response = HttpResponse(json.dumps(data), content_type="application/json")
        response["Content-Disposition"] = f"attachment; filename={instance.id}.json"
        return response


class DiscoveryLogBulkDeleteView(generic.BulkDeleteView):
    """Bulk delete DiscoveryLog view."""

    queryset = models.DiscoveryLog.objects.all()
    table = tables.DiscoveryLogTable
    default_return_url = "plugins:netmapper:discoverylog_list"


#
# MacAddressTableEntry views
#


class MacAddressTableListView(generic.ObjectListView):
    """Summary view listing all MAC address."""

    queryset = models.MacAddressTableEntry.objects.all().order_by(
        "interface__device__name", "interface__name", "mac_address"
    )
    table = tables.MacAddressTableEntryTable
    filterset = filtersets.MacAddressTableEntryFilterSet
    actions = (BulkExport,)


class MacAddressTableView(generic.ObjectView):
    """Detailed MAC address entry view."""

    queryset = models.MacAddressTableEntry.objects.all()
    actions = []  # Read only table

    def get_extra_context(self, request, instance):
        """Get associated MAC Address tables."""
        arp_table_qs = models.ArpTableEntry.objects.filter(
            mac_address=str(instance.mac_address)
        )
        arp_table = tables.ArpTableEntryTable(arp_table_qs)
        arp_table.configure(request)

        macaddress_table_qs = models.MacAddressTableEntry.objects.filter(
            mac_address=instance.mac_address
        )
        macaddress_table = tables.MacAddressTableEntryTable(macaddress_table_qs)
        macaddress_table.configure(request)

        return {
            "arp_table": arp_table,
            "macaddress_table": macaddress_table,
        }


#
# RouteTableEntry view
#


class RouteTableEntryListView(generic.ObjectListView):
    """Summary view listing all routes."""

    queryset = models.RouteTableEntry.objects.all().order_by(
        "device__name", "destination", "protocol", "nexthop_if__name"
    )
    table = tables.RouteTableEntryTable
    filterset = filtersets.RouteTableEntryFilterSet
    actions = (BulkExport,)


class RouteTableEntryView(generic.ObjectView):
    """Detailed route table entry view."""

    queryset = models.RouteTableEntry.objects.all()
    actions = []  # Read only table
