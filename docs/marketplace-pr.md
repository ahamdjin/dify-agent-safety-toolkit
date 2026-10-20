# Plugin Submission

## Plugin information

- **Author**: ahamdjin
- **Plugin name**: agent_safety_toolkit (Agent Safety Toolkit)
- **Version**: 0.1.0
- **Source repository**: https://github.com/ahamdjin/dify-agent-safety-toolkit
- **Contact**: https://www.ahmadyar.co/connect

## Submission type

- [x] New plugin
- [ ] Version update

## What changed

Reusable local JSON allowlisting, required-field validation, bounded compaction, and best-effort text masking for agent context. Exposes named pass/review/block outputs for workflow routing. No credentials or external runtime API are required. An exact-name public marketplace search returned no matching listing on 2026-10-20. Related sandbox-output masking exists; this plugin focuses on service-independent JSON field projection, required-field completeness, bounded compaction and named workflow policy outputs. Search coverage does not guarantee uniqueness.

## Risk level

- [ ] Low risk
- [ ] Medium risk
- [x] High risk

<!-- Select one based on the risk classification in docs/plugin-submission-requirements.md. -->

## Required checks

- [ ] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [x] I have read and comply with the Plugin Developer Agreement.
- [ ] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The package contains only files needed at runtime.
- [x] The package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md` or a hosted privacy policy, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with any localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

## Security and privacy notes

Inputs can include personal, financial, and authentication information, so High risk is selected. Transformations run in memory with no runtime network calls, filesystem operations, code execution, telemetry, or maintainer storage. No provider credentials or plugin permissions are required. Input sizes and configuration are bounded. Pattern masking is best effort; a pass outcome is not a security guarantee. Dify traces and upstream/downstream retention remain outside the plugin boundary.

## Local validation

Python 3.12: `python -m unittest discover -s tests -v` — 38 tests passed.
`python -m benchmarks.measure` — three synthetic scenarios passed.
`uv pip check --python .venv/bin/python` — compatible dependencies.
Official Dify CLI 0.6.10 built the package. Archive verification recorded locally.
Dify Cloud installation and discovery of both actions confirmed. Cloud workflow execution, remote debugging, and Community Edition validation have not been completed. This is an explicit validation limitation; submission is held in draft until functional Cloud validation is recorded.

## Reviewer notes

<!-- Optional: migration notes, known limitations, binary/package exceptions, or breaking changes. -->

The publisher confirmed agreement acceptance on 2026-10-20. This PR remains a draft pending live workflow execution validation.

Sensitive data may include financial and authentication information. Processing is in memory, without runtime network calls, telemetry, or plugin storage. Dify and downstream retention are outside this plugin. Pattern masking is incomplete; pass is not safety certification.
