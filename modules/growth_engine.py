"""
===============================================================================
Drewgent Growth Engine - Self-Evolution Core
===============================================================================
Location: modules/growth_engine.py
Purpose: Pattern detection, analysis, and knowledge base updates

Safety Constraints:
    - NO self-modifying code
    - NO direct deployment
    - All knowledge updates recorded, some require Drew approval
===============================================================================
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import uuid

from logging_v2 import (
    get_log_db_connection,
    get_recent_errors,
    get_task_stats,
    get_tool_stats,
    get_active_patterns,
    detect_and_record_pattern,
    record_knowledge_update,
    find_similar_tasks,
    search_logs,
    audit_log,
    get_request_id,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

MEMORY_BASE = Path("/Volumes/drewgent_storage/_agent/MEMORY")
INSIGHTS_DIR = MEMORY_BASE / "insights"
CONCEPTS_DIR = MEMORY_BASE / "concepts"
PATTERNS_DIR = MEMORY_BASE / "LEARNED_PATTERNS"

# Pattern detection thresholds
THRESHOLD_ERROR_REPETITION = 3  # Same error 3 times
THRESHOLD_TOOL_FAILURE_RATE = 0.3  # 30% failure rate
THRESHOLD_PERFORMANCE_DROP = 1.5  # 50% slower than average
THRESHOLD_REPETITIVE_TASK = 5  # Same task type 5 times

# =============================================================================
# GROWTH ENGINE
# =============================================================================


class GrowthEngine:
    """
    Drewgent's self-evolution engine.

    Maintains the observe -> analyze -> learn -> reflect loop:
    1. Periodically analyzes logs for patterns
    2. Detects problems and opportunities
    3. Updates knowledge base
    4. Generates suggestions for Drew
    """

    def __init__(self):
        self.last_analysis = None
        self.analysis_interval_minutes = 60  # Run analysis every hour

    def should_analyze(self) -> bool:
        """Check if enough time has passed since last analysis"""
        if not self.last_analysis:
            return True

        elapsed = datetime.now() - self.last_analysis
        return elapsed.total_seconds() / 60 >= self.analysis_interval_minutes

    def run_analysis(self, force: bool = False) -> dict:
        """
        Run the growth analysis cycle.
        Returns dict with analysis results and any suggestions.
        """
        if not force and not self.should_analyze():
            return {"status": "skipped", "reason": "Not enough time elapsed"}

        audit_log(
            level="INFO",
            logger_name="growth_engine",
            message="Starting growth analysis cycle",
            context={"force": force},
        )

        results = {
            "patterns_detected": [],
            "knowledge_updates": [],
            "suggestions": [],
            "errors_analyzed": 0,
        }

        # 1. Analyze error patterns
        error_results = self._analyze_error_patterns()
        results["patterns_detected"].extend(error_results["patterns"])
        results["errors_analyzed"] = error_results["count"]

        # 2. Analyze tool performance
        tool_results = self._analyze_tool_performance()
        results["patterns_detected"].extend(tool_results["patterns"])

        # 3. Analyze task success patterns
        task_results = self._analyze_task_patterns()
        results["patterns_detected"].extend(task_results["patterns"])

        # 4. Generate daily insights
        insight_results = self._generate_daily_insight()
        results["knowledge_updates"].extend(insight_results)

        # 5. Check for improvement suggestions
        suggestions = self._generate_suggestions()
        results["suggestions"] = suggestions

        self.last_analysis = datetime.now()

        audit_log(
            level="INFO",
            logger_name="growth_engine",
            message="Growth analysis cycle complete",
            context={
                "patterns_found": len(results["patterns_detected"]),
                "suggestions": len(results["suggestions"]),
                "errors_analyzed": results["errors_analyzed"],
            },
        )

        return results

    def _analyze_error_patterns(self) -> dict:
        """Detect repeated error patterns"""
        errors = get_recent_errors(hours=24)

        # Group by error message pattern
        error_groups = {}
        for error in errors:
            msg = error.get("message", "")
            # Simplify error to pattern (e.g., "API timeout" vs "API timeout after 30s")
            pattern_key = msg.split(":")[0] if ":" in msg else msg[:50]

            if pattern_key not in error_groups:
                error_groups[pattern_key] = []
            error_groups[pattern_key].append(error)

        patterns = []

        for pattern_key, occurrences in error_groups.items():
            if len(occurrences) >= THRESHOLD_ERROR_REPETITION:
                # Extract affected request IDs
                req_ids = [e.get("request_id") for e in occurrences[:10]]

                pattern_id = detect_and_record_pattern(
                    pattern_type="error_repetition",
                    severity="warning" if len(occurrences) < 5 else "alert",
                    description=f"Error '{pattern_key}' occurred {len(occurrences)} times in 24h",
                    affected_items=req_ids,
                    recommendation=f"Consider investigating error pattern: {pattern_key}",
                )

                patterns.append(
                    {
                        "id": pattern_id,
                        "type": "error_repetition",
                        "pattern": pattern_key,
                        "count": len(occurrences),
                        "severity": "warning" if len(occurrences) < 5 else "alert",
                    }
                )

        return {"patterns": patterns, "count": len(errors)}

    def _analyze_tool_performance(self) -> dict:
        """Detect tools with high failure rates or slow performance"""
        conn = get_log_db_connection()
        cursor = conn.cursor()

        # Get tool stats for last 24h
        cursor.execute("""
            SELECT 
                tool_name,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                AVG(duration_ms) as avg_duration
            FROM tool_call_registry
            WHERE created_at >= datetime('now', '-24 hours')
            GROUP BY tool_name
            HAVING total >= 3
        """)

        tools = cursor.fetchall()
        conn.close()

        patterns = []

        for tool in tools:
            tool_name = tool["tool_name"]
            total = tool["total"]
            failures = tool["failures"]
            failure_rate = failures / total if total > 0 else 0
            avg_duration = tool["avg_duration"] or 0

            # Check failure rate
            if failure_rate >= THRESHOLD_TOOL_FAILURE_RATE:
                pattern_id = detect_and_record_pattern(
                    pattern_type="tool_high_failure",
                    severity="alert" if failure_rate > 0.5 else "warning",
                    description=f"Tool '{tool_name}' has {failure_rate * 100:.1f}% failure rate ({failures}/{total})",
                    affected_items=[tool_name],
                    recommendation=f"Investigate tool '{tool_name}' - high failure rate detected",
                )

                patterns.append(
                    {
                        "id": pattern_id,
                        "type": "tool_high_failure",
                        "tool": tool_name,
                        "failure_rate": failure_rate,
                        "severity": "alert" if failure_rate > 0.5 else "warning",
                    }
                )

            # Check performance degradation (future: compare to historical average)
            # This would require storing historical baselines

        return {"patterns": patterns}

    def _analyze_task_patterns(self) -> dict:
        """Detect repetitive tasks that could be automated"""
        conn = get_log_db_connection()
        cursor = conn.cursor()

        # Get recent task types
        cursor.execute(
            """
            SELECT 
                task_type,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM task_history
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY task_type
            HAVING total >= ?
        """,
            (THRESHOLD_REPETITIVE_TASK,),
        )

        tasks = cursor.fetchall()
        conn.close()

        patterns = []

        for task in tasks:
            task_type = task["task_type"]
            total = task["total"]
            completed = task["completed"]
            success_rate = completed / total if total > 0 else 0

            if success_rate >= 0.8:
                # High success repetitive task - good candidate for automation
                pattern_id = detect_and_record_pattern(
                    pattern_type="repetitive_task",
                    severity="info",
                    description=f"Task '{task_type}' executed {total} times (7 days), {success_rate * 100:.0f}% success",
                    affected_items=[task_type],
                    recommendation=f"Task '{task_type}' is repetitive and successful - consider creating an automated workflow",
                )

                patterns.append(
                    {
                        "id": pattern_id,
                        "type": "repetitive_task",
                        "task_type": task_type,
                        "count": total,
                        "success_rate": success_rate,
                    }
                )

        return {"patterns": patterns}

    def _generate_daily_insight(self) -> list:
        """Generate daily insight file"""
        today = datetime.now().strftime("%Y-%m-%d")
        insight_file = INSIGHTS_DIR / f"{today}.md"

        # Get today's stats
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        task_stats = get_task_stats(from_time=today_start)
        errors = get_recent_errors(hours=24)

        # Build insight content
        lines = [
            f"# Daily Insight - {today}",
            "",
            f"## Overview",
            f"- Total tasks: {task_stats.get('total', 0)}",
            f"- Completed: {task_stats.get('completed', 0)}",
            f"- Failed: {task_stats.get('failed', 0)}",
            f"- Pending: {task_stats.get('pending', 0)}",
            f"- Errors (24h): {len(errors)}",
            "",
        ]

        # Add active patterns
        active_patterns = get_active_patterns()
        if active_patterns:
            lines.append("## Active Patterns")
            for p in active_patterns[:5]:
                lines.append(f"- [{p['severity'].upper()}] {p['description']}")
            lines.append("")

        # Add recent errors if any
        if errors[:5]:
            lines.append("## Recent Errors")
            for e in errors[:5]:
                ts = e.get("timestamp", "")[:19]
                lines.append(f"- {ts}: {e.get('message', '')[:80]}")
            lines.append("")

        content = "\n".join(lines)

        # Check if file exists and compare
        content_before = None
        if insight_file.exists():
            content_before = insight_file.read_text()
            if content_before == content:
                return []  # No change

        # Record knowledge update
        update_id = record_knowledge_update(
            update_type="insight",
            target_file=str(insight_file),
            summary=f"Daily insight update: {task_stats.get('total', 0)} tasks, {len(errors)} errors",
            content_before=content_before,
            content_after=content,
            auto_generated=True,
        )

        return [
            {
                "id": update_id,
                "type": "insight",
                "file": str(insight_file),
                "summary": f"Daily insight for {today}",
            }
        ]

    def _generate_suggestions(self) -> list:
        """Generate improvement suggestions based on patterns"""
        suggestions = []
        active_patterns = get_active_patterns(severity="alert")

        for pattern in active_patterns:
            suggestions.append(
                {
                    "type": "improvement",
                    "pattern_id": pattern["id"],
                    "description": pattern["description"],
                    "recommendation": pattern.get("recommendation"),
                    "severity": pattern["severity"],
                }
            )

        return suggestions

    def get_contextual_advice(self, task_type: str) -> Optional[str]:
        """
        Get contextual advice before executing a task.
        Called by the task executor before running a new task.
        """
        similar = find_similar_tasks(task_type, limit=5)

        if not similar:
            return None

        # Calculate success rate
        completed = [t for t in similar if t.get("status") == "completed"]
        failed = [t for t in similar if t.get("status") == "failed"]

        success_rate = len(completed) / len(similar) if similar else 0
        completed_with_duration = [t for t in completed if t.get("duration_ms")]
        avg_duration = (
            sum(t["duration_ms"] for t in completed_with_duration)
            / len(completed_with_duration)
            if completed_with_duration
            else 0
        )

        # Build advice
        advice_parts = []

        if len(similar) >= 3:
            advice_parts.append(f"Similar tasks: {len(similar)} found in history")

        if success_rate < 0.7:
            advice_parts.append(
                f"⚠️ Low success rate: {success_rate * 100:.0f}% ({len(completed)}/{len(similar)})"
            )
        elif success_rate >= 0.9:
            advice_parts.append(f"✅ High success rate: {success_rate * 100:.0f}%")

        if avg_duration > 0:
            advice_parts.append(f"Average duration: {avg_duration / 1000:.1f}s")

        if failed:
            # Get common error
            errors = [t.get("error_message") for t in failed if t.get("error_message")]
            if errors:
                advice_parts.append(f"Common error: {errors[0][:50]}")

        return " | ".join(advice_parts) if advice_parts else None


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

growth_engine = GrowthEngine()


def run_growth_analysis(force: bool = False) -> dict:
    """Convenience function to run growth analysis"""
    return growth_engine.run_analysis(force=force)


def get_task_advice(task_type: str) -> Optional[str]:
    """Convenience function to get contextual advice before task"""
    return growth_engine.get_contextual_advice(task_type)
