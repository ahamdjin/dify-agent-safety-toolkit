"""Reproducible offline characterization on fictional CRM/support/webhook payloads.

Compares against unfiltered JSON, NOT against Dify's programmable Code node,
and does not claim model token/cost savings or a security benchmark.
"""
from __future__ import annotations

import json

from agent_safety import prepare_agent_json


def serialize(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


SCENARIOS = {
    "crm_lead_routing": {
        "payload": {
            "leads": [
                {
                    "id": f"lead-{i:03d}",
                    "company": f"Example Contractors {i}",
                    "priority": i % 3,
                    "source": "website",
                    "email": f"fictional{i}@example.com",
                    "debug_trace": "irrelevant-field-" * 24,
                    "internal_auth": {"apiKey": "sample-only-token"},
                }
                for i in range(40)
            ],
            "audit": {"raw_payload": "unused-debug-payload-" * 100},
        },
        "allowed_paths": "leads[].id\nleads[].company\nleads[].priority",
        "required_paths": "leads[].id\nleads[].company",
    },
    "support_triage": {
        "payload": {
            "tickets": [
                {
                    "id": f"T-{i:03d}",
                    "category": "onboarding",
                    "summary": f"Customer requested an update for case {i}.",
                    "support_notes": "contact customer@example.com if needed",
                    "private_comment": "Never forward this internal note. " * 12,
                }
                for i in range(25)
            ],
            "metadata": {"session_token": "another-fake-token"},
        },
        "allowed_paths": "tickets[].id\ntickets[].category\ntickets[].summary",
        "required_paths": "tickets[].id\ntickets[].category",
    },
    "webhook_normalization": {
        "payload": {
            "events": [
                {
                    "eventId": f"evt-{i:04d}",
                    "eventType": "lead.created",
                    "createdAt": "2026-10-20T00:00:00Z",
                    "headers": {"authorization": "sample-value"},
                    "verbose": "repeated transport detail " * 32,
                }
                for i in range(50)
            ],
            "debug": {"trace": "raw-webhook-data-" * 75},
        },
        "allowed_paths": "events[].eventId\nevents[].eventType\nevents[].createdAt",
        "required_paths": "events[].eventId\nevents[].eventType",
    },
}


def evaluate():
    rows = []
    for name, scenario in SCENARIOS.items():
        raw = serialize(scenario["payload"])
        prepared = prepare_agent_json(
            raw,
            allowed_paths=scenario["allowed_paths"],
            required_paths=scenario["required_paths"],
            max_items=100,
            max_string=1000,
        )
        if prepared["policy_status"] != "pass" or not prepared["may_auto_continue"]:
            raise AssertionError(f"{name}: expected complete, explicit allowlist projection")
        result = json.loads(prepared["json_text"])
        if name == "crm_lead_routing":
            assert len(result["leads"]) == 40
            assert result["leads"][0] == {
                "id": "lead-000", "company": "Example Contractors 0", "priority": 0
            }
        if name == "support_triage":
            assert len(result["tickets"]) == 25
            assert result["tickets"][0]["category"] == "onboarding"
        if name == "webhook_normalization":
            assert len(result["events"]) == 50
            assert result["events"][-1]["eventId"] == "evt-0049"
        if "fake-token" in prepared["json_text"] or "raw-webhook-data" in prepared["json_text"]:
            raise AssertionError(f"{name}: an excluded field was forwarded")
        rows.append({
            "scenario": name,
            "input_characters": len(raw),
            "output_characters": prepared["output_characters"],
            "characters_removed": prepared["characters_removed"],
            "reduction_pct": round(100 * (len(raw) - prepared["output_characters"]) / len(raw), 1),
            "fields_excluded": prepared["fields_excluded"],
            "policy_status": prepared["policy_status"],
        })
    return rows


if __name__ == "__main__":
    print(json.dumps({
        "method": "synthetic-payload size/required-field characterization; not model token or dollar savings",
        "scenarios": evaluate(),
    }, indent=2))
