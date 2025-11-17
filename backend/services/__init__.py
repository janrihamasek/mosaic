"""
Service layer package.

Each module encapsulates domain logic independent of Flask or HTTP concerns.
"""

# Export convenience imports for service modules
__all__ = [
    "activities_service",
    "entries_service",
    "stats_service",
    "backup_service",
    "nightmotion_service",
    "wearable_service",
    "admin_service",
    "auth_service",
    "common",
    "idempotency",
]
