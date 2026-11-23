"""Server-side reads and view models for the authenticated GTM dashboard."""

from urllib.parse import urlsplit

import pandas as pd
import requests

TABLE_COLUMNS = {
    "companies": "id,name,domain,industry,headquarters_country,employee_count,icp_score,priority_tier,qualification_status,source_url,source_data",
    "contacts": "id,company_id,full_name,job_title,linkedin_url,business_email,email_verification_status,phone_number,phone_verification_status,role_verification_status,outreach_status,source_data",
    "buying_signals": "id,company_id,signal_type,description,evidence_url,observed_at,source_data",
    "campaigns": "id,name,platform,channel,status,sequence_plan,source_data",
    "campaign_activities": "id,campaign_id,contact_id,activity_type,activity_status,sequence_step,occurred_at",
}
EVENT_LABELS = {
    "email_sent": "Emails sent", "emailsSent": "Emails sent",
    "email_replied": "Replies", "emailsReplied": "Replies",
    "meeting_booked": "Meetings", "meetingBooked": "Meetings",
}


class DataUnavailable(Exception):
    """A backend response could not be safely used."""


def _json(value):
    return value if isinstance(value, dict) else {}


def _rows(client, base_url, table):
    page_size = 250
    rows = []
    previous_ids = set()
    while True:
        response = client.get(
            f"{base_url}/rest/v1/{table}",
            params={"select": TABLE_COLUMNS[table], "order": "id.asc", "offset": len(rows), "limit": page_size},
            timeout=(5, 15), allow_redirects=False,
        )
        if response.status_code not in (200, 206):
            raise DataUnavailable(f"Supabase read failed ({table}, HTTP {response.status_code}).")
        batch = response.json()
        if not isinstance(batch, list) or any(not isinstance(row, dict) or not row.get("id") for row in batch):
            raise DataUnavailable(f"Supabase returned an unexpected response for {table}.")
        if not batch:
            return rows
        for row in batch:
            if row["id"] in previous_ids:
                raise DataUnavailable(f"Supabase returned duplicate rows for {table}. Please refresh.")
            previous_ids.add(row["id"])
        rows.extend(batch)
        # Keep going even when the server caps the requested page size.
        content_range = response.headers.get("Content-Range", "")
        total = content_range.rpartition("/")[2]
        if total.isdigit() and len(rows) >= int(total):
            return rows


def load_supabase(settings):
    url = str(settings.get("url", "")).strip().rstrip("/")
    key = str(settings.get("secret_key", "")).strip()
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if (
        parsed.scheme != "https" or not hostname.endswith(".supabase.co")
        or parsed.netloc != hostname or parsed.path or parsed.query or parsed.fragment
        or not key.startswith("sb_secret_") or not key.removeprefix("sb_secret_")
    ):
        raise DataUnavailable("Configure the project HTTPS URL and a server-side Supabase secret key in Streamlit secrets.")
    try:
        with requests.Session() as client:
            client.trust_env = False
            client.headers.update({"apikey": key, "Accept": "application/json", "Prefer": "count=exact"})
            return {table: _rows(client, url, table) for table in TABLE_COLUMNS}
    except (requests.RequestException, ValueError) as error:
        raise DataUnavailable("Supabase did not return usable data. Verify the server connection and project settings.") from error


def make_views(data):
    company_by_id = {row["id"]: row for row in data["companies"]}
    contact_by_id = {row["id"]: row for row in data["contacts"]}
    signals = []
    for row in data["buying_signals"]:
        source = _json(row.get("source_data"))
        company = company_by_id.get(row.get("company_id"), {})
        signals.append({
            "company_id": row.get("company_id"),
            "company_name": company.get("name"),
            "website_domain": company.get("domain"),
            "score": company.get("icp_score"),
            "original_buying_signal": row.get("description"),
            "signal_categories": row.get("signal_type"),
            "signal_date": source.get("signal_date") or row.get("observed_at"),
            "evidence_url": row.get("evidence_url"),
            "confirmed_evidence": source.get("confirmed_evidence"),
            "conifer_fit_inference": source.get("conifer_fit_inference"),
            "missing_information": source.get("missing_information"),
        })
    signals_by_company = {}
    for row in signals:
        signals_by_company.setdefault(row["company_id"], []).append(row)

    companies = []
    for row in data["companies"]:
        source = _json(row.get("source_data"))
        company_signals = signals_by_company.get(row["id"], [])
        primary = next((signal for signal in company_signals if signal["evidence_url"] == row.get("source_url")), None)
        primary = primary or (company_signals[0] if company_signals else {})
        companies.append({
            **primary,
            **_json(source.get("scoring")),
            "company_name": row.get("name"), "website_domain": row.get("domain"),
            "industry": row.get("industry"), "headquarters_country": row.get("headquarters_country"),
            "observed_employee_count": row.get("employee_count"),
            "estimated_employee_range": source.get("estimated_employee_range"),
            "score": row.get("icp_score"), "priority_tier": row.get("priority_tier"),
            "rank": source.get("rank"), "qualification_status": row.get("qualification_status"),
            "score_explanation": source.get("score_explanation"),
        })

    contacts = []
    for row in data["contacts"]:
        company = company_by_id.get(row.get("company_id"), {})
        source = _json(row.get("source_data"))
        contacts.append({
            "full_name": row.get("full_name"), "job_title": row.get("job_title"),
            "company_domain": company.get("domain"), "company": company.get("name"),
            "account_score": company.get("icp_score"), "linkedin_url": row.get("linkedin_url"),
            "business_email": row.get("business_email"), "email_verification_status": row.get("email_verification_status"),
            "phone_number": row.get("phone_number"), "phone_verification_status": row.get("phone_verification_status"),
            "role_verification_status": row.get("role_verification_status"),
            "email_review_status": source.get("email_review_status"),
            "decision_maker_relevance": source.get("decision_maker_relevance"),
            "role_evidence_url": source.get("role_evidence_url"),
        })

    steps = []
    for campaign in data["campaigns"]:
        plan = campaign.get("sequence_plan")
        if not isinstance(plan, list):
            continue
        for entry in plan:
            if not isinstance(entry, dict):
                continue
            contact = contact_by_id.get(entry.get("contact_id"), {})
            company = company_by_id.get(contact.get("company_id"), {})
            steps.append({
                "campaign_id": campaign["id"], "contact_id": entry.get("contact_id"),
                "companyName": company.get("name"), "contactName": contact.get("full_name"),
                "relativeDay": entry.get("relative_day"), "stepType": entry.get("step_type"),
                "condition": entry.get("condition"), "subject": entry.get("subject"), "message": entry.get("message"),
                "evidenceUrl": entry.get("evidence_url"), "campaignStatus": "Planned",
                "reviewStatus": entry.get("review_status"),
            })

    return {key: pd.DataFrame(values) for key, values in {
        "companies": companies, "contacts": contacts, "signals": signals,
        "campaigns": data["campaigns"], "sequence": steps, "activities": data["campaign_activities"],
    }.items()}


def recorded_outcomes(activities):
    counts = dict.fromkeys(EVENT_LABELS.values(), 0)
    unmapped = 0
    for row in activities.to_dict("records"):
        label = EVENT_LABELS.get(row.get("activity_type"))
        if label:
            counts[label] += 1
        else:
            unmapped += 1
    return counts, unmapped
