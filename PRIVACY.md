# Privacy policy — Agent Safety Toolkit

**Maintainer:** [Ahmad Yar](https://www.ahmadyar.co/) · [Source repository](https://github.com/ahamdjin/dify-agent-safety-toolkit)

**Updated:** 2026-10-20 · **Plugin version:** 0.0.1

## What data the plugin sees

The tool receives only text or JSON that a Dify workflow explicitly passes to it. This data may contain personal details, secret strings, or confidential API responses. It processes those values in memory to perform known-pattern redaction or bounded compaction and returns the transformed result and count-only statistics.

## Collection, storage, network, logs

- The plugin itself does **not** call external services at runtime, track users, create accounts, or use third-party telemetry.
- The plugin code does **not** intentionally store inputs or transformed outputs in a file or database, and does not send them to the maintainer.
- Runtime errors are designed not to interpolate source content.
- Dependencies are installed from PyPI at setup time; this installation does not upload the workflow's customer data.
- The Dify platform, plugin daemon, request infrastructure, other workflow nodes, configured log/tracing providers and downstream LLMs may still receive or retain inputs/outputs according to their own policies and your configuration. This policy does **not** override their behavior.

## Limits

Pattern matching is not guaranteed to catch every credential, person, payment-related value, or regulated detail. The result may still be sensitive. Compacted output intentionally omits data. **This plugin is not complete DLP, anonymization, or compliance protection.** Do not rely on it as the only control for confidential or regulated data.

## Contact and security

Report vulnerabilities privately using [GitHub private vulnerability reporting](https://github.com/ahamdjin/dify-agent-safety-toolkit/security/advisories/new) if enabled, or reach the maintainer through [the contact page](https://www.ahmadyar.co/connect). Do not post actual secrets or customer data in public issues.
