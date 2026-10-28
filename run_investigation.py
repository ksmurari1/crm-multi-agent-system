
from core.workflow import run_investigation


if __name__ == "__main__":
    case_id = input("Enter CRM case ID (e.g. CASE-2045): ").strip()

    result = run_investigation(case_id)

    print("\n" + "=" * 70)
    print("CRM MULTI-AGENT INVESTIGATION")
    print("=" * 70)

    if result["status"] != "investigated":
        print(result)
    else:
        print(f"Case: {result['case_id']}")
        print(f"Customer: {result['customer']}")
        print(f"Approval: {result['approval_status']}")

        print("\n--- SPECIALIST FINDINGS ---")
        for agent, finding in result["findings"].items():
            print(f"\n[{agent.upper()}]\n{finding}")

        print("\n--- FINAL RESOLUTION REPORT ---")
        print(result["resolution_report"])
