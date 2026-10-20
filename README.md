# Agent Safety Toolkit — Dify plugin

**Prepare only the data an AI agent actually needs.** This is an open-source, deterministic Dify tool provider by [Ahmad Yar](https://www.ahmadyar.co/) that lets a workflow **select approved JSON fields, mask recognizable sensitive values, bound response size, and route incomplete outputs for review or blocking** before handing context to an LLM.

**Not a security certification, a prompt-injection defense, or complete DLP.** An explicit allowlist reduces unnecessary disclosure, but even a `pass` outcome is **not proof** that data is safe. See [Privacy](PRIVACY.md) and [Limitations](#security-and-data-handling).

## What actually helps a Dify workflow builder?

| Tool | Purpose |
| --- | --- |
| **Prepare Agent JSON** | Explicitly choose nested fields and array fields; require business-critical fields; mask known and custom credential keys; trim excess data; return `pass`, `review` or `block`. |
| **Redact Sensitive Text** | Best-effort pattern masking of recognizable emails, telephone numbers, IPs, card candidates and credentials. Optionally replace exact custom literals. |

Both tools are local transformations inside the Dify plugin process, using [ahmad-yar-gpt-tools==0.3.1](https://pypi.org/project/ahmad-yar-gpt-tools/). They do **not** call a model, access CRMs, or send data to the maintainer. No plugin account or API key is needed.

**Why not just use a Dify Code node?** You can implement all of this in a Code node if you want. This plugin makes the rules reusable, supplies tested bounds and a documented output contract, and provides a consistent `pass` / `review` / `block` branch signal. Its value is integration and repeatability, **not an exclusive detection algorithm**.

## Example: safely prepare a CRM lead record

Suppose the HTTP Request node returns fictional JSON:

```json
{
  "lead": {
    "id": "lead-009",
    "company": "Example Services",
    "email": "person@example.com",
    "internalCredential": "demo-internal-value",
    "privateNotes": "Do not expose this negotiation history"
  },
  "debug": {"headers": {"authorization": "example-only-value"}}
}
```

In **Tools → Agent Safety Toolkit → Prepare Agent JSON**, bind the response as serialized JSON in **JSON input** and configure:

| Setting | Enter this |
| --- | --- |
| Allowed paths | `lead.id` newline `lead.company` |
| Required paths | `lead.id` newline `lead.company` |
| Extra secret field names | Leave blank for this example |
| Block if truncated | Enable for critical downstream decisions |

The tool projects only the explicitly approved fields before masking and compaction:

```json
{"lead":{"id":"lead-009","company":"Example Services"}}
```

The output has `policy_status: "pass"`, `may_auto_continue: true` and counts of excluded JSON fields and removed characters. The private notes, debug headers, and email are **not forwarded**. No secret value is required in the configuration.

**Important:** this status is a deterministic rule result, **not proof that the selected fields are safe**. Inspect your allowlist and the data source's classification before enabling automatic forwarding.

### Connecting the policy to Dify (essential)

1. Open **Studio → Workflow**. Connect your CRM/API/Webhook node to **Prepare Agent JSON**.
2. Bind the node's response to `json_text`. If Dify supplies an object, JSON-serialize it first (using an appropriate previous node).
3. Use the configuration above. Save and execute with fictional test data.
4. Add a **Dify IF/ELSE** node immediately after **Prepare Agent JSON**.
5. In the Dify IF/ELSE node, select the named **Prepare Agent JSON → `may_auto_continue`** output variable and test **equals true**. Route that branch to the LLM using the tool's named **`json_text`** output—never the original HTTP response.
6. Route all other outcomes to your own review/manual handling route; for `block`, the plugin deliberately returns an **empty `json_text`**.
7. Inspect `policy_reasons` and `missing_required_paths` when debugging, not the raw input.

If you do not set an allowlist, the tool returns **`review`**, not `pass`. If a required field goes missing, or you enable **Block if truncated** and data is cut, it returns **`block`**. If a selected value is masked, or optional data is truncated, it returns **`review`** by default.

## Configure the tools

### Prepare Agent JSON

- **JSON input**: valid JSON *string*, up to **120,000 characters**. Root arrays and primitives are supported only with **no allowlist** (status `review`).
- **Allowed paths**: one path per line **or comma-separated**, at most 32; omit to keep the full source JSON but require review. Nested syntax: `lead.id`, `lead.company`, `events[].type`, `events[].createdAt`. The `[]` syntax applies the next field selection to **every item** of a list. There is no dot-wildcard, arbitrary JSONPath, or expression execution.
- **Required paths**: one per line (or comma-separated); missing, null, blank, structurally masked, or truncated values block output. For an array path such as `events[].id`, **every retained item** must have a valid value. A truncated array containing a cutoff marker cannot satisfy this requirement. A required path must be included in or covered by the allowlist.
- **Extra secret field names**: one simple JSON key per line (or comma-separated), max 32. Example: `internalCredential`. Matching is normalized for camelCase, underscores, and hyphens across nested JSON. Entire value becomes `[REDACTED]`.
- **Extra literal values to mask**: optional newline-separated exact strings, 4–128 characters each, max 20. These are **case-sensitive** matches, not user-supplied regex; no arbitrary code is executed. **Do not put real API keys here** if your Dify configuration/trace access is not trusted.
- **Max string**: 100–4,000 characters, default **1,000**.
- **Max array items**: 1–100, default **25** (adds a `_truncated_items` marker when cut).
- **Max depth**: 1–16, default **8** (nested structures beyond the cap become a marker).
- **Block if truncated**: default **false**. When enabled, any string/list/depth cutoff returns status `block` and **no `json_text`**.

The plugin emits **both a JSON result and named Dify output variables** for direct use in IF/ELSE and downstream nodes. If the named outputs do not appear after updating a local package, remove and re-add the Tool node to refresh its output schema.

**Returned fields** are `json_text` (serialized JSON or empty on block), `policy_status` (`pass` / `review` / `block`), `policy_reasons`, `missing_required_paths`, `may_auto_continue`, `fields_excluded`, `input_characters`, `output_characters`, `characters_removed`, `redaction_counts`, `compaction` and `changed`.

Metrics represent **JSON field and character counts**, *not LLM token savings or cost reductions*. Some transformations can increase output length. The `characters_removed` count is floored at zero; use input/output counts for the exact difference.

### Redact Sensitive Text

- Pass raw text to `text`; returned fields are `text`, `changed`, and `redaction_counts`.
- Optionally provide **Extra literal values to mask** as above.
- Use its returned `text` in the downstream LLM node, never the original input.
- This simpler tool does **not** provide a policy gate; use the JSON tool for conditional routing.

## Installation

**The plugin has not been published in the Dify Marketplace.** Version 0.1.0 has been installed in Dify Cloud and both actions are visible. Workflow execution and Community Edition validation are not yet complete.

1. Open [GitHub Actions — Validate Dify Agent Safety Toolkit](https://github.com/ahamdjin/dify-agent-safety-toolkit/actions/workflows/validate.yml).
2. Select the latest **successful** build on `main`.
3. Under **Artifacts**, download **agent-safety-toolkit-dify-package**, then unzip it.
4. In **Dify → Plugins → Install Plugin → Local Package**, upload `agent_safety_toolkit-0.1.0.difypkg` (labels may vary).
5. Use a Tool node to test **Prepare Agent JSON** with the fictional CRM payload above. Verify that the next LLM node receives the projected output only.

To package the source manually, install the [official Dify plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli) and run `dify plugin package .` from the repository root.

### Developer tests

Python 3.12; in your environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m benchmarks.measure
```

To run Dify's local debugger, copy `.env.example` to `.env`, set `REMOTE_INSTALL_URL` and `REMOTE_INSTALL_KEY` from your Dify instance's **Plugins → Plugin Debugging** screen, and run `python -m main`. Do not commit credentials.

CI uses Dify's official CLI to package the `.difypkg`, checks its required runtime files, excludes development files, and stores it as a downloadable GitHub Actions artifact.

## Evidence, not marketing

[`benchmarks/measure.py`](https://github.com/ahamdjin/dify-agent-safety-toolkit/blob/main/benchmarks/measure.py) and [the measured examples](https://github.com/ahamdjin/dify-agent-safety-toolkit/blob/main/docs/measurements.md) runs three **fictional, reproducible** workloads: CRM routing, support ticket triage, and webhook normalization. It verifies preserved required fields and records before/after JSON character size and excluded keys. This is compared against unfiltered JSON, **not against an optimized Dify Code node**; no accuracy, production latency, model-token, or dollar-savings claims are made.

Our [automated tests](https://github.com/ahamdjin/dify-agent-safety-toolkit/tree/main/tests) cover allowlist projection, required-field preservation, masking, blocked-result fail-closed behavior, array truncation, excessive depth, malformed JSON, invalid settings and Dify SDK output messages.

## Security and data handling

- Best-effort known-pattern redaction can **miss information** or misidentify harmless strings. Custom masking is an exact string operation, not a complete data-classification engine.
- An allowlist is meaningful only if a knowledgeable operator chooses the approved fields. Whitelisted free text can still contain personal data or malicious prompt instructions.
- **`pass` means only that the configured deterministic criteria were met.** It does not mean the data is sanitized, compliant, safe or authorized for a given model provider.
- Truncation is lossy. Use strict blocking when completeness is required. Missing required fields return a blocked outcome with no forwarded payload.
- The plugin runs **after** prior workflow nodes, so raw values can already be present in Dify tracing, upstream logs and integrations. Dify and downstream LLM provider retention is outside this plugin's control.
- Configuration errors omit input values; metrics contain counts, not copies of detected sensitive values. There are no runtime network calls or maintainer-operated storage.
- Marketplace risk classification should be reviewed as **High** because content can include personal, financial and authentication information.

[Privacy policy](PRIVACY.md) · [GitHub source](https://github.com/ahamdjin/dify-agent-safety-toolkit) · [Underlying Python package](https://github.com/ahamdjin/ahmad-yar-automation-lab) · [Portfolio](https://www.ahmadyar.co/)

**License:** MIT for this Dify adapter. The underlying `ahmad-yar-gpt-tools` dependency retains its Apache-2.0 license.
