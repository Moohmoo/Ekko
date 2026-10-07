"""Modèles de données Pydantic pour le système de veille Ekko.

Définit les schémas canoniques utilisés par les collecteurs,
le trieur et le rédacteur pour garantir la cohérence des flux.
"""

from typing import Literal
from pydantic import BaseModel, Field

# Catégories canoniques cibles pour l'Agent 1 (Le Trieur)
ArticleCategory = Literal["Tech & IA", "Data & Backend", "Sciences & Bio"]


class Article(BaseModel):
    """Modèle standardisé d'un article brut extrait par un collecteur."""

    title: str = Field(description="Titre de l'article ou du papier de recherche")
    url: str = Field(description="URL source de l'article")
    summary: str = Field(default="", description="Résumé ou extrait textuel de l'article")
    source_name: str = Field(description="Nom de la source (ex: Hacker News, Hugging Face)")


class SelectedArticle(BaseModel):
    """Modèle d'un article filtré et catégorisé par l'Agent 1."""

    title: str = Field(description="Titre retenu pour l'article")
    url: str = Field(description="URL canonique de l'article")
    category: str = Field(
        description="Catégorie parmi : Tech & IA, Data & Backend, Sciences & Bio",
    )


class SelectionResult(BaseModel):
    """Structure de sortie forcée (Structured Output) générée par l'Agent 1."""

    articles: list[SelectedArticle] = Field(
        default_factory=list,
        description="Liste des articles majeurs retenus (3 à 5 maximum)",
    )
