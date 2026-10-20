# Dify Cloud validation — 2026-10-20

Workspace visible in Arc: Dify's Workspace, Sandbox plan.

User reported installation after selecting the locally built 0.1.0 package. On independent UI inspection, Dify's Installing integrations panel showed **Agent Safety Toolkit — Installing...**. The installed Tool Plugin list contained only the four built-in providers; the toolkit was not yet available. No installation error or detailed log was exposed in that panel.

Installation completion and tool execution are therefore unverified. Do not mark marketplace live-test checkboxes complete based on package upload or this pending task. No workflow was created, no model credits were used, and no marketplace submission was made during this check.

A page reload was attempted; the refreshed Tool Plugin page remained on loading placeholders after another 20 seconds. This provides no evidence of a successful installation or a specific plugin defect. Next step: reopen the installation task when Cloud responds and inspect any completion/failure message.

## Confirmed installation on subsequent refresh

The user correctly reported that the plugin was available. A subsequent independent UI refresh confirmed **Agent Safety Toolkit 0.1.0**, marked **LOCAL PLUGIN**, at https://cloud.dify.ai/integrations/tools/built-in. Its details panel displayed publisher `ahamdjin/agent_safety_toolkit`, **2 ACTIONS INCLUDED**, **Redact Sensitive Text**, and **Prepare Agent JSON**. The earlier installing/loading observations were temporary and are superseded for installation status.

Installation and action discovery are confirmed. Actual execution, named output routing, pass/review/block behavior in Cloud, remote debugging, and CE testing remain unverified. No test workflow was saved or published.
