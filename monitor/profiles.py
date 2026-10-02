"""Tracker profiles.

Everything that is specific to one job search lives here - which companies are
scanned, which role rules admit a posting, which file the results are stored
in, which dashboard reads that file, and which Discord webhook is notified.
Everything else (fetchers, de-duplication, state, source health, prune) is
profile-agnostic and shared.

  india-java  - Java backend / senior software engineer roles in India,
                tuned for ~6 years of experience (SDE II -> Lead).

Adding a second tracker (say, a different city or stack) is a Profile entry,
a companies-*.yaml, a filters module, a dashboard page and a workflow - no
changes to the engine.
"""
import os
from dataclasses import dataclass
from types import ModuleType

from . import filters

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    config: str        # company registry, under config/
    state: str         # tracker file, under docs/data/
    dashboard: str     # page that reads it, under docs/
    webhook_env: str   # env var holding this tracker's Discord webhook
    rules: ModuleType  # the filters module deciding what is in scope
    tiers: tuple       # (key, discord label, colour) in display order

    @property
    def config_path(self) -> str:
        return os.path.join(ROOT, "config", self.config)

    @property
    def state_path(self) -> str:
        return os.path.join(ROOT, "docs", "data", self.state)

    @property
    def tier_labels(self) -> dict:
        return {k: label for k, label, _ in self.tiers}

    @property
    def tier_colors(self) -> dict:
        return {k: color for k, _, color in self.tiers}


DEFAULT = "india-java"

PROFILES = {
    "india-java": Profile(
        key="india-java",
        label="Java backend / Senior SWE - India",
        config="companies.yaml",
        state="jobs.json",
        dashboard="index.html",
        webhook_env="DISCORD_WEBHOOK_URL",
        rules=filters,
        tiers=(("mid", "🛠 SDE II / Mid", 0x2ECC71),
               ("senior", "🚀 Senior / SDE III", 0xE67E22),
               ("lead", "🧭 Lead / Staff", 0x9B59B6)),
    ),
}


def get(key: str) -> Profile:
    try:
        return PROFILES[key]
    except KeyError:
        raise SystemExit(f"unknown profile '{key}' "
                         f"(known: {', '.join(PROFILES)})") from None
