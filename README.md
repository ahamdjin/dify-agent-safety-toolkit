# Agent Safety Toolkit for Dify

**Two practical workflow tools, not a security certification.** Built by [Ahmad Yar](https://www.ahmadyar.co/) and powered by the published open-source Python package [Ahmad Yar GPT Tools](https://github.com/ahamdjin/ahmad-yar-automation-lab).

| Tool | Why it exists |
| --- | --- |
| **Redact Sensitive Text** | Mask common emails, phone numbers, IP addresses, payment-card candidates, and recognizable API tokens in ticket text or notes **before** an LLM step. |
| **Prepare Agent JSON** | Mask known secret fields and sensitive text values, remove null object fields, and cap oversized API response strings, lists and nesting **before** an LLM step. |

The operations run inside the Dify plugin runtime. No additional account, API key, external inference call, or hosted service is required. They use pinned package `ahmad-yar-gpt-tools==0.3.1` and return JSON results with redaction/compaction counts.

**Not comprehensive data loss prevention (DLP):** pattern matching misses unknown secret formats and personal details; it can also change legitimate data. Compaction is lossy. This is an optional preparation layer, not anonymization or a GDPR/compliance guarantee.

## Use in a Dify workflow

### 1. Text redaction

1. Add a **Tools → Agent Safety Toolkit → Redact Sensitive Text** node after text extraction, a helpdesk integration, or a webhook.
2. Bind upstream text into its **Text** input.
3. Use the returned JSON field **text** in your next LLM node, instead of the original unmasked text.
4. During testing, inspect **redaction_counts** and manually review the masked output.

Fictional example:

    Before: Contact alice@example.com about the ticket.
    After:  Contact [EMAIL_1] about the ticket.

Returned object has fields `text`, `changed` and `redaction_counts`. It does not guarantee the text no longer identifies a person.

### 2. Prepare JSON for an agent

1. Add the tool after a CRM/HTTP Request node. Serialize the previous JSON response as a string if necessary.
2. Bind it to **Prepare Agent JSON → JSON input**.
3. Start with the defaults: max string **1000**, max array items **25**, max depth **8**.
4. Use result field **json_text** (a serialized JSON string) in your downstream LLM prompt. If you need an object, parse it with a subsequent node.
5. Inspect `redaction_counts`, `compaction` and `output_characters`. Do not feed truncated responses to a calculation or decision that requires full records.

Fictional input:

    {"lead":{"email":"buyer@example.com","accessToken":"example-value"},"events":[null,{"status":"new"}]}

Representative output:

    {"lead":{"email":"[EMAIL_1]","accessToken":"[REDACTED]"},"events":[null,{"status":"new"}]}

Null object *fields* are removed; null array elements remain. Secret fields with common camelCase, snake_case and hyphenated names are masked.

## Install on Dify

The plugin is **not published in the Dify Marketplace yet**. To install and test it yourself:

1. Install the official [Dify plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli).
2. Clone [this repository](https://github.com/ahamdjin/dify-agent-safety-toolkit) and open its root directory.
3. Run `dify plugin package .` to create a `.difypkg` file.
4. In Dify, go to **Plugins → Install Plugin → Local Package** (labels may vary by version) and select the generated package.
5. In a Workflow/Chatflow, add a **Tool** node and select **Agent Safety Toolkit**. The provider needs no API credentials.

### Local debugging

Requires Python **3.12**. In the repository root:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v

Copy `.env.example` to `.env`. In your Dify instance, open **Plugins → Plugin Debugging**, copy the Host Address into `REMOTE_INSTALL_URL` and the Debugging API Key into `REMOTE_INSTALL_KEY`. The debugging key authenticates your development process to Dify, not the plugin tools. Run `python -m main`. Never commit `.env`.

## API contract

**Redact Sensitive Text:** required non-empty string `text`, up to 120,000 characters. JSON output contains `text`, `changed` and `redaction_counts`.

**Prepare Agent JSON:** required `json_text` (serialized valid JSON, up to 120,000 characters). Optional numeric `max_string` (100–4000), `max_items` (1–100), `max_depth` (1–16). JSON output includes `json_text`, `changed`, input/output character counts, `redaction_counts` and `compaction`. Root JSON objects, arrays, or primitives are supported. Duplicate keys, nonstandard JSON numeric constants, malformed JSON and excessive nesting fail closed.

Input content is never embedded into validation error messages. This does *not* control logging/tracing performed by earlier Dify nodes.

## Real security boundaries

Designed for **best-effort known-pattern masking** and **bounded API response preparation**.

Not designed for complete secret discovery, access control, cryptographic protection, irreversible anonymization, robust prompt-injection defense, compliance certification, proof of data safety, or a reliable count of LLM tokens. The tool may omit meaningful data. It must not replace security controls on source systems and should not be the only protection for sensitive or regulated data.

The plugin sends no data to an external service itself, but Dify, upstream nodes, workflow traces and downstream models may store or transmit raw or transformed data depending on how you configure them. See [PRIVACY.md](PRIVACY.md). The Marketplace risk category should be assessed as **High** because it intentionally processes potentially sensitive personal/financial/authentication information.

## Engineering and provenance

- **Source:** [ahamdjin/dify-agent-safety-toolkit](https://github.com/ahamdjin/dify-agent-safety-toolkit)
- **Underlying code:** [ahmad-yar-automation-lab](https://github.com/ahamdjin/ahmad-yar-automation-lab) and [PyPI distribution](https://pypi.org/project/ahmad-yar-gpt-tools/)
- **Maintainer:** [Ahmad Yar](https://www.ahmadyar.co/)
- **License:** MIT for this Dify adapter, Apache-2.0 for the upstream Python library.

GitHub Actions tests the Python transformation logic, validates plugin file links, and imports Dify SDK adapters using Python 3.12. Installation into a live Dify instance and Marketplace review are **additional acceptance steps**; passing CI alone does not prove live compatibility.
