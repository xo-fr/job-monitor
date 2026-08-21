"""Company-specific fetchers for big-tech careers APIs, pinned to India.

These use unofficial-but-public JSON endpoints that back each company's own
careers site. They can change without notice — if one starts failing, check
the network tab of the careers page and update the endpoint.

Google, Apple, Tesla, Uber and Microsoft used to live here. Every one of those
endpoints is now gone, so they are not fetched directly any more; India roles
for those companies surface through the Instahyre aggregator instead. Verified
before removal, so nobody has to re-discover it:

  - careers.google.com/api/v3/search          -> 404
  - uber.com/api/loadSearchJobsResults        -> 404 "Missing RPC handler"
  - jobs.apple.com/api/role/search            -> connection reset for non-browsers
  - gcsservices.careers.microsoft.com         -> serves a cert valid only for
    *.azureedge.net, so TLS verification fails for every correct client (this
    reproduces identically on a GitHub Actions runner — it is not a local
    network problem), and no replacement JSON endpoint is exposed by the
    jobs.careers.microsoft.com SPA.
"""
from .http import session, get_json, iso_date, clean_text


def _sched(value: str) -> str:
    """Amazon job_schedule_type -> the shared vocabulary."""
    v = str(value or "").lower()
    return "Full-time" if "full" in v else ("Part-time" if "part" in v else "")


def amazon(c):
    """India postings from amazon.jobs.

    The country filter is `normalized_country_code[]=IND`; the plain
    `country[]` parameter is silently ignored by the endpoint.
    """
    s = session()
    query = c.get("search", "software engineer").replace(" ", "+")
    out = []
    for offset in (0, 100):
        url = ("https://www.amazon.jobs/en/search.json?result_limit=100&sort=recent"
               f"&offset={offset}"
               "&category%5B%5D=software-development"
               "&normalized_country_code%5B%5D=IND"
               f"&base_query={query}")
        data = get_json(s, url)
        jobs = data.get("jobs", [])
        if not jobs:
            break
        for j in jobs:
            out.append({
                "company": "Amazon",
                "title": j.get("title", ""),
                "location": j.get("normalized_location", "") or j.get("location", ""),
                "country": "India",          # pinned by the country filter above
                "url": "https://www.amazon.jobs" + j.get("job_path", ""),
                "external_id": str(j.get("id_icims", "") or j.get("id", "")),
                "source": "amazon.jobs",
                "posted_at": iso_date(j.get("posted_date")),
                "employment_type": "Intern" if j.get("is_intern") else _sched(
                    j.get("job_schedule_type", "")),
                "department": j.get("job_category", "") or j.get("business_category", ""),
                "snippet": clean_text(j.get("description_short", "") or j.get("description", "")),
            })
    return out
