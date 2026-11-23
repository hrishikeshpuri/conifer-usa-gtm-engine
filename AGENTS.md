# Conifer GTM Engineering

## Project layout

- `apis/` holds Markdown documentation for Exa, CompanyEnrich, FullEnrich, Blitz API, and RapidAPI. Create a Markdown file for each provider when its documentation is supplied.
- `output/` holds campaign results.
- `.env` holds local API credentials. Keep credentials out of Markdown, source code, and campaign output.

## Workflow

1. Explain each step in plain language before taking it.
2. Document each integration from the supplied API documentation. Record credential variable names in Markdown and store their values in `.env`.
3. Generate and execute Python or JavaScript when needed so the user can work in plain language.
4. Save requested campaign results in `output/`.

Do not use Clay, Make.com, n8n, Apollo, or Sales Navigator.
