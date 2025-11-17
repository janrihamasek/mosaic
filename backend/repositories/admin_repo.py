"""Repository for administrative database operations.

Admin operations primarily reuse users_repo; admin-specific queries can be added here.
"""

from typing import Any, Dict, List, Optional

from db_utils import connection as sa_connection
from db_utils import transactional_connection
