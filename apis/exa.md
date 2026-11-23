# Exa API Integration

Documentation: https://docs.exa.ai
Base URL: https://api.exa.ai

## Authentication

Use `EXA_API_KEY` from `.env`.
Never print or expose the key.

## Search

`POST /search`

## Campaign objective

Discover B2B companies likely to be US-based and have approximately 20–250 employees.

1. Prioritize companies building AI agents, supporting multiple LLM providers, or expanding AI infrastructure. Look for deployment evidence, reliability or inference cost work, and infrastructure hiring.
2. Use public company profiles as screening clues. Exclude known large enterprises from the active shortlist and qualified prospect list.
3. Record a supporting source URL for each signal and its date when published. Treat Conifer relevance as a hypothesis and avoid inferring buying intent from weak evidence.
4. Keep company size and headquarters marked unverified until CompanyEnrich confirms each field. Qualify a prospect only after it meets the size and US headquarters criteria and has a documented B2B use case and infrastructure signal.
5. Save the active discovery shortlist to `output/company_discovery.csv`. See [CompanyEnrich](companyenrich.md) for enrichment setup.

Search for:

- Multiple AI model providers
- AI agents and LLM applications
- AI infrastructure hiring
- LLM latency and reliability problems
- Model routing and inference cost challenges

## Output

- Company name
- Company website
- Signal type
- Signal evidence
- Source URL
- Signal date, if available
- Verification status
