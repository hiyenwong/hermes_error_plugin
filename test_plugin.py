#!/usr/bin/env python3
"""Quick test script to verify plugin functionality.

Run from the parent directory:
    python test_plugin.py
"""

from hermes_error_plugin import ErrorCategory, ErrorMapper, load_config


def test_error_classification():
    """Test error classification from various sources."""
    print("🧪 Testing Error Classification...\n")

    config = load_config()
    mapper = ErrorMapper(config)

    # Test 1: Rate limit error (from structured error_info)
    error_info = {
        "reason": "rate_limit",
        "message": "API rate limit exceeded",
        "status_code": 429,
    }
    category = mapper.classify(error_info)
    print(f"✅ Rate limit (reason): {category.value}")
    assert category == ErrorCategory.RATE_LIMIT

    # Test 2: Auth error (from text pattern)
    text = "Invalid API key provided. HTTP 401 Unauthorized"
    category = mapper.classify_from_text(text)
    print(f"✅ Auth error (pattern): {category.value}")
    assert category == ErrorCategory.AUTH

    # Test 3: Context overflow (from text pattern)
    text = "The prompt is too long. Maximum tokens exceeded."
    category = mapper.classify_from_text(text)
    print(f"✅ Context overflow (pattern): {category.value}")
    assert category == ErrorCategory.CONTEXT_OVERFLOW

    # Test 4: Billing error (from text pattern)
    text = "Insufficient credits for this request. Billing quota exceeded."
    category = mapper.classify_from_text(text)
    print(f"✅ Billing error (pattern): {category.value}")
    assert category == ErrorCategory.BILLING

    # Test 5: Server error (from text pattern)
    text = "Service unavailable. HTTP 503 Bad Gateway"
    category = mapper.classify_from_text(text)
    print(f"✅ Server error (pattern): {category.value}")
    assert category == ErrorCategory.SERVER_ERROR

    # Test 6: Unknown error
    text = "Something completely unexpected happened"
    category = mapper.classify_from_text(text)
    print(f"✅ Unknown error: {category.value}")
    assert category == ErrorCategory.UNKNOWN

    print("\n✅ All classification tests passed!\n")


def test_error_detection():
    """Test error response detection."""
    print("🧪 Testing Error Detection...\n")

    config = load_config()
    mapper = ErrorMapper(config)

    # Test error responses
    error_responses = [
        "⏳ 请求太频繁了",
        "❌ Error: API rate limit exceeded",
        "⚠️ Warning: Service unavailable",
        "Error: Authentication failed",
        "Rate limit exceeded",
        "Context length exceeded",
    ]

    for response in error_responses:
        is_error = mapper.is_error_response(response)
        print(f"✅ Detected error: '{response[:40]}...' -> {is_error}")
        assert is_error, f"Should detect error: {response}"

    # Test non-error responses
    normal_responses = [
        "Hello! How can I help you today?",
        "The answer is 42.",
        "Let me explain this concept...",
    ]

    for response in normal_responses:
        is_error = mapper.is_error_response(response)
        print(f"✅ Not an error: '{response[:40]}...' -> {is_error}")
        assert not is_error, f"Should not detect error: {response}"

    print("\n✅ All detection tests passed!\n")


def test_message_generation():
    """Test user-friendly message generation."""
    print("🧪 Testing Message Generation...\n")

    from hermes_error_plugin.message_templates import get_message

    config = load_config()

    # Test each error category
    for category in ErrorCategory:
        message = get_message(
            category=category,
            provider="openai",
            model="gpt-4",
            config=config,
            error_info={"message": "Test error message"},
        )
        print(f"✅ {category.value}:")
        print(f"   {message.split(chr(10))[0]}")  # First line only
        assert message, f"Should generate message for {category.value}"
        assert len(message) > 10, f"Message too short for {category.value}"

    print("\n✅ All message generation tests passed!\n")


def test_config_loading():
    """Test configuration loading."""
    print("🧪 Testing Configuration Loading...\n")

    config = load_config()

    print(f"✅ Language: {config.language}")
    print(f"✅ Show technical details: {config.show_technical_details}")
    print(f"✅ Custom messages: {len(config.custom_messages)} entries")
    print(f"✅ Error patterns: {len(config.error_patterns)} categories")

    assert config.language in ["zh-CN", "en-US"], "Invalid default language"

    print("\n✅ Configuration loading test passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Hermes Error Handler Plugin - Quick Test")
    print("=" * 60)
    print()

    try:
        test_config_loading()
        test_error_classification()
        test_error_detection()
        test_message_generation()

        print("=" * 60)
        print("🎉 All tests passed successfully!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise
