"""No account/API credentials required for local deterministic tools."""
from typing import Any
from dify_plugin import ToolProvider


class AgentSafetyToolkitProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # Both tools run locally inside the Dify plugin runtime.
        return None
