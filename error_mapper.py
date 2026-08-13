"""Error classification and mapping.

This module provides:
- ErrorCategory enum for user-friendly error types
- ErrorMapper class for classifying errors from various sources
- Mapping from Hermes FailoverReason to ErrorCategory
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Pattern

from .config import Config


class ErrorCategory(Enum):
    """User-friendly error categories.

    These categories are designed to be meaningful to end users
    and map to specific recovery actions.
    """

    RATE_LIMIT = "rate_limit"  # 429, too many requests
    BILLING = "billing"  # 402, quota exceeded, insufficient credits
    AUTH = "auth"  # 401, 403, invalid API key
    CONTEXT_OVERFLOW = "context_overflow"  # Context length exceeded
    SERVER_ERROR = "server_error"  # 500, 502, 503, overloaded
    NETWORK = "network"  # Timeout, connection errors
    MODEL_NOT_FOUND = "model_not_found"  # Invalid model name
    UNKNOWN = "unknown"  # Unclassified errors


# Mapping from Hermes FailoverReason to ErrorCategory
# See: hermes-agent/agent/error_classifier.py for FailoverReason enum
_REASON_TO_CATEGORY: Dict[str, ErrorCategory] = {
    "auth": ErrorCategory.AUTH,
    "auth_permanent": ErrorCategory.AUTH,
    "billing": ErrorCategory.BILLING,
    "rate_limit": ErrorCategory.RATE_LIMIT,
    "overloaded": ErrorCategory.SERVER_ERROR,
    "server_error": ErrorCategory.SERVER_ERROR,
    "timeout": ErrorCategory.NETWORK,
    "context_overflow": ErrorCategory.CONTEXT_OVERFLOW,
    "payload_too_large": ErrorCategory.CONTEXT_OVERFLOW,
    "image_too_large": ErrorCategory.CONTEXT_OVERFLOW,
    "model_not_found": ErrorCategory.MODEL_NOT_FOUND,
    "format_error": ErrorCategory.UNKNOWN,
    "invalid_encrypted_content": ErrorCategory.UNKNOWN,
    "multimodal_tool_content_unsupported": ErrorCategory.UNKNOWN,
    "thinking_signature": ErrorCategory.UNKNOWN,
    "long_context_tier": ErrorCategory.CONTEXT_OVERFLOW,
    "provider_policy_blocked": ErrorCategory.AUTH,
    "unknown": ErrorCategory.UNKNOWN,
}

# Default error patterns for classification
# These can be overridden in config.yaml
DEFAULT_ERROR_PATTERNS: Dict[str, List[str]] = {
    ErrorCategory.RATE_LIMIT.value: [
        r"rate limit",
        r"too many requests",
        r"throttl",
        r"429",
        r"requests per minute",
        r"tokens per minute",
    ],
    ErrorCategory.BILLING.value: [
        r"insufficient.*credit",
        r"quota exceeded",
        r"billing",
        r"402",
        r"payment required",
        r"usage limit",
        r"balance.*exceeded",
    ],
    ErrorCategory.AUTH.value: [
        r"invalid.*api.*key",
        r"unauthorized",
        r"forbidden",
        r"401",
        r"403",
        r"authentication.*failed",
        r"access.*denied",
        r"api.*key.*expired",
    ],
    ErrorCategory.CONTEXT_OVERFLOW.value: [
        r"context.*length",
        r"token.*limit",
        r"too.*long",
        r"exceeds.*limit",
        r"maximum.*tokens",
        r"prompt.*too.*long",
        r"context.*window",
    ],
    ErrorCategory.SERVER_ERROR.value: [
        r"server.*error",
        r"500",
        r"502",
        r"503",
        r"overloaded",
        r"internal.*error",
        r"service.*unavailable",
        r"bad gateway",
    ],
    ErrorCategory.NETWORK.value: [
        r"timeout",
        r"connection",
        r"network",
        r"connect.*refused",
        r"dns",
        r"ssl",
        r"tls",
    ],
    ErrorCategory.MODEL_NOT_FOUND.value: [
        r"model.*not.*found",
        r"invalid.*model",
        r"404.*model",
        r"unknown.*model",
        r"model.*does.*not.*exist",
    ],
}


class ErrorMapper:
    """Classify and map errors to user-friendly categories.

    This class provides two classification methods:
    1. classify() - Uses structured error_info (from on_llm_error hook)
    2. classify_from_text() - Uses pattern matching on raw text
    """

    def __init__(self, config: Config) -> None:
        """Initialize mapper with configuration.

        Args:
            config: Plugin configuration instance.
        """
        self._config = config

        # Build error patterns from config + defaults
        all_patterns: Dict[ErrorCategory, List[str]] = {}
        for category in ErrorCategory:
            # Start with defaults
            patterns = DEFAULT_ERROR_PATTERNS.get(category.value, [])
            # Override with config if provided
            if category.value in config.error_patterns:
                patterns = config.error_patterns[category.value]
            # Map to ErrorCategory enum
            all_patterns[category] = patterns

        self._error_patterns: Dict[ErrorCategory, List[Pattern]] = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in all_patterns.items()
        }

    def classify(self, error_info: Dict[str, Any]) -> ErrorCategory:
        """Classify error from structured error_info.

        This method is called when on_llm_error hook is invoked,
        providing structured error information from the host.

        Classification priority:
        1. FailoverReason from host's error_classifier
        2. Pattern matching on message text

        Args:
            error_info: Structured error information.

        Returns:
            Classified error category.
        """
        # Try FailoverReason first (from host's error_classifier)
        reason = error_info.get("reason", "")
        if reason in _REASON_TO_CATEGORY:
            return _REASON_TO_CATEGORY[reason]

        # Fall back to pattern matching
        message = error_info.get("message", "")
        if message:
            return self.classify_from_text(message)

        return ErrorCategory.UNKNOWN

    def classify_from_text(self, text: str) -> ErrorCategory:
        """Classify error from text content.

        Uses pattern matching to identify error type.
        Patterns are checked in category order.

        Args:
            text: Raw error text to classify.

        Returns:
            Classified error category.
        """
        for category, patterns in self._error_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return category
        return ErrorCategory.UNKNOWN

    def is_error_response(self, text: str) -> bool:
        """Check if text looks like an error response.

        Used by transform_llm_output hook to determine if
        the response should be transformed.

        Args:
            text: Response text to check.

        Returns:
            True if text appears to be an error response.
        """
        error_indicators = [
            r"^⏳\s+",  # Hourglass emoji (used by host for errors)
            r"^❌\s+",  # Cross mark
            r"^⚠️\s+",  # Warning
            r"^🚫\s+",  # Prohibited
            r"^💥\s+",  # Collision
            r"error[:\s]",
            r"failed[:\s]",
            r"rate limit",
            r"quota exceeded",
            r"insufficient.*credit",
            r"context.*exceeded",
            r"token.*limit",
            r"api.*error",
            r"service.*unavailable",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in error_indicators)
