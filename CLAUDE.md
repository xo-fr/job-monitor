# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A zero-server monitor for **Indian** software engineering job postings (intern / fresher
/ experienced ≤5yrs) across big-tech India centres, Indian product companies, fintech,
GCCs, and semiconductor/EDA firms. GitHub Actions runs the scan on a cron schedule,
commits results into `docs/data/jobs.json`, and posts new postings to a Discord webhook.
`docs/index.html` is a static dashboard (served via GitHub Pages) for triaging results.

The project was originally US-focused and was pivoted to India; if you find a stray
US-market assumption, it is a leftover bug, not intentional.

There is no build step, no server, and no database beyond the committed JSON file.

## Commands

```bash
pip install -r requirements.txt

# Run a scan locally without saving state or sending Discord notifications:
python -m monitor.main --tier all --dry-run
python -m monitor.main --tier bigtech --dry-run

# Real run (writes docs/data/jobs.json, sends Discord webhook if DISCORD_WEBHOOK_URL is set):
python -m monitor.main --tier all
python -m monitor.main --tier bigtech
python -m monitor.main --tier all --include-senior   # widen scope to include Senior titles
python -m monitor.main --tier all --no-notify        # save/backfill state but suppress Discord (use after fixing a broken fetcher, to absorb its backlog quietly)
```

There is no test suite and no linter configured. To verify a change to a fetcher or to
`filters.py`, run `--dry-run` and read the printed `raw -> in scope -> new` summary and
the per-company `✓ / ∅ / ! FAILED` lines — `∅` means the endpoint was reachable but
returned zero postings, `!` means the fetcher raised. A single company's fetcher can be
exercised in isolation from a Python shell: `from monitor.fetchers import FETCHERS;
FETCHERS["greenhouse"]({"name": "Foo", "token": "foo"})`.

## Architecture

**Pipeline** (`monitor/main.py` is the entrypoint, run as `python -m monitor.main`):

1. Load `config/companies.yaml`, filter to the companies in scope for `--tier`
   (`bigtech`, `other`, or `all` — `other` also pulls in `aggregators`).
2. Run every company's fetcher concurrently (`ThreadPoolExecutor`, 8 workers). Each
   fetcher is a plain function `(company_dict) -> list[raw_job_dict]`; a fetcher that
   raises is caught, logged, and treated as zero results — one bad endpoint never fails
   the whole run.
3. `filters.in_scope()` (in `monitor/filters.py`) classifies each raw job by title regex
   (role match, tier: intern/newgrad/experienced, staff/senior/lead exclusion) and
   location (India-only). Only jobs that pass both are kept. Note the tier id stays
   `newgrad` in the data while the UI labels it "fresher" — don't rename the id without
   migrating `docs/data/jobs.json`.
4. `state.add_new()` (in `monitor/state.py`) diffs against `docs/data/jobs.json` using a
   stable id (`company + sha1(external_id or url)[:12]`) and returns only the jobs never
   seen before. Existing entries — crucially their `status` field, which the dashboard
   writes — are **never** overwritten; only missing enrichment fields get backfilled.
5. On the very first run (empty state file), everything found is seeded into state with
   **no Discord notification** — otherwise a fresh repo would flood the webhook with
   every currently-open role. Every run after that notifies only genuinely new job ids.
6. `notify.send()` posts batches of 10 Discord embeds per message (Discord's embed
   limit) with a short delay between batches for rate limiting.

**Fetchers** (`monitor/fetchers/`) all normalize to the same raw job shape (`company`,
`title`, `location`, `url`, `external_id`, `source`, optionally `country`, `posted_at`,
`comp`, `employment_type`, `workplace`, `department`, `snippet`) so `filters.py` and
`state.py` never need to know which ATS a job came from:
- `generic.py` — six fetchers driven entirely by `companies.yaml` parameters:
  Greenhouse, Lever, Ashby, Workday, Eightfold, SmartRecruiters. Adding a company on one
  of these ATSes is a config-only change (see the token-finding instructions at the top
  of `companies.yaml`).
- `custom.py` — Amazon only (`normalized_country_code[]=IND`; the plain `country[]` param
  is silently ignored by that endpoint). The Google, Apple, Tesla, Uber and Microsoft
  fetchers were **deleted, not disabled**, and the module header records exactly what
  each endpoint does now so nobody re-discovers it. Microsoft is the subtle one:
  `gcsservices.careers.microsoft.com` serves a certificate valid only for
  `*.azureedge.net`, which reproduces identically on a GitHub Actions runner — if you see
  that SSL error, it is Microsoft's misconfiguration, not the local network. Don't re-add
  any of them without verifying the endpoint first.
- `instahyre.py` — the India aggregator (replaced the US-only SimplifyJobs scraper). It
  is what covers companies with no usable public API at all: Google India, Uber India,
  Flipkart, Swiggy, Zomato, and the TCS/Infosys/Wipro services sector. Three API quirks
  are load-bearing and documented in the module: `limit` is ignored (always 35 rows), only
  one `job_functions` value is accepted per request, and there is no sort parameter — but
  ordering is deterministic across calls, which is what makes new-id diffing meaningful.
- `http.py` — shared `requests.Session` (browser UA), retry-on-429/5xx wrapper, and the
  normalization helpers (`iso_date`, `rel_date`, `clean_text`) fetchers use to produce
  consistent enrichment fields from each ATS's own date/HTML formats.
- The `fetcher:` string in each `companies.yaml` entry is looked up in the `FETCHERS`
  dict in `fetchers/__init__.py` — that's the only place a new fetcher module needs to
  be registered.

**State** (`docs/data/jobs.json`, `monitor/state.py`): the single source of truth, keyed
by job id. The dashboard (`docs/index.html`) only ever edits the `status` field
(`new|applied|skip|interview|rejected|closed`) via a direct GitHub Contents API PUT
(fetches current file SHA, then commits `dashboard: update statuses`); the scanner only
ever adds new ids or backfills blank enrichment fields on existing ones. This separation
of writers is why user triage state is safe from being clobbered by a scan. The GitHub
token lives only in the browser's `localStorage`, entered once through the dashboard's
⚙ settings panel.

**Scheduling** (`.github/workflows/`): only `scan-all.yml` has a cron (`30 */3 * * *` =
06:00, 09:00, 12:00… IST). `scan-bigtech.yml` is `workflow_dispatch`-only **by design** —
`--tier all` is a strict superset of `--tier bigtech`, so scheduling both just did the
work twice, and the Indian companies worth polling often live in the `other` tier that
only the full sweep reaches. Don't "fix" the missing cron by adding one back. Both share
the `job-scan` concurrency group, set `TZ: Asia/Kolkata`, carry `timeout-minutes`, and
take tier/dry-run/no-notify/include-senior as `workflow_dispatch` inputs (read via env
vars rather than inline expressions, so the booleans survive `bash -e`).

Both push through a merge-and-retry loop rather than `git pull --rebase`. The rebase
approach had a real failure mode: the dashboard and the scanner both write
`docs/data/jobs.json`, so a scan finishing mid-triage hit a JSON conflict, failed the
run *after* `notify.send()` had already fired, and re-notified the same jobs on the next
pass. On a rejected push the workflow now fetches the remote copy and runs
`python -m monitor.merge_state <remote> <local>` (remote wins on `status`, local
contributes new ids), then resets onto the remote tip and retries — up to 3 times.

## Adding or fixing a company

- New company on Greenhouse/Lever/Ashby/Workday/Eightfold/SmartRecruiters: add an entry
  to `config/companies.yaml` only (find the token/tenant per the comment at the top of
  that file). No Python change needed.
- New company with a bespoke careers API: add a function to `monitor/fetchers/custom.py`
  returning the normalized raw job shape used elsewhere, then register it in
  `fetchers/__init__.py`'s `FETCHERS` dict.
- A company failing every run: its ATS token/tenant or an unofficial endpoint changed.
  Open the careers page's network tab and diff against the URL the fetcher builds.
- Changing which titles/locations are in scope: edit the regexes in `monitor/filters.py`
  (`ROLE_INCLUDE`/`ROLE_EXCLUDE`, `INTERN`/`NEWGRAD`/`EXPERIENCED`, `INDIA_HINT`) — there
  is no other place role/tier/location logic lives. Two traps when editing these: the
  `(?<!technical )` guard on `\bstaff\b` is what keeps "Member of Technical Staff" (a
  normal Indian mid-level IC title) in scope, and India detection deliberately matches
  `\bind\b` but never `\bin\b`, because "Indianapolis, IN" would otherwise read as India.

## Verified-source discipline

Every entry in `config/companies.yaml` was confirmed to return real India-located
postings before being added, and carries an `# india=N` comment recording the count at
the time. Global boards are pinned to India where the API allows it (Workday
`facets: {locationCountry: [c4f78be1a8f14da0ab49ce1162348a5e]}` — accepted by some
tenants, HTTP 400 from others, in which case use `search: software engineer India`).
Keep this up: when adding a company, probe the endpoint first and only commit the entry
if India postings actually come back. A dry run should show 59 sources and roughly
9.6k raw → 570 in scope, with zero FAILED lines — a permanently-failing source is a
bug to remove, not background noise.
