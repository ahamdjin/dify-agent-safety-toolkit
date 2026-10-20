"""Check that each advertised Dify tool has a real Python implementation."""
import importlib.util
import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


class PluginContractTests(unittest.TestCase):
    def test_manifest_metadata_and_permissions(self):
        manifest = read_yaml("manifest.yaml")
        self.assertEqual(manifest["type"], "plugin")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["author"], "ahamdjin")
        self.assertEqual(manifest["name"], "agent_safety_toolkit")
        self.assertEqual(manifest["privacy"], "PRIVACY.md")
        self.assertEqual(manifest["resource"]["permission"], {})
        self.assertEqual(
            manifest["plugins"]["tools"], ["provider/agent_safety_toolkit.yaml"]
        )
        self.assertTrue((ROOT / "PRIVACY.md").is_file())
        self.assertTrue((ROOT / "_assets" / manifest["icon"]).is_file())
        self.assertEqual(manifest["meta"]["runner"]["language"], "python")

    def test_tools_are_real_and_have_explicit_outputs(self):
        provider = read_yaml("provider/agent_safety_toolkit.yaml")
        self.assertEqual(provider["credentials_for_provider"], {})
        self.assertTrue((ROOT / provider["extra"]["python"]["source"]).is_file())
        self.assertEqual(
            provider["tools"], ["tools/redact_text.yaml", "tools/compact_json.yaml"]
        )
        for path in provider["tools"]:
            with self.subTest(tool=path):
                cfg = read_yaml(path)
                self.assertTrue((ROOT / cfg["extra"]["python"]["source"]).is_file())
                self.assertEqual(cfg["identity"]["author"], "ahamdjin")
                self.assertTrue(cfg["description"]["human"]["en_US"])
                self.assertTrue(cfg["description"]["llm"])
                self.assertEqual(cfg["output_schema"]["type"], "object")
                self.assertTrue(cfg["output_schema"]["properties"])
                self.assertTrue(all(p["form"] in {"form", "llm"} for p in cfg["parameters"]))

    def test_dify_sdk_provider_schema_loads(self):
        from dify_plugin.entities.tool import ToolProviderConfiguration

        provider = ToolProviderConfiguration.model_validate(
            read_yaml("provider/agent_safety_toolkit.yaml")
        )
        self.assertEqual(len(provider.tools), 2)
        prepare = read_yaml("tools/compact_json.yaml")
        parameters = {p["name"] for p in prepare["parameters"]}
        self.assertTrue({
            "allowed_paths", "required_paths", "additional_secret_keys",
            "mask_literals", "block_on_truncation"
        }.issubset(parameters))
        self.assertTrue({
            "policy_status", "policy_reasons", "may_auto_continue",
            "fields_excluded", "missing_required_paths"
        }.issubset(prepare["output_schema"]["properties"]))
        self.assertEqual(
            [tool.identity.name for tool in provider.tools],
            ["redact_text", "compact_json"],
        )

    def test_real_sdk_messages_do_not_echo_redacted_values(self):
        from tools.redact_text import RedactTextTool
        from tools.compact_json import CompactJsonTool
        from dify_plugin.entities.tool import ToolInvokeMessage

        raw = "Contact alice@example.com about the case"
        text_tool = RedactTextTool.__new__(RedactTextTool)
        text_tool.response_type = ToolInvokeMessage  # normally injected by Dify
        text_messages = list(text_tool._invoke({"text": raw}))
        self.assertGreater(len(text_messages), 1)
        text_vars = {
            m.message.variable_name: m.message.variable_value
            for m in text_messages if m.type.value == "variable"
        }
        self.assertEqual(text_vars["text"], "Contact [EMAIL_1] about the case")
        self.assertTrue(text_vars["changed"])
        self.assertNotIn("alice@example.com", text_messages[0].model_dump_json())
        self.assertIn("[EMAIL_1]", text_messages[0].model_dump_json())

        json_tool = CompactJsonTool.__new__(CompactJsonTool)
        json_tool.response_type = ToolInvokeMessage  # normally injected by Dify
        json_messages = list(json_tool._invoke({
            "json_text": '{"apiKey":"private-value","email":"alice@example.com"}',
        }))
        self.assertGreater(len(json_messages), 1)
        variables = {
            m.message.variable_name: m.message.variable_value
            for m in json_messages if m.type.value == "variable"
        }
        self.assertEqual(variables["policy_status"], "review")
        self.assertFalse(variables["may_auto_continue"])
        self.assertIn("[REDACTED]", variables["json_text"])
        self.assertTrue(all(key in variables for key in (
            "json_text", "policy_reasons", "fields_excluded", "redaction_counts",
        )))
        self.assertNotIn("private-value", json_messages[0].model_dump_json())
        self.assertNotIn("alice@example.com", json_messages[0].model_dump_json())

    def test_blocked_dify_tool_returns_no_context_variable(self):
        from tools.compact_json import CompactJsonTool
        from dify_plugin.entities.tool import ToolInvokeMessage

        tool = CompactJsonTool.__new__(CompactJsonTool)
        tool.response_type = ToolInvokeMessage
        messages = list(tool._invoke({
            "json_text": '{"lead":{"company":"Example Services"}}',
            "allowed_paths": "lead.id",
            "required_paths": "lead.id",
        }))
        variables = {
            m.message.variable_name: m.message.variable_value
            for m in messages if m.type.value == "variable"
        }
        self.assertEqual(variables["policy_status"], "block")
        self.assertFalse(variables["may_auto_continue"])
        self.assertEqual(variables["json_text"], "")
        self.assertEqual(variables["missing_required_paths"], ["lead.id"])
        self.assertTrue(all("Example Services" not in m.model_dump_json() for m in messages))

    def test_sdk_adapter_modules_import(self):
        for module in ("main", "provider.agent_safety_toolkit", "tools.redact_text", "tools.compact_json"):
            with self.subTest(module=module):
                # The Dify SDK is installed by the CI workflow and must resolve.
                self.assertIsNotNone(importlib.util.find_spec(module))
        from provider.agent_safety_toolkit import AgentSafetyToolkitProvider
        from tools.redact_text import RedactTextTool
        from tools.compact_json import CompactJsonTool
        self.assertTrue(all(obj is not None for obj in [
            AgentSafetyToolkitProvider, RedactTextTool, CompactJsonTool
        ]))


if __name__ == "__main__":
    unittest.main()
