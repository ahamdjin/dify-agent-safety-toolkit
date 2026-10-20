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
