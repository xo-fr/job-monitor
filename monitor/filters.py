"""Role, seniority and India-location filtering.

Scope:
  - Roles: Java / backend / general software engineering (SDE, SWE, Software
    Developer, Full-stack with a Java/backend lean, Platform, Distributed
    Systems). Titles that name a different stack or discipline outright
    (".NET Developer", "React Engineer", "iOS", "Data Scientist", "QA") are out.
  - Seniority: tuned for ~6 years of experience - SDE II / mid-level, Senior /
    SDE III, and Lead / Tech Lead. Interns, freshers, SDE I, and Principal /
    Architect / Manager / Director titles are excluded. Staff is out by
    default; `--include-staff` lets it in.
  - Location: India (any city, India-remote, or "India" itself).

Every rule here is a plain regex so it is easy to widen or narrow. The test
suite (tests/test_filters.py) pins the cases each one was written for.
"""
import re

# ---- role scope ------------------------------------------------------------
ROLE_INCLUDE = re.compile(
    r"(?<![a-z])java(?![a-z])|j2ee|spring|microservice|kotlin"
    r"|software|\bswe\b|\bsde\b|developer|programmer"
    r"|back.?end|full.?stack|platform engineer|distributed systems"
    r"|member of technical staff|\bmts\b|\bsmts\b|\blmts\b"
    r"|product engineer|\bsde\s*[- ]?(i{2,3}|iv|[234])\b",
    re.I,
)

ROLE_EXCLUDE = re.compile(
    # leadership / non-IC above the target band
    r"principal|distinguished|architect|manager|director|\bvp\b|vice president"
    r"|head of|chief|fellow|executive|\bcto\b"
    # not engineering
    r"|recruit|talent acquisition|sales|accountant|\bhr\b|attorney|counsel|marketing"
    r"|business analyst|support engineer|customer success|technician"
    # other disciplines that share the word "engineer" or "developer"
    r"|\bui\b|\bux\b|\bios\b|android|mobile|flutter|react native"
    r"|machine learning|\bml\b|\bai\b|data scien|data analyst|deep learning"
    r"|\bqa\b|quality assurance|\btest\b|\bsdet\b|in test\b|automation tester"
    r"|data engineer|big ?data engineer|\betl\b|devrel|developer advocate"
    r"|automation (developer|engineer)|windows|workday developer|\brpa\b"
    r"|devops|site reliability|\bsre\b|network engineer|security engineer"
    r"|embedded|firmware|hardware|silicon|asic|fpga|\bvlsi\b|verification"
    r"|systems? software|\bgpu\b|driver|kernel|boot ?loader|boot sw|\bsoc\b|robotics"
    r"|electrical|mechanical|civil|manufacturing|facilities"
    r"|salesforce|\bsap\b|servicenow|oracle apps|mainframe|cobol"
    r"|game dev|game engineer|unity|unreal",
    re.I,
)

# A different stack named in the title. Only disqualifying when Java is NOT
# also named: "Full Stack Java Developer (React)" stays, "React Developer" and
# "Backend Engineer (Golang)" go.
OTHER_STACK = re.compile(
    r"front.?end|react|angular|\bvue\b|javascript|typescript|\bnode(\.?js)?\b"
    r"|\.net\b|c#|dot ?net|\bphp\b|laravel|ruby|rails|golang|\bgo\b|python|django"
    r"|c\+\+|\brust\b|scala|elixir|\bswift\b",
    re.I,
)

# Titles that are below the target band no matter what else they say.
JUNIOR = re.compile(
    r"\bintern(ship)?\b|co-?op\b|trainee|fresher|apprentice|graduate|new ?grad"
    r"|campus|university|entry.?level|early.?career|junior|\bjr\.?\b"
    r"|master'?s|\bph\.?d\b|\banalyst\b"
    r"|associate (software|engineer|developer)"
    r"|(engineer|developer|sde|swe)\s*[- ]?(i|1)\b(?!\s*[-/]?\s*(i|ii|2))"
    r"|\bsde\s*[- ]?(i|1)\b(?!\s*(i|ii))",
    re.I,
)

STAFF = re.compile(r"(?<!technical )\bstaff\b", re.I)

# ---- tier detection --------------------------------------------------------
# lead   - Lead / Tech Lead / Staff (only with --include-staff) / SDE III+ at
#          companies that use III as a lead grade
# senior - Senior / Sr / SDE III / SE III / SMTS
# mid    - SDE II / SE II / plain "Software Engineer" with no level marker
LEAD = re.compile(r"\blead\b|tech lead|team lead|(?<!technical )\bstaff\b|\blmts\b", re.I)
SENIOR = re.compile(
    r"\bsenior\b|\bsr\.?\b|\bsmts\b"
    r"|(engineer|developer|sde|swe)\s*[- ]?(iii|3|iv|4)\b|\bsde\s*[- ]?(iii|3)\b",
    re.I)

# Explicit stack signal - used for the role bucket and for sorting Java first.
# Lookarounds rather than \b: titles like "Software Engineer_Java_Springboot"
# glue words with underscores, which \b treats as part of the word.
JAVA = re.compile(r"(?<![a-z])java(?![a-z])|j2ee|(?<![a-z])jee(?![a-z])|spring"
                  r"|kotlin|(?<![a-z])jvm(?![a-z])", re.I)

# ---- India location --------------------------------------------------------
INDIA_HINT = re.compile(
    r"\bindia\b|\bind\b|bharat"
    r"|bengaluru|bangalore|hyderabad|secunderabad|pune|chennai|mumbai|bombay"
    r"|navi mumbai|thane|gurgaon|gurugram|noida|greater noida|new delhi|\bdelhi\b"
    r"|\bncr\b|faridabad|ghaziabad|kolkata|ahmedabad|gandhinagar|gift city"
    r"|jaipur|kochi|cochin|trivandrum|thiruvananthapuram|coimbatore|mysore|mysuru"
    r"|mangalore|mangaluru|indore|bhopal|chandigarh|mohali|panchkula|nagpur"
    r"|vadodara|surat|lucknow|bhubaneswar|visakhapatnam|vizag|vijayawada"
    r"|madurai|hubli|goa|dehradun|kanpur|patna|ranchi|raipur|nashik|aurangabad"
    r"|karnataka|telangana|maharashtra|tamil nadu|haryana|uttar pradesh"
    r"|kerala|gujarat|west bengal|rajasthan|andhra pradesh|odisha",
    re.I,
)

# Indeed writes "KA, IN" / "MH, IN": an Indian state code, then the country.
# Requiring the state code keeps "Indianapolis, IN" (Indiana) out.
INDIA_STATE_CODE = re.compile(
    r"\b(KA|MH|TN|TS|TG|AP|UP|HR|DL|WB|GJ|RJ|KL|MP|PB|CH|GA|OR|OD|UK|UL|JH|BR|CG|AS)"
    r"\s*,\s*IN\s*$")

ISO_INDIA = ("in", "ind", "india", "bharat")

LOC_SPLIT = re.compile(r"\s*[;|]\s*|\s+/\s+")


def _site_is_india(loc: str) -> bool:
    # A bare ", IN" suffix is deliberately not a signal - it is also Indiana.
    return bool(INDIA_HINT.search(loc) or INDIA_STATE_CODE.search(loc))


def is_india(location: str, country: str = "") -> bool:
    """True when any site of the posting is in India.

    Unlike a "keep if unsure" rule, an unknown location ("Remote", "3
    Locations") is dropped: the boards scanned here are global, and an
    unlabelled remote role at a US company is almost never India-open. Sources
    that already restrict to India (Naukri, LinkedIn with location=India,
    Workday with country: India) supply the country explicitly.
    """
    if country and country.strip().lower() in ISO_INDIA:
        return True
    loc = (location or "").strip()
    if not loc:
        return False
    return any(_site_is_india(p.strip()) for p in LOC_SPLIT.split(loc) if p.strip())


# ---- role family -----------------------------------------------------------
# First match wins.
ROLE_FAMILY = [
    ("java", JAVA),
    ("fullstack", re.compile(r"full.?stack", re.I)),
    ("platform", re.compile(r"platform|infrastructure|cloud|distributed systems", re.I)),
    ("backend", re.compile(r"back.?end|server|\bapi\b|microservice|payments?", re.I)),
]


def role_family(title: str) -> str:
    """Coarse bucket, for filtering the dashboard."""
    for name, pattern in ROLE_FAMILY:
        if pattern.search(title or ""):
            return name
    return "software"          # generic SDE/SWE with no stack in the title


def classify(title: str, include_staff: bool = False) -> str | None:
    """Return tier string if the title is in scope, else None."""
    if not title or ROLE_EXCLUDE.search(title) or JUNIOR.search(title):
        return None
    if OTHER_STACK.search(title) and not JAVA.search(title):
        return None
    if not ROLE_INCLUDE.search(title):
        return None
    if STAFF.search(title) and not include_staff:
        return None
    if LEAD.search(title):
        return "lead"
    if SENIOR.search(title):
        return "senior"
    return "mid"


# Stated experience bars outside this band are not a fit for ~6 years.
# parse_yoe returns the LOWEST number in the posting ("4-8 years" -> 4), so a
# floor of 2 only drops postings that are explicitly junior ("0-2 years").
YOE_MIN = 2
YOE_MAX = 10


def in_scope(job: dict, include_staff: bool = False) -> dict | None:
    tier = classify(job.get("title", ""), include_staff)
    if tier is None:
        return None
    if not is_india(job.get("location", ""), job.get("country", "")):
        return None
    yoe = job.get("yoe")
    if yoe is not None and not (YOE_MIN <= yoe <= YOE_MAX):
        return None
    job["tier"] = tier
    job["role"] = role_family(job.get("title", ""))
    return job


# ---- years of experience ---------------------------------------------------
# The tier a title implies is often wrong ("Software Engineer" says nothing),
# so where a posting states its own bar in prose we read it. Only a stated
# requirement counts - company history ("founded 15 years ago"), degree length
# ("4-year degree") and anniversaries must not register.

# "years" only counts when what follows reads like a requirement, never "ago".
YOE_RE = re.compile(
    r"(?:(?:minimum|min\.?|at least)\s+(?:of\s+)?)?"
    r"(\d{1,2})\s*(?:\+|plus)?\s*(?:[-–]|to)?\s*(?:\d{1,2})?\s*(?:\+|plus)?\s*"
    r"(?:years?|yrs?)\b(?!\s+ago)"
    r"\s+(?:of|in|with|working|building|developing|professional|relevant"
    r"|industry|hands.?on|post|full.?time|prior|related|applicable|exp)",
    re.I)

# Cues just before the number that mean it is describing the company, not you.
YOE_HISTORY = re.compile(
    r"(founded|formed|established|spent|celebrat|anniversary|history|been around"
    r"|over the (past|last)|in the (past|last)|for the (past|last)|since)\b[^.]{0,40}$",
    re.I)

# ...and cues just after it, for the same reason ("10 years of company history").
YOE_HISTORY_AFTER = re.compile(
    r"^\s*(of\s+)?(company|corporate|business|operation|growth|history|innovation"
    r"|partnership|service|success)", re.I)

# "4-year degree", "four year program" - length of study, not experience.
YOE_DEGREE = re.compile(r"\d\s*[-\s]?year\s+(degree|program|university|college|school)", re.I)


def parse_yoe(text: str, title: str = "") -> int | None:
    """Lowest stated years-of-experience requirement, or None if unstated.

    The minimum is taken rather than the maximum: a posting asking for "4+
    years backend, 8+ years distributed systems" is reachable at four.
    """
    if not text or re.search(r"\bintern(ship)?\b", title or "", re.I):
        return None                      # an internship never states a real bar
    best = None
    for m in YOE_RE.finditer(text):
        before = text[max(0, m.start() - 60): m.start()]
        if YOE_HISTORY.search(before):
            continue
        if YOE_HISTORY_AFTER.search(text[m.end(): m.end() + 40]):
            continue
        if YOE_DEGREE.search(text[max(0, m.start() - 20): m.end() + 20]):
            continue
        n = int(m.group(1))
        if 0 <= n <= 20:
            best = n if best is None else min(best, n)
    return best
