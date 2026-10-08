"""Registre central d'outils (Plugin Registry) pour l'agent Ekko.

Gère l'enregistrement, l'indexation et la fourniture des outils
au routeur et au moteur de raisonnement d'Ekko avec support d'alias.
"""

import json
from typing import Any
from .base import BaseTool

TOOL_ALIASES: dict[str, str] = {
    "web_search": "search",
    "fetch_page": "reader",
}


class ToolRegistry:
    """Gestionnaire central de découverte et d'accès aux outils."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Enregistre une nouvelle instance d'outil dans le catalogue."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        """Récupère un outil par son nom identifiant ou via ses alias."""
        clean_name = name.strip() if name else ""
        if clean_name in self._tools:
            return self._tools[clean_name]
        alias_target = TOOL_ALIASES.get(clean_name)
        if alias_target and alias_target in self._tools:
            return self._tools[alias_target]
        return None

    def list_tools(self) -> list[BaseTool]:
        """Retourne la liste de tous les outils canoniques actuellement chargés."""
        return list(self._tools.values())

    def get_prompt_catalog(self) -> str:
        """Construit la documentation des outils disponibles pour le prompt système."""
        if not self._tools:
            return "Aucun outil disponible pour le moment."

        catalog_entries: list[str] = []
        for tool in self._tools.values():
            schema_str = json.dumps(
                tool.parameters_schema.model_json_schema().get("properties", {}),
                ensure_ascii=False,
            )
            catalog_entries.append(
                f"- Nom : `{tool.name}`\n"
                f"  Description : {tool.description}\n"
                f"  Arguments acceptés : {schema_str}"
            )
        return "\n\n".join(catalog_entries)

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Valide et normalise les arguments via le schéma Pydantic de l'outil."""
        tool = self.get_tool(name)
        if not tool:
            return arguments
        try:
            return tool.parameters_schema.model_validate(arguments).model_dump()
        except Exception:
            return arguments

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Valide et exécute un outil par son nom avec les arguments fournis."""
        tool = self.get_tool(name)
        if not tool:
            return f"Erreur : L'outil '{name}' n'existe pas dans le registre."

        try:
            validated_args = tool.parameters_schema.model_validate(arguments)
            return await tool.execute(**validated_args.model_dump())
        except Exception as exc:
            return f"Erreur durant l'exécution de '{name}' : {exc}"


# Instance globale partagée du registre
default_registry = ToolRegistry()
