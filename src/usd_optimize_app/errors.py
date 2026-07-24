"""Custom exceptions for the USD Optimize App."""


class UsdOptimizeAppError(Exception):
    """Base exception for expected application failures."""


class EnvironmentError(UsdOptimizeAppError):
    """Raised when the NVIDIA usd-optimize environment is invalid."""


class PresetError(UsdOptimizeAppError):
    """Raised when a preset cannot be loaded or validated."""


class OptimizeError(UsdOptimizeAppError):
    """Raised when an optimization job fails."""
