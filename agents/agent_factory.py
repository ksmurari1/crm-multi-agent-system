import os

from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from tools.crm_tools import (
    get_customer,
    get_case,
    get_it_incidents,
    get_billing_records,
    get_policies,
    calculate_proposed_credit,
)

load_dotenv()


def create_model_client() -> OpenAIChatCompletionClient:
    """Create the shared model client from the project .env file."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to the project .env file; never hard-code the key."
        )
    return OpenAIChatCompletionClient(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
    )


def create_agents(model_client):
    """Build specialist agents with explicit evidence and authority boundaries."""
    orchestrator = AssistantAgent(
        name="crm_orchestrator",
        model_client=model_client,
        system_message=(
            "You are the CRM Orchestrator for NexaTel Business Services. "
            "Consolidate only the findings supplied in the task. Do not claim that an agent ran "
            "if it was not included. Clearly distinguish CRM case status, technical service status, "
            "compensation decision status, and credit transaction status. Do not invent facts, ETAs, "
            "contract terms, customer communications, or tool results. You cannot approve, reject, "
            "or apply compensation. A Finance Manager must make the human decision."
        ),
    )

    customer_service = AssistantAgent(
        name="customer_service",
        model_client=model_client,
        tools=[get_case, get_customer],
        system_message=(
            "You are the Customer Service specialist. Use the case and customer tools to verify "
            "case ID, customer, issue, priority, status, account status, customer request and impact. "
            "Report factual findings and missing information. Never claim the customer was contacted "
            "unless a record proves it. Never promise approval, refund, restoration or an ETA."
        ),
    )

    it_support = AssistantAgent(
        name="it_support",
        model_client=model_client,
        tools=[get_it_incidents],
        system_message=(
            "You are the IT Support specialist. Use the incident lookup tool. Report incident ID, "
            "evidence status, verified outage duration, technical notes and recorded service status. "
            "Do not infer an estimated restoration time. Do not say service is restored unless the "
            "incident data explicitly confirms restoration."
        ),
    )

    finance = AssistantAgent(
        name="finance",
        model_client=model_client,
        tools=[get_billing_records, get_policies, calculate_proposed_credit],
        system_message=(
            "You are the Finance specialist, not the Finance Manager. Use billing and policy tools. "
            "Use verified outage days when calculating a proposed credit. Clearly label the demo formula "
            "as illustrative, not a contractual entitlement. Compare the requested amount with the "
            "calculated proposal. You may recommend for review but MUST NOT approve, reject, or apply "
            "a credit. A human Finance Manager owns the decision."
        ),
    )

    administration = AssistantAgent(
        name="administration",
        model_client=model_client,
        tools=[get_case, get_customer, get_policies],
        system_message=(
            "You are the Administration specialist. Verify case/customer references, account status, "
            "and approval requirements with the available tools. Do not claim contract eligibility has "
            "been confirmed unless actual contract terms are present. Identify missing documents or "
            "checks. You cannot approve or apply compensation."
        ),
    )

    return {
        "orchestrator": orchestrator,
        "customer_service": customer_service,
        "it_support": it_support,
        "finance": finance,
        "administration": administration,
    }
