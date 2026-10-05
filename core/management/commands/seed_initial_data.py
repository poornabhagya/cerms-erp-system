"""
CERMS - Initial Database Seeding Command (Core Wrapper)
Reference: docs/15_DATA_SEEDING_AND_FIXTURES.md
"""

from fleet.management.commands.seed_initial_data import Command as FleetSeedCommand


class Command(FleetSeedCommand):
    """Core wrapper for the comprehensive idempotent database seeding routine."""
    help = "Populates the database with core RBAC groups, default users, fleet categories, equipment master assets, and rental rates."
