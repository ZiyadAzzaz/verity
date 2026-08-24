"""The four bounded agents that make up the Verity pipeline.

Imports are lazy so the minimal Cloud Run sandbox image can import the Environment Agent
without also installing the Parser Agent's HTTP and ADK dependency tree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from verity.agents.debug import DebugAgent
    from verity.agents.environment import EnvironmentAgent
    from verity.agents.parser import ParserAgent
    from verity.agents.reporter import ReporterAgent

__all__ = ["DebugAgent", "EnvironmentAgent", "ParserAgent", "ReporterAgent"]


def __getattr__(name: str) -> Any:
    if name == "DebugAgent":
        from verity.agents.debug import DebugAgent

        return DebugAgent
    if name == "EnvironmentAgent":
        from verity.agents.environment import EnvironmentAgent

        return EnvironmentAgent
    if name == "ParserAgent":
        from verity.agents.parser import ParserAgent

        return ParserAgent
    if name == "ReporterAgent":
        from verity.agents.reporter import ReporterAgent

        return ReporterAgent
    raise AttributeError(name)
