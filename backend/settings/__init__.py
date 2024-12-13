# __init__.py

from .readonly import ReadOnlySettings

settings = ReadOnlySettings()

# Expose only the settings instance
__all__ = ["settings"]
