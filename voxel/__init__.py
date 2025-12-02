# Mark voxel as a package and centralize exports if desired.

from . import settings  # re-export for convenience

__all__ = ["settings"]
