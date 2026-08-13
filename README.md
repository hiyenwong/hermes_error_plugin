# Hermes Error Handler Plugin

Transform LLM API errors into user-friendly messages.

## Features

- **User-Friendly Messages**: Converts technical API errors into clear, actionable messages in Chinese (简体中文)
- **Dual-Layer Interception**: Catches both soft failures (via `transform_llm_output`) and hard failures (via `on_llm_error`)
- **Customizable**: Override messages per error category, provider, or model
- **Developer-Friendly**: Optionally show technical details in collapsed sections
- **Graceful Degradation**: Works without host patch (covers ~20% of errors), full coverage with patch

## Error Categories

| Category | Emoji | Description | Example |
|----------|-------|-------------|---------|
| Rate Limit | ⏳ | Too many requests | 429 errors |
| Billing | 💳 | Insufficient credits | 402 errors |
| Auth | 🔐 | Authentication failed | 401/403 errors |
| Context Overflow | 📝 | Conversation too long | Token limit exceeded |
| Server Error | 🔧 | Service unavailable | 500/502/503 errors |
| Network | 🌐 | Connection issues | Timeout, DNS |
| Model Not Found | 🤖 | Invalid model | 404 model errors |
| Unknown | ⚠️ | Unclassified | Other errors |

## Installation

### 1. Install Plugin

```bash
# Create plugin directory
mkdir -p ~/.hermes/plugins/error-handler

# Copy plugin files
cp -r hermes_error_plugin/* ~/.hermes/plugins/error-handler/

# Enable plugin
hermes plugins enable error-handler
```

### 2. Apply Host Patch (Optional, for Full Coverage)

See [host_patches/README.md](host_patches/README.md) for instructions.

**Without patch**: Plugin works via `transform_llm_output` (covers ~20% of errors)  
**With patch**: Full coverage (100% of errors)

## Configuration

Create `~/.hermes/plugins/error-handler/config.yaml`:

```yaml
# Message language
language: "zh-CN"  # or "en-US"

# Show technical details in collapsed section
show_technical_details: false

# Custom messages (optional)
# Format: {category}:{provider}:{model} -> message
custom_messages:
  rate_limit:openai:gpt-4: "GPT-4 is very popular right now! Please try again in a minute."
  billing:anthropic:claude-3-opus: "Claude 3 Opus credits exhausted."

# Custom error patterns (optional)
# Format: category -> [regex patterns]
error_patterns:
  rate_limit:
    - "custom_rate_limit_pattern"
    - "another_pattern"
```

### Environment Variables

```bash
# Override language
export HERMES_ERROR_HANDLER_LANG="en-US"

# Enable technical details
export HERMES_ERROR_HANDLER_SHOW_TECHNICAL="true"
```

## Example Output

### Without Plugin (Raw Error)

```
Error: API rate limit exceeded. Expected retry after 30 seconds.
HTTP 429 Too Many Requests
Request ID: req_abc123
```

### With Plugin (User-Friendly)

```
⏳ 请求太频繁了

系统暂时无法处理您的请求，请稍后再试。

💡 **建议**：等待 30 秒后重试
```

### With Technical Details Enabled

```
⏳ 请求太频繁了

系统暂时无法处理您的请求，请稍后再试。

💡 **建议**：等待 30 秒后重试

---
<details>
<summary>技术详情 (Technical Details)</summary>

```
Error: API rate limit exceeded. Expected retry after 30 seconds.
HTTP 429 Too Many Requests
```
</details>
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Hermes Agent                                                │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  conversation_loop.py                                   │ │
│  │                                                         │ │
│  │  Soft Failures ──────┐                                  │ │
│  │  (break)             │                                  │ │
│  │                      ▼                                  │ │
│  │              transform_llm_output ◄── Plugin Hook       │ │
│  │                                                         │ │
│  │  Hard Failures ──────┐                                  │ │
│  │  (return failed)     │                                  │ │
│  │                      │                                  │ │
│  └──────────────────────┼──────────────────────────────────┘ │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────────┐ │
│  │  run_agent.py: chat()                                    │ │
│  │                                                          │ │
│  │  if result["failed"]:                                    │ │
│  │      invoke_hook("on_llm_error") ◄── Plugin Hook         │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Development

### Project Structure

```
hermes_error_plugin/
├── plugin.yaml              # Plugin manifest
├── __init__.py              # Entry point + hooks
├── config.py                # Configuration loading
├── error_mapper.py          # Error classification
├── message_templates.py     # Message templates
├── host_patches/
│   └── README.md            # Host patch instructions
└── README.md                # This file
```

### Testing

```bash
# Install in dev mode
ln -s $(pwd) ~/.hermes/plugins/error-handler

# Run Hermes with debug logging
hermes chat --debug 2>&1 | grep error-handler

# Test error scenarios
# 1. Rate limit: Send many requests quickly
# 2. Auth error: Use invalid API key
# 3. Context overflow: Send very long conversation
```

### Adding New Error Categories

1. Add category to `ErrorCategory` enum in `error_mapper.py`
2. Add default message in `message_templates.py`
3. Add patterns in `DEFAULT_ERROR_PATTERNS`
4. Update `README.md` error categories table

## Compatibility

- **Hermes Agent**: Requires version with plugin support
- **Python**: 3.10+
- **Dependencies**: `pyyaml`

## License

MIT License

## Contributing

Contributions welcome! Areas for improvement:

- Additional language support
- More error patterns
- Provider-specific messages
- Integration with Hermes error_classifier

## References

- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Hermes Plugin Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
- [Error Classifier Source](../../hermes-agent/agent/error_classifier.py)
