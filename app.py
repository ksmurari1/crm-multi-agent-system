import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from autogen_agentchat.agents import AssistantAgent

from agents.agent_factory import create_model_client, create_agents
from core.workflow import run_investigation
from tools.crm_tools import get_case, get_it_incidents, load_data


# ---------------------------------------------------------------------
# Page setup and visual system
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="NexaTel | Support Hub",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DECISIONS_FILE = DATA_DIR / "approval_decisions.json"

BG = "#ffe6d1"
PANEL = "#FFFDF8"
PANEL_2 = "#F0E8DC"
BORDER = "#D8CCBC"
TEXT = "#20252B"
MUTED = "#5E6872"
BLUE = "#2F6FAD"
BLUE_STRONG = "#245A8D"
SAND = "#8B5E3C"
GREEN = "#217A57"
AMBER = "#98651A"
RED = "#B4232F"

st.markdown(
    f"""
    <style>
    :root {{
      --nx-bg: {BG};
      --nx-panel: {PANEL};
      --nx-panel-2: {PANEL_2};
      --nx-border: {BORDER};
      --nx-text: {TEXT};
      --nx-muted: {MUTED};
      --nx-blue: {BLUE};
      --nx-blue-strong: {BLUE_STRONG};
      --nx-sand: {SAND};
      --nx-green: {GREEN};
      --nx-amber: {AMBER};
      --nx-red: {RED};
    }}
    .stApp {{
      background:
        radial-gradient(ellipse at 8% 0%, rgba(47,111,173,.10), transparent 36%),
        radial-gradient(ellipse at 95% 12%, rgba(139,94,60,.08), transparent 30%),
        var(--nx-bg);
      color: var(--nx-text);
    }}
    [data-testid="stHeader"] {{
        background: rgba(164,149,141,.94);
        backdrop-filter: blur(12px);
        position: relative;
    }}

    [data-testid="stHeader"]::after {{
        content: "CRM  ·  Intelligent Multi-Agent Service Operations";
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        color: #FFFFFF;
        font-size: 24px;
        font-weight: 600;
        letter-spacing: 1px;
        white-space: nowrap;
        pointer-events: none;
    }}
    [data-testid="stSidebar"] {{
      background: #F0E8DC;
      border-right: 1px solid var(--nx-border);
    }}
    [data-testid="stMarkdownContainer"], [data-testid="stText"], label,
    p, li, span, div {{
      color: inherit;
    }}
    .stApp, .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"] {{
      color: var(--nx-text);
    }}
    h1, h2, h3 {{ letter-spacing: -.025em; color: var(--nx-text); }}
    .nx-eyebrow {{
      color: var(--nx-blue);
      font-size: .76rem;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
      margin-bottom: .45rem;
    }}
    .nx-brand-title {{
      font-size: clamp(1.1rem, 1.8vw, 1.55rem);
      line-height: 1.15;
      font-weight: 850;
      letter-spacing: -.025em;
      color: var(--nx-text);
      margin-top: 2px;
    }}
    .nx-brand-sub {{
      color: var(--nx-muted);
      font-size: .84rem;
      margin-top: 3px;
    }}
    .nx-hero {{
      border: 1px solid rgba(47,111,173,.24);
      border-radius: 24px;
      padding: 18px 24px;
      background: linear-gradient(120deg, rgba(255,253,248,.98), rgba(240,232,220,.94));
      box-shadow: 0 16px 44px rgba(65,49,31,.08);
    }}
    .nx-title {{
      font-size: clamp(1.65rem, 2.6vw, 2.35rem);
      line-height: 1.12;
      font-weight: 850;
      letter-spacing: -.055em;
      color: var(--nx-text);
      margin: 0;
    }}
    .nx-title span {{ color: var(--nx-blue); }}
    .nx-subtitle {{
      color: var(--nx-muted);
      font-size: .93rem;
      line-height: 1.45;
      margin-top: .55rem;
      max-width: 760px;
    }}
    .nx-chip {{
      display: inline-block;
      border: 1px solid rgba(47,111,173,.22);
      background: rgba(47,111,173,.08);
      color: var(--nx-blue);
      border-radius: 999px;
      padding: 5px 11px;
      font-size: .74rem;
      font-weight: 750;
      letter-spacing: .04em;
      margin: 3px 5px 3px 0;
    }}
    .nx-card {{
      border: 1px solid var(--nx-border);
      border-radius: 18px;
      background: linear-gradient(160deg, rgba(255,253,248,.99), rgba(244,237,226,.96));
      padding: 18px;
      height: 100%;
      box-shadow: 0 8px 22px rgba(65,49,31,.045);
    }}
    .nx-card-title {{
      font-size: 1.05rem;
      font-weight: 750;
      margin: 0 0 .35rem 0;
      color: var(--nx-text);
    }}
    .nx-muted {{ color: var(--nx-muted); font-size: .9rem; line-height: 1.5; }}
    .nx-stat {{
      border: 1px solid var(--nx-border);
      border-radius: 16px;
      padding: 15px 17px;
      background: rgba(255,253,248,.94);
      box-shadow: 0 5px 16px rgba(65,49,31,.04);
    }}
    .nx-stat-label {{
      color: var(--nx-muted); font-size: .78rem; text-transform: uppercase;
      letter-spacing: .08em; font-weight: 750;
    }}
    .nx-stat-value {{
      color: var(--nx-text); font-size: 1.8rem; font-weight: 850;
      letter-spacing: -.04em; margin-top: .25rem;
    }}
    .nx-agent {{
      border: 1px solid var(--nx-border);
      border-radius: 15px;
      background: rgba(255,253,248,.96);
      padding: 14px 15px;
      margin-bottom: 9px;
    }}
    .nx-agent.done {{ border-color: rgba(33,122,87,.42); box-shadow: inset 3px 0 0 var(--nx-green); }}
    .nx-agent.wait {{ border-color: rgba(152,101,26,.35); box-shadow: inset 3px 0 0 var(--nx-amber); }}
    .nx-agent.skipped {{ border-color: rgba(94,104,114,.30); box-shadow: inset 3px 0 0 #89939D; opacity: .88; }}
    .nx-agent.running {{ border-color: rgba(47,111,173,.60); box-shadow: inset 3px 0 0 var(--nx-blue); }}
    .nx-agent.error {{ border-color: rgba(180,35,47,.50); box-shadow: inset 3px 0 0 var(--nx-red); }}
    .nx-agent-name {{ font-weight: 800; color: var(--nx-text); }}
    .nx-agent-state {{ color: var(--nx-green); font-size: .76rem; font-weight: 800; letter-spacing: .07em; }}
    .nx-divider {{ border-top: 1px solid var(--nx-border); margin: 1.1rem 0; }}
    .stButton > button, [data-testid="stFormSubmitButton"] > button {{
      border-radius: 12px !important;
      min-height: 2.7rem;
      font-weight: 800 !important;
      border: 1px solid #6F482F !important;
      background: linear-gradient(110deg, #6F482F, #8A5B3B) !important;
      color: #FFFFFF !important;
      box-shadow: 0 4px 12px rgba(79,51,33,.12);
      transition: all .15s ease;
    }}
    .stButton > button p, .stButton > button span,
    .stButton > button div, .stButton > button div p,
    [data-testid="stFormSubmitButton"] > button p,
    [data-testid="stFormSubmitButton"] > button span {{
      color: #FFFFFF !important;
    }}
    .stButton > button:hover,
    .stButton > button:focus,
    .stButton > button[kind="secondary"]:hover,
    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] > button:hover {{
      background: #4F3324 !important;
      border-color: #4F3324 !important;
      color: #FFFFFF !important;
      transform: translateY(-1px);
      box-shadow: 0 7px 16px rgba(79,51,33,.18);
    }}
    .stButton > button:hover p, .stButton > button:hover span,
    .stButton > button:hover div, .stButton > button:hover div p,
    [data-testid="stFormSubmitButton"] > button:hover p,
    [data-testid="stFormSubmitButton"] > button:hover span {{
      color: #FFFFFF !important;
    }}
    [data-testid="stMetric"] {{
      background: rgba(255,253,248,.96);
      border: 1px solid var(--nx-border);
      border-radius: 15px;
      padding: 13px 15px;
      box-shadow: 0 5px 16px rgba(65,49,31,.04);
    }}
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {{ color: var(--nx-muted) !important; }}
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] div {{ color: var(--nx-blue) !important; }}
    [data-testid="stChatMessage"] {{
      border: 1px solid rgba(94,104,114,.16);
      border-radius: 16px;
      background: rgba(255,253,248,.92);
      padding: 10px 13px;
    }}
    [data-testid="stChatInput"] {{
    background-color: #E8DFD1 !important;
    border-radius: 14px !important;
    padding: 8px !important;
    }}

    [data-testid="stChatInput"] textarea {{
      background: #FFFDF8 !important;
      color: #20252B !important;
      border-color: #D8CCBC !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea {{
      background-color: #f2d9a2 !important;
      color: #20252B !important;
      border-color: #D8CCBC !important;
      border-radius: 11px !important;
    }}
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label {{
      color: var(--nx-text) !important;
    }}
    [data-testid="stAlert"] {{ border-radius: 12px; }}
    .nx-foot {{
      color: var(--nx-muted); font-size: .75rem; text-align: center;
      padding: 22px 0 8px 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Session state = short-term memory for this active Streamlit session.
# This is not permanent memory and is not shared between users.
# ---------------------------------------------------------------------
DEFAULTS = {
    "portal": "Home",
    "customer_messages": [],
    "active_case_id": "",
    "investigation": None,
    "investigation_case_id": "",
    "last_investigation_at": None,
    "approval_feedback": None,
    "employee_messages": [],
    "employee_agent_activity": {},
    "latest_agent_activity": {},
    "employee_last_answer_meta": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def now_local() -> datetime:
    return datetime.now().astimezone()


def formatted_now() -> str:
    return now_local().strftime("%d %b %Y · %I:%M:%S %p %Z")


def read_decisions() -> list[dict[str, Any]]:
    try:
        if DECISIONS_FILE.exists():
            payload = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        st.warning("Approval history could not be read. Please check the decision JSON file.")
    return []


def write_decision(record: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = read_decisions()
    existing.append(record)
    DECISIONS_FILE.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def latest_decision(case_id: str) -> dict[str, Any] | None:
    matching = [d for d in read_decisions() if d.get("case_id", "").upper() == case_id.upper()]
    return matching[-1] if matching else None


def get_cases() -> list[dict[str, Any]]:
    try:
        data = load_data()
        cases = data.get("cases", data.get("support_cases", []))
        if isinstance(cases, list):
            return cases
    except Exception:
        pass
    return [{"case_id": "CASE-2045", "issue": "Business internet unavailable", "priority": "Critical"}]


def extract_case_id(text: str) -> str | None:
    match = re.search(r"\bCASE[-\s]?\d+\b", text, flags=re.IGNORECASE)
    if match:
        value = match.group(0).upper().replace(" ", "")
        if not value.startswith("CASE-"):
            value = value.replace("CASE", "CASE-", 1)
        return value
    return None


def lookup_customer_context(case_id: str) -> dict[str, Any]:
    case_result = get_case(case_id)
    if case_result.get("status") == "not_found":
        return {"status": "not_found", "case_id": case_id}

    case = case_result.get("case")
    customer = case_result.get("customer")
    if not case or not customer:
        return {"status": "data_error", "case_id": case_id}

    canonical_id = case.get("case_id", case_id)
    incidents = get_it_incidents(canonical_id).get("incidents", [])
    decision = latest_decision(canonical_id)
    verified_days = max(
        (
            item.get("verified_outage_days", 0)
            for item in incidents
            if item.get("evidence_status") == "Verified"
        ),
        default=0,
    )

    return {
        "status": "found",
        "case": case,
        "customer": customer,
        "incidents": incidents,
        "verified_outage_days": verified_days,
        "decision": decision,
    }


def customer_fallback_reply(query: str, context: dict[str, Any]) -> str:
    """Reliable fallback when the language model is unavailable."""
    if context.get("status") == "not_found":
        return (
            f"I couldn't find a case matching **{context.get('case_id', 'that ID')}**. "
            "Please check the case number and try again."
        )
    if context.get("status") != "found":
        return "I couldn't retrieve the case details just now. Please try again or contact support."

    case = context["case"]
    customer = context["customer"]
    incidents = context["incidents"]
    decision = context.get("decision")
    lowered = query.lower()

    if any(word in lowered for word in ("refund done", "refund completed", "credit completed", "has it been paid")):
        if decision and decision.get("decision") == "APPROVED":
            return (
                f"The Finance Manager approved a proposed credit of **{decision.get('amount', 'an amount not recorded')} "
                f"{case.get('currency', 'INR')}** on {decision.get('decided_at', 'a recorded date')}. "
                "This demo does not process real payments, so I cannot confirm that a refund or account credit has been executed."
            )
        if decision and decision.get("decision") == "REJECTED":
            return (
                "The Finance Manager rejected the compensation request. "
                f"Recorded reason: {decision.get('reason', 'No reason was recorded')}."
            )
        return "Your compensation request has not yet received a Finance Manager decision. No refund or credit has been processed by this demo."

    if any(word in lowered for word in ("compensation", "refund", "credit", "money", "reimburse")):
        if decision:
            state = decision.get("decision", "PENDING")
            if state == "APPROVED":
                return (
                    f"The Finance Manager approved the proposed credit of **{decision.get('amount', 0)} "
                    f"{case.get('currency', 'INR')}**. "
                    "This demo records approval only; it does not execute a real refund or account credit."
                )
            return (
                f"The latest recorded decision for your request is **{state.lower()}**. "
                f"Reason: {decision.get('reason', 'Not provided')}."
            )
        request_amount = case.get("requested_compensation", "not recorded")
        proposal = customer.get("monthly_fee", 0) / 30 * context["verified_outage_days"]
        return (
            f"Your case records a compensation request of **{request_amount} {case.get('currency', 'INR')}**. "
            f"The verified outage record shows {context['verified_outage_days']} day(s). "
            f"For this demo, the illustrative calculation is **{proposal:,.2f} {case.get('currency', 'INR')}**. "
            "This is not a confirmed entitlement, and the Finance Manager has not yet made a decision."
        )

    if any(word in lowered for word in ("eta", "when", "expected", "resolution time", "resolve", "restored", "fixed")):
        incident = incidents[0] if incidents else {}
        status = incident.get("service_status", "Not available")
        notes = incident.get("technician_notes", "")
        return (
            f"Your case **{case.get('case_id')}** is currently **{case.get('status', 'under review')}**. "
            f"The latest technical record says the service status is **{status}**. "
            f"{notes} "
            "An estimated restoration date or time is not present in the current records, so I don't want to give you an unverified ETA."
        )

    incident_summary = (
        f"The latest IT record shows {context['verified_outage_days']} verified outage day(s). "
        if incidents else
        "No linked IT incident was found in the current records. "
    )
    return (
        f"I found case **{case.get('case_id')}** for **{customer.get('name')}**. "
        f"Its current CRM status is **{case.get('status', 'not recorded')}**, with priority **{case.get('priority', 'not recorded')}**. "
        f"{incident_summary}"
        "You can ask about the technical status, expected resolution, or compensation request."
    )


async def generate_customer_reply(query: str, context: dict[str, Any], history: list[dict[str, str]]) -> str:
    """Use AutoGen for a natural-language answer grounded in retrieved case data."""
    model_client = create_model_client()
    try:
        assistant = AssistantAgent(
            name="customer_portal_assistant",
            model_client=model_client,
            system_message=(
                "You are NexaTel's customer support assistant. Answer politely, clearly, "
                "and concisely. Use only the supplied CRM evidence and recent conversation. "
                "Never invent an ETA, restoration status, refund, approval, or transaction. "
                "Always distinguish CRM case status, compensation decision status, and credit execution status. "
                "If a saved Finance Manager decision is supplied, report it accurately. "
                "If no ETA exists, say it is not recorded. A proposed credit is illustrative, "
                "not contractual entitlement. Approval is not the same as payment completion. "
                "Do not expose internal agent reasoning, private billing details, or internal-only notes. "
                "If the case is not found, ask the user to verify the case ID. "
                "For this demo, do not claim the customer identity has been authenticated."
            ),
        )
        history_text = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in history[-8:]
        )
        # Only send customer-appropriate fields to the customer-facing model.
        # Internal technician notes and other internal operational details stay in the employee portal.
        if context.get("status") == "found":
            case = context["case"]
            customer = context["customer"]
            customer_evidence = {
                "status": "found",
                "case": {
                    "case_id": case.get("case_id"),
                    "issue": case.get("issue"),
                    "reported_date": case.get("reported_date"),
                    "priority": case.get("priority"),
                    "status": case.get("status"),
                    "requested_compensation": case.get("requested_compensation"),
                    "currency": case.get("currency"),
                },
                "customer": {
                    "name": customer.get("name"),
                    "service_plan": customer.get("service_plan"),
                    "account_status": customer.get("account_status"),
                },
                "incidents": [
                    {
                        "incident_id": item.get("incident_id"),
                        "incident_type": item.get("incident_type"),
                        "verified_outage_days": item.get("verified_outage_days"),
                        "service_status": item.get("service_status"),
                        "evidence_status": item.get("evidence_status"),
                    }
                    for item in context.get("incidents", [])
                ],
                "verified_outage_days": context.get("verified_outage_days", 0),
                "decision": context.get("decision"),
            }
        else:
            customer_evidence = {"status": context.get("status"), "case_id": context.get("case_id")}

        prompt = (
            f"CUSTOMER QUERY:\n{query}\n\n"
            f"RECENT CHAT HISTORY:\n{history_text or '(No earlier messages)'}\n\n"
            f"CUSTOMER-APPROPRIATE CRM EVIDENCE (use only what is present):\n"
            f"{json.dumps(customer_evidence, ensure_ascii=False, default=str)}\n\n"
            "Respond as a customer-facing support agent. Be empathetic and direct."
        )
        result = await assistant.run(task=prompt)
        for message in reversed(result.messages):
            content = getattr(message, "content", None)
            source = getattr(message, "source", "")
            if isinstance(content, str) and content.strip() and source not in ("user", "system"):
                return content.strip()
        return customer_fallback_reply(query, context)
    finally:
        await model_client.close()



def decision_aware_customer_reply(query: str, context: dict[str, Any]) -> str | None:
    """Return an evidence-grounded answer when a recorded decision matters."""
    if context.get("status") != "found":
        return None

    decision = context.get("decision")
    if not decision:
        return None

    lowered = query.lower()
    decision_terms = (
        "compensation", "refund", "credit", "approved", "approval",
        "decision", "reimbursement", "money", "payment",
    )
    # Do not let a generic case-status query get hijacked by an existing approval.
    # Compensation decisions are authoritative only for compensation/payment/approval intents.
    if not any(term in lowered for term in decision_terms):
        return None

    case = context["case"]
    case_status = str(case.get("status", "Not recorded"))
    case_id = case.get("case_id", context.get("case_id", "your case"))
    currency = case.get("currency", decision.get("currency", "INR"))
    state = str(decision.get("decision", "PENDING")).upper()
    reason = str(decision.get("reason", "")).strip()
    amount = decision.get("amount")

    if state == "APPROVED":
        amount_text = (
            f"{currency} {float(amount):,.2f}".rstrip("0").rstrip(".")
            if isinstance(amount, (int, float))
            else "the recorded amount"
        )
        return (
            f"Update for **{case_id}**: your compensation request has been **approved** "
            f"by the Finance Manager for **{amount_text}**.\n\n"
            f"- **Case status:** {case_status}. The service issue is still tracked separately.\n"
            "- **Compensation status:** Approved.\n"
            "- **Credit/refund status:** Not yet processed. This demo records approval but does not execute real payments or account credits.\n\n"
            "We do not have a confirmed transaction-completion record, so we cannot say the refund or credit has been completed."
        )

    if state == "REJECTED":
        reason_line = f" Recorded reason: {reason}" if reason else ""
        return (
            f"Update for **{case_id}**: the Finance Manager has **rejected** the compensation request. "
            f"Case status remains **{case_status}** unless separately updated.{reason_line}\n\n"
            "This demo does not execute a refund or account credit."
        )

    return (
        f"Update for **{case_id}**: the compensation request is awaiting a Finance Manager decision. "
        f"The CRM case status is **{case_status}**. No refund or credit has been processed."
    )


def case_status_customer_reply(query: str, context: dict[str, Any]) -> str | None:
    """Answer straightforward case/technical status questions from CRM records."""
    if context.get("status") != "found":
        return None
    lowered = query.lower()
    case_terms = ("status", "ticket", "case", "outage", "internet", "service", "restored", "fixed", "resolve", "eta", "when")
    compensation_terms = ("compensation", "refund", "credit", "approved", "approval", "decision", "reimbursement", "payment")
    if not any(term in lowered for term in case_terms) or any(term in lowered for term in compensation_terms):
        return None

    case = context["case"]
    incidents = context.get("incidents", [])
    case_id = case.get("case_id", "your case")
    case_status = case.get("status", "Not recorded")
    issue = case.get("issue", "Issue not recorded")
    priority = case.get("priority", "Not recorded")
    if any(term in lowered for term in ("eta", "when", "restored", "fixed", "resolve")):
        incident = incidents[0] if incidents else {}
        service_status = incident.get("service_status", "Not available")
        notes = incident.get("technician_notes", "")
        return (
            f"**Case {case_id}** is currently **{case_status}** (priority: **{priority}**).\n\n"
            f"The latest IT record lists the service as **{service_status}**. {notes}\n\n"
            "A confirmed restoration ETA is not recorded, so I can't provide an exact date or time."
        )
    if any(term in lowered for term in ("cause", "why", "outage", "internet")):
        incident = incidents[0] if incidents else {}
        cause = incident.get("technician_notes", "No linked technical notes are available.")
        incident_id = incident.get("incident_id", "No incident ID recorded")
        return (
            f"**Case {case_id}** is **{case_status}** (priority: **{priority}**).\n\n"
            f"Issue: {issue}.\n\nIT record ({incident_id}): {cause}"
        )
    return (
        f"**Case {case_id}** is currently **{case_status}** with **{priority}** priority.\n\n"
        f"Issue: {issue}. The compensation decision, if any, is tracked separately from the technical case status."
    )

def ask_customer(query: str) -> str:
    case_id = extract_case_id(query) or st.session_state.get("active_case_id", "")
    if not case_id:
        return "Please include your case number, for example **CASE-2045**, so I can check the correct record."

    context = lookup_customer_context(case_id)
    if context.get("status") == "found":
        st.session_state.active_case_id = context["case"]["case_id"]

    # A saved human decision is authoritative. For compensation/status questions,
    # return a deterministic answer so the LLM cannot omit or misstate the decision.
    decision_reply = decision_aware_customer_reply(query, context)
    if decision_reply:
        return decision_reply

    status_reply = case_status_customer_reply(query, context)
    if status_reply:
        return status_reply

    try:
        return asyncio.run(
            generate_customer_reply(
                query=query,
                context=context,
                history=st.session_state.customer_messages,
            )
        )
    except Exception:
        return customer_fallback_reply(query, context)


def _last_agent_text(result) -> str:
    """Return the latest non-empty text message from an AutoGen run."""
    for message in reversed(getattr(result, "messages", [])):
        content = getattr(message, "content", None)
        source = getattr(message, "source", "")
        if isinstance(content, str) and content.strip() and source not in ("user", "system"):
            return content.strip()
    return "The agent completed without a text response."


def _employee_query_route(query: str) -> tuple[list[str], str]:
    """Choose the smallest sensible specialist set for an employee question."""
    q = query.lower()
    if any(term in q for term in ("incident", "outage", "restored", "restoration", "network", "technical", "connectivity", "service down")):
        return ["it_support", "customer_service"], "Technical incidents and service evidence"
    if any(term in q for term in ("compensation", "credit", "refund", "billing", "invoice", "payment", "amount", "calculate", "finance", "approval", "approved", "reject", "pending approval")):
        return ["customer_service", "finance", "administration"], "Compensation, billing, or approval"
    if any(term in q for term in ("critical case", "critical cases", "priority", "case list", "all cases", "open cases", "case status", "status of", "case-")):
        return ["customer_service"], "CRM cases and customer status"
    if any(term in q for term in ("account", "customer details", "customer list", "customer information", "validate")):
        return ["customer_service", "administration"], "Customer and account validation"
    return ["customer_service", "administration"], "General CRM question"


def _employee_data_context(query: str) -> dict[str, Any]:
    """Build a grounded, compact context from local CRM JSON and approval history."""
    data = load_data()
    cases = data.get("cases", data.get("support_cases", []))
    customers = data.get("customers", [])
    incidents = data.get("it_incidents", data.get("incidents", []))
    invoices = data.get("invoices", [])
    payments = data.get("payments", [])
    policies = data.get("policies", [])
    q = query.lower()
    case_id = extract_case_id(query)
    if case_id:
        matching_cases = [c for c in cases if str(c.get("case_id", "")).upper() == case_id]
        matching_incidents = [i for i in incidents if str(i.get("case_id", "")).upper() == case_id]
        customer_ids = {str(c.get("customer_id", "")) for c in matching_cases}
        matching_customers = [c for c in customers if str(c.get("customer_id", "")) in customer_ids]
        invoices = [x for x in invoices if str(x.get("customer_id", "")) in customer_ids]
        payments = [x for x in payments if str(x.get("customer_id", "")) in customer_ids]
        cases, incidents, customers = matching_cases, matching_incidents, matching_customers
    elif "critical" in q and ("case" in q or "cases" in q):
        cases = [c for c in cases if str(c.get("priority", "")).lower() == "critical"]
        case_ids = {str(c.get("case_id", "")).upper() for c in cases}
        incidents = [i for i in incidents if str(i.get("case_id", "")).upper() in case_ids]
        customer_ids = {str(c.get("customer_id", "")) for c in cases}
        customers = [c for c in customers if str(c.get("customer_id", "")) in customer_ids]
    elif "critical" in q and ("incident" in q or "incidents" in q):
        case_ids = {str(c.get("case_id", "")).upper() for c in cases if str(c.get("priority", "")).lower() == "critical"}
        incidents = [i for i in incidents if str(i.get("case_id", "")).upper() in case_ids or str(i.get("severity", "")).lower() == "critical" or str(i.get("priority", "")).lower() == "critical"]
        cases = [c for c in cases if str(c.get("case_id", "")).upper() in {str(i.get("case_id", "")).upper() for i in incidents}]
        customer_ids = {str(c.get("customer_id", "")) for c in cases}
        customers = [c for c in customers if str(c.get("customer_id", "")) in customer_ids]
    elif any(term in q for term in ("approval", "approved", "reject", "compensation", "credit", "refund")):
        # Keep all cases for cross-case approval questions; attach persisted human decisions separately.
        pass
    else:
        # For broad inventory questions, include all records from the local JSON knowledge source.
        pass
    decisions = read_decisions()
    if case_id:
        decisions = [d for d in decisions if str(d.get("case_id", "")).upper() == case_id]
    return {
        "cases": cases,
        "customers": customers,
        "it_incidents": incidents,
        "invoices": invoices,
        "payments": payments,
        "policies": policies,
        "finance_manager_decisions": decisions,
        "source": "Local CRM JSON records and saved approval_decisions.json; no live web search.",
    }


async def _run_employee_assistant(query: str) -> tuple[str, dict[str, dict[str, Any]], dict[str, Any]]:
    """Run routed AutoGen specialists plus the orchestrator and return real activity metadata."""
    import time
    from datetime import datetime

    def stamp() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    selected_agents, route_reason = _employee_query_route(query)
    context = _employee_data_context(query)
    labels = {
        "orchestrator": "CRM Orchestrator",
        "customer_service": "Customer Service",
        "it_support": "IT Support",
        "finance": "Finance",
        "administration": "Administration",
    }
    activity: dict[str, dict[str, Any]] = {}
    for key, label in labels.items():
        if key == "orchestrator":
            state, detail = "QUEUED", "Will consolidate the specialist response."
        elif key in selected_agents:
            state, detail = "QUEUED", f"Selected for: {route_reason}."
        else:
            state, detail = "SKIPPED", "Not required for this question; agent was not invoked."
        activity[key] = {"agent": label, "status": state, "detail": detail, "started_at": None, "finished_at": None, "duration_seconds": 0.0}

    model_client = create_model_client()
    try:
        agents = create_agents(model_client)
        specialist_outputs: dict[str, str] = {}
        for key in selected_agents:
            event = activity[key]
            event["status"] = "RUNNING"
            event["started_at"] = stamp()
            t0 = time.perf_counter()
            try:
                result = await agents[key].run(task=(
                    f"You are answering an internal employee's CRM question.\n"
                    f"QUESTION: {query}\n\nGROUNDING DATA (authoritative local JSON records):\n{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
                    "Answer directly and concisely using only supplied records. If a record field is absent, say it is not recorded. "
                    "Distinguish case priority/status, technical incident status, Finance Manager decision, and transaction execution. "
                    "Never invent case records, incident severity, contractual entitlement, or actions. Do not approve/reject/apply a credit."
                ))
                specialist_outputs[key] = _last_agent_text(result)
                event["status"] = "COMPLETED"
                event["detail"] = f"Answered using {labels[key]} and its available CRM tools/context."
            except Exception as exc:
                specialist_outputs[key] = f"Agent execution failed: {type(exc).__name__}: {exc}"
                event["status"] = "ERROR"
                event["detail"] = f"{type(exc).__name__}: {exc}"
            finally:
                event["finished_at"] = stamp()
                event["duration_seconds"] = round(time.perf_counter() - t0, 2)

        event = activity["orchestrator"]
        event["status"] = "RUNNING"
        event["started_at"] = stamp()
        t0 = time.perf_counter()
        try:
            final_result = await agents["orchestrator"].run(task=(
                f"Respond to this employee question: {query}\n\n"
                f"Authoritative local CRM data: {json.dumps(context, ensure_ascii=False, default=str)}\n\n"
                f"Selected specialist outputs: {json.dumps(specialist_outputs, ensure_ascii=False, default=str)}\n\n"
                "Give a clear employee-facing answer. Use bullets or a small table when useful. Never invent missing data. "
                "If asked for critical cases, identify cases whose case priority is Critical. Do not call an incident critical unless the incident itself has a recorded severity/priority or explain that criticality is inferred from the linked case. "
                "Keep case status, incident service status, Finance Manager decision, and credit/refund transaction status separate. "
                "Never approve, reject, or execute compensation."
            ))
            answer = _last_agent_text(final_result)
            event["status"] = "COMPLETED"
            event["detail"] = "Consolidated the selected specialist response into the employee-facing answer."
        except Exception as exc:
            event["status"] = "ERROR"
            event["detail"] = f"{type(exc).__name__}: {exc}"
            answer = "The CRM Orchestrator could not complete the answer. Please retry or use the investigation workflow."
        finally:
            event["finished_at"] = stamp()
            event["duration_seconds"] = round(time.perf_counter() - t0, 2)
        meta = {"route_reason": route_reason, "selected_agents": selected_agents + ["orchestrator"], "case_id": extract_case_id(query), "source": context.get("source")}
        return answer, activity, meta
    finally:
        await model_client.close()


def render_employee_agent_strip(activity: dict[str, dict[str, Any]]) -> None:
    """Compact horizontal five-agent strip for the employee workspace."""
    agent_info = [
        ("orchestrator", "CRM Orchestrator", "✦"),
        ("customer_service", "Customer Service", "◉"),
        ("it_support", "IT Support", "⌁"),
        ("finance", "Finance", "◇"),
        ("administration", "Administration", "▤"),
    ]
    state_style = {
        "COMPLETED": ("#E6F4EC", "#217A57", "Completed"),
        "RUNNING": ("#E5F0FC", "#245A8D", "Running"),
        "QUEUED": ("#F8EEDB", "#98651A", "Queued"),
        "ERROR": ("#FBE8E8", "#B4232F", "Failed"),
        "SKIPPED": ("#ECEFF2", "#66717C", "Skipped"),
        "IDLE": ("#ECEFF2", "#66717C", "Idle"),
    }
    cols = st.columns(5, gap="small")
    for col, (key, name, icon) in zip(cols, agent_info):
        event = activity.get(key, {})
        state = str(event.get("status", "IDLE")).upper()
        bg, fg, label = state_style.get(state, state_style["IDLE"])
        duration = event.get("duration_seconds")
        duration_text = f"{duration:.2f}s" if isinstance(duration, (int, float)) and state in ("COMPLETED", "ERROR") else "—"
        detail = str(event.get("detail", "No activity in this session."))
        if len(detail) > 76:
            detail = detail[:73] + "..."
        with col:
            st.markdown(
                f'<div style="height:142px;border:1px solid {BORDER};border-radius:13px;padding:10px 9px;background:{PANEL};box-shadow:0 3px 10px rgba(65,49,31,.035);">'
                f'<div style="font-size:.78rem;font-weight:800;line-height:1.25;min-height:34px;">{icon} {name}</div>'
                f'<div style="display:inline-block;margin:5px 0 7px;padding:3px 7px;border-radius:999px;background:{bg};color:{fg};font-size:.67rem;font-weight:800;">{label}</div>'
                f'<div style="font-size:.72rem;color:{MUTED};line-height:1.35;height:39px;overflow:hidden;">{detail}</div>'
                f'<div style="font-size:.7rem;font-weight:800;color:{fg};margin-top:5px;">{duration_text}</div>'
                '</div>', unsafe_allow_html=True
            )


def render_hero(eyebrow: str, title: str, accent: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="nx-hero">
          <div class="nx-eyebrow">{eyebrow}</div>
          <div class="nx-title">{title} <span>{accent}</span></div>
          <div class="nx-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_agent_card(name: str, icon: str, state: str, detail: str, duration: Any = None, started_at: str | None = None) -> None:
    state = (state or "NOT RUN").upper()
    css_map = {
        "COMPLETED": ("done", "✓ COMPLETED"),
        "SKIPPED": ("skipped", "↷ SKIPPED"),
        "RUNNING": ("running", "● RUNNING"),
        "QUEUED": ("wait", "○ QUEUED"),
        "PENDING": ("wait", "○ PENDING"),
        "ERROR": ("error", "! ERROR"),
        "NOT RUN": ("skipped", "○ NOT RUN"),
    }
    css_class, label = css_map.get(state, ("wait", state))
    duration_text = f" · {duration:.2f}s" if isinstance(duration, (int, float)) else ""
    timestamp_text = f"<div class='nx-muted' style='font-size:.75rem;margin-top:4px;'>Started: {started_at}</div>" if started_at else ""
    st.markdown(
        f"""
        <div class="nx-agent {css_class}">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">
            <div class="nx-agent-name">{icon} &nbsp; {name}</div>
            <div class="nx-agent-state">{label}{duration_text}</div>
          </div>
          <div class="nx-muted" style="margin-top:7px;">{detail}</div>
          {timestamp_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Header and navigation
# ---------------------------------------------------------------------
# Navigation first, followed by a compact CRM product identity header.
portal_options = ["Home", "Customer Portal", "Employee Portal"]
current = st.session_state.portal if st.session_state.portal in portal_options else "Home"
selected = st.radio(
    "Navigate",
    portal_options,
    horizontal=True,
    index=portal_options.index(current),
    label_visibility="collapsed",
)
st.session_state.portal = selected

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown(
        '<div class="nx-eyebrow">NEXATEL BUSINESS SERVICES</div><div class="nx-brand-title">CRM · CUSTOMER RELATIONSHIP MANAGEMENT</div><div class="nx-brand-sub">Customer Support &amp; Intelligent Service Operations</div>',
        unsafe_allow_html=True,
    )
with header_right:
    st.markdown(
        f'<div style="text-align:right;color:{MUTED};font-size:.8rem;padding-top:6px;">● DEMO ENVIRONMENT<br>{formatted_now()}</div>',
        unsafe_allow_html=True,
    )
st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------
if selected == "Home":
    # Compact home page: the CRM header already provides the product identity.
    st.write("")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(
            """
            <div class="nx-card">
              <div class="nx-eyebrow">01 · CUSTOMER EXPERIENCE</div>
              <div style="font-size:2rem;margin:.2rem 0 .6rem 0;">◉</div>
              <div class="nx-card-title" style="font-size:1.35rem;">Customer Portal</div>
              <div class="nx-muted">A conversational support experience. Ask about an existing case, understand what is pending, and receive grounded updates without searching through forms.</div>
              <div style="margin-top:16px;"><span class="nx-chip">Chat history</span><span class="nx-chip">Case status</span><span class="nx-chip">Follow-up questions</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Customer Portal  →", key="home_customer", type="primary", use_container_width=True):
            st.session_state.portal = "Customer Portal"
            st.rerun()
    with c2:
        st.markdown(
            """
            <div class="nx-card">
              <div class="nx-eyebrow">02 · SERVICE OPERATIONS</div>
              <div style="font-size:2rem;margin:.2rem 0 .6rem 0;">⌘</div>
              <div class="nx-card-title" style="font-size:1.35rem;">Employee Portal</div>
              <div class="nx-muted">A multi-agent investigation desk with department findings, evidence, compensation recommendations, and a human approval checkpoint.</div>
              <div style="margin-top:16px;"><span class="nx-chip">AutoGen workflow</span><span class="nx-chip">Agent activity</span><span class="nx-chip">Human approval</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Employee Portal  →", key="home_employee", use_container_width=True):
            st.session_state.portal = "Employee Portal"
            st.rerun()

    st.write("")
    st.markdown("### A connected resolution journey")
    steps = st.columns(4)
    journey = [
        ("01", "Customer asks", "A question enters the support conversation."),
        ("02", "AI investigates", "CRM tools retrieve case and incident evidence."),
        ("03", "Employee reviews", "Specialists and the orchestrator prepare findings."),
        ("04", "Human decides", "An authorized manager records the decision."),
    ]
    for col, (number, title, desc) in zip(steps, journey):
        with col:
            st.markdown(
                f'<div class="nx-card"><div class="nx-eyebrow">{number}</div><div class="nx-card-title">{title}</div><div class="nx-muted">{desc}</div></div>',
                unsafe_allow_html=True,
            )
    st.caption("Demo notice: sample CRM data is used. Customer authentication and real payment processing are not implemented.")


# ---------------------------------------------------------------------
# Customer portal: short-term conversational memory
# ---------------------------------------------------------------------
elif selected == "Customer Portal":
    render_hero(
        "CUSTOMER PORTAL · SUPPORT ASSISTANT",
        "How can we help",
        "today?",
        "Ask a question about your case. The assistant uses the current CRM records and remembers recent messages during this active session.",
    )
    st.write("")
    with st.container(border=True):
        top_a, top_b = st.columns([3, 1])
        with top_a:
            st.markdown("**NexaTel Support Assistant**")
            st.caption("Case-aware assistance · Recent conversation memory")
        with top_b:
            if st.session_state.active_case_id:
                st.markdown(f'<span class="nx-chip">ACTIVE CASE · {st.session_state.active_case_id}</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="nx-chip">READY FOR YOUR CASE ID</span>', unsafe_allow_html=True)

        chat_area = st.container(height=430, border=False)
        with chat_area:
            if not st.session_state.customer_messages:
                with st.chat_message("assistant"):
                    st.markdown(
                        "Welcome to NexaTel Support. I can help you check a ticket, understand the latest recorded status, or ask about a compensation request.\n\n"
                        "To begin, enter your case number—for example, **CASE-2045**."
                    )
            for message in st.session_state.customer_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        prompt = st.chat_input("Enter your query… e.g. What is the status of CASE-2045?")
        chat_a, chat_b = st.columns([1, 1])
        with chat_a:
            if st.button("Clear conversation memory", use_container_width=True):
                st.session_state.customer_messages = []
                st.session_state.active_case_id = ""
                st.rerun()
        with chat_b:
            st.caption("Memory is temporary and scoped to this browser session.")

    if prompt:
        st.session_state.customer_messages.append({"role": "user", "content": prompt})
        with st.spinner("Checking CRM records and preparing a response…"):
            reply = ask_customer(prompt)
        st.session_state.customer_messages.append({"role": "assistant", "content": reply})
        st.rerun()

    st.write("")
    st.markdown("**Try asking**")
    quick_cols = st.columns(3)
    quick_prompts = [
        "What is the status of CASE-2045?",
        "When will my service be restored?",
        "What is happening with my compensation?",
    ]
    for col, quick in zip(quick_cols, quick_prompts):
        with col:
            if st.button(quick, key=f"quick_{quick}", use_container_width=True):
                st.session_state.customer_messages.append({"role": "user", "content": quick})
                with st.spinner("Checking the case records…"):
                    reply = ask_customer(quick)
                st.session_state.customer_messages.append({"role": "assistant", "content": reply})
                st.rerun()


# ---------------------------------------------------------------------
# Employee portal: case investigation and human-in-the-loop approval
# ---------------------------------------------------------------------
elif selected == "Employee Portal":
    render_hero(
        "EMPLOYEE PORTAL · SERVICE OPERATIONS",
        "Investigation",
        "control room.",
        "Run the cross-functional AutoGen workflow, inspect evidence, ask the CRM assistant, and record a Finance Manager decision with an audit reason.",
    )
    st.write("")
    st.markdown("### Agent activity at a glance")
    st.caption("This strip reflects the most recent employee chat or investigation run. Idle/skipped agents are not represented as having executed.")
    initial_activity = st.session_state.latest_agent_activity or {}
    if not initial_activity:
        initial_activity = {key: {"status": "IDLE", "detail": "No activity in this session.", "duration_seconds": 0.0} for key in ("orchestrator", "customer_service", "it_support", "finance", "administration")}
    render_employee_agent_strip(initial_activity)
    st.write("")

    cases = get_cases()
    case_ids = [str(item.get("case_id")) for item in cases if item.get("case_id")]
    if not case_ids:
        case_ids = ["CASE-2045"]

    selector_col, scope_col, run_col, time_col = st.columns([1.5, 2, 1.2, 2])
    with selector_col:
        chosen_case = st.selectbox(
            "CRM case",
            case_ids,
            index=case_ids.index(st.session_state.investigation_case_id)
            if st.session_state.investigation_case_id in case_ids else 0,
        )
    with scope_col:
        chosen_scope = st.selectbox(
            "Investigation scope",
            ["Full investigation", "Technical status", "Compensation review", "Account and case validation"],
            help="Different queries activate only the agents needed for that task.",
        )
    with run_col:
        st.write("")
        run_clicked = st.button("Run workflow", type="primary", use_container_width=True)
    with time_col:
        st.markdown(
            f'<div class="nx-stat"><div class="nx-stat-label">Workspace time</div><div style="font-size:1rem;font-weight:800;margin-top:6px;">{formatted_now()}</div><div class="nx-muted">Local machine time</div></div>',
            unsafe_allow_html=True,
        )

    if run_clicked:
        st.session_state.investigation = None
        st.session_state.investigation_case_id = chosen_case
        try:
            with st.status("Running CRM investigation workflow…", expanded=True) as status:
                st.write("1 · Validating case and customer records")
                st.write("2 · Retrieving incident, billing and policy evidence")
                st.write(f"3 · Executing agents selected for: {chosen_scope}")
                st.write("4 · Recording actual agent start/end times and durations")
                st.write("5 · Asking the CRM Orchestrator to consolidate returned findings")
                result = run_investigation(chosen_case, chosen_scope)
                status.update(label="Investigation run finished", state="complete", expanded=False)
            st.session_state.investigation = result
            st.session_state.last_investigation_at = formatted_now()
            st.session_state.investigation_case_id = chosen_case
            if result.get("agent_activity"):
                st.session_state.latest_agent_activity = result["agent_activity"]
            st.rerun()
        except Exception as exc:
            st.error(f"Investigation failed: {exc}")

    st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Employee AI Assistant")
    st.caption("Ask questions about CRM cases, incidents, billing, compensation, or pending approvals. Answers are grounded in the local JSON records and saved Finance Manager decisions.")
    with st.expander("Try a question", expanded=not bool(st.session_state.employee_messages)):
        sample_cols = st.columns(3)
        sample_questions = ["What are the critical cases?", "What are the critical incidents?", "Which cases need Finance Manager approval?"]
        for idx, (col, question) in enumerate(zip(sample_cols, sample_questions)):
            with col:
                if st.button(question, key=f"employee_sample_{idx}", use_container_width=True):
                    st.session_state.employee_pending_prompt = question
    for message in st.session_state.employee_messages:
        with st.chat_message(message.get("role", "assistant")):
            st.markdown(message.get("content", ""))
            if message.get("role") == "assistant" and message.get("meta"):
                meta = message["meta"]
                st.caption(f"Responding agent: CRM Orchestrator · Specialists used: {', '.join(meta.get('agent_labels', []))} · Route: {meta.get('route_reason', 'CRM question')}")
    employee_prompt = st.chat_input("Ask the CRM assistant…", key="employee_chat_input")
    pending_prompt = st.session_state.pop("employee_pending_prompt", None)
    employee_prompt = employee_prompt or pending_prompt
    if employee_prompt:
        st.session_state.employee_messages.append({"role": "user", "content": employee_prompt})
        with st.chat_message("user"):
            st.markdown(employee_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Selecting specialist agents and checking CRM records…"):
                try:
                    answer, chat_activity, chat_meta = asyncio.run(_run_employee_assistant(employee_prompt))
                    st.session_state.employee_agent_activity = chat_activity
                    st.session_state.latest_agent_activity = chat_activity
                    chat_meta["agent_labels"] = [chat_activity[key]["agent"] for key in chat_meta.get("selected_agents", []) if key in chat_activity and key != "orchestrator"]
                    st.session_state.employee_last_answer_meta = chat_meta
                    st.markdown(answer)
                    st.caption(f"Responding agent: CRM Orchestrator · Specialists used: {', '.join(chat_meta['agent_labels']) or 'None'} · Route: {chat_meta.get('route_reason', 'CRM question')}")
                    st.session_state.employee_messages.append({"role": "assistant", "content": answer, "meta": chat_meta})
                except Exception as exc:
                    err = f"I couldn't answer this question because the assistant workflow failed: {type(exc).__name__}: {exc}"
                    st.error(err)
                    st.session_state.employee_messages.append({"role": "assistant", "content": err})
        st.rerun()
    if st.session_state.employee_messages:
        clear_col, source_col = st.columns([1, 4])
        with clear_col:
            if st.button("Clear employee chat", key="clear_employee_chat"):
                st.session_state.employee_messages = []
                st.session_state.employee_agent_activity = {}
                st.session_state.latest_agent_activity = {}
                st.session_state.employee_last_answer_meta = None
                st.rerun()
        with source_col:
            st.caption("Employee chat memory is session-only. It does not modify investigation results or Finance Manager decisions.")

    result = st.session_state.investigation
    if result and result.get("case_id") == st.session_state.investigation_case_id:
        case_id = result["case_id"]
        customer_name = result.get("customer", "Unknown customer")
        findings = result.get("findings", {})
        approval = latest_decision(case_id)
        approval_status = approval.get("decision") if approval else result.get("approval_status", "PENDING_FINANCE_MANAGER")
        proposal = result.get("proposed_credit", {})
        proposed_amount = proposal.get("proposed_credit") if isinstance(proposal, dict) else None
        currency = result.get("currency", "INR")
        request_amount = result.get("requested_compensation")

        st.write("")
        metrics = st.columns(4)
        metrics[0].metric("Case", case_id)
        metrics[1].metric("Priority", "Critical" if "critical" in str(findings.get("customer_service", "")).lower() else "Review")
        metrics[2].metric("Requested", f"{currency} {request_amount:,}" if isinstance(request_amount, (int, float)) else "See case")
        metrics[3].metric("Proposed", f"{currency} {proposed_amount:,.0f}" if isinstance(proposed_amount, (int, float)) else "Not available")

        meta_a, meta_b, meta_c = st.columns([2, 1, 2])
        with meta_a:
            st.markdown(f"**{customer_name}**")
            st.caption(f"Customer · Case status: {result.get('case_status', 'Not recorded')}")
        with meta_b:
            st.markdown(f'<span class="nx-chip">● {approval_status}</span>', unsafe_allow_html=True)
        with meta_c:
            st.caption(f"Last investigation: {st.session_state.last_investigation_at or 'Not recorded'}")
        st.caption(result.get("scope_description", ""))

        left, right = st.columns([1.1, 1.5], gap="large")
        with left:
            st.markdown("### Agent activity")
            st.caption("Statuses come from the workflow execution log. Skipped agents were not invoked for this scope.")
            st.caption(f"Scope: {result.get('scope', 'Full investigation')} · Total elapsed: {result.get('total_duration_seconds', 0):.2f}s")
            agent_info = [
                ("orchestrator", "CRM Orchestrator", "✦", "Consolidates the findings returned by selected specialists."),
                ("customer_service", "Customer Service", "◉", "Checks customer identity, case issue and priority."),
                ("it_support", "IT Support", "⌁", "Checks incident evidence and service status."),
                ("finance", "Finance", "◇", "Checks billing, compensation policy and illustrative credit."),
                ("administration", "Administration", "▤", "Checks account and approval requirements."),
            ]
            activity = result.get("agent_activity", {})
            for key, name, icon, detail in agent_info:
                event = activity.get(key, {})
                state = event.get("status", "NOT RUN")
                render_agent_card(
                    name, icon, state,
                    event.get("detail", detail),
                    event.get("duration_seconds"),
                    event.get("started_at"),
                )
            with st.expander("Workflow execution log"):
                for key, name, icon, detail in agent_info:
                    event = activity.get(key, {})
                    st.markdown(f"**{name} — {event.get('status', 'NOT RUN')}**")
                    st.caption(f"Start: {event.get('started_at') or 'Not started'} · End: {event.get('finished_at') or 'Not finished'} · Duration: {event.get('duration_seconds', 0)}s")
                    st.write(event.get("detail", detail))

        with right:
            st.markdown("### Investigation report")
            st.caption("Consolidated evidence and recommendations")
            st.markdown(result.get("resolution_report", "No report was returned."))
            with st.expander("View department findings"):
                for title, key in [
                    ("Customer Service", "customer_service"),
                    ("IT Support", "it_support"),
                    ("Finance", "finance"),
                    ("Administration", "administration"),
                ]:
                    st.markdown(f"**{title}**")
                    st.write(findings.get(key, "No findings available."))
                    st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)

        st.write("")
        st.markdown("### Finance Manager decision")
        st.markdown(
            '<div class="nx-card"><div class="nx-eyebrow">HUMAN-IN-THE-LOOP CHECKPOINT</div>'
            '<div class="nx-card-title">Review before any credit is applied</div>'
            '<div class="nx-muted">The proposed amount is illustrative only. Confirm contractual eligibility and supporting evidence before recording a decision. This demo records the decision but does not execute a real refund or account credit.</div></div>',
            unsafe_allow_html=True,
        )

        if approval and approval.get("decision") in ("APPROVED", "REJECTED"):
            st.success(
                f"Latest decision: {approval['decision']} · {approval.get('decided_at', '')}"
            )
            st.write(f"**Reviewer:** {approval.get('reviewer', 'Not recorded')}")
            st.write(f"**Reason:** {approval.get('reason', 'Not recorded')}")
            if approval.get("decision") == "APPROVED":
                st.info("Approval recorded. This does not mean a refund or credit transaction has been executed.")
        else:
            with st.form(f"approval_form_{case_id}"):
                reviewer = st.text_input("Finance Manager / reviewer", placeholder="Enter reviewer name")
                decision = st.radio("Decision", ["Approve proposed credit", "Reject request"], horizontal=True)
                reason = st.text_area(
                    "Decision reason (required)",
                    placeholder="Explain the evidence and rationale for this decision…",
                    height=100,
                )
                confirm = st.checkbox("I have reviewed the evidence and understand this demo does not execute a real transaction.")
                submitted = st.form_submit_button("Record decision", type="primary", use_container_width=True)

                if submitted:
                    if not reviewer.strip():
                        st.error("Enter the reviewer name.")
                    elif not reason.strip():
                        st.error("A decision reason is required.")
                    elif not confirm:
                        st.error("Confirm that you reviewed the evidence before recording the decision.")
                    else:
                        decision_value = "APPROVED" if decision == "Approve proposed credit" else "REJECTED"
                        record = {
                            "case_id": case_id,
                            "customer": customer_name,
                            "decision": decision_value,
                            "amount": proposed_amount if decision_value == "APPROVED" else None,
                            "currency": currency,
                            "reviewer": reviewer.strip(),
                            "reason": reason.strip(),
                            "decided_at": now_local().isoformat(timespec="seconds"),
                            "recorded_at_display": formatted_now(),
                            "transaction_status": "NOT_EXECUTED",
                            "source": "Streamlit demo",
                        }
                        try:
                            write_decision(record)
                            st.session_state.approval_feedback = f"{decision_value} decision saved for {case_id}."
                            st.success(st.session_state.approval_feedback)
                            st.rerun()
                        except OSError as exc:
                            st.error(f"Could not save the decision: {exc}")

        with st.expander("Decision audit history"):
            history = [d for d in read_decisions() if d.get("case_id", "").upper() == case_id.upper()]
            if history:
                for item in reversed(history):
                    st.markdown(
                        f"**{item.get('decision')}** · {item.get('decided_at', '')}  \n"
                        f"Reviewer: {item.get('reviewer', 'Unknown')}  \n"
                        f"Reason: {item.get('reason', 'Not recorded')}  \n"
                        f"Transaction status: {item.get('transaction_status', 'Unknown')}"
                    )
                    st.markdown('<div class="nx-divider"></div>', unsafe_allow_html=True)
            else:
                st.caption("No decision has been recorded for this case.")
    else:
        st.markdown(
            '<div class="nx-card"><div class="nx-eyebrow">READY FOR INVESTIGATION</div>'
            '<div class="nx-card-title">Select a case and run the workflow</div>'
            '<div class="nx-muted">The agent activity panel will highlight roles with returned findings. No case is investigated until you click Run investigation.</div></div>',
            unsafe_allow_html=True,
        )

    st.write("")
    st.caption("Demo safeguards: decision records are local JSON data; reviewer identity is self-entered, not authenticated. Do not use this prototype to authorize real payments.")


st.markdown(
    '<div class="nx-foot">NexaTel Support Hub · AutoGen CRM prototype · Dark slate / glacier blue / warm sand</div>',
    unsafe_allow_html=True,
)
