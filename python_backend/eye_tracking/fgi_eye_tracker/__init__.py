"""ZuDoc FGI-Net eye tracking package."""

from .tracker import EyeTracker, GazeResult
from .plot import EyeXYGraph

__all__ = ["EyeTracker", "GazeResult", "EyeXYGraph"]
