# src/scraper/handlers/__init__.py
"""Special functionality handlers"""

from .cookie_handler import CookieHandler
from .load_more_handler import LoadMoreHandler
from .pagination_handler import PaginationHandler

__all__ = [
    "CookieHandler",
    "LoadMoreHandler",
    "PaginationHandler",
]