
import json
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "crm_data.json"


def load_data() -> dict[str, Any]:
    """Load the fictional CRM dataset."""
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_customer(customer_id: str) -> dict[str, Any]:
    """Retrieve a customer by ID."""
    data = load_data()
    for customer in data["customers"]:
        if customer["customer_id"] == customer_id:
            return customer
    return {"status": "not_found", "customer_id": customer_id}



def get_case(case_id: str) -> dict[str, Any]:
    """Retrieve a support case and its related customer, case-insensitively."""
    data = load_data()
    normalized_id = case_id.strip().upper()

    for case in data["support_cases"]:
        if case["case_id"].upper() == normalized_id:
            customer = next(
                (
                    item for item in data["customers"]
                    if item["customer_id"] == case["customer_id"]
                ),
                None,
            )
            return {"case": case, "customer": customer}

    return {"status": "not_found", "case_id": normalized_id}


def get_it_incidents(case_id: str) -> dict[str, Any]:
    """Retrieve IT incidents associated with a support case."""
    data = load_data()
    incidents = [
        incident for incident in data["it_incidents"]
        if incident["case_id"] == case_id
    ]
    return {
        "case_id": case_id,
        "incidents": incidents,
        "count": len(incidents),
    }


def get_billing_records(customer_id: str) -> dict[str, Any]:
    """Retrieve invoices and payments belonging to a customer."""
    data = load_data()

    invoices = [
        invoice for invoice in data["invoices"]
        if invoice["customer_id"] == customer_id
    ]
    invoice_ids = {invoice["invoice_id"] for invoice in invoices}

    payments = [
        payment for payment in data["payments"]
        if payment["customer_id"] == customer_id
        and payment["invoice_id"] in invoice_ids
    ]

    return {
        "customer_id": customer_id,
        "invoices": invoices,
        "payments": payments,
    }


def get_policies(topic: str = "") -> dict[str, Any]:
    """Retrieve policies relevant to a topic."""
    data = load_data()
    query = topic.casefold().strip()

    policies = [
        policy for policy in data["policies"]
        if not query
        or query in policy["topic"].casefold()
        or query in policy["rule"].casefold()
    ]

    return {"policies": policies, "count": len(policies)}


def calculate_proposed_credit(
    customer_id: str,
    verified_outage_days: int,
) -> dict[str, Any]:
    """Calculate a proposed credit; never approves or applies it."""
    if verified_outage_days < 0:
        return {"status": "invalid_input", "reason": "Outage days cannot be negative."}

    data = load_data()
    customer = next(
        (
            item for item in data["customers"]
            if item["customer_id"] == customer_id
        ),
        None,
    )

    if customer is None:
        return {"status": "not_found", "customer_id": customer_id}

    monthly_fee = customer["monthly_fee"]
    proposed_credit = round(monthly_fee / 30 * verified_outage_days, 2)

    return {
        "status": "calculated",
        "customer_id": customer_id,
        "monthly_fee": monthly_fee,
        "verified_outage_days": verified_outage_days,
        "proposed_credit": proposed_credit,
        "currency": customer["currency"],
        "note": "Illustrative calculation only; Finance Manager approval is required.",
    }
