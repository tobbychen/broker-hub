"""Re-export dispatcher skills for use by other agents."""

from .loader import get_skill_loader, SkillLoader

__all__ = ['get_skill_loader', 'SkillLoader']
