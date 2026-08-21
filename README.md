# Job Monitor — India

A self-hosted, zero-server monitor for newly posted **Indian software engineering
jobs** (intern / fresher / experienced up to ~5 yrs) across **big tech India
centres, Indian product companies & unicorns, fintech, GCCs, and semiconductor
/ EDA firms**.

- **GitHub Actions** runs the scans on a schedule (big tech every 3 hours, a
  full sweep of everything every 3 hours, offset by 30 min). No server, no cost.
- **Discord** receives an alert for every genuinely new posting, with a direct
  apply link. The same job ID is **never notified twice**.
- **A web dashboard** (GitHub Pages) shows everything found so far, filters by
  city (Bengaluru, Hyderabad, Pune, Delhi NCR…), and lets you mark roles
  **Applied / Skip / Interview**. Your marks are saved back to the repo and
  survive forever.

---

## 1. How it works (30-second version)

```
                     ┌────────────────────────────────────────────┐
 GitHub Actions cron │  every 3h  → scan big tech (12 sources)    │
                     │  every 3h  → scan everything (60 sources)  │
                     └───────────────────┬────────────────────────┘
                                         │
             fetchers pull JSON from public careers APIs
             (Greenhouse, Lever, Ashby, Workday, Eightfold,
              SmartRecruiters + Amazon India / Microsoft India
              + the Instahyre India aggregator)
                                         │
             filters: India-only · SWE + adjacent roles · tier
             detection · staff/principal/senior/lead excluded
                                         │
             compare against docs/data/jobs.json (the database,
             committed back into this repo after every run)
                                         │
              new jobs only → Discord webhook notification
```

The dashboard is a single static HTML page that reads `docs/data/jobs.json`
and writes your Applied/Skip status back through the GitHub API.

A full sweep currently pulls ~9,600 raw postings and narrows them to ~570
in-scope Indian roles.

---

## 2. What every file does

```
job-monitor/
├── README.md                      ← this file
├── CLAUDE.md                      ← orientation notes for Claude Code
├── requirements.txt               ← Python dependencies (requests, PyYAML)
│
├── config/
│   └── companies.yaml             ← THE COMPANY LIST. Three sections:
│                                    · bigtech:     scanned every 3 hours
│                                    · other:       scanned in the full sweep
│                                    · aggregators: Instahyre
│                                    Each entry names a fetcher + its
│                                    parameters (ATS token, Workday tenant…).
│                                    Every entry was verified to return real
│                                    India postings; the india= comments show
│                                    how many each board had when added.
│                                    This is the file you'll edit most.
│
├── monitor/                       ← the Python package (the scanner)
│   ├── main.py                    ← ENTRYPOINT. Reads the config, runs all
│   │                                fetchers in parallel, filters results,
│   │                                dedupes against the database, saves new
│   │                                jobs, triggers Discord. CLI flags:
│   │                                --tier bigtech|other|all, --dry-run,
│   │                                --no-notify, --include-senior
│   ├── filters.py                 ← ALL FILTERING RULES as regexes:
│   │                                which titles count as SWE/adjacent
│   │                                (including Indian title vocabulary — SDE,
│   │                                MTS, Technology Analyst, Programmer
│   │                                Analyst, Graduate Engineer Trainee), tier
│   │                                detection (intern / fresher / experienced),
│   │                                staff/principal/senior/lead exclusion, and
│   │                                India-location detection (metros, states,
│   │                                "IND" country codes, work-from-home).
│   │                                Edit this to widen or narrow scope.
│   ├── state.py                   ← the "database" layer. Reads/writes
│   │                                docs/data/jobs.json, generates stable
│   │                                job IDs (company + hash of job ID/URL),
│   │                                appends only unseen jobs, NEVER touches
│   │                                your Applied/Skip statuses.
│   ├── notify.py                  ← Discord webhook sender. Batches embeds
│   │                                (10 per message), handles rate limits.
│   │                                Reads DISCORD_WEBHOOK_URL from env.
│   │
│   └── fetchers/                  ← one module per data-source type
│       ├── __init__.py            ← FETCHERS registry: maps the `fetcher:`
│       │                            name in companies.yaml to a function
│       ├── http.py                ← shared HTTP session (browser-like
│       │                            User-Agent, retries on 429/5xx)
│       ├── generic.py             ← the 6 generic ATS fetchers. Any company
│       │                            on Greenhouse, Lever, Ashby, Workday,
│       │                            Eightfold, or SmartRecruiters can be
│       │                            added with 3–5 lines of YAML.
│       ├── custom.py              ← company-specific fetchers pinned to
│       │                            India: Amazon (normalized_country_code
│       │                            =IND) and Microsoft (lc=India). These
│       │                            endpoints are unofficial and may change.
│       └── instahyre.py           ← the India aggregator. ~13k live Indian
│                                    tech postings; this is what covers the
│                                    companies with no usable public API —
│                                    Google India, Uber India, Flipkart,
│                                    Swiggy, Zomato, Ola, and the whole
│                                    TCS/Infosys/Wipro services sector.
│
├── docs/                          ← served by GitHub Pages
│   ├── index.html                 ← THE DASHBOARD. Single self-contained
│   │                                page: filters by tier/status/company/city,
│   │                                search, Applied/Skip/Interview buttons.
│   │                                Saves statuses back to the repo via the
│   │                                GitHub API (your token stays in your
│   │                                browser's localStorage only).
│   └── data/
│       └── jobs.json              ← THE DATABASE. One entry per job ever
│                                    seen: company, title, tier, location,
│                                    url, first_seen, status. Ships empty;
│                                    Actions commits updates after each run.
│
└── .github/workflows/
    ├── scan-all.yml               ← THE SCHEDULED ONE. cron "30 */3 * * *"
    │                                (every 3h at :30 UTC = 06:00, 09:00,
    │                                12:00… IST): all 60 sources, commits
    │                                jobs.json if changed. Manual runs take
    │                                tier / dry-run / no-notify / include-senior
    │                                as form inputs.
    └── scan-bigtech.yml           ← manual only, no cron: a ~30s check of just
                                     the 11 big-tech India sources. It has no
                                     schedule on purpose — `--tier all` already
                                     includes everything it scans, so a cron
                                     here would only duplicate the sweep.
```

### Why only one workflow is scheduled

`--tier bigtech` is a strict subset of `--tier all`, so running both on a cron
did the same work twice. It also had the priorities backwards for an India
monitor: the companies worth checking often — PhonePe, Paytm, Meesho, CRED,
Groww, InMobi — live in the `other` tier, which only the full sweep covers.
One sweep every 3 hours covers all 60 sources; the big-tech workflow stays
around for a fast manual check.

Both workflows share the `job-scan` concurrency group so they can never write
`docs/data/jobs.json` at the same time, and both push through a merge-and-retry
loop: if you happen to be marking jobs Applied while a scan finishes, the
scan's push is rejected, and `monitor/merge_state.py` merges the two copies
(your statuses win, the scan's new job ids are added) instead of failing the
run and re-notifying those jobs on the next pass.

---

## 3. Setup guide — from zip to working (~15 minutes)

### Prerequisites

- A GitHub account.
- Git installed (`git --version` in a terminal; download from
  https://git-scm.com if missing).
- A Discord server where you can manage webhooks (any server you own; create
  one free in Discord with **+ Add a Server** if needed).
- (Optional, for local testing) Python 3.10+.

### Step 1 — Create the GitHub repository

1. Go to https://github.com/new
2. Repository name: `job-monitor` (anything works).
3. Visibility: **Public** is simplest (free GitHub Pages). Private also works,
   but Pages on a private repo needs GitHub Pro — see Step 6 for the
   workaround.
4. Do **NOT** check "Add a README" / .gitignore / license (the project already
   has them; an empty repo avoids merge conflicts).
5. Click **Create repository**.

### Step 2 — Push the project

Open a terminal **inside the `job-monitor` folder** (the one containing
`README.md`) and run:

```bash
git init
git add -A
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/job-monitor.git
git push -u origin main
```

Replace `<YOUR-USERNAME>` with your GitHub username. If git asks you to log
in, follow the browser prompt (or use GitHub Desktop / `gh auth login` if you
prefer).

### Step 3 — Create the Discord webhook

1. In Discord, pick (or create) the channel where alerts should land, e.g.
   `#job-alerts`.
2. Server Settings → **Integrations** → **Webhooks** → **New Webhook**.
3. Name it (e.g. "Job Monitor"), select the channel, click
   **Copy Webhook URL**. Treat it like a password — anyone with it can post to
   your channel.

### Step 4 — Add the webhook as a repo secret

1. On GitHub: your repo → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**.
2. Name: `DISCORD_WEBHOOK_URL` (exactly this, case-sensitive).
3. Secret: paste the webhook URL. Click **Add secret**.

### Step 5 — Enable workflows and run the seed scan

1. Repo → **Actions** tab. If prompted "Workflows aren't being run on this
   repository", click **I understand my workflows, go ahead and enable them**.
2. In the left sidebar click **Full sweep India (every 3h)** → **Run workflow**.
3. Wait 3–5 minutes, then read the log of the "Run full sweep" step. You'll see
   one line per source (`✓ Amazon India: 200 raw postings` / `! SomeCompany:
   FAILED …`) and a summary like
   `9635 raw -> 567 in scope -> 567 new (seed run: notifications suppressed)`.

**Important:** this first run is a **seed run**. It records everything
currently open into the database **without sending any Discord messages** —
otherwise you'd be flooded with hundreds of alerts for old postings. Every
run after this one notifies **only new postings**.

4. Check that the run committed — the repo should show a commit like
   `scan(all): update jobs.json`, and `docs/data/jobs.json` should be full.

### Step 6 — Turn on the dashboard (GitHub Pages)

1. Repo → **Settings** → **Pages**.
2. Source = **Deploy from a branch**, Branch = `main`, Folder = **/docs**. Save.
3. After ~1 minute your dashboard is live at
   `https://<YOUR-USERNAME>.github.io/job-monitor/`.

**Private repo without GitHub Pro?** Skip Pages entirely: pull the repo and
open `docs/index.html` directly in your browser — the dashboard works the same.

### Step 7 — Enable "mark as Applied" saving

1. GitHub → avatar → **Settings** → **Developer settings** → **Personal access
   tokens** → **Fine-grained tokens** → **Generate new token**.
2. Repository access: **Only select repositories** → choose `job-monitor`.
3. Permissions → Repository permissions → **Contents** → **Read and write**.
   Nothing else.
4. Generate, copy the `github_pat_...` value.
5. Open your dashboard → **⚙ GitHub token** → Owner = your username,
   Repo = `job-monitor`, Branch = `main`, Token = the PAT. Save.

The token is stored **only in your own browser's localStorage** — it is never
committed or sent anywhere except api.github.com.

### Step 8 — Verify end-to-end

1. In the dashboard, click **✓ Applied** on any job → "Saved ✓", and on GitHub
   a commit `dashboard: update statuses`.
2. Actions → run **Scan big tech India (manual)** → since the seed already
   happened, any *genuinely new* posting now produces a Discord message. (If
   nothing new was posted since the last sweep, no message — that's correct.)

---

## 4. Daily use

- New postings arrive in Discord with tier, location, and a direct apply link.
- Open the dashboard (default filter shows **Open (new)**), narrow to your city,
  apply on the company site, click **✓ Applied**. Clicking again undoes it.
- **✗ Skip** hides roles you don't want; **★ Interview** tracks progress.
- Applied/skipped roles never re-alert. The scanner only ever *adds* new job
  IDs — it cannot overwrite your statuses.

---

## 5. Customizing

| Want to… | Edit |
|---|---|
| Add/remove a company | `config/companies.yaml` (see comment at top for how to find a company's Greenhouse/Lever/Ashby/Workday token) |
| Change scan frequency | the `cron:` line in `.github/workflows/scan-all.yml` — times are **UTC**; IST is UTC+5:30 |
| Include Senior/Lead titles | tick **include_senior** when running the workflow manually, or add `--include-senior` to the `run:` command for every run |
| Run a one-off scan by hand | Actions → **Full sweep India** → Run workflow; the form offers tier, dry-run, no-notify and include-senior |
| Change role/tier/location rules | the regexes in `monitor/filters.py` |
| Wider aggregator coverage | raise `max_pages` under `aggregators:` in the config (requests = job_types × job_functions × max_pages) |
| Test locally without side effects | `pip install -r requirements.txt` then `python -m monitor.main --tier all --dry-run` |

---

## 6. Troubleshooting

**A company shows `! FAILED` in every run.** Its endpoint or ATS token is
wrong/changed. Open that company's careers page with your browser's network
tab (F12 → Network) and look for requests to `boards-api.greenhouse.io/...`,
`api.lever.co/...`, `api.ashbyhq.com/...`, or
`<tenant>.wdX.myworkdayjobs.com/wday/cxs/...`, then correct the entry in
`companies.yaml`.

**Workday board returns HTTP 400.** That tenant rejects the
`locationCountry` facet. Drop the `facets:` line and use
`search: software engineer India` instead — the location filter catches the
rest.

**A company returns postings but none are in scope.** Its India roles are
outside the first ~100 results for that search. Give the entry a narrower
`search:` value, or add `max_results: 200` for Workday boards.

**No Discord messages ever.** Check the secret name is exactly
`DISCORD_WEBHOOK_URL`; the Actions log prints `DISCORD_WEBHOOK_URL not set` if
missing. The very first run never notifies (seed), and later runs only notify
*new* jobs.

**"Save failed" in the dashboard.** Token expired, missing Contents-write
permission, or wrong owner/repo/branch in ⚙ settings.

**Workflow stops running after ~60 days.** GitHub disables cron on repositories
with no activity. The scanner's own commits count as activity, so this only
matters if all scans fail for 60 days straight.

**jobs.json grows big.** Delete old `applied`/`skip` entries occasionally.
(Past ~1 MB the dashboard's save round-trip may fail due to a GitHub API limit;
prune before that.)

---

## 7. Known limitations (honest list)

- **Unofficial APIs**: the fetchers use the same JSON endpoints the careers
  sites themselves use — they can change without notice. A failing fetcher is
  logged and skipped, never fatal.
- **Google, Apple, Meta, LinkedIn and Uber have no usable public careers API**
  any more (`careers.google.com/api/v3` and
  `uber.com/api/loadSearchJobsResults` both 404; `jobs.apple.com` refuses
  non-browser clients). Their India roles arrive via Instahyre instead, which
  means a delay and less complete coverage.
- **Naukri and foundit are not usable as sources.** Naukri's job API returns
  `recaptcha required` to server-side clients and foundit rejects the request
  at content negotiation. Instahyre is the aggregator that does work.
- **Fresher/intern volume is genuinely low here.** Most Indian campus hiring
  runs through college placement cells, TCS NextStep, and Naukri rather than
  the ATS boards this tool reads. Expect the `experienced` tier to dominate.
- **"Experienced ≤5 yrs" is title-based** (SDE II/III, Engineer 2, MTS 2…).
  Plain "Software Engineer" titles are included too — verify the years
  requirement in the actual posting.
- **The IT services majors** (TCS, Infosys, Wipro, HCLTech, Tech Mahindra) run
  JavaScript-only career portals with no JSON API; they appear only when they
  post through Instahyre.
