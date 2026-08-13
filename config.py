"""Configuration loading and management.

This module handles loading plugin configuration from:
1. Default values
2. YAML config file (~/.hermes/plugins/error-handler/config.yaml)
3. Environment variables (HERMES_ERROR_HANDLER_*)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml

if TYPE_CHECKING:
    from .error_mapper import ErrorCategory


@dataclass
class Config:
    """Plugin configuration.

    Attributes:
        language: Message language code (e.g., 'zh-CN', 'en-US')
        show_technical_details: Whether to show technical error details
        custom_messages: Custom error messages per category/provider/model
        error_patterns: Custom regex patterns for error classification
    """

    language: str = "zh-CN"
    show_technical_details: bool = False
    custom_messages: Dict[str, str] = field(default_factory=dict)
    error_patterns: Dict[str, List[str]] = field(default_factory=dict)

    def get_custom_message(
        self,
        category: ErrorCategory,
        provider: str,
        model: str,
    ) -> Optional[str]:
        """Get custom message for category/provider/model combination.

        Checks in order of specificity:
        1. category:provider:model (most specific)
        2. category:provider
        3. category (least specific)

        Returns:
            Custom message string, or None if not found.
        """
        # Check model-specific first
        if model:
            key = f"{category.value}:{provider}:{model}"
            if key in self.custom_messages:
                return self.custom_messages[key]

        # Check provider-specific
        if provider:
            key = f"{category.value}:{provider}"
            if key in self.custom_messages:
                return self.custom_messages[key]

        # Check category-only
        key = category.value
        if key in self.custom_messages:
            return self.custom_messages[key]

        return None


def load_config() -> Config:
    """Load configuration from YAML file and environment.

    Priority order:
    1. Environment variables (highest)
    2. Config file
    3. Default values (lowest)

    Returns:
        Loaded Config instance.
    """
    config = Config()

    # Try to load from hermes_home
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    config_path = Path(hermes_home) / "plugins" / "error-handler" / "config.yaml"

    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            config = _merge_config(config, data)
        except Exception:
            # Silently ignore config load errors, use defaults
            pass

    # Environment overrides
    if os.environ.get("HERMES_ERROR_HANDLER_LANG"):
        config.language = os.environ["HERMES_ERROR_HANDLER_LANG"]

    if os.environ.get("HERMES_ERROR_HANDLER_SHOW_TECHNICAL"):
        config.show_technical_details = (
            os.environ["HERMES_ERROR_HANDLER_SHOW_TECHNICAL"].lower() == "true"
        )

    return config


def _merge_config(config: Config, data: Dict[str, Any]) -> Config:
    """Merge YAML data into config.

    Args:
        config: Existing config to merge into.
        data: YAML data to merge.

    Returns:
        Updated config instance.
    """
    if "language" in data:
        config.language = data["language"]
    if "show_technical_details" in data:
        config.show_technical_details = data["show_technical_details"]
    if "custom_messages" in data:
        config.custom_messages.update(data["custom_messages"])
    if "error_patterns" in data:
        for cat, patterns in data["error_patterns"].items():
            config.error_patterns[cat] = patterns
    return config
