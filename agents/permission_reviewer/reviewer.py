"""Permission reviewer for Claude Code.

Reviews permission requests against project policies and provides
recommendations. Can be used as a pre-operation hook.

Usage:
    from agents.permission_reviewer import review

    result = review("Bash", command="rm -rf /tmp")
    if result.decision == "deny":
        print("Permission denied!")
"""
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class PermissionPolicy:
    """Project-specific permission policies."""

    def __init__(self, policy_file: Optional[str] = None):
        self.policy_file = self._resolve_policy_file(policy_file)
        self.policies = self._load()

    def _resolve_policy_file(self, custom: Optional[str]) -> Path:
        if custom:
            return Path(custom)
        base = Path(__file__).parent.parent.parent
        return base / "config" / "permission_policies.yaml"

    def _load(self) -> dict:
        if not self.policy_file.exists():
            return self._default_policies()
        try:
            with open(self.policy_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load {self.policy_file}: {e}")
            return self._default_policies()

    def _default_policies(self) -> dict:
        return {
            "allow_rules": [
                {"permission": "Read", "patterns": ["**/*.py", "**/*.yaml", "**/*.vue"]},
                {"permission": "Write", "patterns": ["**/agents/**/*.py", "**/dashboard/**/*.py", "**/config/*.yaml"]},
                {"permission": "Bash", "patterns": ["python*", "pytest*", "npm*", "git status", "git diff"]},
            ],
            "deny_rules": [
                {"permission": "Write", "patterns": ["**/.env", "**/credentials*.json"]},
                {"permission": "Bash", "patterns": ["rm -rf", "git push --force"]},
            ],
            "review_required": [
                {"permission": "Agent"},
                {"permission": "Bash", "patterns": ["git push", "npm install"]},
            ],
        }


class PermissionDecision:
    """Result of a permission review."""

    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"

    def __init__(self, decision: str, reason: str, suggestions: list = None):
        self.decision = decision
        self.reason = reason
        self.suggestions = suggestions or []

    def __repr__(self):
        return f"[{self.decision.upper()}] {self.reason}"

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "suggestions": self.suggestions,
        }


class PermissionReviewer:
    """Reviews permissions against project policies."""

    # Patterns that indicate dangerous operations
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf", r"del\s+/[fqs]", r"format\s+", r"shutdown",
        r"git\s+push\s+--force", r"git\s+push\s+-f", r"git\s+reset\s+--hard",
        r"curl.*-H.*Authorization", r"net\s+user", r"reg\s+delete",
    ]

    # Trusted command patterns
    TRUSTED_COMMANDS = [
        r"^python", r"^pytest", r"^uvicorn", r"^npm\s+(run|dev|build)",
        r"^git\s+(status|diff|log|branch|show)", r"^curl\s+-s",
        r"^ls\b", r"^dir\b", r"^mkdir\b", r"^type\b", r"^echo\b",
    ]

    def __init__(self, policy_file: Optional[str] = None):
        self.policy = PermissionPolicy(policy_file)

    def review(
        self,
        permission: str,
        tool_name: Optional[str] = None,
        command: Optional[str] = None,
        target: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PermissionDecision:
        """
        Review a permission request.

        Args:
            permission: The permission type (Bash, Write, Read, Agent, etc.)
            tool_name: The tool being invoked
            command: The command (for Bash)
            target: The file/target (for Write, Read)
            description: Human-readable description

        Returns:
            PermissionDecision with recommendation
        """
        value = command or target or description or ""

        # 1. Check deny rules
        for rule in self.policy.policies.get("deny_rules", []):
            if self._rule_matches(rule, permission, value):
                return PermissionDecision(
                    decision=PermissionDecision.DENY,
                    reason=f"Deny: {rule.get('reason', 'Matches deny rule')}",
                    suggestions=["Review the command carefully", "Consider alternatives"],
                )

        # 2. Check allow rules
        for rule in self.policy.policies.get("allow_rules", []):
            if self._rule_matches(rule, permission, value):
                return PermissionDecision(
                    decision=PermissionDecision.ALLOW,
                    reason=f"Allow: {rule.get('reason', 'Matches allow rule')}",
                    suggestions=[],
                )

        # 3. Check review_required
        for rule in self.policy.policies.get("review_required", []):
            if self._rule_matches(rule, permission, value):
                return PermissionDecision(
                    decision=PermissionDecision.REVIEW,
                    reason=f"Review: {rule.get('reason', 'Requires human review')}",
                    suggestions=["Verify this action is intended", "Check project requirements"],
                )

        # 4. Default heuristics for common dangerous patterns
        if permission == "Bash" and command:
            return self._review_bash_command(command)
        if permission == "Write" and target:
            return self._review_write_target(target)
        if permission == "Agent":
            return PermissionDecision(
                decision=PermissionDecision.REVIEW,
                reason="Spawning sub-agents requires review",
                suggestions=["Verify the agent purpose", "Check if it aligns with project goals"],
            )

        # Default: require review
        return PermissionDecision(
            decision=PermissionDecision.REVIEW,
            reason=f"Permission '{permission}' requires review",
            suggestions=["Evaluate the necessity of this operation"],
        )

    def _rule_matches(self, rule: dict, permission: str, value: str) -> bool:
        """Check if a rule matches the permission and value."""
        if rule.get("permission") not in ("*", permission):
            return False

        patterns = rule.get("patterns", [])
        if not patterns:
            return True  # Rule applies to any value

        # Normalize value
        normalized = value.replace("\\", "/").lower()
        normalized_stripped = normalized.strip()

        for pattern in patterns:
            p = pattern.lower()
            p_stripped = p.strip()

            # Glob-style with **/ (directory patterns)
            if "**/" in p:
                dir_part = p.replace("**/", "").replace("/*", "")
                if dir_part in normalized:
                    return True

            # Prefix patterns like "python*" - check if command starts with pattern prefix
            if p_stripped.endswith("*"):
                prefix = p_stripped.rstrip("*")
                if normalized_stripped.startswith(prefix):
                    return True
            # Glob matching for wildcards in middle/end
            elif "*" in p_stripped:
                import fnmatch
                if fnmatch.fnmatch(normalized_stripped, p_stripped):
                    return True
            # Exact or substring match
            elif p_stripped in normalized:
                return True

        return False

    def _review_bash_command(self, command: str) -> PermissionDecision:
        """Heuristic review of bash commands."""
        cmd_lower = command.lower()

        # Check dangerous patterns
        for dangerous in self.DANGEROUS_PATTERNS:
            if re.search(dangerous, cmd_lower):
                return PermissionDecision(
                    decision=PermissionDecision.DENY,
                    reason=f"Dangerous command pattern detected: {dangerous}",
                    suggestions=["Use safer alternatives", "Review the full command"],
                )

        # Check trusted patterns
        for trusted in self.TRUSTED_COMMANDS:
            if re.match(trusted, cmd_lower.strip()):
                return PermissionDecision(
                    decision=PermissionDecision.ALLOW,
                    reason="Trusted development command",
                    suggestions=[],
                )

        # Default for unknown bash commands
        return PermissionDecision(
            decision=PermissionDecision.REVIEW,
            reason="Bash command requires review",
            suggestions=["Verify the command is safe", "Consider using Python instead"],
        )

    def _review_write_target(self, target: str) -> PermissionDecision:
        """Review write target paths."""
        target_lower = target.lower()

        # Sensitive files
        if ".env" in target_lower or "credentials" in target_lower:
            return PermissionDecision(
                decision=PermissionDecision.DENY,
                reason="Writing to sensitive file (.env, credentials)",
                suggestions=["Use environment variables instead", "Never hardcode secrets"],
            )

        # Database files
        if ".db" in target_lower or ".sqlite" in target_lower:
            return PermissionDecision(
                decision=PermissionDecision.REVIEW,
                reason="Database file modification",
                suggestions=["Use API endpoints instead", "Avoid direct DB writes"],
            )

        # Project code directories
        safe_dirs = ["agents", "dashboard", "config", "tests", "docs"]
        if any(safe in target_lower for safe in safe_dirs):
            return PermissionDecision(
                decision=PermissionDecision.ALLOW,
                reason="Writing to allowed project directory",
                suggestions=[],
            )

        return PermissionDecision(
            decision=PermissionDecision.REVIEW,
            reason="Write to non-standard directory requires review",
            suggestions=["Verify target is correct", "Check if it aligns with project structure"],
        )


# Global singleton
_reviewer: Optional[PermissionReviewer] = None


def get_reviewer() -> PermissionReviewer:
    global _reviewer
    if _reviewer is None:
        _reviewer = PermissionReviewer()
    return _reviewer


def review(
    permission: str,
    tool_name: Optional[str] = None,
    command: Optional[str] = None,
    target: Optional[str] = None,
    description: Optional[str] = None,
) -> PermissionDecision:
    """Review a permission request. Main entry point."""
    return get_reviewer().review(permission, tool_name, command, target, description)


# CLI interface for manual review
def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("""Permission Reviewer CLI

Usage:
    python -m agents.permission_reviewer <permission> [options]

Examples:
    python -m agents.permission_reviewer Bash --command "rm -rf /tmp"
    python -m agents.permission_reviewer Write --target "agents/test.py"
    python -m agents.permission_reviewer Agent --tool_name "general-purpose"

Options:
    --permission <type>   Permission type (Bash, Write, Read, Agent)
    --command <cmd>       Bash command
    --target <path>       File/target path
    --tool_name <name>    Tool name
    --description <desc>  Operation description
""")
            return

        # Parse arguments
        args = {}
        for i in range(1, len(sys.argv)):
            if sys.argv[i] == "--permission":
                args["permission"] = sys.argv[i + 1]
            elif sys.argv[i] == "--command":
                args["command"] = sys.argv[i + 1]
            elif sys.argv[i] == "--target":
                args["target"] = sys.argv[i + 1]
            elif sys.argv[i] == "--tool_name":
                args["tool_name"] = sys.argv[i + 1]
            elif sys.argv[i] == "--description":
                args["description"] = sys.argv[i + 1]

        result = review(**args)
        print(result)
        sys.exit(0 if result.decision == PermissionDecision.ALLOW else 1)


if __name__ == "__main__":
    main()