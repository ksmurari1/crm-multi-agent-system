# NexaTel CRM — AutoGen Solution Design

## Architecture diagram

![NexaTel CRM AutoGen multi-agent architecture](images/crm_autogen_architecture.png)

The diagram above is included in this repository. Use the SVG for scalable rendering and `../docs/architecture.mmd` (from the repository root: `docs/architecture.mmd`) to edit the Mermaid source.

## 1. Purpose

NexaTel CRM demonstrates customer support and service operations using Streamlit, structured local CRM data, AutoGen agents, and a human-controlled Finance Manager decision process. The Employee AI Assistant is an additional feature; it does not replace the existing investigation workflow.

## 2. Logical layers

1. **Experience layer:** Customer Portal and Employee Portal. Employee Portal retains case selection, investigation scope, Run Workflow, investigation report, and Finance Manager decision form; it adds a chat-style AI assistant and horizontal five-agent activity strip.
2. **Routing/orchestration layer:** Rule-based query router selects relevant specialists for employee chat. `core/workflow.py` runs the separate full investigation flow. The CRM Orchestrator synthesizes findings where configured.
3. **AutoGen agent layer:** CRM Orchestrator, Customer Service, IT Support, Finance, and Administration.
4. **Tool/data layer:** `tools/crm_tools.py` reads structured data from `data/crm_data.json`.
5. **Human decision layer:** Finance Manager approves/rejects with a required reason; decision history is stored in `data/approval_decisions.json`.

## 3. Agent responsibilities

| Agent | Responsibility |
|---|---|
| CRM Orchestrator | Coordinates selected work and synthesizes the final response where configured. |
| Customer Service | Customer profile, case details, and customer-facing status. |
| IT Support | Technical incident details, outage evidence, and service status. |
| Finance | Billing/policy context and illustrative proposed-credit calculation. It does not make the final human approval decision. |
| Administration | Case/customer validation and administrative policy context. |

The current workflow uses sequential specialist execution. Query-based routing is rule-driven. Agent statuses, actions, timestamps, and durations should be taken from actual execution events. A skipped agent must be displayed as skipped, not completed.

## 4. Employee AI Assistant flow

1. Employee submits a question.
2. Rule-based router classifies the question intent.
3. Relevant specialist agent(s) and CRM tools are invoked.
4. The orchestrator prepares a response from available evidence, where configured.
5. UI shows the answer and agent activity details.
6. Chat session state stays separate from investigation output and persisted approval decisions.

Example intents include critical-case lookup, critical-incident lookup, case status, pending finance approvals, and proposed-credit questions.

## 5. Full investigation flow

1. Employee selects a case and investigation scope.
2. Employee clicks Run Workflow.
3. Workflow loads case and related incident context.
4. Specialist agents inspect relevant customer, technical, finance, and administrative evidence.
5. Orchestrator composes findings and a resolution report.
6. UI shows the report and agent activity.
7. Finance Manager approval remains a separate human action.

## 6. Data model

- **Customer:** business account, service plan, monthly fee, account status, contact.
- **Case:** customer-facing request, priority, reported date, status, and requested compensation.
- **IT incident:** technical event, evidence status, outage timing/duration, service status, notes, linked by `case_id`.
- **Billing/payment/policy records:** context for checks and illustrative calculation.
- **Approval decision:** reviewer-entered identity, decision, reason, timestamp, and transaction state.

The illustrative proposed-credit formula is demo logic and is not a determination of contractual entitlement.

## 7. Technology

- Python 3.12
- Streamlit
- AutoGen AgentChat
- AutoGen OpenAI extension
- OpenAI model configured through environment variables
- `python-dotenv`
- JSON files for demo records and approval history

See `requirements.txt` for the project dependency list.

## 8. Security and production considerations

- Keep API keys in `.env` or a secret manager; never commit secrets.
- Reviewer identity is self-entered in this demo; production requires authenticated identity and authorization.
- Local JSON files are not suitable for concurrent transactional production workloads.
- Real financial actions require independent server-side authorization, audit controls, and transaction integration.
- Agent attribution and timings must be based on actual workflow events.

## 9. Explicit non-features

The current version does not implement RAG, vector retrieval, knowledge-graph retrieval, live web search, production authentication/authorization, or real payment/credit execution.

## 10. Test plan

- Critical cases and critical incidents queries.
- CASE-2045 status query.
- Pending Finance Manager approval query.
- Full CASE-2045 investigation.
- Unknown case ID.
- Agent status/action/timing accuracy.
- Reviewer/reason validation.
- Persistence after application restart.
- Clean dependency installation and application startup.

Freeze a release only after the running application passes these checks.
