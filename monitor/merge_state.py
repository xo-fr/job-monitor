"""Merge two jobs.json copies after a rejected push.

Two writers commit to docs/data/jobs.json: the scanner (adds job ids) and the
dashboard (edits `status`). A scan that finishes while you are marking things
Applied gets its push rejected, and a plain `git rebase` would stop on a JSON
conflict — which would leave the run failed *after* Discord was already
notified, so the next scan would re-notify the same jobs.

This merges the two copies by the same rules the scanner already follows:

  - the remote copy wins on `status` — that is your triage state
  - job ids present only locally are added
  - blank enrichment fields are backfilled from whichever copy has them

Usage:  python -m monitor.merge_state <remote.json> <local.json>
Writes the merged result over <local.json>.
"""
import json
import sys

from .state import ENRICH


def merge(remote: dict, local: dict) -> dict:
    """Remote is authoritative for existing entries; local contributes new ones."""
    jobs = dict(remote.get("jobs") or {})
    added = 0
    for jid, entry in (local.get("jobs") or {}).items():
        if jid in jobs:
            for key in ENRICH:                    # never touches "status"
                if entry.get(key):
                    jobs[jid].setdefault(key, entry[key])
        else:
            jobs[jid] = entry
            added += 1
    stamps = [s for s in (remote.get("updated"), local.get("updated")) if s]
    return {
        "version": remote.get("version") or local.get("version") or 1,
        "updated": max(stamps) if stamps else None,
        "jobs": jobs,
    }, added


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    remote_path, local_path = sys.argv[1], sys.argv[2]
    with open(remote_path, "r", encoding="utf-8") as f:
        remote = json.load(f)
    with open(local_path, "r", encoding="utf-8") as f:
        local = json.load(f)

    merged, added = merge(remote, local)
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=1, ensure_ascii=False, sort_keys=True)

    print(f"merged: {len(remote.get('jobs') or {})} remote + {added} new "
          f"-> {len(merged['jobs'])} total")


if __name__ == "__main__":
    main()
