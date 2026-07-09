"""API URLs, called by Views, used for add/edit actions."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from netbox.api.routers import NetBoxRouter
from netmapper.api import views


app_name = "netmapper-api"  # pylint: disable=invalid-name

router = NetBoxRouter()
router.register("arptableentry", views.ArpTableEntryViewSet)
router.register("credential", views.CredentialViewSet)
router.register("snmpcredential", views.SnmpCredentialViewSet)
router.register("diagram", views.DiagramViewSet)
router.register("discoverylog", views.DiscoveryLogViewSet)
router.register("discoverable", views.DiscoverableViewSet)
router.register("macaddresstableentry", views.MacAddressTableEntryViewSet)
router.register("routetableentry", views.RouteTableEntryViewSet)

urlpatterns = router.urls
