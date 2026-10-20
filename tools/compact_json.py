"""Dify adapter for bounded agent JSON preparation."""
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from agent_safety import prepare_agent_json


class CompactJsonTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield self.create_json_message(
            prepare_agent_json(
                tool_parameters.get("json_text"),
                max_string=tool_parameters.get("max_string", 1000),
                max_items=tool_parameters.get("max_items", 25),
                max_depth=tool_parameters.get("max_depth", 8),
                allowed_paths=tool_parameters.get("allowed_paths"),
                required_paths=tool_parameters.get("required_paths"),
                additional_secret_keys=tool_parameters.get("additional_secret_keys"),
                mask_literals=tool_parameters.get("mask_literals"),
                block_on_truncation=tool_parameters.get("block_on_truncation", False),
            )
        )
