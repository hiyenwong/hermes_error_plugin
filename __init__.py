"""Hermes Error Handler Plugin

Intercepts LLM API errors and transforms them into user-friendly messages.

This plugin provides two layers of error handling:
1. on_llm_error hook: Catches hard failures (requires host patch)
2. transform_llm_output hook: Catches soft failures (works without host patch)

Usage:
    1. Install plugin:
       mkdir -p ~/.hermes/plugins/error-handler
       cp -r hermes_error_plugin/* ~/.hermes/plugins/error-handler/
       hermes plugins enable error-handler

    2. Apply host patch (optional, for full coverage):
       See host_patches/README.md for instructions
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .config import load_config, Config
from .error_mapper import ErrorMapper, ErrorCategory as ErrorCategory
from .message_templates import get_message

__all__ = [
    "register",
    "ErrorCategory",
    "ErrorMapper",
    "Config",
    "load_config",
    "get_message",
]

logger = logging.getLogger(__name__)

# Global state
_config: Optional[Config] = None
_mapper: Optional[ErrorMapper] = None


def register(ctx: Any) -> None:
    """Plugin entry point.

    Called by Hermes plugin loader when plugin is enabled.
    Registers hooks for error interception.

    Args:
        ctx: Plugin context with register_hook() method.
    """
    global _config, _mapper
    _config = load_config()
    _mapper = ErrorMapper(_config)

    # Register hooks
    # on_llm_error: Catches hard failures (requires host patch)
    # transform_llm_output: Catches soft failures (works without patch)
    ctx.register_hook("on_llm_error", _on_llm_error)
    ctx.register_hook("transform_llm_output", _transform_llm_output)

    logger.debug(
        "error-handler plugin registered (language=%s, technical_details=%s)",
        _config.language,
        _config.show_technical_details,
    )


def _on_llm_error(
    error_info: Dict[str, Any],
    provider: str = "",
    model: str = "",
    session_id: str = "",
    **kwargs: Any,
) -> Optional[str]:
    """Transform LLM API error to user-friendly message.

    Called by host when on_llm_error hook is invoked.
    This hook catches hard failures that bypass transform_llm_output.

    Args:
        error_info: Structured error information from host.
                   May contain 'reason', 'message', 'status_code', etc.
        provider: Provider name (e.g., 'openai', 'anthropic').
        model: Model name (e.g., 'gpt-4', 'claude-3-opus').
        session_id: Session identifier.
        **kwargs: Additional context from host.

    Returns:
        Transformed message string, or None to use default error.
    """
    if not _config or not _mapper:
        logger.warning("Plugin not initialized")
        return None

    try:
        # Classify error
        category = _mapper.classify(error_info)

        # Generate user-friendly message
        message = get_message(
            category=category,
            provider=provider,
            model=model,
            config=_config,
            error_info=error_info,
        )

        logger.info(
            "Transformed error: %s -> %s (category=%s, provider=%s, model=%s)",
            error_info.get("message", "")[:50],
            message[:50],
            category.value,
            provider,
            model,
        )

        return message

    except Exception as exc:
        # Graceful degradation: don't break error flow
        logger.warning("Error transformation failed: %s", exc)
        return None


def _transform_llm_output(
    response_text: str,
    session_id: str = "",
    model: str = "",
    platform: str = "",
    **kwargs: Any,
) -> Optional[str]:
    """Transform LLM output if it contains error patterns.

    This is a fallback for errors that slip through on_llm_error.
    It detects error-like responses and transforms them.

    Args:
        response_text: Raw LLM response text.
        session_id: Session identifier.
        model: Model name.
        platform: Platform identifier.
        **kwargs: Additional context.

    Returns:
        Transformed message string, or None if not an error.
    """
    if not _config or not _mapper:
        return None

    # Check if response looks like an error
    if not _mapper.is_error_response(response_text):
        return None

    try:
        # Classify error from text
        category = _mapper.classify_from_text(response_text)

        # Generate user-friendly message
        message = get_message(
            category=category,
            provider="",
            model=model,
            config=_config,
            error_info={"raw": response_text},
        )

        logger.debug(
            "Transformed error response: %s -> %s (category=%s)",
            response_text[:50],
            message[:50],
            category.value,
        )

        return message

    except Exception as exc:
        # Graceful degradation
        logger.debug("transform_llm_output error handling failed: %s", exc)
        return None
