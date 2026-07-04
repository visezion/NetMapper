"""Run discovery via NetBox's current script job API.

Usage:
/opt/netbox/venv/bin/python3 /opt/netbox/netbox/manage.py shell < discovery.py
"""
from users.models import User

from netmapper.models import Discoverable
from netmapper.utils import spawn_script

FILTERS = ["172.25.82.45"]  # List of discoverable IP addresses
FILTERS = []

# Don't edit below this line


def main():
    """Main function."""
    data = {
        "discoverables": Discoverable.objects.filter(address__in=FILTERS)
        if FILTERS
        else [],
    }
    user = User.objects.filter(is_superuser=True).order_by("pk")[0]
    spawn_script("Discover", post_data=data, user=user)


if __name__ == "django.core.management.commands.shell":
    main()
