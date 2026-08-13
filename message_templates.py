"""User-friendly message templates.

This module provides:
- Default error messages in Chinese (简体中文)
- Message retrieval function with customization support
- Technical detail formatting for developers
"""

from __future__ import annotations

from typing import Any, Dict

from .error_mapper import ErrorCategory
from .config import Config


# Default messages in Chinese (简体中文)
# These messages are designed to be:
# 1. User-friendly and non-technical
# 2. Actionable with specific suggestions
# 3. Emoji-enhanced for visual clarity
DEFAULT_MESSAGES: Dict[ErrorCategory, str] = {
    ErrorCategory.RATE_LIMIT: (
        "⏳ 请求太频繁了\n\n"
        "系统暂时无法处理您的请求，请稍后再试。\n\n"
        "💡 **建议**：等待 30 秒后重试"
    ),
    ErrorCategory.BILLING: (
        "💳 额度不足\n\n"
        "当前服务的额度已用完，请联系管理员或稍后重试。\n\n"
        "💡 **建议**：检查账户余额或切换到其他服务"
    ),
    ErrorCategory.AUTH: (
        "🔐 认证失败\n\n"
        "无法验证服务身份，可能是 API 密钥问题。\n\n"
        "💡 **建议**：联系管理员检查配置"
    ),
    ErrorCategory.CONTEXT_OVERFLOW: (
        "📝 对话太长了\n\n"
        "当前对话超出了处理能力，请开始新对话或总结之前的内容。\n\n"
        "💡 **建议**：使用 `/clear` 开始新对话"
    ),
    ErrorCategory.SERVER_ERROR: (
        "🔧 服务暂时不可用\n\n"
        "服务出现问题，正在尝试修复。请稍后再试。\n\n"
        "💡 **建议**：等待几分钟后重试"
    ),
    ErrorCategory.NETWORK: (
        "🌐 网络连接问题\n\n"
        "无法连接到服务，请检查网络连接。\n\n"
        "💡 **建议**：检查网络后重试"
    ),
    ErrorCategory.MODEL_NOT_FOUND: (
        "🤖 模型不可用\n\n"
        "请求的 AI 模型暂时不可用或不存在。\n\n"
        "💡 **建议**：稍后重试或使用 `/model` 切换模型"
    ),
    ErrorCategory.UNKNOWN: (
        "⚠️ 遇到了一些问题\n\n"
        "无法完成请求，请稍后重试。\n\n"
        "💡 **建议**：如果问题持续，请联系支持"
    ),
}

# English translations (for future i18n support)
DEFAULT_MESSAGES_EN: Dict[ErrorCategory, str] = {
    ErrorCategory.RATE_LIMIT: (
        "⏳ Too Many Requests\n\n"
        "The system is temporarily unable to handle your request. Please try again later.\n\n"
        "💡 **Tip**: Wait 30 seconds and retry"
    ),
    ErrorCategory.BILLING: (
        "💳 Insufficient Credits\n\n"
        "Your service quota has been exhausted. Please contact your administrator.\n\n"
        "💡 **Tip**: Check your account balance or switch to another service"
    ),
    ErrorCategory.AUTH: (
        "🔐 Authentication Failed\n\n"
        "Unable to verify service identity. This may be an API key issue.\n\n"
        "💡 **Tip**: Contact your administrator to check the configuration"
    ),
    ErrorCategory.CONTEXT_OVERFLOW: (
        "📝 Conversation Too Long\n\n"
        "The current conversation exceeds the processing capacity. "
        "Please start a new conversation or summarize previous content.\n\n"
        "💡 **Tip**: Use `/clear` to start a new conversation"
    ),
    ErrorCategory.SERVER_ERROR: (
        "🔧 Service Unavailable\n\n"
        "The service is experiencing issues and is being fixed. Please try again later.\n\n"
        "💡 **Tip**: Wait a few minutes and retry"
    ),
    ErrorCategory.NETWORK: (
        "🌐 Network Connection Issue\n\n"
        "Unable to connect to the service. Please check your network connection.\n\n"
        "💡 **Tip**: Check your network and retry"
    ),
    ErrorCategory.MODEL_NOT_FOUND: (
        "🤖 Model Not Available\n\n"
        "The requested AI model is temporarily unavailable or does not exist.\n\n"
        "💡 **Tip**: Retry later or use `/model` to switch models"
    ),
    ErrorCategory.UNKNOWN: (
        "⚠️ Something Went Wrong\n\n"
        "Unable to complete the request. Please try again later.\n\n"
        "💡 **Tip**: If the problem persists, please contact support"
    ),
}


def get_message(
    category: ErrorCategory,
    provider: str,
    model: str,
    config: Config,
    error_info: Dict[str, Any],
) -> str:
    """Get user-friendly message for error category.

    Priority order:
    1. Custom message from config (if defined)
    2. Default message for category

    If show_technical_details is enabled, appends raw error
    information in a collapsed <details> section.

    Args:
        category: Error category.
        provider: Provider name (e.g., 'openai', 'anthropic').
        model: Model name (e.g., 'gpt-4', 'claude-3-opus').
        config: Plugin configuration.
        error_info: Raw error information.

    Returns:
        User-friendly error message.
    """
    # Check for custom messages in config
    custom = config.get_custom_message(category, provider, model)
    if custom:
        message = custom
    else:
        # Use default message based on language
        if config.language.startswith("en"):
            message = DEFAULT_MESSAGES_EN.get(
                category, DEFAULT_MESSAGES_EN[ErrorCategory.UNKNOWN]
            )
        else:
            message = DEFAULT_MESSAGES.get(
                category, DEFAULT_MESSAGES[ErrorCategory.UNKNOWN]
            )

    # Append technical details for developers (if enabled)
    if config.show_technical_details:
        raw_message = error_info.get("message", "") or error_info.get("raw", "")
        if raw_message:
            # Truncate very long messages
            if len(raw_message) > 500:
                raw_message = raw_message[:497] + "..."
            # Escape backticks in raw message
            raw_message = raw_message.replace("```", "``\\`")
            message += (
                f"\n\n---\n"
                f"<details>\n"
                f"<summary>技术详情 (Technical Details)</summary>\n\n"
                f"```\n{raw_message}\n```\n"
                f"</details>"
            )

    return message
