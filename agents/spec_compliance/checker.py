"""Spec Compliance Checker.

Validates agent actions against the active spec scope.
If it's in the spec, it's pre-authorized. If not, requires spec amendment.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import fnmatch
import logging
import re
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Frontmatter standard for specs
FRONTMATTER_TEMPLATE = '''
---
name: feature-name
date: YYYY-MM-DD
version: 1.0.0
scope:
  files:
    read: ["path/**/*.py", "path/**/*.yaml"]
    write: ["path/**/*.py"]
    create: ["path/**"]
  commands:
    allowed: ["python", "pytest", "git status"]
    blocked: ["git push --force", "npm install"]
  blocked:
    - "Direct API key modifications"
    - "Database migrations without rollback"
---
'''


class SpecScope:
    """Defines what's allowed under a spec."""

    def __init__(self, name: str, date: str, version: str):
        self.name = name
        self.date = date
        self.version = version
        self.read_files: list[str] = []
        self.write_files: list[str] = []
        self.create_files: list[str] = []
        self.allowed_commands: list[str] = []
        self.blocked_commands: list[str] = []
        self.blocked_operations: list[str] = []
        self.constraints: list[str] = []

    @classmethod
    def from_frontmatter(cls, meta: dict) -> "SpecScope":
        scope = cls(
            name=meta.get("name", "unknown"),
            date=meta.get("date", ""),
            version=meta.get("version", "1.0.0"),
        )

        scope_data = meta.get("scope", {})

        files = scope_data.get("files", {})
        scope.read_files = files.get("read", [])
        scope.write_files = files.get("write", [])
        scope.create_files = files.get("create", [])

        commands = scope_data.get("commands", {})
        scope.allowed_commands = commands.get("allowed", [])
        scope.blocked_commands = commands.get("blocked", [])

        scope.blocked_operations = scope_data.get("blocked", [])

        scope.constraints = meta.get("constraints", [])

        return scope


class SpecComplianceChecker:
    """
    Checks if an action is within the allowed scope of active specs.

    Usage:
        checker = SpecComplianceChecker()
        checker.activate_spec("skill-hot-loading")

        result = checker.check_action(
            action="write",
            target="agents/dispatcher/skills/loader.py"
        )
        # result.compliant = True/False
    """

    def __init__(self, specs_dir: Optional[Path] = None):
        if specs_dir is None:
            base = Path(__file__).parent.parent.parent
            specs_dir = base / "docs" / "superpowers" / "specs"

        self.specs_dir = Path(specs_dir)
        self.active_specs: dict[str, SpecScope] = {}
        self._all_scopes: list[SpecScope] = []
        self._load_all_specs()

    def _load_all_specs(self):
        """Load all specs from the specs directory."""
        if not self.specs_dir.exists():
            logger.warning(f"Specs directory not found: {self.specs_dir}")
            return

        for spec_file in self.specs_dir.glob("*.md"):
            try:
                scope = self._parse_spec(spec_file)
                if scope:
                    self._all_scopes.append(scope)
                    logger.info(f"Loaded spec: {scope.name} v{scope.version}")
            except Exception as e:
                logger.warning(f"Failed to load spec {spec_file}: {e}")

    def _parse_spec(self, spec_file: Path) -> Optional[SpecScope]:
        """Parse a spec file and extract frontmatter scope."""
        content = spec_file.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            # Try to find scope section in the doc
            return self._parse_scope_from_doc(content, spec_file.stem)

        frontmatter = frontmatter_match.group(1)
        try:
            meta = yaml.safe_load(frontmatter)
            return SpecScope.from_frontmatter(meta)
        except yaml.YAMLError as e:
            logger.warning(f"YAML parse error in {spec_file}: {e}")
            return None

    def _parse_scope_from_doc(self, content: str, fallback_name: str) -> Optional[SpecScope]:
        """Parse scope from document structure (for specs without frontmatter)."""
        # This allows gradual adoption - extract what we can from existing docs
        scope = SpecScope(
            name=fallback_name,
            date="",
            version="1.0.0",
        )

        # Look for file path patterns in the doc
        file_patterns = re.findall(r'`([^`]*\.(?:py|yaml|md|sql|vue|ts))`', content)
        for pattern in file_patterns:
            # Convert to glob pattern
            if "/" in pattern:
                pattern = f"**/{pattern.split('/')[-1]}"
            else:
                pattern = f"**/{pattern}"
            if pattern not in scope.read_files:
                scope.read_files.append(pattern)

        # Look for commands mentioned
        commands = re.findall(r'`(python|pytest|git|npm|uvicorn|pytest)`', content)
        scope.allowed_commands.extend(list(set(commands)))

        return scope

    def activate_spec(self, name: str) -> bool:
        """Activate a spec by name. Returns True if found."""
        for scope in self._all_scopes:
            if scope.name.lower() == name.lower():
                self.active_specs[scope.name] = scope
                logger.info(f"Activated spec: {scope.name}")
                return True
        return False

    def deactivate_spec(self, name: str):
        """Deactivate a spec."""
        self.active_specs.pop(name, None)

    def get_active_scopes(self) -> list[SpecScope]:
        """Get all currently active scopes."""
        return list(self.active_specs.values())

    def check_action(
        self,
        action: str,
        target: Optional[str] = None,
        command: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "ComplianceResult":
        """
        Check if an action is within active spec scope.

        Returns ComplianceResult with:
        - compliant: bool
        - reason: str
        - suggestion: str (if not compliant)
        - required_scope_additions: list (if not compliant)
        """
        if not self.active_specs:
            # No active specs - use default project scope
            return self._check_default_scope(action, target, command)

        # Check each active scope
        for scope in self.active_specs.values():
            result = self._check_against_scope(
                scope, action, target, command, description
            )
            if result.compliant:
                return result

        # Not compliant with any active scope
        return ComplianceResult(
            compliant=False,
            reason="Action is outside the scope of all active specs",
            suggestion="Either: (1) Modify the spec to include this action, or (2) Complete current work first",
            required_scope_additions=self._suggest_scope_additions(action, target, command),
        )

    def _check_default_scope(self, action: str, target: str | None, command: str | None) -> "ComplianceResult":
        """Check against project defaults."""
        # Default project scope - conservative
        default_write_dirs = ["agents/", "dashboard/", "config/", "tests/", "docs/"]
        default_read_dirs = ["agents/", "dashboard/", "config/", "tests/", "docs/", "database/"]
        default_allowed_cmds = ["python", "pytest", "git status", "git diff", "git log"]
        default_blocked_cmds = ["git push --force", "rm -rf /*", "format"]

        if action == "read":
            if target:
                for dir in default_read_dirs:
                    if dir in target:
                        return ComplianceResult(compliant=True, reason="Standard project read")
            return ComplianceResult(compliant=True, reason="Read operations allowed")

        if action == "write":
            if target:
                # Check if in allowed directories
                for dir in default_write_dirs:
                    if dir in target:
                        return ComplianceResult(compliant=True, reason=f"Writing to {dir} is allowed")

                # Check if blocking sensitive files
                if ".env" in target or "credentials" in target:
                    return ComplianceResult(
                        compliant=False,
                        reason="Writing to sensitive files requires spec update",
                        suggestion="Add explicit permission in spec frontmatter",
                    )

            return ComplianceResult(
                compliant=True,
                reason="Write within default project scope",
            )

        if action == "Bash" and command:
            cmd_lower = command.lower()

            # Check blocked
            for blocked in default_blocked_cmds:
                if blocked.lower() in cmd_lower:
                    return ComplianceResult(
                        compliant=False,
                        reason=f"Command matches blocked pattern: {blocked}",
                        suggestion="This command is blocked by default project policy",
                    )

            # Check allowed
            for allowed in default_allowed_cmds:
                if cmd_lower.strip().startswith(allowed):
                    return ComplianceResult(compliant=True, reason=f"{allowed} is allowed")

            # Unknown command
            return ComplianceResult(
                compliant=False,
                reason="Command not in default allowed list",
                suggestion="Add command to spec scope or use default allowed commands",
            )

        # Default to compliant for unknown actions
        return ComplianceResult(compliant=True, reason="Default scope allows this action")

    def _check_against_scope(
        self,
        scope: SpecScope,
        action: str,
        target: str | None,
        command: str | None,
        description: str | None,
    ) -> "ComplianceResult":
        """Check action against a specific scope."""
        # Check blocked operations first
        if description:
            for blocked in scope.blocked_operations:
                if blocked.lower() in description.lower():
                    return ComplianceResult(
                        compliant=False,
                        reason=f"Action matches blocked operation: {blocked}",
                        suggestion=f"Remove or rephrase to avoid: {blocked}",
                    )

        # Check file operations
        if target and action in ("read", "write", "create"):
            if action == "read":
                patterns = scope.read_files
            elif action == "write":
                patterns = scope.write_files
            else:  # create
                patterns = scope.create_files

            if patterns:
                if self._matches_any_pattern(target, patterns):
                    return ComplianceResult(
                        compliant=True,
                        reason=f"Allowed by spec '{scope.name}'",
                    )
                else:
                    return ComplianceResult(
                        compliant=False,
                        reason=f"Target not in spec '{scope.name}' scope",
                        suggestion=f"Add to spec scope or create new spec for this work",
                    )

        # Check command operations
        if command and action == "Bash":
            cmd_lower = command.lower()

            # Check blocked commands
            for blocked in scope.blocked_commands:
                if blocked.lower() in cmd_lower:
                    return ComplianceResult(
                        compliant=False,
                        reason=f"Command blocked by spec '{scope.name}'",
                        suggestion=f"Use alternative: {self._suggest_alternative(blocked)}",
                    )

            # Check allowed commands
            if scope.allowed_commands:
                for allowed in scope.allowed_commands:
                    if cmd_lower.strip().startswith(allowed.lower()):
                        return ComplianceResult(
                            compliant=True,
                            reason=f"Command allowed by spec '{scope.name}'",
                        )

                # Not in allowed list
                return ComplianceResult(
                    compliant=False,
                    reason=f"Command not in spec '{scope.name}' allowed list",
                    suggestion="Add command to spec scope or use listed allowed commands",
                )

        # If no specific rules matched, it's not in scope
        if target or command:
            return ComplianceResult(
                compliant=False,
                reason=f"Action not defined in spec '{scope.name}'",
            )

        # Default - allow if nothing matched
        return ComplianceResult(compliant=True, reason="Within spec scope")

    def _matches_any_pattern(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any of the glob patterns."""
        # Normalize path
        normalized = path.replace("\\", "/")

        for pattern in patterns:
            # Normalize pattern
            pattern_normalized = pattern.replace("\\", "/")

            # Direct match
            if normalized == pattern_normalized:
                return True

            # Glob match
            if fnmatch.fnmatch(normalized, pattern_normalized):
                return True

            # Directory match - pattern like "agents/**/*.py" matches "agents/dispatcher/skills/loader.py"
            if "**" in pattern_normalized:
                dir_part = pattern_normalized.split("**")[0].rstrip("/")
                if normalized.startswith(dir_part) or dir_part in normalized:
                    return True

        return False

    def _suggest_alternative(self, blocked: str) -> str:
        """Suggest alternative to blocked command."""
        alternatives = {
            "git push --force": "git push (coordinate with team first)",
            "rm -rf": "rm -ri (interactive, safer)",
            "git reset --hard": "git reset --soft (reversible)",
        }
        return alternatives.get(blocked, "review command necessity")

    def _suggest_scope_additions(self, action: str, target: str | None, command: str | None) -> list[str]:
        """Suggest what to add to scope for this action."""
        suggestions = []
        if target:
            suggestions.append(f"  {action}: ['{target}']")
        if command:
            suggestions.append(f"  allowed_commands: ['{command.split()[0]}']")
        return suggestions

    def generate_scope_additions(self, action: str, target: str | None = None, command: str | None = None) -> str:
        """Generate YAML snippet to add to spec for this action."""
        lines = ["# Add to spec frontmatter scope section:"]
        lines.append("scope:")

        if target:
            if action == "write":
                lines.append(f"  files:")
                lines.append(f"    write: ['{target}']")
            elif action == "create":
                lines.append(f"  files:")
                lines.append(f"    create: ['{target}']")
            elif action == "read":
                lines.append(f"  files:")
                lines.append(f"    read: ['{target}']")

        if command:
            lines.append(f"  commands:")
            lines.append(f"    allowed: ['{command.split()[0]}']")

        return "\n".join(lines)


class ComplianceResult:
    """Result of a compliance check."""

    def __init__(
        self,
        compliant: bool,
        reason: str,
        suggestion: str = "",
        required_scope_additions: list = None,
    ):
        self.compliant = compliant
        self.reason = reason
        self.suggestion = suggestion
        self.required_scope_additions = required_scope_additions or []


# Global singleton
_checker: Optional[SpecComplianceChecker] = None


def get_compliance_checker() -> SpecComplianceChecker:
    """Get the global compliance checker singleton."""
    global _checker
    if _checker is None:
        _checker = SpecComplianceChecker()
    return _checker


def check_compliance(action: str, target: str = None, command: str = None) -> "ComplianceResult":
    """Quick compliance check."""
    return get_compliance_checker().check_action(action, target, command)
