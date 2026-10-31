# Fanoos: cPanel deployment package

This folder is a ready-to-run Fanoos web app for cPanel hosting with **Setup Python App**
(Phusion Passenger or LiteSpeed). No Docker, root access, SSH, Node.js or database is needed.

> Persian, step-by-step guide for beginners: **`DEPLOY_CPanel_FA.md`** (in this folder).

## Requirements

- cPanel with **Setup Python App** (CloudLinux Python Selector) and **Python 3.10 or newer**
  (3.12 recommended; tested on 3.10, 3.12 and 3.13).
- A domain or **subdomain** pointing at the account. Fanoos must run at the **root** of its
  domain or subdomain (for example `https://fanoos.example.com/`), not under a path such as
  `example.com/fanoos`, because the UI loads `/static/…`, `/assets/…` and `/api/…` from the root.
- HTTPS (cPanel AutoSSL is enough).
- One AI provider key: `XAI_API_KEY`, `GEMINI_API_KEY` (free tier) or `GROQ_API_KEY` (free tier).
- About 40 MB of disk for the virtual environment.

## Python App settings

| Field | Value |
|---|---|
| Python version | 3.10 or newer (3.12 recommended) |
| Application root | `fanoos-app` (the folder created when you extract the ZIP in your home directory) |
| Application URL | your domain or subdomain, with the path left empty |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |
| Passenger log file | e.g. `/home/<user>/logs/fanoos.log` |

Then, under **Configuration files**, add `requirements.txt` and click **Run Pip Install**.
Without that button, use cPanel **Terminal**:

```bash
source /home/<user>/virtualenv/fanoos-app/<version>/bin/activate && cd /home/<user>/fanoos-app && pip install -r requirements.txt
```

## Environment variables

Set them in the Python App page (**Environment variables → Add variable**), then **Restart**.
See `.env.example` for every variable with its default. Only one is required:

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `XAI_API_KEY` | one of them | Never put a key in JavaScript, HTML or `public_html` |
| `FANOOS_PROVIDER` | no | `xai`, `gemini` or `groq`; empty = first key present (xai → gemini → groq) |
| `FANOOS_MODEL` | no | Override the provider's default model |
| `FANOOS_RATE_LIMIT` | no | Default `10/hour` per visitor IP, protects your AI quota |
| `FANOOS_MAX_CONCURRENT` | no | Default `2` reviews at once |
| `FANOOS_TIMEOUT` | no | Default `180` seconds |
| `FANOOS_MAX_UPLOAD_MB` | no | Default `15` |
| `FANOOS_ENV` | no | Default `production` (disables `/docs`) |
| `FANOOS_TRUST_PROXY` | no | `1` only behind a proxy that sets `X-Forwarded-*` |
| `FANOOS_LOG_LEVEL` | no | Default `INFO` |

A `.env` file in `fanoos-app/` also works (it never overrides variables set in cPanel), but
the cPanel variables are safer. `fanoos-app/` lives in your home directory, **outside
`public_html`**, so none of its files can be downloaded directly.

## Verify

1. `https://<your-domain>/health` returns
   `{"status":"ok","version":"0.3.0","provider":"gemini","live_search":false}`.
   `provider` is `null` if no key is configured.
2. Open `https://<your-domain>/`, paste a public portfolio URL, click **روشن کن**, and wait 30 to
   120 seconds for the report.
3. Switch to the PDF tab, upload a portfolio PDF and check the report again.

## What is inside

```
fanoos-app/
├── passenger_wsgi.py   # Passenger entry point (WSGI via a2wsgi → FastAPI)
├── requirements.txt    # pinned production dependencies
├── .env.example        # every setting, placeholders only
├── fanoos/             # the Fanoos agent, providers, parser and web server
├── web/                # the web UI (HTML/CSS/JS, Three.js lantern, fonts); no build step
├── assets/             # logos and favicon
├── README_DEPLOY.md    # this file
├── DEPLOY_CPanel_FA.md # Persian step-by-step guide
├── CHANGELOG.md
└── LICENSE
```

## Security built in

SSRF protection on every URL and redirect hop; uploads limited to 15 MB, PDF only and
processed in a temporary folder that is deleted; per-IP rate limit and concurrency cap;
Content-Security-Policy, `X-Frame-Options`, `nosniff` and HSTS over HTTPS; no CORS; API keys
redacted from every error and never returned by any endpoint; model output rendered as text.

## Updating

Upload the new ZIP, extract it over `fanoos-app` (overwrite), click **Run Pip Install**, then
**Restart**. Your environment variables are kept by cPanel.
