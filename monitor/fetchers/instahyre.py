"""Aggregator fetcher: Instahyre (India-only tech job platform).

Replaces the US-oriented SimplifyJobs aggregator. Instahyre lists ~13k live
Indian tech roles across hundreds of companies — including the ones with no
usable public careers API at all (Google India, Uber India, Flipkart, Swiggy,
Zomato, TCS/Infosys/Wipro and most of the services sector).

Endpoint: the public JSON API the instahyre.com job board itself calls.
  https://www.instahyre.com/api/v1/job_search?job_type=<t>&job_functions=<f>&offset=<n>

Quirks worth knowing before editing this:
  - `limit` is ignored; the API always returns 35 rows per page, so pagination
    steps by PAGE_SIZE.
  - Only ONE `job_functions` value is accepted per request (repeating the
    parameter 400s), hence the loop over ids.
  - There is no sort parameter — but result ordering is deterministic across
    calls, so paging the same offsets each scan yields a stable set and only
    genuinely-new postings show up as new ids.
  - Every posting is in India by definition, so `country` is set explicitly;
    that is what lets "Work From Home" rows through the location filter.
"""
import time

from .http import session, get_json

BASE = "https://www.instahyre.com/api/v1/job_search"
PAGE_SIZE = 35

# job_functions ids, from the API's own facet list.
FUNCTIONS = {
    10: "Backend Development",
    1: "Full-Stack Development",
    9: "Data Science / Machine Learning",
    3: "Frontend / Mobile Development",
    76: "Other Software Development",
}
# job_type ids: 1 = full time, 2 = internship.
JOB_TYPES = {1: "Full-time", 2: "Intern"}


def instahyre(c):
    """c: {name, job_functions?: [ids], job_types?: [ids], max_pages?: int}"""
    functions = c.get("job_functions") or list(FUNCTIONS)
    job_types = c.get("job_types") or list(JOB_TYPES)
    max_pages = int(c.get("max_pages", 3))

    s = session()
    s.headers.update({"Referer": "https://www.instahyre.com/search-jobs/",
                      "X-Requested-With": "XMLHttpRequest"})
    out, seen = [], set()
    for job_type in job_types:
        for fn in functions:
            for page in range(max_pages):
                url = (f"{BASE}?job_type={job_type}&job_functions={fn}"
                       f"&offset={page * PAGE_SIZE}&limit={PAGE_SIZE}")
                try:
                    data = get_json(s, url)
                except Exception as e:  # noqa: BLE001 — one bad page must not kill the sweep
                    print(f"    instahyre: fn={fn} type={job_type} page={page} failed: {e}")
                    break
                rows = data.get("objects") or []
                if not rows:
                    break
                for j in rows:
                    jid = str(j.get("id", ""))
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    employer = j.get("employer") or {}
                    out.append({
                        "company": employer.get("company_name", "") or "Unknown",
                        "title": j.get("title", "") or j.get("candidate_title", ""),
                        # "Bangalore,Mumbai" -> "Bangalore, Mumbai"
                        "location": ", ".join(
                            p.strip() for p in str(j.get("locations", "")).split(",") if p.strip()),
                        "country": "India",
                        "url": j.get("public_url", ""),
                        "external_id": jid,
                        "source": "instahyre",
                        "employment_type": JOB_TYPES.get(job_type, ""),
                        "department": FUNCTIONS.get(fn, ""),
                        "snippet": ", ".join(j.get("keywords") or [])[:180],
                    })
                if len(rows) < PAGE_SIZE:
                    break
                time.sleep(0.4)   # be a polite client
    return out
