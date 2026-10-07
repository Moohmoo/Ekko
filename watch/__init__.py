"""Package du domaine métier Veille automatisée pour Ekko."""

from .models import Article, SelectedArticle, SelectionResult
from .pipeline import execute_daily_watch

__all__ = [
    "Article",
    "SelectedArticle",
    "SelectionResult",
    "execute_daily_watch",
]
