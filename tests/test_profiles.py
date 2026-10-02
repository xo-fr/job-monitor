"""Tracker profiles, the company registry, and the multi-term search runner.

A typo in the registry or a profile pointing at a missing file both look like
a successful run - just one with fewer postings. These catch that.
"""
import os

import pytest

from monitor import main, profiles


def test_the_default_profile_is_registered():
    assert profiles.DEFAULT in profiles.PROFILES


def test_unknown_profile_fails_loudly():
    with pytest.raises(SystemExit):
        profiles.get("nope")


@pytest.mark.parametrize("key", list(profiles.PROFILES))
def test_every_profile_points_at_files_that_exist(key):
    p = profiles.get(key)
    assert os.path.exists(p.config_path), p.config_path
    assert os.path.exists(os.path.join(profiles.ROOT, "docs", p.dashboard))


@pytest.mark.parametrize("key", list(profiles.PROFILES))
def test_tier_vocabulary_covers_what_the_rules_emit(key):
    """Every tier the filters can return has a Discord label and its own hue."""
    p = profiles.get(key)
    assert set(p.tier_labels) == {"mid", "senior", "lead"}
    assert len(set(p.tier_colors.values())) == len(p.tiers)


def test_config_entries_all_name_a_known_fetcher():
    """A typo in `fetcher:` is otherwise only visible as a skipped source."""
    from monitor.fetchers import FETCHERS
    for key in profiles.PROFILES:
        cfg = main.load_config(profiles.get(key).config_path)
        for section in ("bigtech", "other", "aggregators"):
            for company in cfg.get(section) or []:
                assert company.get("fetcher") in FETCHERS, (key, company)
                assert company.get("name"), (key, company)


# ---- multi-term searches ---------------------------------------------------

def test_searches_runs_the_fetcher_once_per_term_and_merges():
    """One phrase never covers a job family on a keyword-search board."""
    seen = []

    def fake(c):
        seen.append(c["search"])
        # each term finds one unique posting plus one they all share
        return [{"external_id": c["search"], "title": c["search"]},
                {"external_id": "shared", "title": "shared"}]

    main.FETCHERS["_fake"] = fake
    try:
        jobs = main.run_fetcher({"name": "T", "fetcher": "_fake",
                                 "searches": ["java", "backend"]})
    finally:
        del main.FETCHERS["_fake"]
    assert seen == ["java", "backend"]
    assert len(jobs) == 3                      # the duplicate is folded in
    assert {j["external_id"] for j in jobs} == {"java", "backend", "shared"}


def test_the_newest_first_workday_pass_runs_only_once():
    """Repeating it per term would double the request count for nothing."""
    flags = []

    def fake(c):
        flags.append(c.get("skip_recent", False))
        return []

    main.FETCHERS["_fake"] = fake
    try:
        main.run_fetcher({"name": "T", "fetcher": "_fake", "searches": ["a", "b", "c"]})
    finally:
        del main.FETCHERS["_fake"]
    assert flags == [False, True, True]


def test_one_failing_term_does_not_lose_the_others():
    def fake(c):
        if c["search"] == "boom":
            raise RuntimeError("endpoint changed")
        return [{"external_id": c["search"], "title": c["search"]}]

    main.FETCHERS["_fake"] = fake
    try:
        jobs = main.run_fetcher({"name": "T", "fetcher": "_fake",
                                 "searches": ["boom", "fine"]})
    finally:
        del main.FETCHERS["_fake"]
    assert [j["external_id"] for j in jobs] == ["fine"]


def test_a_source_that_fails_every_term_reports_nothing():
    """An all-failed source must read as 0, so source-health flags it."""
    def fake(c):
        raise RuntimeError("dead")

    main.FETCHERS["_fake"] = fake
    try:
        assert main.run_fetcher({"name": "T", "fetcher": "_fake",
                                 "searches": ["a", "b"]}) == []
    finally:
        del main.FETCHERS["_fake"]


def test_yaml_anchor_block_is_not_scanned_as_companies():
    """companies.yaml holds its shared search list at top level."""
    cfg = main.load_config(profiles.get(profiles.DEFAULT).config_path)
    assert "x-searches" in cfg                 # the anchor block is present...
    companies = ((cfg.get("bigtech") or []) + (cfg.get("other") or [])
                 + (cfg.get("aggregators") or []))
    assert all(isinstance(c, dict) and "fetcher" in c for c in companies)


def test_company_names_are_unique():
    """Source health is keyed by name; two entries sharing one would mask each other."""
    cfg = main.load_config(profiles.get(profiles.DEFAULT).config_path)
    names = [c["name"] for sec in ("bigtech", "other", "aggregators")
             for c in cfg.get(sec) or []]
    assert len(names) == len(set(names))
