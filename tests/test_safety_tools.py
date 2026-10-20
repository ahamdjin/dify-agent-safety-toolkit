"""Behavioral regression suite for real workflow inputs."""
import json
import unittest

from agent_safety import MAX_INPUT_CHARS, prepare_agent_json, redact_sensitive_text


class RedactionTests(unittest.TestCase):
    def test_email_and_api_token_are_not_echoed(self):
        token = "sk-" + "A" * 32
        source = f"Contact alice@example.com; token={token}"
        result = redact_sensitive_text(source)
        self.assertTrue(result["changed"])
        self.assertNotIn("alice@example.com", result["text"])
        self.assertNotIn(token, result["text"])
        self.assertGreaterEqual(result["redaction_counts"]["EMAIL"], 1)
        self.assertGreaterEqual(result["redaction_counts"]["SECRET"], 1)

    def test_no_match_is_explicitly_not_a_security_guarantee(self):
        result = redact_sensitive_text("Schedule a demo tomorrow.")
        self.assertEqual(result["text"], "Schedule a demo tomorrow.")
        self.assertFalse(result["changed"])
        self.assertEqual(result["redaction_counts"], {})

    def test_empty_and_oversized_inputs_fail_closed(self):
        for value in (None, "", "   ", 12, "a" * (MAX_INPUT_CHARS + 1)):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValueError):
                    redact_sensitive_text(value)


class ContextJsonTests(unittest.TestCase):
    def test_nested_secrets_and_personal_details(self):
        token = "ghp_" + "a" * 32
        source = json.dumps({
            "records": [
                {
                    "accessToken": token,
                    "client-secret": "very-secret-value",
                    "contact": "alice@example.com",
                    "meta": {"authorization": "Bearer " + "b" * 25},
                }
            ],
            "ordinary": {"status": "ok", "nullable": None},
        })
        result = prepare_agent_json(source)
        cleaned = json.loads(result["json_text"])
        row = cleaned["records"][0]
        self.assertEqual(row["accessToken"], "[REDACTED]")
        self.assertEqual(row["client-secret"], "[REDACTED]")
        self.assertEqual(row["meta"]["authorization"], "[REDACTED]")
        self.assertNotIn("alice@example.com", result["json_text"])
        self.assertNotIn(token, result["json_text"])
        self.assertNotIn("nullable", cleaned["ordinary"])
        self.assertGreaterEqual(result["redaction_counts"]["FIELDS"], 3)
        self.assertGreaterEqual(result["redaction_counts"]["EMAIL"], 1)

    def test_scrubs_values_before_truncating_them(self):
        token = "sk-" + "z" * 32
        source = json.dumps({"note": "prefix " + token + " " + ("q" * 250)})
        output = prepare_agent_json(source, max_string=100)
        self.assertNotIn(token, output["json_text"])
        self.assertIn("[SECRET_", output["json_text"])
        self.assertEqual(output["compaction"]["truncated_strings"], 1)

    def test_array_limits_and_depth_are_bounded(self):
        raw = json.dumps({"events": [{"id": x} for x in range(40)]})
        result = prepare_agent_json(raw, max_items=5)
        data = json.loads(result["json_text"])
        self.assertEqual(len(data["events"]), 6)
        self.assertEqual(data["events"][-1], {"_truncated_items": 35})
        self.assertEqual(result["compaction"]["truncated_lists"], 1)

        raw = json.dumps({"a": {"b": {"c": 1}}})
        result = prepare_agent_json(raw, max_depth=2)
        self.assertIn("[MAX_DEPTH_REACHED]", result["json_text"])

    def test_root_arrays_and_primitives_work(self):
        self.assertEqual(json.loads(prepare_agent_json("[1,2,3]")["json_text"]), [1, 2, 3])
        self.assertEqual(json.loads(prepare_agent_json('"hello"')["json_text"]), "hello")
        self.assertIsNone(json.loads(prepare_agent_json("null")["json_text"]))

    def test_rejects_duplicate_keys_and_nonstandard_numbers(self):
        for sample in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', "{not-json}"):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    prepare_agent_json(sample)

    def test_rejects_oversized_or_unbounded_inputs(self):
        with self.assertRaises(ValueError):
            prepare_agent_json("[" + (" " * MAX_INPUT_CHARS) + "]")
        for kwargs in (
            {"max_items": 0},
            {"max_string": 99},
            {"max_depth": 99},
            {"max_items": 2.5},
            {"max_depth": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    prepare_agent_json('{"ok":true}', **kwargs)

    def test_deeply_nested_input_fails_cleanly(self):
        deep = "[" * 40 + "null" + "]" * 40
        with self.assertRaisesRegex(ValueError, "nested too deeply"):
            prepare_agent_json(deep)

    def test_reports_stats_without_input_values(self):
        result = prepare_agent_json('{"apiKey":"somethingsecret","note":"hi","null_field":null}')
        self.assertIn("compaction", result)
        self.assertIn("output_characters", result)
        self.assertEqual(result["redaction_counts"]["FIELDS"], 1)
        self.assertNotIn("somethingsecret", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
