"""Company-specific fetchers for big-tech careers APIs, pinned to India.

These use unofficial-but-public JSON endpoints that back each company's own
careers site. They can change without notice — if one starts failing, check
the network tab of the careers page and update the endpoint.

Google, Apple, Tesla and Uber used to live here. Their endpoints were removed
or locked down (careers.google.com/api/v3 and uber.com/api/loadSearchJobsResults
both 404 now, jobs.apple.com resets the connection for non-browser clients), so
they are no longer fetched directly; India roles for those companies surface
through the Instahyre aggregator instead.
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


def microsoft(c):
    """India postings from the Microsoft careers search API (`lc=India`)."""
    s = session()
    out = []
    for pg in (1, 2):
        url = ("https://gcsservices.careers.microsoft.com/search/api/v1/search"
               f"?q={c.get('search', 'software engineer').replace(' ', '%20')}"
               f"&lc=India&l=en_us&pg={pg}&pgSz=100&o=Relevance&flt=true")
        data = get_json(s, url)
        jobs = (((data.get("operationResult") or {}).get("result") or {}).get("jobs")) or []
        if not jobs:
            break
        for j in jobs:
            props = j.get("properties") or {}
            out.append({
                "company": "Microsoft",
                "title": j.get("title", ""),
                "location": props.get("primaryLocation", "") or ", ".join(
                    props.get("locations", []) or []),
                "url": f"https://jobs.careers.microsoft.com/global/en/job/{j.get('jobId','')}",
                "external_id": str(j.get("jobId", "")),
                "source": "microsoft careers",
                "posted_at": iso_date(props.get("postingDate")),
                "employment_type": props.get("employmentType", ""),
                "workplace": ("Remote" if str(props.get("workSiteFlexibility", "")).lower()
                              .startswith("up to 100") else ""),
                "department": props.get("discipline", "") or props.get("profession", ""),
                "snippet": clean_text(props.get("description", "")),
            })
    return out
