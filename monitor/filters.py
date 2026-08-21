"""Role, tier, and India-location filtering.

Scope (from project spec):
  - Roles: SWE + adjacent tech (data, ML, DevOps/SRE, security, QA, mobile/web).
  - Tiers: intern, fresher / new grad / entry level, experienced up to ~5 years.
  - Exclude: staff/principal/architect/management and (by default) senior & lead titles.
  - India locations only (incl. India-remote / "work from home").
"""
import re

# ---- role scope ------------------------------------------------------------
# Includes the title vocabulary Indian employers actually use: SDE, MTS
# (Member of Technical Staff), "Technology Analyst" (Infosys), "Programmer
# Analyst" (Cognizant), "Systems Engineer" (TCS/Wipro).
ROLE_INCLUDE = re.compile(
    r"software|swe\b|sde\b|developer|full.?stack|front.?end|back.?end|mobile engineer"
    r"|ios engineer|android|machine learning|\bml\b|\bai engineer|data engineer"
    r"|data scientist|devops|site reliability|\bsre\b|security engineer"
    r"|infrastructure engineer|platform engineer|cloud engineer|systems? engineer"
    r"|test engineer|quality (assurance|engineer)|\bqa engineer"
    r"|member of technical staff|\bmts\b|programmer|technology analyst"
    r"|application developer|graduate engineer trainee|\bget\b",
    re.I,
)

ROLE_EXCLUDE = re.compile(
    # (?<!technical ) keeps "Member of Technical Staff" — a normal Indian
    # mid-level IC title — out of the Staff-Engineer exclusion.
    r"(?<!technical )\bstaff\b|principal|distinguished|architect|manager|director|\bvp\b"
    r"|vice president|head of|chief|fellow|executive|recruiter|sales|account"
    r"|\bhr\b|attorney|counsel|technician\b|electrical|mechanical|civil engineer"
    r"|manufacturing|hvac|facilities|\bbpo\b|voice process|tele.?caller"
    r"|business development|talent acquisition",
    re.I,
)

# Titles above the ~5-year band. "Lead"/"Tech Lead" is India's usual label for
# an 8+ year IC, so it rides along with Senior behind --include-senior.
SENIOR = re.compile(r"\bsenior\b|\bsr\.?\s|\bsr\.$|\blead\b|\bii+\b\s*\+|\bl[4-9]\b", re.I)

# ---- tier detection --------------------------------------------------------
INTERN = re.compile(r"\bintern(ship)?\b|co-?op\b|industrial trainee|summer analyst", re.I)

# "Fresher" and "Graduate Engineer Trainee (GET)" are the Indian equivalents of
# "new grad"; campus-cycle roles often carry the batch year in the title.
NEWGRAD = re.compile(
    r"fresher|new ?grad|university grad|campus|early.?career|entry.?level|college grad"
    r"|\bgraduate\b|graduate engineer trainee|\bget\b|\btrainee\b|apprentice"
    r"|(engineer|swe|sde|mts|developer|staff)\s*[-–]?\s*(i|1)\b|\bl3\b|\be3\b"
    r"|associate (software|engineer|developer)|\b20\d{2}\b(?!\s*(years|yrs))",
    re.I,
)
# Explicit mid-level markers (II/III/2/3). A plain "Software Engineer" title
# also lands in "experienced" — verify years-of-experience in the posting.
EXPERIENCED = re.compile(
    r"(engineer|swe|sde|mts|developer|staff)\s*[-–]?\s*(ii|iii|2|3)\b|mid.?level", re.I)

# ---- India location --------------------------------------------------------
INDIA_CITIES = (
    r"bengaluru|bangalore|hyderabad|pune|chennai|mumbai|new delhi|\bdelhi\b"
    r"|gurgaon|gurugram|noida|kolkata|ahmedabad|jaipur|kochi|cochin|coimbatore"
    r"|thiruvananthapuram|trivandrum|chandigarh|indore|bhubaneswar|mysuru|mysore"
    r"|nagpur|vadodara|surat|visakhapatnam|vizag|gandhinagar|lucknow|kanpur"
    r"|nashik|thane|navi mumbai|whitefield|electronic city|hinjewadi|manyata"
    r"|madhapur|gachibowli|powai|\bncr\b"
)
INDIA_STATES = (
    r"karnataka|maharashtra|telangana|tamil nadu|haryana|uttar pradesh"
    r"|west bengal|gujarat|kerala|andhra pradesh|punjab|rajasthan"
    r"|madhya pradesh|odisha|assam|bihar|jharkhand|chhattisgarh|goa"
)
# \bind\b catches the "Bengaluru, Karnataka, IND" / "Pune, IND" country codes
# without matching "Indianapolis" or the US state code "IN" (Indiana).
INDIA_HINT = re.compile(
    rf"\bindia\b|\bind\b|{INDIA_CITIES}|{INDIA_STATES}"
    r"|work from home|anywhere in india|pan.?india|remote.*india|india.*remote",
    re.I,
)

IN_COUNTRY = {"in", "ind", "india", "republic of india"}


def is_india(location: str, country: str = "") -> bool:
    """True if the posting is based in India (including India-remote)."""
    if country:
        return country.strip().lower() in IN_COUNTRY
    if not location:
        return False
    return bool(INDIA_HINT.search(location))


def classify(title: str, include_senior: bool = False) -> str | None:
    """Return tier string if the job is in scope, else None."""
    if not title or ROLE_EXCLUDE.search(title):
        return None
    if INTERN.search(title):
        return "intern" if ROLE_INCLUDE.search(title) else None
    if not ROLE_INCLUDE.search(title):
        return None
    if SENIOR.search(title) and not include_senior:
        return None
    if NEWGRAD.search(title):
        return "newgrad"
    if EXPERIENCED.search(title):
        return "experienced"
    # Plain engineer title with no level marker: treat as experienced-unknown.
    return "experienced"


def in_scope(job: dict, include_senior: bool = False) -> dict | None:
    tier = classify(job.get("title", ""), include_senior)
    if tier is None:
        return None
    if not is_india(job.get("location", ""), job.get("country", "")):
        return None
    job["tier"] = tier
    return job
