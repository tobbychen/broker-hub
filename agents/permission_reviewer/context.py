"""Session context tracker for permission review.

Tracks what the main agent (Claude Code) is working on so the
permission reviewer sub-agent can understand the full context.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Context file location
CONTEXT_FILE = Path.home() / ".claude" / "permission_context.json"


class SessionContext:
    """Tracks the current session context for permission review."""

    def __init__(self, context_file: Optional[Path] = None):
        self.context_file = context_file or CONTEXT_FILE
        self._context = self._load()

    def _load(self) -> dict:
        """Load existing context from file."""
        if self.context_file.exists():
            try:
                with open(self.context_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load context: {e}")
        return self._empty_context()

    def _empty_context(self) -> dict:
        """Create empty context structure."""
        return {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "started_at": datetime.now().isoformat(),
            "current_task": None,
            "target_file": None,
            "recent_actions": [],
            "goals": [],
            "constraints": [],
        }

    def _save(self):
        """Save context to file."""
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.context_file, "w", encoding="utf-8") as f:
                json.dump(self._context, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.warning(f"Failed to save context: {e}")

    def update_task(self, task: str, target_file: Optional[str] = None):
        """Update the current task context."""
        self._context["current_task"] = task
        if target_file:
            self._context["target_file"] = target_file
        self._save()

    def add_action(self, action: str, details: Optional[str] = None):
        """Record an action the main agent has taken."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
        }
        if details:
            entry["details"] = details
        self._context["recent_actions"].append(entry)

        # Keep only last 20 actions
        if len(self._context["recent_actions"]) > 20:
            self._context["recent_actions"] = self._context["recent_actions"][-20:]

        self._save()

    def set_goals(self, goals: list):
        """Set the current goals."""
        self._context["goals"] = goals
        self._save()

    def add_constraint(self, constraint: str):
        """Add a constraint to the context."""
        if constraint not in self._context["constraints"]:
            self._context["constraints"].append(constraint)
            self._save()

    def get_context_summary(self) -> str:
        """Get a human-readable summary of current context."""
        parts = []

        if self._context.get("current_task"):
            parts.append(f"Current task: {self._context['current_task']}")

        if self._context.get("target_file"):
            parts.append(f"Target file: {self._context['target_file']}")

        if self._context.get("goals"):
            parts.append(f"Goals: {', '.join(self._context['goals'])}")

        if self._context.get("recent_actions"):
            recent = self._context["recent_actions"][-5:]
            actions = [a["action"] for a in recent]
            parts.append(f"Recent actions: {', '.join(actions)}")

        if self._context.get("constraints"):
            parts.append(f"Constraints: {', '.join(self._context['constraints'])}")

        return "\n".join(parts) if parts else "No context available"

    def clear(self):
        """Clear the context."""
        self._context = self._empty_context()
        if self.context_file.exists():
            self.context_file.unlink()


class RecentChangesAnalyzer:
    """Analyzes recent file changes to provide context for permission review."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or self._find_project_root()

    def _find_project_root(self) -> Path:
        """Find the project root by looking for common markers."""
        current = Path.cwd()
        markers = ["CLAUDE.md", "pyproject.toml", "requirements.txt", "package.json"]

        for parent in [current] + list(current.parents):
            if any((parent / marker).exists() for marker in markers):
                return parent

        return current

    def get_recent_file_changes(self, minutes: int = 30) -> list[dict]:
        """Get files that have been modified recently."""
        changes = []

        git_dir = self.project_root / ".git"
        if git_dir.exists():
            changes.extend(self._get_git_changes(minutes))

        # Also check for untracked/new files
        changes.extend(self._get_untracked_files())

        return changes

    def _get_git_changes(self, minutes: int) -> list[dict]:
        """Get recent git changes."""
        import subprocess
        import os

        changes = []
        try:
            # Get recently modified files from git
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "--since", f"{minutes} minutes ago"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for path in result.stdout.strip().split("\n"):
                    if path:
                        changes.append({
                            "type": "modified",
                            "path": path,
                            "reason": "recently modified in git",
                        })

            # Also get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for path in result.stdout.strip().split("\n"):
                    if path and not any(c["path"] == path for c in changes):
                        changes.append({
                            "type": "staged",
                            "path": path,
                            "reason": "staged for commit",
                        })

        except Exception as e:
            logger.debug(f"Git analysis failed: {e}")

        return changes

    def _get_untracked_files(self) -> list[dict]:
        """Get newly created files."""
        import subprocess

        changes = []
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("?? "):
                        path = line[3:].strip()
                        changes.append({
                            "type": "new",
                            "path": path,
                            "reason": "newly created file",
                        })
        except Exception as e:
            logger.debug(f"Untracked file analysis failed: {e}")

        return changes

    def analyze_target_context(self, target_path: str) -> dict:
        """Analyze the context around a specific target path."""
        target = Path(target_path)

        info = {
            "path": target_path,
            "is_project_file": False,
            "recently_modified": False,
            "recently_created": False,
            "related_files": [],
            "context": "unknown",
        }

        # Check if it's a project file
        try:
            rel_path = target.relative_to(self.project_root)
            info["is_project_file"] = True
            info["relative_path"] = str(rel_path)
        except ValueError:
            info["is_project_file"] = False

        # Check recent changes
        recent_changes = self.get_recent_file_changes(minutes=60)

        for change in recent_changes:
            if change["path"] == str(target) or target.name in change["path"]:
                if change["type"] == "modified":
                    info["recently_modified"] = True
                    info["context"] = "file was recently modified"
                elif change["type"] == "new":
                    info["recently_created"] = True
                    info["context"] = "file was recently created"

        # Find related files
        if target.suffix:
            pattern = f"*{target.suffix}"
            for sibling in target.parent.glob(pattern) if target.parent.exists() else []:
                if sibling.name != target.name:
                    info["related_files"].append(str(sibling))

        return info

    def generate_context_report(self, target_path: str) -> str:
        """Generate a context report for a permission request."""
        target_info = self.analyze_target_context(target_path)

        lines = [f"Context analysis for: {target_path}"]

        if target_info["is_project_file"]:
            lines.append(f"- Project file: {target_info.get('relative_path', 'unknown')}")
        else:
            lines.append("- Not a project file")

        if target_info["recently_created"]:
            lines.append("- This file was recently created in this session")
        elif target_info["recently_modified"]:
            lines.append("- This file was recently modified in this session")

        if target_info["context"] != "unknown":
            lines.append(f"- Context: {target_info['context']}")

        if target_info["related_files"]:
            lines.append(f"- Related files: {len(target_info['related_files'])} files in same directory")

        return "\n".join(lines)


# Global singletons
_context: Optional[SessionContext] = None
_analyzer: Optional[RecentChangesAnalyzer] = None


def get_session_context() -> SessionContext:
    """Get the global session context tracker."""
    global _context
    if _context is None:
        _context = SessionContext()
    return _context


def get_recent_changes_analyzer() -> RecentChangesAnalyzer:
    """Get the global recent changes analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = RecentChangesAnalyzer()
    return _analyzer