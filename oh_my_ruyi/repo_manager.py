"""Backward-compatibility module for repository management and presets."""

from .infra import repo_manager
from .infra.repo_manager import *  # noqa: F403
from .repo_presets import *  # noqa: F403

__all__ = [name for name in dir(repo_manager) if not name.startswith("_")]
