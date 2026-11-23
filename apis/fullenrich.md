# FullEnrich API Integration

## Authentication

Use the v2 base URL `https://app.fullenrich.com/api/v2`. Read `FULLENRICH_API_KEY` from the root `.env` and send it as an `Authorization: Bearer <token>` header over HTTPS. Send JSON request bodies with `Content-Type: application/json`. Keep credentials out of URLs, logs, and output. [Authentication reference](https://docs.fullenrich.com/api/v2/general/authentication)

After the key is saved, `GET /account/keys/verify` checks authentication without starting a job. A valid key returns HTTP 200 with `workspace_id`. [Key verification reference](https://docs.fullenrich.com/api/v2/account/keys/verify/get)

## Start contact enrichment

`POST /contact/enrich/bulk` starts an asynchronous job and returns an `enrichment_id` UUID. Save that ID for result retrieval. [Start bulk enrichment reference](https://docs.fullenrich.com/api/v2/contact/enrich/bulk/post)

| Request field | Purpose |
| --- | --- |
| `name` | Required readable batch name. |
| `data` | Required array of 1–100 contacts. Use an array of one for a single contact. |
| `data[].linkedin_url` | Standard LinkedIn person profile URL. It can identify the contact on its own. |
| `data[].first_name`, `last_name`, `domain`, `company_name` | Alternatively, provide both names and at least one company identifier, either domain or name. Supply these alongside the profile URL when available and reliable. |
| `data[].enrich_fields` | Nonempty array of requested fields. Supported values are `contact.work_emails`, `contact.personal_emails`, and `contact.phones`. Request only fields approved for the run. |
| `data[].custom` | Optional object for correlation. Use string values such as a contact ID. The result echoes this object. |
| `webhook_url` | Optional batch-level callback URL. |
| `webhook_events.contact_finished` | Optional callback URL for each completed contact. |
| `silentFail` | Optional query boolean, default false. When true, invalid contacts are skipped and included in results without enrichment data. |

## Retrieve results

`GET /contact/enrich/bulk/{enrichment_id}` retrieves the existing job. FullEnrich recommends a webhook for ongoing integrations. For a local test, polling the saved ID is supported. Keep the optional `forceResults` query parameter at its default of false because enabling it can return incomplete results. [Get enrichment result reference](https://docs.fullenrich.com/api/v2/contact/enrich/bulk/get)

- The batch response includes `id`, `name`, `status`, `cost.credits`, and `data[]`.
- Status values are `CREATED`, `IN_PROGRESS`, `FINISHED`, `CANCELED`, `CREDITS_INSUFFICIENT`, `RATE_LIMIT`, and `UNKNOWN`. Treat results as complete when the batch is `FINISHED`. Surface other outcomes without treating missing data as a verified result.
- Contact results can include `input`, `custom`, `contact_info`, and `profile`. The profile can include the person's headline, roles, and company details when a LinkedIn URL was submitted.
- `contact_info` can contain `most_probable_work_email`, `most_probable_personal_email`, `most_probable_phone`, and the `work_emails`, `personal_emails`, and `phones` arrays. Email entries carry `email` and `status`. Phone entries carry `number` and may include region, line type, line status, and ownership information. Preserve the returned verification status and leave missing values blank. [Email verification statuses](https://docs.fullenrich.com/api/v2/general/email-status)

## Webhook delivery

Configure a reachable HTTPS endpoint to accept POST callbacks if using webhooks. The batch callback is sent when processing finishes, credits are insufficient, or the batch is canceled. The batch payload has the same shape as the GET result. The optional per-contact callback reports progress as each contact finishes.

Verify `X-Signature-SHA1` before parsing JSON. Compute HMAC-SHA1 over the raw request body using the FullEnrich API key as the secret, encode the digest as lowercase hexadecimal, and compare in constant time. Return a 2xx response after accepting a verified delivery. FullEnrich retries failed deliveries every minute up to five times, so handle repeated events without duplicating records. [Webhook reference](https://docs.fullenrich.com/api/v2/general/webhooks)

## Conifer campaign

Use verified rows from `output/decision_makers.csv` for approved enrichment. Deduplicate by LinkedIn profile URL, use a stable string identifier in `custom`, and preserve the original buying signal and evidence URL on the campaign record. Start with work email only if approved. The setup is pending the local key and authentication test. No webhook listener or enrichment job has been started.
