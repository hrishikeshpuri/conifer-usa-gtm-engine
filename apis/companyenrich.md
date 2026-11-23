# CompanyEnrich API Integration

## Purpose

Verify and enrich companies discovered by Exa.

## API Documentation

Use the official CompanyEnrich API documentation provided by the user. Do not invent endpoints or request parameters. The integration is awaiting that documentation and credential setup. Run paid enrichment only after the integration is configured.

## Authentication

Read `COMPANYENRICH_API_KEY` from `.env`. Never display or log credentials.

## Input

Read `output/company_discovery.csv`. Use the company domain as the primary lookup key.

## Required Fields

- Company name
- Domain
- Employee count
- Headquarters country
- Industry
- Company description
- LinkedIn company URL, if available

## ICP Rules

The target is a US-headquartered company with 20–250 employees, inclusive.

### Qualified

- Verified US headquarters
- Verified 20–250 employees

### Disqualified

- Verified headquarters outside the United States
- Verified fewer than 20 employees
- Verified more than 250 employees

### Needs Review

- Missing employee count
- Missing headquarters country
- Conflicting company information

Keep each field unverified until CompanyEnrich confirms it.

## Output

Save to `output/qualified_companies.csv`. Preserve original Exa signals and source URLs. Never invent missing company information.
