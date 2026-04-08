"""AutoLearning Module - Automatic Pattern Extraction from Conversations

This module provides automatic learning capabilities that extract:
- User preferences and communication style
- Environmental facts and tool preferences
- Interaction patterns and corrections

Integrated with AIAgent to enable proactive memory building without
requiring manual memory tool calls.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Set, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern Definitions
# ---------------------------------------------------------------------------


@dataclass
class Insight:
    """A single insight extracted from conversation."""

    target: str  # "user" or "memory"
    itype: str  # insight type (preference, name, style, etc.)
    content: str
    context: str = ""

    def format(self) -> str:
        """Format for storage in USER.md or MEMORY.md."""
        if self.target == "user":
            return self._format_user()
        return self._format_memory()

    def _format_user(self) -> str:
        """Format user insight."""
        labels = {
            "preference": "Preference",
            "name": "Name",
            "role": "Role",
            "field": "Field",
            "timezone": "Timezone",
            "style_concise": "Communication preference",
            "style_detailed": "Communication preference",
            "correction": "Corrected approach",
            "anti_preference": "Dislikes",
        }
        label = labels.get(self.itype, "Known")
        return f"{label}: {self.content}"

    def _format_memory(self) -> str:
        """Format memory insight."""
        labels = {
            "os": "Environment",
            "tool": "Using tool",
            "project": "Project fact",
        }
        label = labels.get(self.itype, "Fact")
        return f"{label}: {self.content}"


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

# Correction patterns (user correcting agent)
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

# Generic negative patterns
_ANTI_PATTERNS = [
    (r"(?:don't|not)[:\s]+([A-Za-z][^.!?]+)", "anti_preference"),
]


class AutoLearner:
    """
    Extracts insights from conversation turns automatically.

    Tracks learned facts to avoid duplicates. Works alongside MemoryStore
    to enable proactive memory building.
    """

    def __init__(self, memory_store=None, enabled: bool = False, max_per_turn: int = 2):
        self._enabled = enabled
        self._max_per_turn = max_per_turn
        self._store = memory_store

        # Track what's already learned to avoid duplicates
        self._learned_user: Set[str] = set()
        self._learned_memory: Set[str] = set()
        self._turn_count = 0

    def enable(self, memories_dir: Path) -> None:
        """Enable auto-learning and load existing facts."""
        self._enabled = True
        self._load_existing(memories_dir)

    def _load_existing(self, memories_dir: Path) -> None:
        """Load existing entries to avoid duplicates."""
        memories_dir.mkdir(parents=True, exist_ok=True)
        user_file = memories_dir / "USER.md"
        mem_file = memories_dir / "MEMORY.md"

        if user_file.exists():
            content = user_file.read_text()
            for entry in content.split("§"):
                entry = entry.strip()
                if entry:
                    self._learned_user.add(entry.lower()[:60])

        if mem_file.exists():
            content = mem_file.read_text()
            for entry in content.split("§"):
                entry = entry.strip()
                if entry:
                    self._learned_memory.add(entry.lower()[:60])

    def learn_from_turn(self, user_text: str, assistant_text: str) -> Tuple[int, int]:
        """
        Analyze a conversation turn and extract insights.

        Returns (user_insights_count, memory_insights_count) saved.
        """
        if not self._enabled:
            return 0, 0

        self._turn_count += 1

        if not user_text and not assistant_text:
            return 0, 0

        user_insights, memory_insights = self._extract_insights(
            user_text, assistant_text
        )

        # Limit per turn
        user_insights = user_insights[: self._max_per_turn]
        memory_insights = memory_insights[: self._max_per_turn]

        saved_user = 0
        saved_memory = 0

        # Save user insights
        for insight in user_insights:
            if self._save_insight(insight):
                saved_user += 1

        # Save memory insights
        for insight in memory_insights:
            if self._save_insight(insight):
                saved_memory += 1

        if saved_user or saved_memory:
            logger.debug(
                "AutoLearn turn %d: saved %d user, %d memory insights",
                self._turn_count,
                saved_user,
                saved_memory,
            )

        return saved_user, saved_memory

    def _extract_insights(
        self, user_text: str, assistant_text: str
    ) -> Tuple[List[Insight], List[Insight]]:
        """Extract insights from conversation text."""
        user_insights: List[Insight] = []
        memory_insights: List[Insight] = []

        if not user_text or len(user_text) < 3:
            return user_insights, memory_insights

        # Extract user preferences
        for pattern, itype in _USER_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"user:{itype}:{content.lower()[:40]}"
                    if key not in self._learned_user:
                        user_insights.append(
                            Insight(
                                target="user",
                                itype=itype,
                                content=content,
                                context=user_text[:80],
                            )
                        )
                        self._learned_user.add(key)

        # Extract communication style
        for pattern, itype in _STYLE_PATTERNS:
            if re.search(pattern, user_text, re.IGNORECASE):
                content = itype.replace("style_", "")
                key = f"user:style:{content}"
                if key not in self._learned_user:
                    user_insights.append(
                        Insight(
                            target="user",
                            itype=itype,
                            content=f"prefers {content} responses",
                        )
                    )
                    self._learned_user.add(key)

        # Extract corrections
        for pattern, itype in _CORRECTION_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"user:correction:{content.lower()[:40]}"
                    if key not in self._learned_user:
                        user_insights.append(
                            Insight(
                                target="user",
                                itype="correction",
                                content=content,
                                context=f"Previously did: {assistant_text[:50]}...",
                            )
                        )
                        self._learned_user.add(key)

        # Extract anti-preferences
        for pattern, itype in _ANTI_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content) and len(content) > 2:
                    key = f"user:anti:{content.lower()[:40]}"
                    if key not in self._learned_user:
                        user_insights.append(
                            Insight(
                                target="user",
                                itype="anti_preference",
                                content=content,
                            )
                        )
                        self._learned_user.add(key)

        # Extract environment facts
        for pattern, etype in _ENV_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"memory:{etype}:{content.lower()[:40]}"
                    if key not in self._learned_memory:
                        memory_insights.append(
                            Insight(
                                target="memory",
                                itype=etype,
                                content=content,
                            )
                        )
                        self._learned_memory.add(key)

        return user_insights, memory_insights

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
        """Save insight to memory store. Returns True if saved."""
        if not self._store:
            return False

        try:
            content = insight.format()
            target = insight.target

            # Use store's add method for proper handling
            result = self._store.add(target, content)
            return result.get("success", False)
        except Exception as e:
            logger.debug("AutoLearn: failed to save insight: %s", e)
            return False
