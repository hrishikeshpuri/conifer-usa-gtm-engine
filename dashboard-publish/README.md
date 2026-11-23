# Conifer GTM Dashboard

Read-only Streamlit dashboard for the five Conifer GTM tables in Supabase. Sign-in requires a Google account with a verified email on the dashboard allowlist. The server queries Supabase after checking access on each run.

## Local setup

Install `requirements.txt` in a Python 3.12 virtual environment. Create `.streamlit/secrets.toml` inside this folder using the settings below. Git ignores this file. Fill in the placeholders locally.

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "REPLACE_WITH_A_RANDOM_SECRET"
client_id = "REPLACE_WITH_GOOGLE_OIDC_CLIENT_ID"
client_secret = "REPLACE_WITH_GOOGLE_OIDC_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[access]
allowed_emails = ["REPLACE_WITH_APPROVED_GOOGLE_EMAIL"]

[supabase]
url = "https://behesjxeqhxubcnggqrp.supabase.co"
secret_key = "REPLACE_WITH_SUPABASE_SERVER_SECRET_KEY"
```

Register the exact callback URL with your Google web OAuth client. Add approved viewers as Google OAuth test users if your consent screen is in testing. Use a separate Supabase secret key (the `sb_secret_` key type) for this app. This key bypasses Supabase RLS and must stay server-side. The Streamlit app enforces the viewer allowlist before any data query.

From this folder, run the command below and open `http://localhost:8501`.

```powershell
python -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

## Streamlit Community Cloud

After local verification and approval, deploy from `main` with `dashboard.py` as the entry point and select Python 3.12. Keep app sharing private. Enter the same settings in the app’s Secrets settings with the exact deployed HTTPS callback URL ending in `/oauth2callback`. Register that callback with Google and use a separate cookie secret for the deployment.

[Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication) · [Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) · [Supabase API keys](https://supabase.com/docs/guides/api/api-keys)
