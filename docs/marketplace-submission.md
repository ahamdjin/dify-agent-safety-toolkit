# Marketplace preparation — Dify tool kit

Project name: **Dify tool kit**. Marketplace identity stays **Agent Safety Toolkit**, `ahamdjin/agent_safety_toolkit`, version `0.1.0`, matching the existing repository. Local folder: `projects/dify-tool-kit`.

## Completed locally, 2026-10-20

- Cloned the existing source repository; preserved runtime implementation and identity.
- Installed Python 3.12 and dependencies in `.venv`; 38 behavioral/SDK tests pass and dependency compatibility check passes.
- Ran all three synthetic benchmarks; these measure characters, not LLM cost or tokens.
- Corrected privacy-policy version from 0.0.1 to 0.1.0.
- Installed official Dify CLI 0.6.10 locally and built the `.difypkg`.
- Added archive inspection and excluded local tooling/project notes from the installer.

## Required before submitting

1. Confirm publisher identity and monitored contact in `docs/marketplace-pr.md`. Review the Marketplace agreement yourself before checking that box.
2. Search https://marketplace.dify.ai/ for the proposed name and overlapping functionality. Record the result and date; uniqueness is not yet verified.
3. Install `dist/agent_safety_toolkit-0.1.0.difypkg` using Dify Plugins → Install Plugin → Local Package. Test Dify Cloud and Community Edition, or explicitly document unavailable environments in the PR.
4. Run remote debugging using the README instructions with credentials stored only in ignored `.env`. Record Dify version, date, and results without keys or customer data.
5. Exercise both tools with fictional inputs. For JSON, verify pass, review (no allowlist), block (missing required field), and strict truncation. Wire IF/ELSE to named `may_auto_continue`; confirm the downstream node receives only `json_text`. Confirm blocked output is empty and malformed JSON errors omit source data. Verify the text tool masks a fictional email.
6. Capture screenshots using fictional data and record live results in the submission draft. Local SDK tests do not prove these UI flows.
7. Publish reviewed source changes to the source repository, rebuild, and run `scripts/verify_package.py`. Verify version 0.1.0 has not already been published; bump synchronized version references if needed.
8. Fork `langgenius/dify-plugins` and create a focused branch. Add exactly one file at `ahamdjin/agent_safety_toolkit/agent_safety_toolkit-0.1.0.difypkg`. Do not submit loose source files to the marketplace repository.
9. Refresh its official PR template, complete the draft honestly, and submit after explicit authorization. Automated checks and human review determine acceptance. Merge triggers marketplace publication.

## Risk disclosure

Use **High risk** under the current submission rubric because this tool may process financial or authentication data. It performs local in-memory transformations, with no runtime external requests or granted plugin permissions. This does not prevent Dify traces or upstream/downstream services from retaining content. Masking is best effort; `pass` is a rule outcome, not a security guarantee.

## Official sources checked

- https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md
- https://github.com/langgenius/dify-plugins/blob/main/.github/pull_request_template.md
- https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct
- https://dify.ai/legal/marketplace-agreement

No Git push, release, marketplace PR, or publication has been performed.
