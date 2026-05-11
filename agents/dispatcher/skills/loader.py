"""Hot-loading skill loader for dispatcher agent.

Loads skills from markdown files with YAML frontmatter.
Skills can be updated on disk and reloaded without restarting the agent.
"""
import re
import sys
import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any, Callable

import yaml

logger = logging.getLogger(__name__)

# ---- Skill file structure ----

SKILL_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*?)(?=^---|\Z)",
    re.DOTALL | re.MULTILINE,
)

CODE_BLOCK_PATTERN = re.compile(r"```python\n(.*?)\n```", re.DOTALL)


class Skill:
    """A loaded skill with metadata and callable function."""

    def __init__(self, name: str, description: str, category: str, fn: Callable):
        self.name = name
        self.description = description
        self.category = category
        self.fn = fn
        self._tool = None

    def to_langchain_tool(self):
        """Convert skill to a LangChain tool."""
        from langchain_core.tools import tool as lc_tool

        async_fn = self._make_async_wrapper()
        desc = self.description

        @lc_tool(description=desc)
        async def wrapper(**kwargs) -> str:
            return await async_fn(**kwargs)

        wrapper.name = self.name
        self._tool = wrapper
        return wrapper

    def _make_async_wrapper(self):
        """Wrap skill function to ensure async execution."""
        fn = self.fn
        if inspect.iscoroutinefunction(fn):
            return fn

        async def async_wrapper(**kwargs):
            return fn(**kwargs)

        return async_wrapper


class SkillLoader:
    """Hot-reloading skill loader from markdown files."""

    def __init__(self, skills_dir: str | Path | None = None):
        if skills_dir is None:
            base = Path(__file__).parent.parent  # agents/dispatcher/
            skills_dir = base / "skills"  # agents/dispatcher/skills
        self.skills_dir = Path(skills_dir)
        self._skills: dict[str, Skill] = {}
        self._mtimes: dict[str, float] = {}
        self._module_name = "_dynamic_skills"
        self._namespace: dict[str, Any] = {}
        self.load_all()

    def load_all(self):
        """Load or reload all skills from the skills directory."""
        for md_file in self.skills_dir.glob("*.md"):
            if md_file.name == "SKILL_FORMAT.md":
                continue
            self._load_skill_file(md_file)

    def _load_skill_file(self, path: Path) -> list[Skill]:
        """Load a single skill file and return loaded skills."""
        content = path.read_text(encoding="utf-8")
        skills = self._parse_skill_file(content)

        for skill in skills:
            existing = self._skills.get(skill.name)
            if existing:
                logger.info(f"[SkillLoader] Reloaded: {skill.name} from {path.name}")
            else:
                logger.info(f"[SkillLoader] Loaded: {skill.name} from {path.name}")
            self._skills[skill.name] = skill

        self._mtimes[str(path)] = path.stat().st_mtime
        return skills

    def _parse_skill_file(self, content: str) -> list[Skill]:
        """Parse skill markdown file and return list of Skill objects."""
        skills = []

        # Match frontmatter + code block
        for match in SKILL_PATTERN.finditer(content):
            frontmatter = match.group(1)
            body = match.group(2)

            # Parse YAML frontmatter — split on first '---' to avoid trailing delimiter
            frontmatter_str = frontmatter.strip()
            try:
                # Use safe_load on the first document only
                meta = next(yaml.safe_load_all(frontmatter_str))
            except (yaml.YAMLError, StopIteration) as e:
                logger.warning(f"[SkillLoader] YAML parse error: {e}")
                continue

            name = meta.get("name")
            if not name:
                logger.warning("[SkillLoader] Missing 'name' in skill frontmatter")
                continue

            description = meta.get("description", f"Skill: {name}")
            category = meta.get("category", "general")

            # Extract Python code
            code_blocks = CODE_BLOCK_PATTERN.findall(body)
            if not code_blocks:
                logger.warning(f"[SkillLoader] No code block in skill: {name}")
                continue

            # Use the last code block (in case of multiple)
            code = code_blocks[-1]

            # Execute in a clean namespace
            namespace = {"__name__": f"skill_{name}"}
            try:
                compiled = compile(code, f"<skill:{name}>", "exec")
                exec(compiled, namespace)
            except Exception as e:
                logger.error(f"[SkillLoader] Failed to compile skill '{name}': {e}")
                continue

            # Find the skill function (look for skill_fn or name-based function)
            fn = namespace.get("skill_fn") or namespace.get(name)
            if not fn or not callable(fn):
                # Look for any async def in the namespace
                funcs = [
                    v for v in namespace.values()
                    if callable(v) and (
                        importlib.iscoroutinefunction(v) or callable(v)
                    )
                ]
                fn = funcs[0] if funcs else None

            if not fn:
                logger.warning(f"[SkillLoader] No callable function in skill: {name}")
                continue

            skills.append(Skill(name, description, category, fn))

        return skills

    def check_reload(self) -> bool:
        """Check if any skill files changed. Returns True if reload happened."""
        reloaded = False
        for path_str, mtime in list(self._mtimes.items()):
            path = Path(path_str)
            if not path.exists():
                logger.info(f"[SkillLoader] Skill file removed: {path.name}")
                # Don't remove, just mark mtime=0 to skip
                self._mtimes[path_str] = 0
                continue

            current_mtime = path.stat().st_mtime
            if current_mtime > mtime:
                logger.info(f"[SkillLoader] Detected change: {path.name}")
                self._load_skill_file(path)
                reloaded = True

        return reloaded

    def get_tools(self) -> list:
        """Get all skills as LangChain tools. Checks for hot-reload."""
        self.check_reload()
        return [s.to_langchain_tool() for s in self._skills.values()]

    def get_tool_names(self) -> list[str]:
        """Get list of loaded skill names."""
        return list(self._skills.keys())

    def get_skill(self, name: str) -> Skill | None:
        """Get a specific skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """List all skills with metadata."""
        return [
            {"name": s.name, "description": s.description, "category": s.category}
            for s in self._skills.values()
        ]


# ---- Global singleton ----

_loader: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    """Get the global skill loader singleton."""
    global _loader
    if _loader is None:
        _loader = SkillLoader()
    return _loader


def reload_skills() -> list[dict]:
    """Force reload all skills and return updated skill list."""
    loader = get_skill_loader()
    loader.load_all()
    return loader.list_skills()