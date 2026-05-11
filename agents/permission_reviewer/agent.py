"""Permission review sub-agent using LLM.

Reviews Claude Code permission requests using an LLM with project context.
Context includes: current task, target file, recent changes, related files.
"""
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm_config
from .context import get_session_context, get_recent_changes_analyzer

logger = logging.getLogger(__name__)

# System prompt for permission reviewer agent
PERMISSION_REVIEWER_SYSTEM = """You are a permission security reviewer for a multi-agent investment assistant project.

Project: broker-agents
- Multi-agent investment assistant with human approval for all trades
- Tech stack: Python (FastAPI, LangGraph), Vue 3 frontend, SQLite
- Key constraints:
  - No port forwarding (Cloudflare Tunnel)
  - API keys via environment variables only
  - All trades require human approval
  - Skills hot-loaded from markdown files

Your job: Review each permission request with FULL context awareness.

Context you have:
1. Current task the main agent is working on
2. Target file/path being accessed
3. Recent file changes in the project
4. Related files in the same directory/module

Decision categories:
- ALLOW: Safe operation that aligns with current task
- DENY: Dangerous operation that could harm the project
- REVIEW: Operation that requires human confirmation

Be strict with:
- Destructive commands (rm -rf, format, shutdown)
- Force git operations (git push --force, git reset --hard)
- Credential/secrets files (.env, credentials.json)
- Direct database file modifications
- External API calls that might expose secrets

Be lenient when:
- The operation is directly related to the current task
- The target file was recently modified/created by the agent
- It's a standard development workflow (pytest, git status)
- Writing to project source directories

Evaluate the request in context of:
- What the main agent is currently trying to accomplish
- Whether this operation supports or conflicts with the task
- Recent changes that might explain the request
"""


class PermissionReviewAgent:
    """LLM-powered permission reviewer agent with full context awareness."""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self._llm = llm

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            cfg = get_llm_config()
            primary = cfg.get("primary", {})
            self._llm = ChatOpenAI(
                api_key=primary.get("api_key", ""),
                model=primary.get("model", "auto"),
                base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
                temperature=0.1,  # Low temp for consistent decisions
            )
        return self._llm

    async def review(
        self,
        permission: str,
        tool_name: Optional[str] = None,
        command: Optional[str] = None,
        target: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Review a permission request using LLM with full context.

        Returns:
            dict with decision, reason, and suggestion
        """
        # Gather context
        context = self._gather_context(permission, tool_name, command, target, description)

        # Build prompt with context
        prompt = self._build_contextual_prompt(context)

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=PERMISSION_REVIEWER_SYSTEM),
                HumanMessage(content=prompt),
            ])

            return self._parse_response(response.content)

        except Exception as e:
            logger.error(f"Permission review failed: {e}")
            return {
                "decision": "review",
                "reason": f"LLM review failed: {str(e)[:100]}",
                "suggestion": "Review the operation manually",
            }

    def _gather_context(
        self,
        permission: str,
        tool_name: Optional[str],
        command: Optional[str],
        target: Optional[str],
        description: Optional[str],
    ) -> dict:
        """Gather all available context for the review."""
        ctx = {
            "permission": permission,
            "tool_name": tool_name,
            "command": command,
            "target": target,
            "description": description,
        }

        # Session context (what the agent is working on)
        session = get_session_context()
        ctx["session"] = {
            "current_task": session._context.get("current_task"),
            "target_file": session._context.get("target_file"),
            "goals": session._context.get("goals", []),
            "recent_actions": session._context.get("recent_actions", [])[-5:],
        }

        # Recent file changes
        analyzer = get_recent_changes_analyzer()
        ctx["recent_changes"] = analyzer.get_recent_file_changes(minutes=60)

        # Target-specific context
        if target:
            ctx["target_analysis"] = analyzer.analyze_target_context(target)
            ctx["target_context_report"] = analyzer.generate_context_report(target)
        else:
            ctx["target_analysis"] = {}
            ctx["target_context_report"] = ""

        # Related command context
        if command:
            ctx["command_analysis"] = self._analyze_command(command)
        else:
            ctx["command_analysis"] = {}

        return ctx

    def _analyze_command(self, command: str) -> dict:
        """Analyze a command to understand its purpose."""
        cmd_lower = command.lower().strip()

        analysis = {
            "is_destructive": any(p in cmd_lower for p in ["rm -rf", "del /f", "format"]),
            "is_git_write": any(p in cmd_lower for p in ["git push", "git merge", "git rebase"]),
            "is_read_only": any(p in cmd_lower for p in ["git status", "git diff", "ls", "cat", "head"]),
            "is_test": any(p in cmd_lower for p in ["pytest", "test", "npm test"]),
            "is_install": any(p in cmd_lower for p in ["pip install", "npm install", "npm i"]),
            "target_files": self._extract_file_targets(command),
        }

        return analysis

    def _extract_file_targets(self, command: str) -> list[str]:
        """Extract file paths from a command."""
        import re
        # Common patterns for file paths
        patterns = [
            r'[\w/\-\\.]+\.py\b',
            r'[\w/\-\\.]+\.md\b',
            r'[\w/\-\\.]+\.yaml\b',
            r'[\w/\-\\.]+\.json\b',
            r'[\w/\-\\.]+\.sql\b',
            r'[\w/\-\\.]+\.vue\b',
            r'[\w/\-\\.]+\.ts\b',
        ]

        targets = []
        for pattern in patterns:
            matches = re.findall(pattern, command)
            targets.extend(matches)

        return list(set(targets))

    def _build_contextual_prompt(self, context: dict) -> str:
        """Build the review prompt with full context."""
        parts = ["# Permission Request Review\n"]

        # Permission details
        parts.append("## Request Details")
        parts.append(f"- Permission: {context['permission']}")
        if context.get('tool_name'):
            parts.append(f"- Tool: {context['tool_name']}")
        if context.get('command'):
            parts.append(f"- Command: {context['command']}")
        if context.get('target'):
            parts.append(f"- Target: {context['target']}")
        if context.get('description'):
            parts.append(f"- Description: {context['description']}")
        parts.append("")

        # Session context
        session = context.get('session', {})
        if session.get('current_task') or session.get('goals'):
            parts.append("## Main Agent Context")
            if session.get('current_task'):
                parts.append(f"- Current task: {session['current_task']}")
            if session.get('target_file'):
                parts.append(f"- Target file: {session['target_file']}")
            if session.get('goals'):
                parts.append(f"- Goals: {', '.join(session['goals'])}")
            if session.get('recent_actions'):
                actions = [a['action'] for a in session['recent_actions']]
                parts.append(f"- Recent actions: {', '.join(actions)}")
            parts.append("")

        # Target analysis
        if context.get('target_context_report'):
            parts.append("## Target File Context")
            parts.append(context['target_context_report'])
            parts.append("")

        # Recent changes
        recent = context.get('recent_changes', [])
        if recent:
            parts.append("## Recently Changed Files")
            for change in recent[:10]:
                parts.append(f"- [{change['type']}] {change['path']}")
            parts.append("")

        # Command analysis
        cmd_analysis = context.get('command_analysis', {})
        if any(cmd_analysis.values()):
            parts.append("## Command Analysis")
            if cmd_analysis.get('is_destructive'):
                parts.append("- This is a destructive command")
            if cmd_analysis.get('is_git_write'):
                parts.append("- This is a git write operation")
            if cmd_analysis.get('is_read_only'):
                parts.append("- This is a read-only operation")
            if cmd_analysis.get('is_test'):
                parts.append("- This is a test command")
            if cmd_analysis.get('is_install'):
                parts.append("- This is a package installation")
            if cmd_analysis.get('target_files'):
                parts.append(f"- Targets files: {', '.join(cmd_analysis['target_files'])}")
            parts.append("")

        parts.append("## Review Request")
        parts.append("Provide your decision with reasoning that considers the full context above.")

        return "\n".join(parts)

    def _parse_response(self, content: str) -> dict:
        """Parse LLM response into structured decision."""
        result = {
            "decision": "review",
            "reason": "Could not parse LLM response",
            "suggestion": "Review manually",
        }

        # Remove thinking tags - handle both <result> and typical LLM thinking format
        content = re.sub(r'<result>.*?</result>', '', content, flags=re.DOTALL)
        content = re.sub(r'<think>.*?', '', content, flags=re.DOTALL)
        content = content.strip()

        # Normalize markdown bold (**text**) to plain text
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)

        # Look for decision - check various formats
        decision_found = False
        for pattern in [
            r'Decision:\s*ALLOW',
            r'Decision:\s*DENY',
            r'Decision:\s*REVIEW',
        ]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                decision = re.search(r'(ALLOW|DENY|REVIEW)', match.group(), re.IGNORECASE)
                if decision:
                    result['decision'] = decision.group(0).lower()
                    decision_found = True
                    break

        # Extract reasoning - handle various markdown formats
        for pattern in [
            r'(?:###\s*)?Reasoning[ :]?\s*(.+?)(?=\n\n|\n##|\n[A-Z]{2,}|$)',
            r'Reason[ :]?\s*(.+?)(?=\n\n|\n##|\n[A-Z]{2,}|$)',
        ]:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                reason = match.group(1).strip()
                # Clean up any remaining markdown
                reason = re.sub(r'\*+', '', reason)
                reason = re.sub(r'^-', '', reason).strip()
                if reason and len(reason) >= 5:
                    result['reason'] = reason[:500]  # Limit length
                    break

        # Look for suggestion
        suggestion_match = re.search(r'Suggestion:\s*(.+)', content, re.IGNORECASE)
        if suggestion_match:
            result['suggestion'] = suggestion_match.group(1).strip()

        return result


# Global singleton
_agent: Optional[PermissionReviewAgent] = None


def get_permission_agent() -> PermissionReviewAgent:
    """Get the global permission reviewer agent."""
    global _agent
    if _agent is None:
        _agent = PermissionReviewAgent()
    return _agent


async def review_permission(
    permission: str,
    tool_name: Optional[str] = None,
    command: Optional[str] = None,
    target: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Review a permission request using the LLM agent with full context."""
    agent = get_permission_agent()
    return await agent.review(permission, tool_name, command, target, description)