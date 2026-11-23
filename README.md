# Conifer USA GTM Engine

Conifer’s USA outbound research and reporting workspace. The workflow discovers company-level AI infrastructure signals, qualifies accounts, enriches decision-makers, scores evidence, and prepares campaign reporting.

## Architecture

| Stage | Integration or component |
| --- | --- |
| Discover companies and save source URLs | Exa |
| Verify US headquarters and the 20–250 employee ICP | CompanyEnrich |
| Identify decision-makers and verify roles | Blitz |
| Enrich business emails and phones | FullEnrich and BetterContact |
| Score ICP fit, technical relevance, signals, potential pain, and evidence quality | `score_campaign.ps1` |
| Prepare multichannel campaign records | lemlist |
| Report on accounts and recorded campaign activity | Streamlit, Supabase PostgreSQL, and Grafana |

The API guides in `apis/` describe each integration. Discovery, enrichment and lemlist setup are operator-led workflows. The checked-in code automates scoring and reporting.

## Set up and run

1. Install PowerShell 7 and Python 3.12. Copy `.env.example` to `.env` and populate only the integrations you use. Keep the file local.
2. Follow the API guides and save approved company and contact CSVs in the local `output/` folder. The scorer selects the latest compatible inputs by header. See the input checks in `score_campaign.ps1` for the required columns.
3. Copy `icp_reviews.example.json` to `output/icp_reviews.local.json`. Each review is an array containing the domain, three reviewed subscores (infrastructure relevance out of 20, buying signal out of 25, Conifer relevance out of 20), categories, confirmed evidence, Conifer fit inference, and missing information. Map each domain to its reviewed evidence reliability score in `reliability_by_domain`. Use `media_industry_fit_domains` for reviewed industry exceptions.
4. Run `pwsh -File ./score_campaign.ps1` to produce ranked company and contact files and a priority-account list. The script writes those three outputs locally.

For the local CSV dashboard, create `.dashboard-venv`, install `requirements-dashboard.txt`, and run `pwsh -File ./start_dashboard.ps1`. For the authenticated Supabase dashboard, see [its setup guide](dashboard-publish/README.md).

## Supabase and Grafana

The Supabase dashboard reads the existing `companies`, `contacts`, `buying_signals`, `campaigns`, and `campaign_activities` tables. Configure credentials via Streamlit secrets. This checkout contains no database migrations or seed data.

Import [Conifer USA — GTM Command Center](output/conifer_gtm_command_center.grafana.json) in Grafana and select the PostgreSQL connection with read access to the `grafana_reporting` views `company_scores`, `contact_counts`, `buying_signals`, `campaign_summary`, and `activity_summary`. The dashboard refreshes every five minutes. Planned sequences and recorded activities are separate.

Prospect exports, private review inputs, passwords, logs, local databases and runtime environments stay local.
