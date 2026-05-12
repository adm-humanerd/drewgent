#!/usr/bin/env python3
"""
Harvester Memory Sync — P4-cortex trend-harvester output → P2-hippocampus memories

Closes the P4→P2 downstream pipeline:
  trend-harvester/analyzed/ → P2-hippocampus/memories/insights/
  trend-harvester/pending/  → P2-hippocampus/memories/concepts/
  trend-harvester/applied/  → P2-hippocampus/memories/concepts/

Usage:
  python3 harvester_memory_sync.py         # full sync
  python3 harvester_memory_sync.py --dry-run   # show what would be synced
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_DREWGENT_HOME = Path.home() / ".drewgent"
_P4_TREND_HARVESTER = _DREWGENT_HOME / "P4-cortex" / "growth" / "trend-harvester"
_P2_INSIGHTS = _DREWGENT_HOME / "P2-hippocampus" / "memories" / "insights"
_P2_CONCEPTS = _DREWGENT_HOME / "P2-hippocampus" / "memories" / "concepts"
_P4_KNOWLEDGE = _DREWGENT_HOME / "P4-cortex" / "knowledge"
_STATE_FILE = _P4_KNOWLEDGE / "harvester_sync_state.json"
_DRY_RUN = False


def load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"synced_hashes": [], "last_sync_at": None, "synced_count": 0}


def save_state(state: dict) -> None:
    if _DRY_RUN:
        return
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()[:16]


def already_synced(state: dict, h: str) -> bool:
    return h in state.get("synced_hashes", [])


def mark_synced(state: dict, h: str) -> None:
    if h not in state["synced_hashes"]:
        state["synced_hashes"].append(h)
    state["synced_count"] += 1


def sync_analyzed_keep(state: dict) -> list:
    """Copy analyzed/keep/*.json → insights/YYYY-MM.md (appended)"""
    results = []
    keep_dir = _P4_TREND_HARVESTER / "analyzed" / "keep"
    if not keep_dir.exists():
        return results

    for f in keep_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        h = content_hash(data.get("url", "") or data.get("description", ""))
        if already_synced(state, h):
            continue

        month = datetime.now().strftime("%Y-%m")
        insight_file = _P2_INSIGHTS / f"{month}.md"
        insight_file.parent.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"## [{ts}] Trend: {data.get('name', data.get('description', '?')[:60])}",
            f"- **Source**: {data.get('url', data.get('source', 'unknown'))}",
            f"- **Score**: {data.get('score', '?')} | **Axes**: {data.get('axes', {})}",
            f"- **Reason**: {data.get('reason', 'see source')}",
            "",
        ]
        content = "\n".join(lines)
        marker = f"<!-- trend:{h} -->"

        # Append only if marker not already in file
        existing = insight_file.read_text() if insight_file.exists() else ""
        if marker not in existing:
            mode = "a" if not _DRY_RUN else None
            if mode:
                with open(insight_file, mode) as fh:
                    fh.write(content + "\n" + marker + "\n\n")
            results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}keep → {insight_file.name}: {data.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def sync_analyzed_review(state: dict) -> list:
    """Copy analyzed/review/*.json → insights/pending/"""
    results = []
    review_dir = _P4_TREND_HARVESTER / "analyzed" / "review"
    pending_dir = _P2_INSIGHTS / "pending"
    if not review_dir.exists():
        return results
    pending_dir.mkdir(parents=True, exist_ok=True)

    for f in review_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        h = content_hash(data.get("url", "") or data.get("description", ""))
        if already_synced(state, h):
            continue

        slug = data.get("name", f.name).replace("/", "_").replace(" ", "-")[:40]
        dest = pending_dir / f"{slug}.json"
        if not _DRY_RUN:
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}review → {dest.name}: {data.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def sync_pending(state: dict) -> list:
    """Copy pending/*.json → concepts/"""
    results = []
    pending_dir = _P4_TREND_HARVESTER / "pending"
    if not pending_dir.exists():
        return results
    _P2_CONCEPTS.mkdir(parents=True, exist_ok=True)

    for f in pending_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        h = content_hash(data.get("url", "") or data.get("description", ""))
        if already_synced(state, h):
            continue

        slug = data.get("name", f.stem).replace("/", "_").replace(" ", "-")[:40]
        dest = _P2_CONCEPTS / f"trend-{slug}.md"

        # Write as markdown
        md = [
            f"# Trend: {data.get('name', '?')}",
            f"",
            f"**Source**: {data.get('url', 'unknown')}",
            f"**Score**: {data.get('score', '?')}",
            f"**Axes**: {json.dumps(data.get('axes', {}), ensure_ascii=False)}",
            f"**Applied at**: {datetime.now().isoformat()}",
            f"",
            f"## Summary",
            f"{data.get('description', '?')}",
            "",
        ]
        content = "\n".join(md)
        if not _DRY_RUN:
            dest.write_text(content)
        results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}pending → {dest.name}: {data.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def sync_applied(state: dict) -> list:
    """Copy applied/*.json → concepts/ + tag trend-applied"""
    results = []
    applied_dir = _P4_TREND_HARVESTER / "applied"
    if not applied_dir.exists():
        return results
    _P2_CONCEPTS.mkdir(parents=True, exist_ok=True)

    for f in applied_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        h = content_hash(data.get("url", "") or data.get("description", ""))
        if already_synced(state, h):
            continue

        slug = data.get("name", f.stem).replace("/", "_").replace(" ", "-")[:40]
        dest = _P2_CONCEPTS / f"trend-applied-{slug}.md"

        md = [
            f"# Trend Applied: {data.get('name', '?')}",
            f"",
            f"**Source**: {data.get('url', 'unknown')}",
            f"**Score**: {data.get('score', '?')}",
            f"**Applied at**: {datetime.now().isoformat()}",
            f"**Tags**: `trend-applied`",
            f"",
            f"## Summary",
            f"{data.get('description', '?')}",
            f"",
            f"## Application Notes",
            f"{data.get('application_notes', 'Applied via trend-harvester pipeline')}",
            "",
        ]
        if not _DRY_RUN:
            dest.write_text("\n".join(md))
        results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}applied → {dest.name}: {data.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def main() -> int:
    global _DRY_RUN

    parser = argparse.ArgumentParser(description="Harvester Memory Sync — P4→P2 bridge")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _DRY_RUN = args.dry_run

    state = load_state()
    all_results = []

    print(f"Harvester Memory Sync {'(DRY-RUN)' if _DRY_RUN else ''}")
    print(f"  Source: {_P4_TREND_HARVESTER}")
    print(f"  Dest:   {_DREWGENT_HOME}/P2-hippocampus/memories/")
    print()

    r1 = sync_analyzed_keep(state)
    r2 = sync_analyzed_review(state)
    r3 = sync_pending(state)
    r4 = sync_applied(state)

    all_results = r1 + r2 + r3 + r4

    if not all_results:
        print("No new trends to sync (all hashes already synced or no output yet).")
        return 2

    print(f"Synced {len(all_results)} trend(s):")
    for r in all_results:
        print(f"  {r}")

    if not _DRY_RUN:
        state["last_sync_at"] = datetime.now().isoformat()
        state["last_sync_job"] = "trend-harvester-001"
        save_state(state)
        print(f"\nState saved: {state['synced_count']} total synced, last at {state['last_sync_at']}")

    return 0 if all_results else 2


if __name__ == "__main__":
    sys.exit(main())