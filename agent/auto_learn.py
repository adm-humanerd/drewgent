"""AutoLearning Module - Automatic Pattern Extraction to Obsidian Wiki

This module provides automatic learning capabilities that extract:
- User preferences and communication style
- Environmental facts and tool preferences
- Interaction patterns and corrections

Output is in Karpathy's LLM Wiki / Obsidian-compatible Markdown format:
- Individual markdown files with YAML frontmatter
- Wikilinks for cross-references
- Tags for Dataview queries
- Daily log for chronological tracking
- Semantic search via MiniMax embeddings (or local fallback)
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Obsidian Wiki Structure
# ---------------------------------------------------------------------------

WIKI_STRUCTURE = {
    "entities": "entities",
    "concepts": "concepts",
    "insights_log": "insights",
}


# ---------------------------------------------------------------------------
# Insight Types -> Wiki Categories
# ---------------------------------------------------------------------------

INSIGHT_CATEGORIES = {
    "preference": ("entities", "preferences"),
    "name": ("entities", "user-profile"),
    "role": ("entities", "user-profile"),
    "field": ("entities", "user-profile"),
    "timezone": ("entities", "user-profile"),
    "style_concise": ("entities", "communication-style"),
    "style_detailed": ("entities", "communication-style"),
    "correction": ("entities", "corrections"),
    "anti_preference": ("entities", "preferences"),
    "os": ("entities", "environment"),
    "tool": ("entities", "environment"),
    "project": ("entities", "environment"),
}

INSIGHT_TAGS = {
    "preference": ["user", "preference"],
    "name": ["user", "identity"],
    "role": ["user", "identity"],
    "field": ["user", "identity"],
    "timezone": ["user", "identity"],
    "style_concise": ["user", "communication"],
    "style_detailed": ["user", "communication"],
    "correction": ["user", "correction"],
    "anti_preference": ["user", "preference"],
    "os": ["environment", "os"],
    "tool": ["environment", "tool"],
    "project": ["environment", "project"],
}


# ---------------------------------------------------------------------------
# MiniMax Embeddings API
# ---------------------------------------------------------------------------


def get_minimax_embedding(texts: list[str]) -> Optional[list[list[float]]]:
    """Get embeddings from MiniMax API.

    Requires MINIMAX_API_KEY environment variable.
    Uses the emb-01 model.

    Returns list of embedding vectors or None if API unavailable.
    """
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        logger.debug("MINIMAX_API_KEY not set, semantic search unavailable")
        return None

    try:
        import urllib.request

        url = "https://api.minimax.io/v1/embeddings"
        payload = json.dumps(
            {
                "model": "embo-01",
                "input": texts,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return [item["embedding"] for item in result["data"]]

    except Exception as e:
        logger.debug(f"MiniMax embeddings API failed: {e}")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Vector Store (SQLite-based)
# ---------------------------------------------------------------------------


class VectorStore:
    """Lightweight vector store using SQLite + JSON embeddings."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create tables if not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                itype TEXT,
                target TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add(
        self,
        id: str,
        content: str,
        embedding: list[float],
        itype: str = "",
        target: str = "",
    ) -> bool:
        """Add an embedding to the store."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                """
                INSERT OR REPLACE INTO vectors (id, content, embedding, itype, target, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    id,
                    content,
                    json.dumps(embedding),
                    itype,
                    target,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"VectorStore add failed: {e}")
            return False

    def search(self, query_embedding: list[float], limit: int = 5) -> list[dict]:
        """Search for most similar vectors."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute(
                "SELECT id, content, embedding, itype, target FROM vectors"
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                stored_embedding = json.loads(row[2])
                score = cosine_similarity(query_embedding, stored_embedding)
                results.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "score": score,
                        "itype": row[3],
                        "target": row[4],
                    }
                )

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.debug(f"VectorStore search failed: {e}")
            return []

    def count(self) -> int:
        """Return total number of stored embeddings."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM vectors")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Insight Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Insight:
    """A single insight extracted from conversation."""

    target: str  # "user" or "memory"
    itype: str  # insight type
    content: str
    context: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_wiki_category(self) -> Tuple[str, str]:
        """Get (folder, filename) for wiki storage."""
        cats = INSIGHT_CATEGORIES.get(self.itype, ("entities", "general"))
        return cats[0], cats[1]

    def get_tags(self) -> List[str]:
        """Get Obsidian tags for this insight."""
        return INSIGHT_TAGS.get(self.itype, ["insight", "general"])


# ---------------------------------------------------------------------------
# Pattern Definitions
# ---------------------------------------------------------------------------

# User preference patterns
_USER_PATTERNS = [
    (
        r"(?:I prefer|I like|I love|I hate|I'm a|my favorite|my favourite)[:\s]+([^.!?]+)",
        "preference",
    ),
    (r"(?:call me|named?)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "name"),
    (r"(?:I work as|I'm a|my role is|my job is)[:\s]+([^.!?]+)", "role"),
    (r"(?:I'm in|I'm working in)[:\s]+([^.!?]+)", "field"),
    (r"(?:my timezone is|I'm in timezone)[:\s]+([^.!?]+)", "timezone"),
]

# Communication style patterns
_STYLE_PATTERNS = [
    (r"be\s+(?:brief|short|concise|to the point)", "style_concise"),
    (
        r"(?:keep it short|don't overexplain|just the facts|don't repeat)",
        "style_concise",
    ),
    (
        r"(?:explain|dig deeper|tell me more|give me details|in detail|step by step)",
        "style_detailed",
    ),
]

# Correction patterns
_CORRECTION_PATTERNS = [
    (r"(?:no[, ]|actually[,]|not quite)[:\s]+([^.!?]+)", "correction"),
    (r"(?:that's wrong|incorrect|I meant)[:\s]+([^.!?]+)", "correction"),
]

# Environment/technical facts
_ENV_PATTERNS = [
    (
        r"(?:on|using|running)[:\s]*(?:my |the )?(Mac|Linux|Windows|Ubuntu|Debian|CentOS|macOS|iOS|Android)",
        "os",
    ),
    (r"(?:using|with)[:\s]+([A-Za-z][^.\s]+?)(?:\s|$|\.|\,)", "tool"),
]

# Anti-preference patterns
_ANTI_PATTERNS = [
    (r"(?:don't|not)[:\s]+([A-Za-z][^.!?]+)", "anti_preference"),
]


# ---------------------------------------------------------------------------
# Obsidian Wiki Writer
# ---------------------------------------------------------------------------


class ObsidianWriter:
    """Writes insights to Obsidian wiki format."""

    def __init__(self, wiki_path: Path):
        self._wiki_path = wiki_path
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Create wiki directory structure if it doesn't exist."""
        self._wiki_path.mkdir(parents=True, exist_ok=True)
        for folder in WIKI_STRUCTURE.values():
            (self._wiki_path / folder).mkdir(parents=True, exist_ok=True)

        # Create SCHEMA.md if not exists
        schema_path = self._wiki_path / "SCHEMA.md"
        if not schema_path.exists():
            self._write_schema(schema_path)

        # Create index.md if not exists
        index_path = self._wiki_path / "index.md"
        if not index_path.exists():
            self._write_index(index_path)

    def _write_schema(self, path: Path) -> None:
        """Write SCHEMA.md with wiki conventions."""
        content = """---
title: SCHEMA
tags: [meta, wiki]
---

# Wiki Schema

This is a [[Karpathy LLM Wiki]] - a persistent, compounding knowledge base.

## Structure

- [[entities/]] - Entity pages (people, preferences, environment)
- [[concepts/]] - Concept pages (ideas, patterns)
- [[insights/]] - Daily insight logs

## Conventions

### Tags
- `#user` - User-related facts
- `#preference` - User preferences
- `#identity` - User identity
- `#communication` - Communication style
- `#correction` - Corrections made
- `#environment` - Technical environment
- `#insight` - Automatically extracted insights

### Wikilinks
- Use `[[pagename]]` for internal links
- Use `[[pagename#section|alias]]` for section links
- Use `[[pagename^anchor]]` for block references

### Frontmatter
Every page should have:
```yaml
---
tags: [...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## Updating Pages

1. Add new content to relevant entity page
2. Update the Log section with timestamp
3. Index is auto-updated; verify monthly

---
*Auto-generated by Drewgent Auto-Learning*
"""
        path.write_text(content, encoding="utf-8")

    def _write_index(self, path: Path) -> None:
        """Write index.md."""
        content = """---
title: Index
tags: [meta, wiki]
---

# Wiki Index

Auto-generated table of contents for the knowledge base.

## Entities
- [[entities/preferences]] - User preferences
- [[entities/user-profile]] - User identity
- [[entities/environment]] - Technical environment
- [[entities/communication-style]] - Communication preferences
- [[entities/corrections]] - Past corrections

## Concepts
- (Add concept pages here as they emerge)

## Daily Logs
- [[insights/YYYY-MM]] - Monthly insight logs
"""
        content = content.replace("YYYY-MM", datetime.now().strftime("%Y-%m"))
        path.write_text(content, encoding="utf-8")

    def write_insight(self, insight: Insight) -> bool:
        """Write an insight to the appropriate wiki page."""
        try:
            folder, filename = insight.get_wiki_category()
            page_path = self._wiki_path / folder / f"{filename}.md"

            # Read existing content or create new
            if page_path.exists():
                content = page_path.read_text(encoding="utf-8")
            else:
                content = self._create_new_page(filename, insight.get_tags())

            # Add insight to page
            updated_content = self._add_insight_to_page(content, insight)
            page_path.write_text(updated_content, encoding="utf-8")

            # Also append to daily log
            self._append_to_daily_log(insight)

            return True
        except Exception as e:
            logger.debug("ObsidianWriter: failed to write insight: %s", e)
            return False

    def _create_new_page(self, filename: str, tags: List[str]) -> str:
        """Create a new wiki page with frontmatter."""
        title = filename.replace("-", " ").title()
        today = datetime.now().strftime("%Y-%m-%d")
        tag_str = ", ".join(f'"{t}"' for t in tags)

        return f"""---
title: {title}
tags: [{tag_str}]
created: {today}
updated: {today}
---

# {title}

## Known Facts



## Log

- {today}: Initial entry created
---

*Auto-generated by Drewgent Auto-Learning*
"""

    def _add_insight_to_page(self, content: str, insight: Insight) -> str:
        """Add an insight to an existing page."""
        today = datetime.now().strftime("%Y-%m-%d")
        tags = insight.get_tags()
        tag_str = ", ".join(f"#{t}" for t in tags)

        # Format the insight entry
        insight_entry = self._format_insight_entry(insight, today, tag_str)

        # Find insertion point - before the footer or at end
        footer_marker = "\n---\n*Auto-generated"
        if footer_marker in content:
            parts = content.split(footer_marker)
            # Insert before footer, after "Log" section
            log_marker = "## Log"
            if log_marker in parts[0]:
                log_parts = parts[0].split(log_marker)
                if len(log_parts) > 1:
                    # Insert at end of log section
                    log_content = log_parts[1]
                    lines = log_content.strip().split("\n")
                    # Find where log entries end
                    insert_idx = len(lines)
                    for i, line in enumerate(lines):
                        if line.startswith("---") or line.startswith("*Auto"):
                            insert_idx = i
                            break
                    new_log_lines = (
                        lines[:insert_idx] + [insight_entry] + lines[insert_idx:]
                    )
                    parts[0] = log_marker.join([log_parts[0], "\n".join(new_log_lines)])
                else:
                    parts[0] += "\n\n## Log\n\n" + insight_entry
            else:
                parts[0] += f"\n\n## Log\n\n{insight_entry}\n"
            content = footer_marker.join(parts)
        else:
            # No footer, just append
            content += f"\n\n{insight_entry}\n"

        # Update the "updated" frontmatter
        content = re.sub(
            r"^updated: .+$", f"updated: {today}", content, flags=re.MULTILINE
        )

        return content

    def _format_insight_entry(self, insight: Insight, today: str, tag_str: str) -> str:
        """Format an insight as a wiki entry."""
        content = insight.content.strip()
        itype = insight.itype.replace("_", "-")

        # Context if available
        context_str = ""
        if insight.context:
            context_str = f" *(context: {insight.context[:50]}...)*"

        return f"- {today}: {tag_str} {content}{context_str} ^{itype}-{today.replace('-', '')}"

    def _append_to_daily_log(self, insight: Insight) -> None:
        """Append insight to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        tags = insight.get_tags()
        tag_str = ", ".join(f"#{t}" for t in tags)

        log_dir = self._wiki_path / WIKI_STRUCTURE["insights_log"]
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / f"{month}.md"

        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
            # Check if already logged today
            if f"## {today}" in content:
                # Find today's section boundaries
                marker = f"## {today}"
                idx = content.find(marker)
                next_marker = content.find("\n## ", idx + 1)
                section_end = next_marker if next_marker > 0 else len(content)

                # Check if this insight is already in today's section
                today_section = content[idx:section_end]
                if insight.content not in today_section:
                    # Append to today's section
                    entry = f"- {tag_str} {insight.content}\n"
                    content = content[:section_end] + entry + content[section_end:]
            else:
                # Add new day section
                content += f"\n## {today}\n\n- {tag_str} {insight.content}\n"
        else:
            # Create monthly log
            content = f"""---
title: Insights {month}
tags: [insights, log]
created: {month}-01
updated: {today}
---

# Insights Log: {month}

## {today}

- {tag_str} {insight.content}
"""
        log_path.write_text(content, encoding="utf-8")

    def update_index(self) -> None:
        """Update index.md with current state."""
        index_path = self._wiki_path / "index.md"
        entities_path = self._wiki_path / "entities"

        # Find all entity files
        entities = []
        if entities_path.exists():
            for f in sorted(entities_path.glob("*.md")):
                name = f.stem.replace("-", " ").title()
                link = f"[[entities/{f.stem}]]"
                entities.append(f"- {link} - {name}")

        entity_list = "\n".join(entities) if entities else "- (none yet)"

        content = f"""---
title: Index
tags: [meta, wiki]
updated: {datetime.now().strftime("%Y-%m-%d")}
---

# Wiki Index

Auto-generated table of contents for the knowledge base.

## Entities
{entity_list}

## Concepts
- (Add concept pages here as they emerge)

## Daily Logs
- [[insights/{datetime.now().strftime("%Y-%m")}]] - Current month

---
*Auto-updated by Drewgent Auto-Learning*
"""
        index_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# AutoLearner (Obsidian Wiki Edition)
# ---------------------------------------------------------------------------


class AutoLearner:
    """
    Extracts insights from conversation turns and writes to Obsidian wiki.

    Tracks learned facts to avoid duplicates. Outputs to Karpathy's LLM Wiki
    format with proper Obsidian frontmatter, tags, and wikilinks.

    Supports semantic search via MiniMax embeddings (when MINIMAX_API_KEY is set).
    """

    def __init__(
        self,
        wiki_path: Optional[Path] = None,
        enabled: bool = False,
        max_per_turn: int = 2,
        semantic_search: bool = True,
    ):
        self._enabled = enabled
        self._max_per_turn = max_per_turn
        self._wiki_path = wiki_path
        self._writer: Optional[ObsidianWriter] = None
        self._vector_store: Optional[VectorStore] = None
        self._semantic_search_enabled = semantic_search

        # Track what's already learned to avoid duplicates
        self._learned: Set[str] = set()
        self._turn_count = 0

    def enable(self, wiki_path: Path) -> None:
        """Enable auto-learning and initialize wiki writer."""
        self._enabled = True
        self._wiki_path = wiki_path
        self._writer = ObsidianWriter(wiki_path)

        # Initialize vector store for semantic search
        if self._semantic_search_enabled:
            db_path = wiki_path / "vectors.db"
            self._vector_store = VectorStore(db_path)
            logger.debug(
                f"VectorStore initialized at {db_path} ({self._vector_store.count()} vectors)"
            )

        self._load_existing(wiki_path)

    def _load_existing(self, wiki_path: Path) -> None:
        """Load existing entries to avoid duplicates."""
        entities_path = wiki_path / "entities"
        if not entities_path.exists():
            return

        for file_path in entities_path.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            # Extract key phrases for deduplication
            for line in content.split("\n"):
                if line.strip().startswith("-"):
                    # Get the content after date and tags
                    match = re.search(r"[:\-]\s+.+?$", line)
                    if match:
                        key = match.group(0).lower()[:50]
                        self._learned.add(key)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def wiki_path(self) -> Optional[Path]:
        return self._wiki_path

    def learn_from_turn(self, user_text: str, assistant_text: str) -> Tuple[int, int]:
        """
        Analyze a conversation turn and extract insights.

        Returns (user_insights_count, memory_insights_count) saved.
        """
        if not self._enabled or not self._writer:
            return 0, 0

        self._turn_count += 1

        if not user_text and not assistant_text:
            return 0, 0

        insights = self._extract_insights(user_text, assistant_text)

        # Limit per turn
        insights = insights[: self._max_per_turn]

        user_saved = 0
        memory_saved = 0
        for insight in insights:
            if self._save_insight(insight):
                if insight.target == "user":
                    user_saved += 1
                else:
                    memory_saved += 1

        total_saved = user_saved + memory_saved
        if total_saved > 0:
            logger.debug(
                "AutoLearn turn %d: saved %d insights to Obsidian wiki",
                self._turn_count,
                total_saved,
            )
            # Update index after saving
            try:
                self._writer.update_index()
            except Exception:
                pass

        return user_saved, memory_saved

    def _extract_insights(self, user_text: str, assistant_text: str) -> List[Insight]:
        """Extract insights from conversation text."""
        insights: List[Insight] = []

        if not user_text or len(user_text) < 3:
            return insights

        # Extract user preferences
        for pattern, itype in _USER_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"{itype}:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="user",
                                itype=itype,
                                content=content,
                                context=user_text[:80],
                            )
                        )
                        self._learned.add(key)

        # Extract communication style
        for pattern, itype in _STYLE_PATTERNS:
            if re.search(pattern, user_text, re.IGNORECASE):
                content = itype.replace("style_", "")
                key = f"style:{content}"
                if key not in self._learned:
                    insights.append(
                        Insight(
                            target="user",
                            itype=itype,
                            content=f"prefers {content} responses",
                        )
                    )
                    self._learned.add(key)

        # Extract corrections
        for pattern, itype in _CORRECTION_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"correction:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="user",
                                itype="correction",
                                content=content,
                                context=f"Previously: {assistant_text[:50]}...",
                            )
                        )
                        self._learned.add(key)

        # Extract anti-preferences
        for pattern, itype in _ANTI_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content) and len(content) > 2:
                    key = f"anti:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="user",
                                itype="anti_preference",
                                content=content,
                            )
                        )
                        self._learned.add(key)

        # Extract environment facts
        for pattern, etype in _ENV_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"{etype}:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="memory",
                                itype=etype,
                                content=content,
                            )
                        )
                        self._learned.add(key)

        return insights

    def _is_meaningful(self, text: str) -> bool:
        """Check if text is meaningful enough to save."""
        text = text.strip().lower()
        generic = {
            "yes",
            "no",
            "okay",
            "ok",
            "sure",
            "thanks",
            "yeah",
            "nope",
            "please",
            "yes,",
            "no,",
            "ok,",
            "sure,",
            "i see",
            "understood",
            "good",
            "fine",
            "great",
            "cool",
            "nice",
            "yes.",
            "no.",
            "done",
        }
        if text in generic:
            return False
        if len(text) < 2 or len(text) > 150:
            return False
        return True

    def _save_insight(self, insight: Insight) -> bool:
        """Save insight to Obsidian wiki. Returns True if saved."""
        if not self._writer:
            return False

        try:
            # Write to Obsidian wiki
            success = self._writer.write_insight(insight)

            # Also store embedding for semantic search
            if success and self._vector_store:
                self._store_embedding(insight)

            return success
        except Exception as e:
            logger.debug("AutoLearn: failed to save insight: %s", e)
            return False

    def _store_embedding(self, insight: Insight) -> None:
        """Store embedding for semantic search."""
        embedding = get_minimax_embedding([insight.content])
        if embedding:
            # Generate unique ID
            insight_id = f"{insight.itype}_{insight.content[:30].replace(' ', '_')}"
            self._vector_store.add(
                id=insight_id,
                content=insight.content,
                embedding=embedding[0],
                itype=insight.itype,
                target=insight.target,
            )
            logger.debug(f"Stored embedding for: {insight.content[:50]}")

    def semantic_search(self, query: str, limit: int = 5) -> list[dict]:
        """Search memories semantically using MiniMax embeddings.

        Args:
            query: Search query text
            limit: Maximum number of results

        Returns:
            List of dicts with content, score, itype, target
        """
        if not self._vector_store:
            return []

        # Get query embedding
        embeddings = get_minimax_embedding([query])
        if not embeddings:
            logger.debug("Semantic search failed: could not get embeddings")
            return []

        # Search vector store
        results = self._vector_store.search(embeddings[0], limit=limit)

        # Format results
        return [
            {
                "content": r["content"],
                "score": r["score"],
                "type": r["itype"],
                "target": r["target"],
            }
            for r in results
        ]
