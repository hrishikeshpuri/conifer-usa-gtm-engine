# BetterContact API Integration

## Authentication and account check

Base URL: `https://app.bettercontact.rocks/api/v2`. Read `BETTERCONTACT_API_KEY` from the root `.env` and send it as the `X-API-Key` header over HTTPS. Use `Content-Type: application/json` for JSON bodies. Keep the key out of URLs, logs, and output. [Authentication](https://doc.bettercontact.rocks/api-reference/authentication)

`GET /account` reads the shared organization balance in `credits_left`. A successful response confirms the key can access the account API. The response schema does not include the phone add-on entitlement. Check that entitlement in the account before submitting a phone job. BetterContact documents HTTP 402 when the phone add-on is missing. [Account balance](https://doc.bettercontact.rocks/api-reference/endpoint/account) · [Enrich leads](https://doc.bettercontact.rocks/api-reference/endpoint/create)

## Prepare phone-only enrichment

Use `output/enriched_contacts.csv` as the contact source. Include only contacts with a supported current role. Use the saved company domain and standard LinkedIn profile URL. BetterContact requires separate `first_name` and `last_name`, either `company` or `company_domain`, and a `linkedin_url` for phone requests. If a stored full name cannot be split reliably, flag it for review. Use a stable value such as the normalized profile URL in `custom_fields.uuid` to join results back to the campaign. Preserve the original buying signals and evidence URLs.

Submit an approved batch of 1–100 contacts to `POST /async`. The phone-only body shape is:

```json
{
  "data": [
    {
      "first_name": "<given name>",
      "last_name": "<family name>",
      "company_domain": "<verified company domain>",
      "linkedin_url": "<LinkedIn person profile URL>",
      "custom_fields": {"uuid": "<stable contact identifier>"}
    }
  ],
  "enrich_phone_number": true,
  "enrich_email_address": false,
  "enrich_profile": false,
  "verify_catch_all": false
}
```

Set these flags explicitly because email enrichment is the default when no enrichment option is enabled. Leave existing email results in place. A successful submission returns HTTP 201 with `success`, `id`, and `message`. Store the `id` immediately. Submissions are not idempotent, so check for an existing job before repeating any POST with an uncertain outcome. [Request schema](https://doc.bettercontact.rocks/api-reference/endpoint/create)

## Retrieve completed results

Use `GET /async/{request_id}` with the same key that submitted the job. Poll with a short delay on `not_started` or `processing`. Read results only when the body reports `terminated`. An `on_hold` job is paused for insufficient credits and can resume on the same request ID after a top-up. [Request statuses](https://doc.bettercontact.rocks/api-reference/statuses)

The completed response includes `id`, `status`, `credits_consumed`, `credits_left`, `summary`, and `data[]`. Check the per-contact `enriched` flag and read `contact_phone_number` and `contact_phone_number_provider` when present. Correlate results by the returned `custom_fields` identifier. Retain the provider metadata, and leave missing numbers blank. [Result schema](https://doc.bettercontact.rocks/api-reference/endpoint/get)

For a hosted receiver, the optional `webhook` field sends the completed batch payload by POST. BetterContact documents unsigned callbacks. Keep the callback URL private and confirm the job ID and results with the authenticated GET before using them. Polling works for this local campaign without a webhook receiver. [Webhook documentation](https://doc.bettercontact.rocks/api-reference/webhooks)
