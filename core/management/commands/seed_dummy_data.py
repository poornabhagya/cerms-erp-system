"""
CERMS - Realistic Dummy Data Seeding Command (Core Wrapper)
Reference: docs/15_DATA_SEEDING_AND_FIXTURES.md
"""

from rentals.management.commands.seed_dummy_data import Command as RentalsDummySeedCommand


class Command(RentalsDummySeedCommand):
    """Core wrapper for the realistic test data generation routine."""
    help = "Generates realistic mock data (10 customers, 50 equipment assets, 20 rental contracts) for Phase 1 testing."
