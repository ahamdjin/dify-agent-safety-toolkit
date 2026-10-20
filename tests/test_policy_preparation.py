"""Concrete contract tests for policy-aware data minimization (fictional data)."""
import json
import unittest

from agent_safety import prepare_agent_json, redact_sensitive_text


def run(payload, **kwargs):
    return prepare_agent_json(json.dumps(payload), **kwargs)


class FieldProjectionTests(unittest.TestCase):
    def test_allowlist_removes_unnecessary_customer_fields_and_nested_array_data(self):
        source = {
            "lead": {
                "id": "lead-001",
                "company": "Example Roofing",
                "email": "client@example.com",
                "private_notes": "Internal-only negotiation",
                "apiKey": "not-for-an-agent",
            },
            "activities": [
                {"type": "call", "note": "Contact on Tuesday", "debug": "PRIVATE"},
                {"type": "email", "note": "Sent quote", "debug": "SECRET"},
            ],
            "metadata": {"raw_request": "unnecessary"},
        }
        result = run(
            source,
            allowed_paths="lead.id\nlead.company\nactivities[].type",
            required_paths="lead.id\nlead.company",
        )
        cleaned = json.loads(result["json_text"])
        self.assertEqual(cleaned, {
            "lead": {"id": "lead-001", "company": "Example Roofing"},
            "activities": [{"type": "call"}, {"type": "email"}],
        })
        self.assertEqual(result["policy_status"], "pass")
        self.assertTrue(result["may_auto_continue"])
        self.assertGreaterEqual(result["fields_excluded"], 6)
        self.assertNotIn("client@example.com", result["json_text"])
        self.assertNotIn("PRIVATE", result["json_text"])
        self.assertLess(result["output_characters"], result["input_characters"])

    def test_empty_nested_projection_blocks_instead_of_passing(self):
        result = run(
            {"lead": {"unapproved": "private"}},
            allowed_paths="lead.id",
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")
        self.assertIn("no_selected_fields", result["policy_reasons"])

    def test_required_string_truncation_blocks_even_if_relaxed(self):
        result = run(
            {"lead": {"id": "L" * 200}},
            allowed_paths="lead.id",
            required_paths="lead.id",
            max_string=100,
            block_on_truncation=False,
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")
        self.assertEqual(result["missing_required_paths"], ["lead.id"])

    def test_comma_separated_field_config_suits_single_line_dify_forms(self):
        result = run(
            {"lead": {"id": 12, "company": "Example", "internalCredential": "fake"}},
            allowed_paths="lead.id, lead.company, lead.internalCredential",
            required_paths="lead.id, lead.company",
            additional_secret_keys="internalCredential, privatePIN",
        )
        self.assertEqual(result["policy_status"], "review")
        self.assertEqual(json.loads(result["json_text"])["lead"]["internalCredential"], "[REDACTED]")

    def test_required_missing_blocks_with_empty_payload(self):
        result = run(
            {"lead": {"name": "Customer"}},
            allowed_paths="lead.name\nlead.id",
            required_paths="lead.id",
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")
        self.assertEqual(result["missing_required_paths"], ["lead.id"])
        self.assertFalse(result["may_auto_continue"])

    def test_required_field_masked_value_blocks(self):
        result = run(
            {"lead": {"id": "client-token"}},
            allowed_paths="lead.id",
            required_paths="lead.id",
            additional_secret_keys="id",
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["missing_required_paths"], ["lead.id"])

    def test_required_coverage_must_be_explicit(self):
        with self.assertRaisesRegex(ValueError, "required path"):
            run(
                {"lead": {"id": "123", "company": "Example"}},
                allowed_paths="lead.company",
                required_paths="lead.id",
            )

    def test_arrays_require_each_retained_record_to_have_mandatory_field(self):
        result = run(
            {"events": [{"type": "created"}, {"debug": "missing"}]},
            allowed_paths="events[].type",
            required_paths="events[].type",
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")

    def test_empty_or_mismatched_allowlist_does_not_silently_pass(self):
        for payload in ({"x": 1}, {"lead": "unexpected"}):
            with self.subTest(payload=payload):
                result = run(payload, allowed_paths="lead.id")
                self.assertEqual(result["policy_status"], "block")
                self.assertEqual(result["json_text"], "")
                self.assertIn("no_selected_fields", result["policy_reasons"])

    def test_no_allowlist_is_review_not_automatic_approval(self):
        result = run({"status": "new"})
        self.assertEqual(result["policy_status"], "review")
        self.assertFalse(result["may_auto_continue"])
        self.assertIn("no_allowlist_configured", result["policy_reasons"])

    def test_root_arrays_can_still_be_prepared_without_allowlist(self):
        result = run([{"status": "new"}])
        self.assertEqual(result["policy_status"], "review")
        self.assertEqual(json.loads(result["json_text"]), [{"status": "new"}])
        with self.assertRaisesRegex(ValueError, "JSON object"):
            run([{"status": "new"}], allowed_paths="status")


class PolicyTests(unittest.TestCase):
    def test_recognizable_sensitive_values_require_review(self):
        result = run(
            {"lead": {"name": "Alice", "email": "alice@example.com"}},
            allowed_paths="lead.name\nlead.email",
            required_paths="lead.name",
        )
        self.assertEqual(result["policy_status"], "review")
        self.assertEqual(json.loads(result["json_text"])["lead"]["email"], "[EMAIL_1]")
        self.assertIn("patterns_masked", result["policy_reasons"])

    def test_custom_field_name_can_mask_internal_credentials(self):
        result = run(
            {"id": 4, "internalCredential": "test-private-string"},
            allowed_paths="id\ninternalCredential",
            additional_secret_keys="internalCredential",
        )
        self.assertEqual(result["policy_status"], "review")
        self.assertEqual(
            json.loads(result["json_text"])["internalCredential"], "[REDACTED]"
        )
        self.assertEqual(result["redaction_counts"]["FIELDS"], 1)
        self.assertNotIn("test-private-string", json.dumps(result))

    def test_custom_literal_masking_matches_specific_business_identifiers(self):
        result = run(
            {"ticket": "Use ref CASE-SECRET-2026 for this issue"},
            allowed_paths="ticket",
            mask_literals="CASE-SECRET-2026",
        )
        self.assertEqual(result["policy_status"], "review")
        self.assertIn("[CUSTOM_MASK]", result["json_text"])
        self.assertNotIn("CASE-SECRET-2026", json.dumps(result))
        self.assertEqual(result["redaction_counts"]["CUSTOM"], 1)

    def test_redact_text_also_supports_custom_literal_masking(self):
        result = redact_sensitive_text("Ticket CASE-SECRET-2026", "CASE-SECRET-2026")
        self.assertEqual(result["text"], "Ticket [CUSTOM_MASK]")
        self.assertEqual(result["redaction_counts"]["CUSTOM"], 1)

    def test_configured_truncation_block_does_not_return_partial_data(self):
        result = run(
            {"lead": {"notes": "x" * 200}},
            allowed_paths="lead.notes",
            max_string=100,
            block_on_truncation=True,
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")
        self.assertIn("content_truncated", result["policy_reasons"])
        self.assertEqual(result["compaction"]["truncated_strings"], 1)

    def test_truncated_but_not_blocked_means_review(self):
        result = run(
            {"notes": "x" * 200},
            allowed_paths="notes",
            max_string=100,
            block_on_truncation=False,
        )
        self.assertEqual(result["policy_status"], "review")
        self.assertIn("[truncated ", result["json_text"])

    def test_required_path_lost_to_truncation_blocks_even_without_strict_mode(self):
        result = run(
            {"items": [{"id": str(i)} for i in range(10)]},
            allowed_paths="items[].id",
            required_paths="items[].id",
            max_items=2,
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")
        self.assertEqual(result["missing_required_paths"], ["items[].id"])

    def test_missing_required_path_when_stripped_by_null_removal_blocks(self):
        result = run(
            {"lead": {"id": None}},
            allowed_paths="lead.id",
            required_paths="lead.id",
        )
        self.assertEqual(result["policy_status"], "block")
        self.assertEqual(result["json_text"], "")

    def test_invalid_configurations_fail_before_work_and_do_not_echo_secrets(self):
        base = {"lead": {"id": "supersecret-demo"}}
        bad = [
            {"allowed_paths": "lead.$private"},
            {"allowed_paths": "lead.id\n" * 40},
            {"required_paths": "lead.bad[0]"},
            {"additional_secret_keys": "secret.field"},
            {"mask_literals": "abc"},
            {"mask_literals": "too-big-" + ("x" * 200)},
            {"block_on_truncation": "true"},
        ]
        for item in bad:
            with self.subTest(item=list(item)):
                with self.assertRaises(ValueError) as caught:
                    run(base, **item)
                self.assertNotIn("supersecret-demo", str(caught.exception))

    def test_upper_bound_on_custom_literals(self):
        with self.assertRaises(ValueError):
            run(
                {"key": "value"},
                mask_literals="\n".join(f"literal-{i:04d}" for i in range(22)),
            )


if __name__ == "__main__":
    unittest.main()
