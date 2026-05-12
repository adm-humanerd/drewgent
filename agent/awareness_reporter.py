"""Brain Awareness Reporter — action layer that responds to brain signals.

행동 레이어(Cortical Layer 4): 신호를 받아 구체적인 안내나 경고를 제공한다.
Integration workflow 진행 상황, 누락된 단계, 완료 알림 등을 에이전트에게 전달.

Responsibilities:
1. Format integration progress into actionable hints
2. Warn when files are missing in integration workflow
3. Celebrate completion
4. Provide architecture self-awareness during operations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent.event_bus import BrainEvent, get_event_bus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guidance Templates
# ---------------------------------------------------------------------------

_TOOL_INTEGRATION_HINTS = {
    "tool_file_created": {
        "missing": ["model_tools.py"],
        "hint": "이제 model_tools.py의 _discover_tools()에 import를 추가해야 해.",
        "action": "model_tools.py 열어서 _discover_tools() 함수 찾고 새 도구 import 추가",
    },
    "model_tools_modified": {
        "missing": ["toolsets.py"],
        "hint": "이제 toolsets.py에 도구를 추가해야 해.",
        "action": "toolsets.py 열어서 적절한 toolset에 도구 이름 추가",
    },
    "toolsets_modified": {
        "missing": [],
        "hint": None,  # Complete!
        "action": None,
    },
}

_SKILL_INTEGRATION_HINTS = {
    "skill_file_created": {
        "missing": ["agent/skill_commands.py"],
        "hint": "이제 agent/skill_commands.py에 스킬 로딩 로직을 추가해야 해.",
        "action": "agent/skill_commands.py 열어서 스캔 로직에 새 스킬 추가",
    },
    "skill_commands_modified": {
        "missing": [],
        "hint": None,  # Complete!
        "action": None,
    },
}

_GATEWAY_PLATFORM_HINTS = {
    "platform_file_created": {
        "missing": ["gateway/run.py"],
        "hint": "이제 gateway/run.py의 PLATFORM_REGISTRY에 새 플랫폼을 등록해야 해.",
        "action": "gateway/run.py 열어서 PLATFORM_REGISTRY에 어댑터 추가",
    },
    "run_py_modified": {
        "missing": [],
        "hint": None,  # Complete!
        "action": None,
    },
}

_SLASH_COMMAND_HINTS = {
    "commands_file_modified": {
        "missing": ["cli.py"],
        "hint": "이제 cli.py의 process_command()에 새 명령어 handler를 추가해야 해.",
        "action": "cli.py 열어서 process_command()에 if canonical == 'xxx' 분기 추가",
    },
    "cli_handler_added": {
        "missing": [],
        "hint": None,  # Complete!
        "action": None,
    },
}

_MCP_SERVER_HINTS = {
    "mcp_tool_modified": {
        "missing": [],
        "hint": None,  # Complete!
        "action": None,
    },
}

_CRON_JOB_HINTS = {
    "jobs_file_modified": {
        "missing": ["cron/scheduler.py"],
        "hint": "이제 cron/scheduler.py에 job을 등록해야 해.",
        "action": "cron/scheduler.py 열어서 job 등록 추가",
    },
    "scheduler_modified": {
        "missing": [],
        "hint": None,  # Complete!
        "action": None,
    },
}


# ---------------------------------------------------------------------------
# Awareness Reporter
# ---------------------------------------------------------------------------

class AwarenessReporter:
    """Formats brain signals into actionable feedback for the agent.

    Subscribes to awareness signals and provides:
    - Integration progress hints
    - Missing step warnings
    - Completion notifications
    - Architecture guidance
    """

    def __init__(self):
        self._bus = get_event_bus()
        self._last_hint: Optional[str] = None
        self._hint_history: List[str] = []
        self._setup_subscriptions()

        logger.info("AwarenessReporter initialized")

    def _setup_subscriptions(self) -> None:
        """Subscribe to awareness signals."""
        self._bus.subscribe("brain.awareness.integration_started", self._on_integration_started)
        self._bus.subscribe("brain.awareness.integration_progress", self._on_integration_progress)
        self._bus.subscribe("brain.awareness.integration_complete", self._on_integration_complete)
        self._bus.subscribe("brain.awareness.guidance_requested", self._on_guidance_requested)
        self._bus.subscribe("brain.awareness.initialized", self._on_initialized)

    # -------------------------------------------------------------------------
    # Signal Handlers
    # -------------------------------------------------------------------------

    def _on_integration_started(self, event: BrainEvent) -> None:
        """Handle integration_started — provide initial guidance for all types."""
        payload = event.payload
        int_type = payload.get("integration_type", "unknown")
        target = payload.get("target_name", "unknown")

        hints = {
            "tool": (
                f"🔧 **Tool Integration Started**: `{target}`\n\n"
                f"도구를 완전히 통합하려면 다음 3가지 파일을 수정해야 해:\n"
                f"1. `tools/{target}_tool.py` — 도구 핸들러 + registry.register()\n"
                f"2. `model_tools.py` — _discover_tools()에 import 추가\n"
                f"3. `toolsets.py` — 해당 toolset에 도구 이름 추가"
            ),
            "skill": (
                f"🧠 **Skill Integration Started**: `{target}`\n\n"
                f"스킬을 완전히 통합하려면 다음이 필요해:\n"
                f"1. `skills/{target}/SKILL.md` — 스킬 정의\n"
                f"2. `agent/skill_commands.py` — 스캔 로직에 추가"
            ),
            "gateway_platform": (
                f"🌐 **Gateway Platform Integration Started**: `{target}`\n\n"
                f"게이트웨이 플랫폼 어댑터를 완전히 통합하려면 다음이 필요해:\n"
                f"1. `gateway/platforms/{target}.py` — 어댑터 파일 생성\n"
                f"2. `gateway/run.py` — PLATFORM_REGISTRY에 등록"
            ),
            "slash_command": (
                f"⚡ **Slash Command Integration Started**: `{target}`\n\n"
                f"슬래시 명령어를 완전히 통합하려면 다음이 필요해:\n"
                f"1. `drewgent_cli/commands.py` — CommandDef 추가\n"
                f"2. `cli.py` — process_command()에 handler 추가"
            ),
            "mcp_server": (
                f"🔌 **MCP Server Integration Started**: `{target}`\n\n"
                f"MCP 서버를 완전히 통합하려면 다음이 필요해:\n"
                f"1. `tools/mcp_tool.py` — mcp_servers[]에 서버 설정 추가"
            ),
            "cron_job": (
                f"⏰ **Cron Job Integration Started**: `{target}`\n\n"
                f"크론 잡을 완전히 통합하려면 다음이 필요해:\n"
                f"1. `cron/jobs.py` — job 함수 정의\n"
                f"2. `cron/scheduler.py` — job 등록"
            ),
        }
        hint = hints.get(int_type)
        if hint:
            self._deliver_hint(hint)

    def _on_integration_progress(self, event: BrainEvent) -> None:
        """Handle integration_progress — show what's missing."""
        payload = event.payload
        int_type = payload.get("integration_type", "unknown")
        progress = payload.get("progress", {})
        workflow_id = payload.get("workflow_id", "")

        missing = progress.get("missing_files", [])
        next_hint = progress.get("next_hint")

        if not missing:
            return  # No missing files = complete or nothing to report yet

        # Route to type-specific hint formatter
        hint = self._format_progress_hint(int_type, workflow_id, missing, next_hint)
        if hint:
            self._deliver_hint(hint)

    def _format_progress_hint(
        self, int_type: str, workflow_id: str, missing: list, next_hint: Optional[str]
    ) -> Optional[str]:
        """Format a progress hint for any integration type."""
        labels = {
            "tool": ("Tool Integration", "📝"),
            "skill": ("Skill Integration", "🧠"),
            "gateway_platform": ("Gateway Platform Integration", "🌐"),
            "slash_command": ("Slash Command Integration", "⚡"),
            "mcp_server": ("MCP Server Integration", "🔌"),
            "cron_job": ("Cron Job Integration", "⏰"),
        }
        label, icon = labels.get(int_type, ("Integration", "🔧"))
        short_id = workflow_id[:8] + "..." if len(workflow_id) > 8 else workflow_id

        hint = f"{icon} **{label}** (workflow: {short_id})\n\n"
        hint += "누락된 단계:\n"
        for m in missing:
            hint += f"- [ ] {m}\n"

        if next_hint:
            hint += f"\n💡 **다음 단계**: {next_hint}"

        return hint

    def _on_integration_complete(self, event: BrainEvent) -> None:
        """Handle integration_complete — celebrate!"""
        payload = event.payload
        int_type = payload.get("integration_type", "unknown")
        target = payload.get("target_name", "unknown")
        files = payload.get("files_modified", [])
        duration = payload.get("duration_seconds", 0)

        labels = {
            "tool": ("Tool", "🔧", "model_tools.py reload 필요 시 `/reload` 명령어를 사용해"),
            "skill": ("Skill", "🧠", " `/skills` 명령어로 확인할 수 있어"),
            "gateway_platform": ("Gateway Platform", "🌐", "gateway/platforms/에서 확인 가능"),
            "slash_command": ("Slash Command", "⚡", " `/help`에서 확인 가능"),
            "mcp_server": ("MCP Server", "🔌", " `/tools mcp`로 확인 가능"),
            "cron_job": ("Cron Job", "⏰", " crontab -e로 확인 가능"),
        }
        name, icon, usage_tip = labels.get(
            int_type, (int_type.title(), "✅", "")
        )

        msg = (
            f"✅ **{name} Integration Complete!**\n\n"
            f" `{target}` {name.lower()}이(가) 다음 파일에 통합됨:\n"
        )
        for f in files:
            msg += f"- `{f}`\n"

        msg += f"\n⏱️ 소요 시간: {duration:.1f}초\n"
        if usage_tip:
            msg += f"\n{icon} {usage_tip}"

        self._deliver_completion(msg)

    def _on_guidance_requested(self, event: BrainEvent) -> None:
        """Handle guidance_requested — provide architecture awareness."""
        payload = event.payload
        guidance_type = payload.get("guidance_type", "general")

        if guidance_type in ("how to add", "tool add method"):
            hint = (
                f"🗺️ **도구 추가 방법 (Architecture Map)**\n\n"
                f"도구 하나를 완전히 통합하려면 3곳을 수정해야 해:\n\n"
                f"**1️⃣ `tools/<name>_tool.py`** (새 파일 생성)\n"
                f"   - registry.register() 호출로 핸들러 등록\n"
                f"   - schema 정의 (도구 이름, 설명, 파라미터)\n\n"
                f"**2️⃣ `model_tools.py`** (_discover_tools() 함수)\n"
                f"   - from tools.새도구 import 새도구 추가\n"
                f"   - _discover_tools() 리스트에 도구 이름 추가\n\n"
                f"**3️⃣ `toolsets.py`**\n"
                f"   - _HERMES_CORE_TOOLS 또는 해당 도메인 toolset에 추가\n\n"
                f"💡 이 세 가지를 순서대로 적용하면 도구가 활성화돼."
            )
        elif guidance_type in ("how to integrate", "skill add method"):
            hint = (
                f"🗺️ **스킬 추가 방법 (Architecture Map)**\n\n"
                f"스킬 하나를 완전히 통합하려면 다음이 필요해:\n\n"
                f"**1️⃣ `skills/<name>/SKILL.md`** (새 디렉토리 + 파일)\n"
                f"   - YAML frontmatter로 메타데이터 정의\n"
                f"   - markdown body로 스킬 내용 작성\n\n"
                f"**2️⃣ `agent/skill_commands.py`**\n"
                f"   - 스캔 로직에 새 스킬 디렉토리 추가\n\n"
                f"💡 스킬은 `~/.drewgent/skills/` 디렉토리에 놓이면 자동으로 인식돼."
            )
        elif guidance_type == "where to put":
            hint = (
                f"📍 **Integration Points**\n\n"
                f"도구/스킬 통합은 정해진 위选修 있어요:\n"
                f"- 도구: `tools/*.py` + `model_tools.py` + `toolsets.py`\n"
                f"- 스킬: `skills/<name>/` + `agent/skill_commands.py`"
            )
        else:
            hint = (
                f"🗺️ **Integration Architecture**\n\n"
                f"외부 기능 통합은 정해진 패턴이 있어요.\n"
                f"도구 추가는 `/brain fire tool-integration`으로 자세히 알아볼 수 있어."
            )

        self._deliver_hint(hint)

    def _on_initialized(self, event: BrainEvent) -> None:
        """Handle initialized — log agent awareness state."""
        payload = event.payload
        tool_count = payload.get("tool_count", 0)
        tools = payload.get("tools", [])

        logger.info(
            f"Agent awareness initialized: {tool_count} tools loaded. "
            f"Top tools: {tools[:5]}"
        )

    # -------------------------------------------------------------------------
    # Hint Delivery
    # -------------------------------------------------------------------------

    def _deliver_hint(self, hint: str) -> None:
        """Store hint for agent to pick up."""
        self._last_hint = hint
        self._hint_history.append(hint)

        # Also emit as a readable event
        self._bus.emit(
            "brain.report.hint",
            payload={"hint": hint, "hint_id": len(self._hint_history)},
            source="awareness_reporter",
        )

    def _deliver_completion(self, msg: str) -> None:
        """Store completion message for agent."""
        self._deliver_hint(msg)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_last_hint(self) -> Optional[str]:
        """Get the most recent hint."""
        return self._last_hint

    def get_hint_history(self) -> List[str]:
        """Get all hints delivered in this session."""
        return list(self._hint_history)

    def clear_hints(self) -> None:
        """Clear hint history."""
        self._last_hint = None
        self._hint_history.clear()


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_awareness_reporter: Optional[AwarenessReporter] = None


def get_awareness_reporter() -> AwarenessReporter:
    """Get the global AwarenessReporter singleton."""
    global _awareness_reporter
    if _awareness_reporter is None:
        _awareness_reporter = AwarenessReporter()
    return _awareness_reporter