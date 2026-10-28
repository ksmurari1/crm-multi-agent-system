import asyncio
import time
from datetime import datetime
from typing import Any

from agents.agent_factory import create_model_client, create_agents
from tools.crm_tools import (
    get_case,
    get_it_incidents,
    get_billing_records,
    get_policies,
    calculate_proposed_credit,
)


AGENT_LABELS = {
    "customer_service": "Customer Service",
    "it_support": "IT Support",
    "finance": "Finance",
    "administration": "Administration",
    "orchestrator": "CRM Orchestrator",
}

SCOPES = {
    "Full investigation": {
        "agents": ["customer_service", "it_support", "finance", "administration"],
        "description": "All specialists investigate the case; the orchestrator consolidates the report.",
    },
    "Technical status": {
        "agents": ["customer_service", "it_support"],
        "description": "Customer Service and IT Support check the case and incident. Finance and Administration are intentionally skipped.",
    },
    "Compensation review": {
        "agents": ["customer_service", "it_support", "finance", "administration"],
        "description": "All relevant specialists validate evidence, billing, policy and approval requirements.",
    },
    "Account and case validation": {
        "agents": ["customer_service", "administration"],
        "description": "Customer Service and Administration validate the customer and case. IT and Finance are intentionally skipped.",
    },
}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _last_text(result) -> str:
    # AutoGen results can include tool events as well as text responses.
    for message in reversed(result.messages):
        content = getattr(message, "content", None)
        source = getattr(message, "source", "")
        if isinstance(content, str) and content.strip() and source not in ("user", "system"):
            return content.strip()
    return "The agent run finished without a final text response."


async def investigate_case(case_id: str, scope: str = "Full investigation") -> dict[str, Any]:
    started_all = time.perf_counter()
    canonical_input = (case_id or "").strip().upper()
    case_result = get_case(canonical_input)
    if case_result.get("status") == "not_found":
        return {"status": "not_found", "case_id": canonical_input, "error": "CRM case not found."}

    case = case_result["case"]
    customer = case_result.get("customer")
    canonical_id = str(case.get("case_id", canonical_input)).upper()
    if not customer:
        return {
            "status": "data_error",
            "case_id": canonical_id,
            "error": "The case references a missing customer record.",
        }

    incidents = get_it_incidents(canonical_id)
    context = {"case": case, "customer": customer, "it_incidents": incidents}
    incident_rows = incidents.get("incidents", [])
    verified_days = max(
        (int(item.get("verified_outage_days", 0) or 0)
         for item in incident_rows if item.get("evidence_status") == "Verified"),
        default=0,
    )

    selected_scope = scope if scope in SCOPES else "Full investigation"
    active_agents = SCOPES[selected_scope]["agents"]
    activity: dict[str, dict[str, Any]] = {}
    for key, label in AGENT_LABELS.items():
        if key == "orchestrator":
            activity[key] = {
                "agent": label,
                "status": "PENDING",
                "detail": "Consolidates the findings returned by the selected specialists.",
                "started_at": None, "finished_at": None, "duration_seconds": None,
            }
        elif key in active_agents:
            activity[key] = {
                "agent": label,
                "status": "QUEUED",
                "detail": "Selected for this investigation scope.",
                "started_at": None, "finished_at": None, "duration_seconds": None,
            }
        else:
            activity[key] = {
                "agent": label,
                "status": "SKIPPED",
                "detail": f"Not required for the selected scope: {selected_scope}.",
                "started_at": None, "finished_at": None, "duration_seconds": 0.0,
            }

    model_client = create_model_client()
    findings: dict[str, str] = {}
    workflow_error = None
    try:
        agents = create_agents(model_client)

        tasks = {
            "customer_service": (
                f"Investigate the customer complaint and account for case {canonical_id}. "
                f"Use your tools. Context: {context}. Report only evidence-based findings."
            ),
            "it_support": (
                f"Validate the technical incident for case {canonical_id}. "
                f"Use incident tools. Context: {context}. Explicitly report evidence status, "
                "verified outage days and restoration status; do not invent an ETA."
            ),
            "finance": (
                f"Evaluate compensation for case {canonical_id}. Customer ID: {customer['customer_id']}. "
                f"Requested amount: {case.get('requested_compensation')} {case.get('currency', 'INR')}. "
                f"Verified IT incidents: {incidents}. Use billing, policy and calculation tools. "
                "The proposed formula is illustrative only. Recommend, never approve or apply a credit."
            ),
            "administration": (
                f"Validate customer/account and approval process for case {canonical_id}. "
                f"Context: {context}. Use tools and identify missing contract eligibility evidence."
            ),
        }

        for key in active_agents:
            entry = activity[key]
            entry["status"] = "RUNNING"
            entry["started_at"] = _now()
            t0 = time.perf_counter()
            try:
                result = await agents[key].run(task=tasks[key])
                findings[key] = _last_text(result)
                entry["status"] = "COMPLETED"
                entry["detail"] = "Agent returned findings successfully."
            except Exception as exc:
                entry["status"] = "ERROR"
                entry["detail"] = f"{type(exc).__name__}: {exc}"
                findings[key] = f"Agent execution failed: {type(exc).__name__}: {exc}"
                workflow_error = workflow_error or f"{AGENT_LABELS[key]} failed."
            finally:
                entry["finished_at"] = _now()
                entry["duration_seconds"] = round(time.perf_counter() - t0, 2)

        activity["orchestrator"]["status"] = "RUNNING"
        activity["orchestrator"]["started_at"] = _now()
        t0 = time.perf_counter()
        try:
            final_result = await agents["orchestrator"].run(
                task=f"""
Create a concise CRM investigation report for {canonical_id}.
Investigation scope: {selected_scope}
Scope description: {SCOPES[selected_scope]['description']}

CRM RECORDS:
{context}

SPECIALIST FINDINGS (only selected agents were run):
{findings}

Rules:
- Clearly distinguish verified records from recommendations and missing data.
- Never invent a restoration ETA or say service is restored unless the records prove it.
- Do not approve, reject, or apply compensation.
- State that Finance Manager approval is required for compensation.
- If Finance was not selected, say financial assessment was outside this investigation scope.
- Use headings: Summary; Verified evidence; Agent findings; Risks/missing data; Next actions; Human decision required.
"""
            )
            report = _last_text(final_result)
            activity["orchestrator"]["status"] = "COMPLETED"
            activity["orchestrator"]["detail"] = "Consolidated the selected specialist findings."
        except Exception as exc:
            report = "Orchestrator could not generate the final report. Review the specialist findings and execution log."
            activity["orchestrator"]["status"] = "ERROR"
            activity["orchestrator"]["detail"] = f"{type(exc).__name__}: {exc}"
            workflow_error = workflow_error or "CRM Orchestrator failed."
        finally:
            activity["orchestrator"]["finished_at"] = _now()
            activity["orchestrator"]["duration_seconds"] = round(time.perf_counter() - t0, 2)

        # Deterministic demo calculation is also returned as structured data for UI.
        proposed_credit = None
        if "finance" in findings and verified_days > 0:
            try:
                proposed_credit = calculate_proposed_credit(customer["customer_id"], verified_days)
            except Exception:
                proposed_credit = None

        return {
            "status": "investigated" if not workflow_error else "partial",
            "case_id": canonical_id,
            "customer": customer.get("name", "Unknown customer"),
            "customer_id": customer.get("customer_id"),
            "case_status": case.get("status", "Not recorded"),
            "priority": case.get("priority", "Not recorded"),
            "currency": case.get("currency", customer.get("currency", "INR")),
            "requested_compensation": case.get("requested_compensation"),
            "verified_outage_days": verified_days,
            "proposed_credit": proposed_credit,
            "findings": findings,
            "resolution_report": report,
            "approval_status": "PENDING_FINANCE_MANAGER",
            "scope": selected_scope,
            "scope_description": SCOPES[selected_scope]["description"],
            "agent_activity": activity,
            "total_duration_seconds": round(time.perf_counter() - started_all, 2),
            "started_at": _now(),
            "error": workflow_error,
        }
    finally:
        await model_client.close()


def run_investigation(case_id: str, scope: str = "Full investigation") -> dict[str, Any]:
    """Synchronous entry point for CMD and Streamlit."""
    return asyncio.run(investigate_case(case_id, scope))
