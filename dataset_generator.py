"""
dataset_generator.py
--------------------
Generates a complete synthetic enterprise dataset for the RAG demo.
Creates PDFs, CSVs, JSON logs, metadata, access policies, and user-role mappings.
Run this ONCE before ingestion to populate the data/ folder.
"""

import os
import json
import csv
import random
from datetime import datetime, timedelta
from fpdf import FPDF, XPos, YPos


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def save_json(path: str, data) -> None:
    """Write data to a JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def random_date(start_year: int = 2023, end_year: int = 2024) -> str:
    """Return a random ISO date string."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")


def _clean(text: str) -> str:
    """Replace characters outside latin-1 for fpdf2 core fonts."""
    chars = {"\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
             "\u201c": '"', "\u201d": '"', "\u2026": "..."}
    for ch, rep in chars.items():
        text = text.replace(ch, rep)
    return text


# ─────────────────────────────────────────────
# PDF Generation
# ─────────────────────────────────────────────

def create_pdf(filepath: str, title: str, sections: list) -> None:
    """Create a multi-section PDF using fpdf2."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", style="B", size=18)
    pdf.cell(0, 12, _clean(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(6)

    for heading, body in sections:
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.cell(0, 10, _clean(heading), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 7, _clean(body))
        pdf.ln(4)

    pdf.output(filepath)


def generate_pdfs(pdf_dir: str) -> None:
    """Generate three enterprise PDF documents."""

    create_pdf(
        filepath=os.path.join(pdf_dir, "finance_report.pdf"),
        title="Acme Corp - Q2 2024 Finance Report",
        sections=[
            ("Executive Summary",
             "Total revenue for Q2 2024 reached $18.4 million, representing a 12% year-over-year "
             "increase. Net profit margin improved to 21% driven by operational efficiencies. "
             "EBITDA stood at $4.2 million, up from $3.6 million in Q2 2023."),
            ("Revenue Breakdown",
             "Product sales contributed $11.2M (61%), professional services $4.8M (26%), "
             "and subscription licenses $2.4M (13%). The enterprise segment grew 18% quarter-over-"
             "quarter, while SMB revenue remained flat at $3.1M."),
            ("Expenditure Analysis",
             "Operating expenses totalled $14.5M. R&D spend was $3.2M (22% of revenue), "
             "Sales & Marketing $4.1M (28%), and G&A $2.8M (19%). Cost of goods sold was $4.4M."),
            ("Cash Flow Statement",
             "Free cash flow for Q2 was $2.9M. Capital expenditure amounted to $0.8M primarily "
             "for infrastructure upgrades. The company holds $12.6M in cash reserves."),
            ("Forecast Q3 2024",
             "Management projects Q3 revenue of $19.5-$20.2M assuming continued enterprise "
             "growth. Key risks include supply-chain delays and potential FX headwinds in EMEA."),
        ],
    )

    create_pdf(
        filepath=os.path.join(pdf_dir, "hr_policy.pdf"),
        title="Acme Corp - HR Policy Handbook 2024",
        sections=[
            ("Leave Policy",
             "All full-time employees are entitled to 20 days of annual leave per calendar year. "
             "Unused leave (up to 10 days) can be carried forward. Maternity leave is 26 weeks "
             "fully paid; paternity leave is 4 weeks fully paid."),
            ("Employee Records & Privacy",
             "Personal employee records are classified CONFIDENTIAL. Access is restricted to HR "
             "personnel and direct line managers. Records include employment history, performance "
             "reviews, compensation details, and disciplinary actions."),
            ("Performance Review Cycle",
             "Bi-annual reviews are conducted in June and December. Employees receive ratings on "
             "a 1-5 scale across five competencies. Ratings directly influence bonus allocation "
             "and promotion decisions."),
            ("Code of Conduct",
             "All employees must uphold ethical standards including respect, integrity, and "
             "confidentiality. Violations should be reported to hr@acmecorp.com. Retaliation "
             "against reporters is strictly prohibited."),
            ("Recruitment Policy",
             "Open positions must be approved by department heads and HR. Internal candidates are "
             "given a two-week priority window before external advertising. Referral bonuses of "
             "$2,000 are paid after 90-day probation completion."),
        ],
    )

    create_pdf(
        filepath=os.path.join(pdf_dir, "security_audit.pdf"),
        title="Acme Corp - Annual Security Audit Report 2024",
        sections=[
            ("Audit Scope",
             "This audit covers all production systems, network infrastructure, and cloud "
             "environments operated by Acme Corp between January 1 and June 30, 2024. "
             "Third-party penetration testing was performed by CyberShield LLC."),
            ("Critical Findings",
             "Three critical vulnerabilities were identified: (1) CVE-2024-1234 in the legacy "
             "API gateway allowing unauthenticated access; (2) unencrypted S3 bucket storing "
             "PII data; (3) default credentials on two internal database servers."),
            ("Remediation Status",
             "CVE-2024-1234 was patched within 48 hours. S3 encryption was enabled on "
             "June 15. Database credentials were rotated on June 20. All critical findings "
             "are now CLOSED. Two medium findings remain open with target date August 31."),
            ("Security Posture",
             "Overall security posture improved from Moderate to Strong. MFA adoption "
             "reached 97% across all user accounts. Endpoint detection and response (EDR) "
             "is deployed on 100% of managed devices."),
            ("Recommendations",
             "1. Implement zero-trust network segmentation by Q4 2024. "
             "2. Migrate legacy API gateway to OAuth 2.0. "
             "3. Conduct quarterly security awareness training. "
             "4. Automate SIEM alert triage with AI-assisted playbooks."),
        ],
    )

    print("  PDFs generated.")


# ─────────────────────────────────────────────
# CSV Generation
# ─────────────────────────────────────────────

def generate_csvs(csv_dir: str) -> None:
    """Generate three enterprise CSV files."""
    departments = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Operations"]
    first_names = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank",
                   "Iris", "Jack", "Karen", "Leo", "Mona", "Ned", "Olivia", "Paul"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                  "Miller", "Davis", "Wilson", "Taylor"]

    # 1. Employee Records
    with open(os.path.join(csv_dir, "employee_records.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["employee_id", "name", "department", "role", "salary",
                         "hire_date", "leave_balance", "performance_rating", "status"])
        for i in range(1, 41):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            dept = random.choice(departments)
            salary = random.randint(55_000, 140_000)
            rating = round(random.uniform(2.5, 5.0), 1)
            writer.writerow([
                f"EMP{i:04d}", name, dept,
                random.choice(["Engineer", "Manager", "Analyst", "Director", "Lead"]),
                salary, random_date(2019, 2023),
                random.randint(0, 20), rating,
                random.choice(["Active", "Active", "Active", "On Leave"]),
            ])

    # 2. Finance Transactions
    categories = ["Vendor Payment", "Salary Disbursement", "Software License",
                  "Travel Reimbursement", "Equipment Purchase", "Consulting Fee"]
    with open(os.path.join(csv_dir, "finance_transactions.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["txn_id", "date", "category", "department", "amount_usd",
                         "approved_by", "status", "invoice_ref"])
        for i in range(1, 61):
            writer.writerow([
                f"TXN{i:05d}", random_date(), random.choice(categories),
                random.choice(departments), round(random.uniform(500, 85_000), 2),
                f"MGR{random.randint(1,10):03d}",
                random.choice(["Approved", "Approved", "Pending", "Rejected"]),
                f"INV-2024-{i:04d}",
            ])

    # 3. Operations Metrics
    with open(os.path.join(csv_dir, "operations_metrics.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["week", "region", "uptime_pct", "incidents", "mttr_hours",
                         "tickets_opened", "tickets_closed", "sla_compliance_pct"])
        regions = ["US-East", "US-West", "EMEA", "APAC"]
        for week in range(1, 27):
            for region in regions:
                writer.writerow([
                    f"2024-W{week:02d}", region,
                    round(random.uniform(99.1, 99.99), 3),
                    random.randint(0, 8),
                    round(random.uniform(0.5, 6.0), 2),
                    random.randint(10, 80),
                    random.randint(8, 78),
                    round(random.uniform(91.0, 99.5), 1),
                ])

    print("  CSVs generated.")


# ─────────────────────────────────────────────
# JSON Log Generation
# ─────────────────────────────────────────────

def generate_json_logs(log_dir: str) -> None:
    """Generate three JSON log files."""

    actions = ["login_success", "login_failure", "login_failure", "password_reset",
               "privilege_escalation", "file_access", "config_change"]
    users = ["alice", "bob", "charlie", "admin", "svc_account", "unknown_user"]
    ips = ["10.0.1.12", "10.0.2.45", "192.168.1.100", "203.0.113.5", "198.51.100.22"]

    security_logs = []
    for i in range(1, 51):
        action = random.choice(actions)
        security_logs.append({
            "log_id": f"SEC-{i:04d}",
            "timestamp": f"2024-{random.randint(1,6):02d}-{random.randint(1,28):02d}T"
                         f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
            "user": random.choice(users),
            "action": action,
            "source_ip": random.choice(ips),
            "resource": random.choice(["/api/v1/data", "/admin/dashboard", "/files/report",
                                       "/auth/login", "/api/v1/export"]),
            "status": "FAILED" if "failure" in action else "SUCCESS",
            "severity": "HIGH" if action in ["privilege_escalation", "login_failure"] else "LOW",
            "details": f"Automated log entry {i} for action {action}.",
        })
    save_json(os.path.join(log_dir, "security_logs.json"), security_logs)

    audit_trail = []
    operations = ["CREATE", "READ", "UPDATE", "DELETE", "EXPORT", "IMPORT"]
    resources = ["employee_record", "finance_report", "system_config",
                 "user_account", "access_policy", "backup"]
    for i in range(1, 41):
        audit_trail.append({
            "audit_id": f"AUD-{i:04d}",
            "timestamp": f"2024-{random.randint(1,6):02d}-{random.randint(1,28):02d}T"
                         f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
            "user": random.choice(users),
            "operation": random.choice(operations),
            "resource": random.choice(resources),
            "resource_id": f"RES-{random.randint(1000,9999)}",
            "ip_address": random.choice(ips),
            "outcome": random.choice(["SUCCESS", "SUCCESS", "DENIED"]),
            "session_id": f"SES-{random.randint(10000,99999)}",
        })
    save_json(os.path.join(log_dir, "audit_trail.json"), audit_trail)

    alert_types = ["Brute Force Attack", "Anomalous Login", "Data Exfiltration Attempt",
                   "Privilege Abuse", "Malware Detection", "Unauthorized Access"]
    alerts = []
    for i in range(1, 21):
        alerts.append({
            "alert_id": f"ALT-{i:04d}",
            "timestamp": f"2024-{random.randint(1,6):02d}-{random.randint(1,28):02d}T"
                         f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
            "alert_type": random.choice(alert_types),
            "severity": random.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
            "affected_user": random.choice(users),
            "source_ip": random.choice(ips),
            "description": f"Security alert #{i}: Automated detection of suspicious activity.",
            "status": random.choice(["OPEN", "INVESTIGATING", "RESOLVED"]),
            "assigned_to": random.choice(["charlie", "admin", "soc_analyst"]),
        })
    save_json(os.path.join(log_dir, "alerts.json"), alerts)

    print("  JSON logs generated.")


# ─────────────────────────────────────────────
# Metadata Generation
# ─────────────────────────────────────────────

def generate_metadata(meta_dir: str) -> None:
    document_metadata = {
        "finance_report.pdf": {
            "source": "finance_report.pdf", "department": "finance", "role": "Finance",
            "document_type": "pdf", "classification": "confidential",
            "created_by": "finance_team", "created_date": "2024-07-01", "version": "2.1",
        },
        "hr_policy.pdf": {
            "source": "hr_policy.pdf", "department": "hr", "role": "HR",
            "document_type": "pdf", "classification": "internal",
            "created_by": "hr_team", "created_date": "2024-01-15", "version": "5.0",
        },
        "security_audit.pdf": {
            "source": "security_audit.pdf", "department": "security", "role": "Security",
            "document_type": "pdf", "classification": "restricted",
            "created_by": "security_team", "created_date": "2024-07-10", "version": "1.0",
        },
        "employee_records.csv": {
            "source": "employee_records.csv", "department": "hr", "role": "HR",
            "document_type": "csv", "classification": "confidential", "created_by": "hr_team",
        },
        "finance_transactions.csv": {
            "source": "finance_transactions.csv", "department": "finance", "role": "Finance",
            "document_type": "csv", "classification": "confidential", "created_by": "finance_team",
        },
        "operations_metrics.csv": {
            "source": "operations_metrics.csv", "department": "operations", "role": "Admin",
            "document_type": "csv", "classification": "internal", "created_by": "ops_team",
        },
        "security_logs.json": {
            "source": "security_logs.json", "department": "security", "role": "Security",
            "document_type": "json", "classification": "restricted", "created_by": "siem_system",
        },
        "audit_trail.json": {
            "source": "audit_trail.json", "department": "security", "role": "Security",
            "document_type": "json", "classification": "restricted", "created_by": "audit_system",
        },
        "alerts.json": {
            "source": "alerts.json", "department": "security", "role": "Security",
            "document_type": "json", "classification": "restricted", "created_by": "siem_system",
        },
    }

    dataset_catalog = {
        "catalog_version": "1.0",
        "generated_date": "2024-07-15",
        "organization": "Acme Corp",
        "total_documents": len(document_metadata),
        "departments": ["Finance", "HR", "Security", "Operations"],
        "classifications": ["public", "internal", "confidential", "restricted"],
        "documents": list(document_metadata.keys()),
    }

    save_json(os.path.join(meta_dir, "document_metadata.json"), document_metadata)
    save_json(os.path.join(meta_dir, "dataset_catalog.json"), dataset_catalog)
    print("  Metadata generated.")


# ─────────────────────────────────────────────
# Access Policy & User-Role Generation
# ─────────────────────────────────────────────

def generate_access_policies(policy_dir: str) -> None:
    access_policies = {
        "HR": ["hr", "employee_records"],
        "Finance": ["finance", "transactions"],
        "Security": ["security", "security_logs", "audit", "alerts"],
        "Admin": ["*"],
    }

    department_permissions = {
        "HR": {
            "allowed_sources": ["hr_policy.pdf", "employee_records.csv"],
            "allowed_classifications": ["internal", "confidential"],
            "can_export": False, "can_edit": False,
        },
        "Finance": {
            "allowed_sources": ["finance_report.pdf", "finance_transactions.csv"],
            "allowed_classifications": ["confidential"],
            "can_export": True, "can_edit": False,
        },
        "Security": {
            "allowed_sources": ["security_audit.pdf", "security_logs.json",
                                "audit_trail.json", "alerts.json"],
            "allowed_classifications": ["internal", "confidential", "restricted"],
            "can_export": True, "can_edit": True,
        },
        "Admin": {
            "allowed_sources": ["*"],
            "allowed_classifications": ["*"],
            "can_export": True, "can_edit": True,
        },
    }

    save_json(os.path.join(policy_dir, "access_policies.json"), access_policies)
    save_json(os.path.join(policy_dir, "department_permissions.json"), department_permissions)
    print("  Access policies generated.")


def generate_user_roles(user_dir: str) -> None:
    user_role_mapping = {
        "alice": "HR",
        "bob": "Finance",
        "charlie": "Security",
        "admin": "Admin",
    }
    save_json(os.path.join(user_dir, "user_role_mapping.json"), user_role_mapping)
    print("  User roles generated.")


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

def generate_all(base_dir: str = "data") -> None:
    """Run all generators to populate the data/ directory."""
    print("\nGenerating enterprise dataset...\n")

    generate_pdfs(os.path.join(base_dir, "pdfs"))
    generate_csvs(os.path.join(base_dir, "csv"))
    generate_json_logs(os.path.join(base_dir, "json_logs"))
    generate_metadata(os.path.join(base_dir, "metadata"))
    generate_access_policies(os.path.join(base_dir, "access_policies"))
    generate_user_roles(os.path.join(base_dir, "user_roles"))

    print("\nDataset generation complete. All files saved to data/\n")


if __name__ == "__main__":
    generate_all()