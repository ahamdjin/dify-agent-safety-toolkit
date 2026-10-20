"""Dify adapter for conservative text redaction."""
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from agent_safety import redact_sensitive_text


class RedactTextTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        result = redact_sensitive_text(
            tool_parameters.get("text"),
            mask_literals=tool_parameters.get("mask_literals"),
        )
        yield self.create_json_message(result)
        for name, value in result.items():
            yield self.create_variable_message(name, value)
