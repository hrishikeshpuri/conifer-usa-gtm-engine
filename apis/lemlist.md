# lemlist API Integration

## Authentication and account access

Use `https://api.lemlist.com/api`. Read `LEMLIST_API_KEY` from the root `.env`. Use HTTPS Basic authentication with an empty username and the key as the password. Treat the encoded authorization header as a credential. A read-only `GET /user/channels` reports the plan and each channel’s availability and connection status. Verify the selected team and sender separately. [Authentication](https://developer.lemlist.com/api-reference/getting-started/authentication) · [User channels](https://developer.lemlist.com/api-reference/endpoints/users/get-user-channels)

## Campaigns, leads, and personalization

- `GET /campaigns` lists campaigns. `POST /campaigns` provisions a campaign with a sequence and schedule. Verify the campaign state and ID before any later import. [Create campaign](https://developer.lemlist.com/api-reference/endpoints/campaigns/create-campaign)
- `GET /campaigns/{campaignId}/leads` reads campaign leads. `POST /campaigns/{campaignId}/leads/` creates a lead and does not update an existing one. Check prior campaign membership and deduplicate by normalized email and profile URL before importing. [Create lead](https://developer.lemlist.com/api-reference/endpoints/leads/create-lead-in-campaign)
- Built-ins are `firstName`, `lastName`, `companyName`, `jobTitle`, `email`, `linkedinUrl`, and `phone`. Map score, signal, source URL, and per-touch copy to custom fields. Variables can use `{{firstName}}` syntax. Use per-lead step personalization when assigning individually drafted subject lines and bodies. Preview every rendered message. [Per-lead personalization](https://developer.lemlist.com/api-reference/endpoints/leads/personalize-step-for-lead)

## Sequences and LinkedIn conditions

`GET /campaigns/{campaignId}/sequences` reads sequence IDs and steps. The Add Step reference documents `email`, `linkedinVisit`, `linkedinInvite`, `linkedinSend`, and conditional steps. The plan CSV is a local specification. Review delays and branch timing in the editor before activation. [Read sequences](https://developer.lemlist.com/api-reference/endpoints/sequences/get-campaign-sequences) · [Add steps](https://developer.lemlist.com/api-reference/endpoints/sequences/add-step-to-sequence)

The Day 3 profile visit does not create a connection. At Day 10 use the editor’s first-degree network condition for the selected sender. Send a standard LinkedIn message only on the confirmed first-degree branch. Skip if false or unknown and preserve Day 14. Leave invite fallback and InMail disabled. If a later approved design changes Day 3 to an invite, verify acceptance before messaging. LinkedIn steps require a supported plan and sender connection. Advanced conditions are documented for Multichannel Expert and Enterprise. [LinkedIn steps](https://help.lemlist.com/en/articles/4686779-how-to-add-linkedin-steps-to-your-sequence) · [Conditions](https://help.lemlist.com/en/articles/8290177-how-to-use-conditions-in-your-campaign-sequence)

## Activity, suppression, and limitations

- `GET /activities` reads campaign activity, with optional campaign and event filters. Reconcile sent, reply, bounce, and unsubscribe events before release, using activity IDs to deduplicate. [Activity API](https://developer.lemlist.com/api-reference/endpoints/activities/get-many-activities)
- `GET /v2/unsubscribes/variables` lists unsubscribed emails, domains, profiles, and phone numbers. Reconcile platform and local records and prior-outreach history. An empty local register does not establish clearance. [Unsubscribe API](https://developer.lemlist.com/api-reference/endpoints/unsubscribes/list-unsubscribed-variables)
- The documented limit is 20 requests per two seconds per key. Respect pagination, HTTP 429, and `Retry-After`. Authentication does not prove write permissions, sender readiness, or channel entitlement. [Rate limits](https://developer.lemlist.com/api-reference/getting-started/rate-limits)
- Before release, verify the sender identity, connected mailbox, SPF, DKIM and DMARC alignment, postal address, and working opt-out. Confirm recipient jurisdiction and review U.S. CAN-SPAM and any other applicable rules. [FTC guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)

This integration prepares local drafts only. No remote campaign, lead import, schedule, or outbound activity has been created.
