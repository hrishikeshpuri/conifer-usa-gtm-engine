# Blitz API Integration

## Authentication

Use `https://api.blitz-api.ai` as the base URL. Send `BLITZ_API_KEY` from the root `.env` in the `x-api-key` header over HTTPS. Send JSON request bodies with `Content-Type: application/json`. Keep keys out of URLs, logs, documentation, and output files.

## Campaign input

Start with `output/qualified_companies.csv`. Reuse its verified company LinkedIn URL when available. Both search endpoints require a company LinkedIn page URL. If it is missing, the documented `POST /v2/enrichment/domain-to-linkedin` accepts a JSON body with `domain` and returns `found`, `company_linkedin_url`, `company_name`, and alternative matches in `other`. Verify the company match and reuse the resolved URL for later calls. [Domain-to-contacts guide](https://www.blitz-api.ai/guides/domain-to-contacts)

## Employee Finder

`POST /v2/search/employee-finder` lists matching current employees at one company.

| JSON field | Type and behavior |
| --- | --- |
| `company_linkedin_url` | Required company page URL. |
| `job_level` | Optional array of documented levels: `C-Team`, `VP`, `Director`, `Manager`, `Staff`, `Other`. |
| `job_function` | Optional array of documented functions, such as `Engineering`, `Information Technology`, and `Research & Development`. |
| `job_title`, `job_description` | Optional objects with `include` and `exclude` keyword arrays. These apply to the same current position as level and function. Description matching examines the first 10,000 characters. |
| `country_code`, `continent`, `sales_region` | Optional arrays for employee location. Use ISO alpha-2 country codes such as `US`, or `WORLD` for no country filter. |
| `min_connections_count` | Optional number from 0 to 500. Default 0. |
| `is_recent_hire` | Optional boolean. When true, requires the matching job to have started within 90 days. Default false. |
| `max_results`, `page` | Page size 1–50, default 10. Start at page 1 and stop at `total_pages`. The endpoint exposes at most 10,000 results. |

The response includes `company_linkedin_url`, `max_results`, `results_length`, `page`, `total_pages`, `results`, and usage metadata in `fair_usage`. Each result is a person profile. [Employee Finder reference](https://docs.blitz-api.ai/api-reference/people-search/employee-finder) · [Job level and function enums](https://docs.blitz-api.ai/guide/reference/normalization/job-levels)

## Waterfall ICP Search

`POST /v2/search/waterfall-icp-keyword` fills a requested number of slots by searching ranked title tiers in order inside a single company.

| JSON field | Type and behavior |
| --- | --- |
| `company_linkedin_url` | Required company page URL. |
| `cascade` | Required array of 1–10 tiers. Each tier supplies an `include_title` array. Optional tier filters include `exclude_title`, `include_headline_search`, `is_recent_hire`, and `location`. For example, use `location.country_code.include` for allowed employee countries. |
| `max_results` | Optional total across tiers, 1–100. Default 10. |
| `profile_min_connections` | Optional minimum profile connections. Default 0. |

Use title phrases such as `Chief Technology Officer`, `VP Engineering`, or `Head of AI Infrastructure` for Conifer. Brackets request exact matching, as in `[CTO]`. Earlier tiers fill available slots first, and a person matched in an earlier tier is returned only once.

The response includes `company_linkedin_url`, `max_results`, `results_length`, `results`, and `fair_usage`. Each result contains `icp` (matched tier, with 1 highest), `ranking` (overall relevance, with 1 highest), and `person` (profile). Confirm the current title and employer from the returned experience. [Waterfall ICP reference](https://docs.blitz-api.ai/api-reference/people-search/waterfall-icp-search) · [Keyword matching rules](https://docs.blitz-api.ai/guide/reference/normalization/filters)

## Person fields to retain

Capture `full_name`, `linkedin_url`, `headline`, and relevant `location` fields. Use `experiences` to capture the matching current role's `job_title`, `company_name`, `company_domain`, `company_linkedin_url`, and `job_is_current`. Profiles can also include `first_name`, `last_name`, `connections_count`, `education`, `skills`, and `certifications`. Keep missing values blank. Join results to the qualified company by domain and preserve the original buying signal and source URL. Deduplicate people by profile URL.

## Test status

Awaiting the local key. After the key is saved, `GET /v2/account/key-info` can verify authentication and check limits without consuming records. Employee Finder and Waterfall ICP consume one record per returned result. Run record-consuming tests only after approval. [Key details reference](https://docs.blitz-api.ai/api-reference/account/get-api-key-details)
