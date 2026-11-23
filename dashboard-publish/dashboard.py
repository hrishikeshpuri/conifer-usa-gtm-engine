"""Authenticated Streamlit dashboard for Conifer GTM intelligence."""

from time import time
from urllib.parse import urlsplit

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from supabase_dashboard import DataUnavailable, load_supabase, make_views, recorded_outcomes

COMPANY_COLUMNS = dict(
    Company=("company_name", "companyName"), Domain=("website_domain", "companyenrich_domain"),
    Tier=("priority_tier",), Score=("score",), Rank=("rank",),
    Employees=("observed_employee_count",), Range=("estimated_employee_range",),
    Industry=("industry",), Country=("headquarters_country",),
    Signal=("original_buying_signal", "buying_signal"), Categories=("signal_categories",),
    Date=("signal_date",), Evidence=("evidence_url", "supporting_source_url"),
    Confirmed=("confirmed_evidence",), Hypothesis=("conifer_fit_inference", "conifer_relevance"),
    Gaps=("missing_information",), Explanation=("score_explanation",),
)
CONTACT_COLUMNS = dict(
    Name=("full_name", "contact_name"), Company=("company", "company_name"), Domain=("company_domain",),
    Title=("job_title", "current_job_title"), Role=("role_verification_status", "verification_status"),
    Email=("business_email",), EmailStatus=("email_verification_status", "provider_email_status"),
    EmailReview=("email_review_status",), Phone=("phone_number",), PhoneStatus=("phone_verification_status",),
    LinkedIn=("linkedin_url", "linkedin_profile_url"), Relevance=("decision_maker_relevance",),
    RoleEvidence=("role_evidence_url", "evidence_url"), Score=("account_score",),
)
STEP_COLUMNS = dict(
    Company=("companyName", "company"), Name=("contactName", "contact_name"),
    Day=("relativeDay", "relative_send_day"), Step=("stepType", "sequence_step"),
    Rule=("condition",), Subject=("subject", "email_subject"), Message=("message", "email_body"),
    Evidence=("evidenceUrl", "evidence_url"), Review=("reviewStatus", "review_status"),
    Status=("campaignStatus", "campaign_status"),
)
PALETTE = ["#16735d", "#59a891", "#b9d9ce", "#c58143", "#838eac"]
PAGE_NAMES = (
    "Executive Overview", "Company & ICP Intelligence", "Buying Signals",
    "Contact Intelligence", "Campaign Performance",
)
SCORE_COMPONENTS = {
    "icp_fit_25": ("ICP fit", 25), "ai_infrastructure_relevance_20": ("AI infrastructure", 20),
    "buying_signals_25": ("Buying signals", 25), "conifer_pain_relevance_20": ("Conifer relevance", 20),
    "freshness_reliability_10": ("Evidence quality", 10),
}


def require_viewer():
    try:
        auth = st.secrets["auth"]
        access = st.secrets["access"]
        settings = st.secrets["supabase"]
        allowed = access["allowed_emails"]
        if not isinstance(allowed, (list, tuple)) or not allowed or not all(isinstance(email, str) for email in allowed):
            raise ValueError
        emails = {email.strip().casefold() for email in allowed if "@" in email}
        fields = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
        if not emails or not all(auth.get(field) for field in fields) or not settings.get("url") or not settings.get("secret_key"):
            raise ValueError
    except (KeyError, ValueError, TypeError, StreamlitSecretNotFoundError):
        st.title("Conifer GTM")
        st.info("Dashboard access is not configured. Ask the administrator to complete Streamlit secrets setup.")
        st.stop()

    user = st.user
    if not user.is_logged_in:
        st.title("Conifer GTM")
        st.write("Sign in with an approved account to view campaign intelligence.")
        if st.button("Sign in", type="primary"):
            st.login()
        st.stop()

    identity = str(user.get("email", "")).strip().casefold()
    expiry = user.get("exp")
    if (
        user.get("email_verified") is not True or identity not in emails
        or not isinstance(expiry, (int, float)) or expiry <= time()
    ):
        st.title("Conifer GTM")
        st.warning("This sign-in is expired or the account is not approved for this dashboard.")
        if st.button("Sign out"):
            st.logout()
        st.stop()
    return settings


def standardize(frame, schema):
    result = pd.DataFrame(index=frame.index)
    for label, aliases in schema.items():
        field = next((alias for alias in aliases if alias in frame.columns), None)
        result[label] = frame[field].fillna("").astype(str) if field else ""
    return result


def distinct_rows(frame, key):
    if frame.empty:
        return frame
    normalized = frame[key].str.strip().str.lower()
    return frame.loc[~normalized.duplicated() | normalized.eq("")].copy()


def safe_url(value):
    try:
        parsed = urlsplit(str(value))
        return str(value) if parsed.scheme == "https" and parsed.hostname and not parsed.username else ""
    except ValueError:
        return ""


def table(frame, columns, links=(), labels=None):
    if frame.empty:
        st.info("No records match this view.")
        return
    visible = frame.reindex(columns=columns).copy()
    for field in links:
        visible[field] = visible[field].map(safe_url)
    options = {f: st.column_config.LinkColumn(labels.get(f, f) if labels else f, display_text="Open ↗") for f in links}
    options.update({f: label for f, label in (labels or {}).items() if f not in options})
    st.dataframe(visible, hide_index=True, width="stretch", column_config=options)


def section(title, hint=None):
    st.subheader(title)
    if hint:
        st.caption(hint)


def heading(title, subtitle):
    st.title(title)
    st.caption(subtitle)


def metrics(items):
    for col, (label, value, detail) in zip(st.columns(len(items)), items):
        with col:
            st.metric(label, value, border=True)
            if detail:
                st.caption(detail)


def search_rows(frame, query, columns):
    if not query.strip():
        return frame
    mask = pd.Series(False, index=frame.index, dtype=bool)
    for column in columns:
        mask |= frame[column].str.contains(query.strip(), case=False, regex=False, na=False)
    return frame.loc[mask]


def category_chart(values, label, count_label="Companies"):
    counts = values[values.ne("")].value_counts().rename_axis(label).reset_index(name=count_label)
    if counts.empty:
        st.info("No recorded values.")
        return
    chart = alt.Chart(counts).mark_bar(cornerRadiusEnd=5, height=19).encode(
        x=alt.X(f"{count_label}:Q", title=count_label, axis=alt.Axis(tickMinStep=1)),
        y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=250)),
        color=alt.Color(f"{label}:N", scale=alt.Scale(range=PALETTE), legend=None),
        tooltip=[label, count_label],
    ).properties(height=max(112, len(counts) * 33))
    st.altair_chart(chart, width="stretch")


def score_chart(frame):
    sample = frame.dropna(subset=["Score"]).sort_values("Score", ascending=False).head(10)
    if sample.empty:
        st.info("No scores available.")
        return
    chart = alt.Chart(sample[["Company", "Score", "Tier"]]).mark_bar(cornerRadiusEnd=5, height=18).encode(
        x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 100]), title="ICP score / 100"),
        y=alt.Y("Company:N", sort="-x", title=None),
        color=alt.Color("Tier:N", scale=alt.Scale(domain=["Tier 1", "Tier 2", "Tier 3"], range=PALETTE[:3]), legend=None),
        tooltip=["Company", "Score", "Tier"],
    ).properties(height=max(120, len(sample) * 29))
    st.altair_chart(chart, width="stretch")


def overview():
    heading("Executive Overview", "Conifer USA campaign intelligence from Supabase")
    with st.container(border=True):
        st.markdown("**Outreach status**")
        if frames["campaigns"].empty:
            st.write("No campaigns recorded.")
        else:
            for row in frames["campaigns"].to_dict("records"):
                st.write(f"{row.get('name') or 'Campaign'} · {row.get('status') or 'Status unavailable'}")
        st.caption("Campaign records in Supabase.")
    metrics([
        ("Qualified accounts", len(accounts), "Current qualified company list"),
        ("Tier 1 accounts", int(accounts["Tier"].eq("Tier 1").sum()) if has_tiers else "Unavailable", "80–100 ICP score"),
        ("Verified decision-makers", len(verified), "Saved role verification"),
        ("Recorded campaign activities", len(frames["activities"]), "Stored event records"),
    ])
    left, right = st.columns([1.35, 1], gap="large")
    with left.container(border=True):
        section("Highest-scoring accounts")
        score_chart(accounts)
    with right.container(border=True):
        section("ICP tier distribution")
        category_chart(accounts["Tier"], "Tier")
        section("Account coverage")
        coverage = verified["Domain"].str.lower().isin(accounts["Domain"].str.lower())
        covered = verified.loc[coverage & verified["Domain"].ne(""), "Domain"].str.lower().nunique()
        st.write(f"**{covered} of {len(accounts)}** qualified accounts have a verified decision-maker.")
    section("Priority accounts")
    table(accounts.head(5), ["Company", "Domain", "Tier", "Score", "Signal", "Evidence"], ("Evidence",))


def company_profile(row):
    sub = row["Company"] or row["Domain"] or "Company profile"
    st.subheader(sub)
    st.caption(" · ".join(str(row[x]) for x in ["Domain", "Industry", "Country"] if row[x]))
    metrics([
        ("ICP score", f"{row['Score']:g}/100" if pd.notna(row["Score"]) else "Unavailable", row["Tier"]),
        ("Observed employees", f"{row['Employees']:g}" if pd.notna(row["Employees"]) else "Unavailable", f"Estimated range {row['Range']}" if row["Range"] else ""),
    ])
    raw = frames["companies"].loc[row.name]
    pieces = [(label, pd.to_numeric(raw.get(col), errors="coerce"), maximum) for col, (label, maximum) in SCORE_COMPONENTS.items()]
    scored = [(label, score, maximum) for label, score, maximum in pieces if pd.notna(score)]
    left, right = st.columns(2, gap="large")
    with left.container(border=True):
        section("Score breakdown")
        if not scored:
            st.info("This export has no score components.")
        for label, value, maximum in scored:
            st.progress(max(0.0, min(1.0, float(value) / maximum)), text=f"{label} · {value:g}/{maximum}")
    with right.container(border=True):
        section("Buying signal")
        st.write(row["Signal"] or "No signal recorded.")
        for label, field in [("Confirmed evidence", "Confirmed"), ("Conifer hypothesis", "Hypothesis"), ("Open questions", "Gaps")]:
            if row[field]:
                st.markdown(f"**{label}**")
                st.write(row[field])
        if row["Date"]:
            st.caption(f"Signal date · {row['Date']}")
        if safe_url(row["Evidence"]):
            st.link_button("Open evidence", row["Evidence"])
    related = verified[verified["Domain"].str.lower().eq(row["Domain"].lower())] if row["Domain"] else verified.iloc[0:0]
    section("Decision-maker coverage")
    table(related, ["Company", "Title", "Role", "EmailStatus", "PhoneStatus"],
          labels={"EmailStatus": "Email verification", "PhoneStatus": "Phone verification"})


def company_page():
    heading("Company & ICP Intelligence", "Search accounts, compare scores, and inspect the supporting evidence.")
    with st.expander("Qualification counts"):
        qualification = frames["companies"].get("qualification_status", pd.Series(dtype=str)).fillna("").str.lower()
        metrics([
            ("Companies in Supabase", len(frames["companies"]), ""),
            ("Qualified", len(accounts), ""),
            ("Needs review", int(qualification.eq("needs review").sum()), ""),
            ("Disqualified", int(qualification.eq("disqualified").sum()), ""),
        ])
    col1, col2, col3 = st.columns([1.5, 1, 1])
    query = col1.text_input("Search companies", placeholder="Company, domain, or signal")
    tiers = col2.multiselect("Priority tier", sorted(x for x in accounts["Tier"].unique() if x))
    industries = col3.multiselect("Industry", sorted(x for x in accounts["Industry"].unique() if x))
    visible = search_rows(accounts, query, ["Company", "Domain", "Signal"])
    if tiers:
        visible = visible[visible["Tier"].isin(tiers)]
    if industries:
        visible = visible[visible["Industry"].isin(industries)]
    if st.checkbox("Filter by minimum ICP score", disabled=not accounts["Score"].notna().any()):
        minimum = st.slider("Minimum ICP score", 0, 100, 60)
        visible = visible[visible["Score"].ge(minimum)]
    section(f"Qualified accounts · {len(visible)}")
    table(visible, ["Rank", "Company", "Domain", "Tier", "Score", "Employees", "Industry", "Evidence"], ("Evidence",))
    if not visible.empty:
        labels = {i: f"{row.Company} · {row.Domain}" for i, row in visible.iterrows()}
        index = st.selectbox("Open company profile", list(labels), format_func=labels.get)
        company_profile(accounts.loc[index])


def signal_page():
    heading("Buying Signals", "Trace each signal to its recorded source and distinguish evidence from hypotheses.")
    available = standardize(frames["signals"], COMPANY_COLUMNS)
    available["Score"] = pd.to_numeric(available["Score"], errors="coerce")
    available = available[available["Signal"].ne("")].copy()
    available["_categories"] = available["Categories"].str.split(r";\s*")
    category_set = sorted({v.strip() for row in available["_categories"] for v in row if v.strip()})
    first, second, third = st.columns([1.2, 1.4, 1])
    query = first.text_input("Search signals", placeholder="Company, infrastructure, or cost")
    categories = second.multiselect("Signal category", category_set)
    dates = third.selectbox("Evidence date", ["All signals", "Dated only", "Undated only"])
    visible = search_rows(available, query, ["Company", "Signal", "Categories"])
    if categories:
        visible = visible[visible["_categories"].map(lambda entries: any(s.strip() in categories for s in entries))]
    if dates != "All signals":
        visible = visible[visible["Date"].ne("") if dates == "Dated only" else visible["Date"].eq("")]
    dated = int(visible["Date"].ne("").sum())
    metrics([("Matching signals", len(visible), ""), ("Dated evidence", dated, ""), ("Undated evidence", len(visible) - dated, "")])
    with st.container(border=True):
        section("Signal categories", "One account can appear in multiple categories.")
        category_chart(visible["_categories"].explode().dropna().str.strip(), "Category", "Account signals")
    table(visible, ["Company", "Score", "Categories", "Date", "Signal", "Evidence"], ("Evidence",))
    if not visible.empty:
        index = st.selectbox("Inspect signal", visible.index.tolist(), format_func=lambda i: visible.loc[i, "Company"])
        row = visible.loc[index]
        for title, field in [("Confirmed evidence", "Confirmed"), ("Conifer hypothesis", "Hypothesis"), ("Open questions", "Gaps")]:
            section(title)
            st.write(row[field] or "Not recorded.")


def contact_page():
    heading("Contact Intelligence", "Review recorded role, email, and phone verification.")
    metrics([
        ("Named contacts", len(contacts), ""),
        ("Verified current roles", len(verified), ""),
        ("Deliverable company emails", int(email_usable.sum()) if has_email_status else "Unavailable", "Provider status and employer-domain match"),
        ("Phones returned", int(contacts["Phone"].ne("").sum()) if has_phone else "Unavailable", "See provider verification status"),
    ])
    cols = st.columns([1.3, 1, 1])
    query = cols[0].text_input("Search company or title", placeholder="Company, domain, or role")
    email_filter = cols[1].multiselect("Email verification", sorted(contacts["EmailStatus"].replace("", "Unavailable").unique()))
    phone_filter = cols[2].selectbox("Phone availability", ["All contacts", "Phone present", "Phone missing"])
    visible = search_rows(contacts, query, ["Company", "Title", "Domain"])
    if email_filter:
        visible = visible[visible["EmailStatus"].replace("", "Unavailable").isin(email_filter)]
    if phone_filter != "All contacts":
        visible = visible[visible["Phone"].ne("") if phone_filter == "Phone present" else visible["Phone"].eq("")]
    show = st.checkbox("Reveal contact details in this session", key="contact_reveal")
    visible = visible.copy()
    visible["EmailAvailable"] = visible["Email"].map(lambda value: "Available" if value else "Missing")
    visible["PhoneAvailable"] = visible["Phone"].map(lambda value: "Available" if value else "Missing")
    cols = ["Company", "Title", "Role", "EmailStatus", "EmailReview", "PhoneStatus"]
    table(visible, (["Name"] + cols + ["Email", "Phone", "LinkedIn"]) if show else (cols + ["EmailAvailable", "PhoneAvailable"]),
          ("LinkedIn",) if show else (), {"Role": "Role verification", "EmailStatus": "Email verification", "EmailReview": "Email review", "PhoneStatus": "Phone verification"})
    if not visible.empty:
        index = st.selectbox("Inspect contact role", visible.index.tolist(), format_func=lambda i: f"{visible.at[i, 'Company']} · {visible.at[i, 'Name'] if show else (visible.at[i, 'Title'] or 'Role unavailable')}")
        row = visible.loc[index]
        section("Decision-maker relevance")
        st.write(row["Relevance"] or "Relevance not recorded.")
        if show and safe_url(row["RoleEvidence"]):
            st.link_button("Open role evidence", row["RoleEvidence"])


def campaign_page():
    heading("Campaign Performance", "Read planned outreach separately from recorded events in Supabase.")
    campaigns = frames["campaigns"]
    if campaigns.empty:
        st.info("No campaigns recorded.")
        return

    choices = {row["id"]: row.get("name") or "Campaign" for row in campaigns.to_dict("records")}
    campaign_id = st.selectbox("Campaign", list(choices), format_func=choices.get)
    campaign = campaigns.loc[campaigns["id"].eq(campaign_id)].iloc[0]
    st.info(f"Campaign status in Supabase: {campaign.get('status') or 'Unavailable'}")
    raw_steps = frames["sequence"]
    if not raw_steps.empty:
        raw_steps = raw_steps.loc[raw_steps["campaign_id"].eq(campaign_id)]
    activities = frames["activities"]
    if not activities.empty:
        activities = activities.loc[activities["campaign_id"].eq(campaign_id)]
    planned_contacts = raw_steps["contact_id"].dropna().nunique() if "contact_id" in raw_steps else 0
    metrics([
        ("Planned contacts", planned_contacts, "From the saved sequence plan"),
        ("Planned touches", len(raw_steps), "Email and LinkedIn steps"),
        ("Recorded activities", len(activities), "From campaign activities"),
    ])
    section("Recorded outreach outcomes", "Counts reflect stored events only. The sequence plan is separate.")
    counts, unmapped = recorded_outcomes(activities)
    metrics([(name, count, "") for name, count in counts.items()])
    if unmapped:
        st.caption(f"{unmapped} recorded events have types outside the outcome metrics.")
    if not activities.empty:
        table(activities, ["activity_type", "activity_status", "sequence_step", "occurred_at"])
    section("Sequence details")
    step_frame = standardize(raw_steps, STEP_COLUMNS)
    step_frame["Day"] = pd.to_numeric(step_frame["Day"], errors="coerce")
    if step_frame.empty:
        st.info("No sequence steps recorded.")
    else:
        options = list(dict.fromkeys(c for c in step_frame["Company"] if c))
        company = st.selectbox("Sequence company", options) if options else None
        visible = step_frame[step_frame["Company"].eq(company)] if company else step_frame
        choices = sorted(set(c for c in visible["Step"] if c))
        channels = st.multiselect("Step type", choices)
        if channels:
            visible = visible[visible["Step"].isin(channels)]
        visible = visible.sort_values("Day", na_position="last")
        table(visible, ["Day", "Step", "Subject", "Rule", "Status", "Evidence"], ("Evidence",))
        reveal = st.checkbox("Reveal personalized message text in this session", key="message_reveal")
        if reveal:
            for _, row in visible.iterrows():
                day = f"Day {row['Day']:g}" if pd.notna(row["Day"]) else "Day unavailable"
                with st.expander(f"{day} · {row['Step'] or 'Step'}"):
                    if row["Name"]:
                        st.caption(row["Name"])
                    if row["Subject"]:
                        st.markdown("**Subject**")
                        st.text(row["Subject"])
                    st.text(row["Message"] or "No message for this step.")
                    if row["Review"]:
                        st.caption(row["Review"])
    source = campaign.get("source_data")
    if isinstance(source, dict) and source.get("remote_state"):
        st.caption(f"Saved platform snapshot: {source['remote_state']}")


st.set_page_config(page_title="Conifer GTM", page_icon="🌲", layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"] {background: #f6f8f5;}
[data-testid="stSidebar"] {background: #e9f0eb;}
[data-testid="stSidebar"] h2 {color:#164636; letter-spacing:-.04em;}
.stMainBlockContainer {padding-top: 2.6rem; max-width: 1360px;}
[data-testid="stMetric"] {background:#fff;border-color:#dbe6dd;border-radius:13px;}
[data-testid="stMetricValue"] {color:#145941; font-weight:700;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#dbe6dd;border-radius:13px;}
h1 {letter-spacing:-.045em;color:#163a2e;}
</style>""", unsafe_allow_html=True)
settings = require_viewer()
try:
    frames = make_views(load_supabase(settings))
except DataUnavailable as error:
    st.error(str(error))
    st.stop()
company_records = frames["companies"]
if "qualification_status" in company_records:
    company_records = company_records.loc[company_records["qualification_status"].fillna("").str.lower().eq("qualified")]
accounts = distinct_rows(standardize(company_records, COMPANY_COLUMNS), "Domain")
for field in ("Score", "Employees", "Rank"):
    accounts[field] = pd.to_numeric(accounts[field], errors="coerce")
accounts = accounts.sort_values(["Score", "Rank"], ascending=[False, True], na_position="last")
contacts = standardize(frames["contacts"], CONTACT_COLUMNS)
contacts = distinct_rows(contacts[contacts["Name"].ne("")], "LinkedIn")
verified = contacts[contacts["Role"].str.startswith("Verified", na=False)]
has_tiers = accounts["Tier"].ne("").any()
has_email_status = any(f in frames["contacts"] for f in CONTACT_COLUMNS["EmailStatus"])
has_phone = any(f in frames["contacts"] for f in CONTACT_COLUMNS["Phone"])
email_domain = contacts["Email"].str.rsplit("@", n=1).str[-1].str.lower()
email_usable = contacts["EmailStatus"].eq("DELIVERABLE") & contacts["Email"].str.contains("@", regex=False) & email_domain.eq(contacts["Domain"].str.lower())
views = dict(zip(PAGE_NAMES, (overview, company_page, signal_page, contact_page, campaign_page)))
with st.sidebar:
    st.markdown("## Conifer")
    st.caption("USA GTM · Supabase")
    page = st.radio("Navigate", PAGE_NAMES, label_visibility="collapsed")
    st.divider()
    st.caption("Contact details are hidden until revealed in this session.")
    if st.button("Sign out"):
        st.logout()
    with st.expander("Data sources"):
        st.write("Companies, contacts, buying signals, campaigns, and campaign activities in Supabase.")
views[page]()
