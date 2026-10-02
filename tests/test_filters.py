"""Scope rules: India location, Java/backend role, seniority tier, experience.

These are the judgements every posting passes through, and getting one wrong is
silent - the run succeeds, the log looks tidy, and postings quietly stop
arriving (or the wrong ones start to). Most cases below are real titles seen
on the boards this repo scans.
"""
import pytest

from monitor import filters as F
from monitor.fetchers.generic import _find_facet, workday_country


# ---- India location --------------------------------------------------------

@pytest.mark.parametrize("loc", [
    "Bengaluru, Karnataka, India", "Bangalore", "Hyderabad", "Pune, MH, IN",
    "Gurugram, Haryana", "Gurgaon", "Noida, Uttar Pradesh, India", "Chennai",
    "Mumbai", "Navi Mumbai", "New Delhi", "Kochi", "Remote - India", "India",
    "Pune Division, Maharashtra, India",
    "KA, IN", "MH, IN",                         # Indeed's state-code format
    "San Francisco, CA; Bengaluru, India",      # one Indian site carries it
])
def test_india_locations_are_kept(loc):
    assert F.is_india(loc) is True


@pytest.mark.parametrize("loc", [
    "San Francisco, CA", "London, UK", "Singapore", "Remote",
    "3 Locations", "", "Indianapolis, IN", "Indiana", "Dublin, Ireland",
])
def test_non_india_or_unknown_locations_are_dropped(loc):
    """Unknown is dropped: on a global board it is almost never India-open."""
    assert F.is_india(loc) is False


def test_an_explicit_country_settles_it():
    assert F.is_india("3 Locations", country="India") is True
    assert F.is_india("Remote", country="IN") is True
    assert F.is_india("Remote", country="US") is False


def test_workday_country_reads_the_url_slug():
    assert workday_country("/job/BangaloreIndia/SWE_R5") == "India"
    assert workday_country("/job/India-Hyderabad/SWE_R6") == "India"
    assert workday_country("/job/US-CA-Santa-Clara/SWE_R1") == "US"
    assert workday_country("/job/Somewhere-Odd/SWE_R6") == ""


def test_workday_india_facet_is_found_even_when_nested():
    facets = [
        {"facetParameter": "jobFamilyGroup", "values": [{"descriptor": "Engineering", "id": "e1"}]},
        {"facetParameter": "locationMainGroup", "values": [
            {"facetParameter": "locationCountry", "descriptor": "Country", "values": [
                {"descriptor": "United States of America", "id": "us1"},
                {"descriptor": "India", "id": "in1"},
            ]},
        ]},
    ]
    assert _find_facet(facets, "India") == {"locationCountry": ["in1"]}
    assert _find_facet(facets, "Narnia") == {}


# ---- role and tier ---------------------------------------------------------

@pytest.mark.parametrize("title,tier", [
    ("Senior Software Engineer", "senior"),
    ("Sr. Java Spring Boot Developer", "senior"),
    ("Senior Java Developer", "senior"),
    ("Senior Backend Engineer", "senior"),
    ("Software Engineer III", "senior"),
    ("SDE III", "senior"),
    ("Software Development Engineer II", "mid"),
    ("SDE II", "mid"),
    ("SDE-2", "mid"),
    ("Software Engineer", "mid"),
    ("Java Developer", "mid"),
    ("Member of Technical Staff", "mid"),           # not "Staff Engineer"
    ("Software Engineer I/II", "mid"),               # a band reaching II
    ("Full Stack Java Developer (React)", "mid"),    # Java named: React is fine
    ("Software Engineer_Java_Springboot_Microservices_Kafka", "mid"),
    ("Lead Software Engineer", "lead"),
    ("Lead Java Engineer", "lead"),
    ("Java FullStack Developer - Tech Lead", "lead"),
])
def test_in_scope_titles_get_a_tier(title, tier):
    assert F.classify(title) == tier


@pytest.mark.parametrize("title", [
    # below the band
    "Software Engineer I", "SDE-1", "Associate Software Engineer",
    "Software Engineering Intern", "Graduate Engineer Trainee",
    "Software Engineer- Master's (Full Time)", "Junior Java Developer",
    # above the band / not an IC
    "Principal Engineer", "Staff Software Engineer", "Engineering Manager",
    "Director of Engineering", "Solutions Architect", "Java Architect",
    # another discipline or stack
    "Senior Frontend Engineer", "React Developer", "Senior Software Engineer - iOS",
    "Android Developer", "Senior Data Scientist", "Data Engineer II",
    "Senior Software Development Engineer in Test", "Senior SDET",
    "DevOps Engineer", "Site Reliability Engineer", "Machine Learning Engineer",
    "Backend Engineer (Golang)", "Senior Software Engineer (Python)",
    ".NET Developer", "Senior Salesforce Developer", "SAP ABAP Developer",
    "Senior Windows Application Developer",
    "Senior System Software Engineer - GPU and SOC",   # Nvidia: C/C++ drivers
    "Senior Systems Software Engineer",
    # not engineering
    "Technical Recruiter", "Business Analyst", "Product Manager",
])
def test_out_of_scope_titles_are_rejected(title):
    assert F.classify(title) is None


def test_include_staff_opens_the_door_deliberately():
    assert F.classify("Staff Software Engineer") is None
    assert F.classify("Staff Software Engineer", include_staff=True) == "lead"


@pytest.mark.parametrize("title,family", [
    ("Senior Java Developer", "java"),
    ("Backend Engineer - Spring Boot", "java"),
    ("Senior Full Stack Engineer", "fullstack"),
    ("Software Engineer, Platform", "platform"),
    ("Senior Backend Engineer", "backend"),
    ("Senior Software Engineer, Payments", "backend"),
    ("Senior Software Engineer", "software"),
])
def test_role_family_buckets(title, family):
    assert F.role_family(title) == family


def test_in_scope_annotates_and_filters_in_one_pass():
    job = {"title": "Senior Java Developer", "location": "Bengaluru, India"}
    out = F.in_scope(dict(job))
    assert out["tier"] == "senior" and out["role"] == "java"
    assert F.in_scope(dict(job, location="Austin, TX")) is None
    assert F.in_scope(dict(job, title="Engineering Manager")) is None


@pytest.mark.parametrize("yoe,kept", [
    (None, True), (2, True), (5, True), (8, True), (10, True),
    (0, False), (1, False),        # explicitly junior
    (12, False), (15, False),      # explicitly principal-level
])
def test_a_stated_experience_bar_outside_the_band_drops_the_posting(yoe, kept):
    job = {"title": "Senior Software Engineer", "location": "Pune", "yoe": yoe}
    assert (F.in_scope(dict(job)) is not None) is kept


# ---- years of experience ---------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("We require 5+ years of professional software development experience.", 5),
    ("You have at least 4 years of relevant experience", 4),
    ("Minimum of 8 years in industry", 8),
    ("4-8 years of experience in Java", 4),
    ("6+ yrs of experience with Spring Boot", 6),
    ("10+ years working on distributed systems", 10),
    # the lowest stated bar is the reachable one
    ("3+ years of experience with Kafka; 6+ years of Java", 3),
])
def test_a_stated_requirement_is_read(text, want):
    assert F.parse_yoe(text) == want


@pytest.mark.parametrize("text", [
    "Founded 15 years ago, we...",
    "5 years of company history",
    "Over the past 10 years of innovation",
    "A 4-year degree in CS",
    "Three years of experience",                # spelled out, not parsed
    "",
])
def test_things_that_are_not_a_requirement_are_ignored(text):
    assert F.parse_yoe(text) is None
