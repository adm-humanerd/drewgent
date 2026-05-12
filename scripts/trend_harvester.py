#!/usr/bin/env python3
"""
Trend Harvester — P4-cortex AI Trend Collection & 5-Axis Filtering

Collects AI tools/techniques from GitHub trending and scores through Drewgent's
5-axis philosophy filter. Only trends that pass the filter get to analyzed/keep.

Usage:
    python3 trend_harvester.py --dry-run    # collect & score, no file writes
    python3 trend_harvester.py              # full run
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---- config ----
_DREWGENT_HOME = Path.home() / ".drewgent"
_P4_TREND = _DREWGENT_HOME / "P4-cortex" / "growth" / "trend-harvester"
_STATE_FILE = _P4_TREND / ".harvester_state.json"
_PID_FILE = _P4_TREND / ".harvester.lock"
_DRY_RUN = False

# GitHub trending languages to scan
LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "java", "shell"]

# GitHub API rate limit handling
GH_RATE_LIMIT_DELAY = 1.0  # seconds between requests (avoid rate limit)

# ---- helpers ----

def log(msg: str) -> None:
    print(f"[harvester] {msg}", flush=True)


def load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"synced_hashes": [], "last_run": None, "runs": 0}


def save_state(state: dict) -> None:
    if _DRY_RUN:
        return
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def acquire_lock() -> bool:
    """PID lock to prevent concurrent runs."""
    if _PID_FILE.exists():
        try:
            pid = int(_PID_FILE.read_text().strip())
            # Check if process still alive
            os.kill(pid, 0)
            log(f"Already running (PID {pid}), exiting.")
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            log(f"Stale lock file (PID unknown or no permission), overwriting.")
    if not _DRY_RUN:
        _PID_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    if not _DRY_RUN and _PID_FILE.exists():
        _PID_FILE.unlink()


# ---- collection ----

def fetch_github_trending(lang: str) -> list[dict]:
    """Fetch GitHub trending repos for a language via HTML scraping."""
    import urllib.request

    url = f"https://github.com/trending/{lang}?since=daily"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Drewgent-Harvester/1.0)"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"  Failed to fetch trending/{lang}: {e}")
        return []

    repos = []
    articles = re.findall(r'<article class="Box-row">(.*?)</article>', html, re.DOTALL)

    for article in articles:
        # Find repo path - look for /owner/repo pattern, skip login links
        hrefs = re.findall(r'href="(/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"', article)
        repo_path = None
        for href in hrefs:
            if not href.startswith('/login') and href.count('/') >= 1 and len(href) > 1:
                repo_path = href[1:]  # remove leading /
                break
        if not repo_path:
            continue

        # Repo name is the second part after /
        repo_name = repo_path.split('/')[-1]

        # Description
        desc_match = re.search(r'<p[^>]*>([^<]+)</p>', article)
        description = desc_match.group(1).strip() if desc_match else ""
        description = re.sub(r'\s+', ' ', description)
        description = description.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")

        # Stars and today's stars
        article_text = re.sub(r'<[^>]+>', ' ', article)
        article_text = re.sub(r'\s+', ' ', article_text)

        stars_match = re.search(r'([\d,]+)\s{1,4}stars(?! today)', article_text)
        stars = int(stars_match.group(1).replace(',', '')) if stars_match else 0

        today_match = re.search(r'([\d,]+)\s+stars today', article_text)
        today_stars = int(today_match.group(1).replace(',', '')) if today_match else 0

        # Programming language
        lang_match = re.search(r'<span itemprop="programmingLanguage">([^<]+)</span>', article)
        language = lang_match.group(1) if lang_match else lang

        if not description:
            description = f"{repo_name} — {language} project on GitHub"

        repos.append({
            "name": repo_name,
            "full_name": repo_path,
            "description": description[:500],
            "language": language,
            "stars": stars,
            "today_stars": today_stars,
            "url": f"https://github.com/{repo_path}",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(GH_RATE_LIMIT_DELAY)

    return repos


# ---- 5-axis scoring ----

AXES = {
    "practical": {
        "weight": 1.0,
        "pass_threshold": 0.6,
        "hard_block": False,
        "keywords_boost": ["cli", "terminal", "tool", "script", "automation", "fast", "lightweight", "small"],
        "keywords_penalize": ["enterprise", "cloud-native", "kubernetes", "aws-scale"],
        "keywords_reject": ["gpt-4", "claude-4", "gpt4", "claude4", "openai", "openai-api"],
    },
    "integratable": {
        "weight": 1.0,
        "pass_threshold": 0.5,
        "hard_block": False,
        "keywords_boost": ["python", "api", "tool", "plugin", "extension", "integration", "hook", "script", "cli"],
        "keywords_penalize": ["ios-only", "android-only", "mobile-native"],
        "keywords_reject": [],
    },
    "drewgent_first": {
        "weight": 1.0,
        "pass_threshold": 0.5,
        "hard_block": False,
        "keywords_boost": ["terminal", "cli", "shell", "bash", "zsh", "linux", "unix", "productivity", "developer-tools"],
        "keywords_penalize": ["figma", "notion", "slack-native"],
        "keywords_reject": [],
    },
    "no_model_dependency": {
        "weight": 1.5,
        "pass_threshold": 0.7,
        "hard_block": True,
        "keywords_boost": ["small", "fast", "local", "on-device", "edge", "lightweight", "efficient", "cpu"],
        "keywords_penalize": ["openai", "anthropic", "google-ai", "cloud-ai"],
        "keywords_reject": ["gpt-4", "gpt4", "claude-4", "claude4", "gpt-5", "gpt5", "gemini-2", "openai-api-required"],
    },
    "safety": {
        "weight": 1.0,
        "pass_threshold": 0.6,
        "hard_block": False,
        "keywords_boost": ["secure", "safe", "privacy", "local", "open-source", "verified"],
        "keywords_penalize": ["eval", "experimental", "beta"],
        "keywords_reject": ["malware", "cryptominer", "backdoor", "exploit-kit"],
    },
}

AXIS_ORDER = ["practical", "integratable", "drewgent_first", "no_model_dependency", "safety"]


def score_trend(item: dict) -> dict:
    """Score a single trend item through 5-axis philosophy filter."""
    text = f"{item.get('name', '')} {item.get('description', '')} {item.get('language', '')}".lower()

    scores = {}
    details = {}

    for axis_name in AXIS_ORDER:
        axis = AXES[axis_name]

        # Base score from stars (normalized 0-1, cap at 5000 stars = 1.0)
        stars = item.get("stars", 0)
        star_score = min(stars / 5000, 1.0) if stars else 0.0

        # Keyword matching
        boost_count = sum(1 for kw in axis.get("keywords_boost", []) if kw in text)
        penalize_count = sum(1 for kw in axis.get("keywords_penalize", []) if kw in text)
        reject_count = sum(1 for kw in axis.get("keywords_reject", []) if kw in text)

        keyword_score = (boost_count * 0.15) - (penalize_count * 0.1)
        keyword_score = max(0.0, min(1.0, 0.5 + keyword_score))  # 0.5 base, ± keyword influence

        # Today stars boost (freshness signal)
        today_stars = item.get("today_stars", 0)
        freshness_score = min(today_stars / 200, 1.0) if today_stars else 0.0

        # Combined axis score (weighted average)
        axis_score = (star_score * 0.3) + (keyword_score * 0.5) + (freshness_score * 0.2)
        axis_score = max(0.0, min(1.0, axis_score))

        # Hard block check
        hard_blocked = reject_count > 0

        scores[axis_name] = round(axis_score, 3)
        details[axis_name] = {
            "star_score": round(star_score, 3),
            "keyword_score": round(keyword_score, 3),
            "freshness_score": round(freshness_score, 3),
            "boost_kw": boost_count,
            "penalize_kw": penalize_count,
            "reject_kw": reject_count,
            "hard_blocked": hard_blocked,
        }

    # Calculate weighted total score
    weighted_sum = sum(scores[axis] * AXES[axis]["weight"] for axis in AXIS_ORDER)
    total_weight = sum(AXES[axis]["weight"] for axis in AXIS_ORDER)
    total_score = round(weighted_sum / total_weight * 10, 2)  # scale to 0-10

    # Determine decision
    no_model = scores["no_model_dependency"]
    if no_model < 0.5:
        decision = "graveyard"
        reason = f"hard_block: no_model_dependency={no_model}"
    elif total_score < 4.0:
        decision = "graveyard"
        reason = f"score={total_score} < 4.0"
    elif total_score >= 6.0 and no_model >= 0.7:
        decision = "keep"
        reason = f"keep: score={total_score}, no_model={no_model}"
    else:
        decision = "review"
        reason = f"review: 4.0 <= score={total_score} < 6.0 or no_model < 0.7"

    return {
        "item": item,
        "scores": scores,
        "details": details,
        "total_score": total_score,
        "decision": decision,
        "reason": reason,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ---- output ----

def write_trend(result: dict, base_dir: Path) -> None:
    """Write a scored trend to the appropriate analyzed/ subdirectory."""
    decision = result["decision"]
    subdir = base_dir / "analyzed" / decision
    subdir.mkdir(parents=True, exist_ok=True)

    # Use hashed name for uniqueness
    h = content_hash(result["item"].get("url", result["item"].get("name", "")))
    filename = f"{h}.json"
    filepath = subdir / filename

    if not _DRY_RUN:
        filepath.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        log(f"  [{decision.upper()}] {result['item']['name']} (score={result['total_score']})")
    else:
        log(f"  [DRY-RUN {decision.upper()}] {result['item']['name']} (score={result['total_score']})")


def write_collected(item: dict, base_dir: Path) -> None:
    """Write raw collected item to collected/ directory."""
    collected_dir = base_dir / "collected"
    collected_dir.mkdir(parents=True, exist_ok=True)

    h = content_hash(item.get("url", item.get("name", "")))
    filepath = collected_dir / f"{h}.json"

    if not _DRY_RUN:
        filepath.write_text(json.dumps(item, indent=2, ensure_ascii=False))


# ---- main ----

def main() -> int:
    global _DRY_RUN

    parser = argparse.ArgumentParser(description="Drewgent Trend Harvester")
    parser.add_argument("--dry-run", action="store_true", help="Collect and score, don't write files")
    args = parser.parse_args()
    _DRY_RUN = args.dry_run

    log(f"Trend Harvester starting (dry_run={_DRY_RUN})")

    if not acquire_lock():
        return 1

    try:
        state = load_state()
        all_items = []

        # Collect from GitHub trending
        for lang in LANGUAGES:
            log(f"Fetching GitHub trending/{lang}...")
            repos = fetch_github_trending(lang)
            log(f"  Found {len(repos)} repos")
            all_items.extend(repos)

        log(f"Total collected: {len(all_items)} items")

        if not all_items:
            log("No items collected, exiting.")
            return 0

        # Score each item
        keep_count = review_count = graveyard_count = 0

        for item in all_items:
            result = score_trend(item)

            # Write to collected/
            write_collected(item, _P4_TREND)

            # Write to analyzed/ subdir based on decision
            write_trend(result, _P4_TREND)

            if result["decision"] == "keep":
                keep_count += 1
            elif result["decision"] == "review":
                review_count += 1
            else:
                graveyard_count += 1

        log(f"Results: keep={keep_count}, review={review_count}, graveyard={graveyard_count}")

        # Update state
        if not _DRY_RUN:
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            state["runs"] += 1
            save_state(state)
            log(f"State saved (runs={state['runs']})")

        return 0

    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())