# Host Patches for Full Error Coverage

This directory contains patches for the Hermes Agent host to enable full error interception.

## Background

Hermes has two error paths:
1. **Soft failures**: Trigger `transform_llm_output` hook (works without patch)
2. **Hard failures**: Return early with `{"failed": True}`, bypassing all hooks (~80% of errors)

To intercept **all** errors, a minimal host patch is required.

## Patch Details

### 1. Add `on_llm_error` to VALID_HOOKS

**File**: `hermes_cli/plugins.py` (line ~128-168)

```python
VALID_HOOKS: Set[str] = {
    "pre_tool_call",
    "post_tool_call",
    "transform_terminal_output",
    "transform_tool_result",
    "transform_llm_output",
    "pre_llm_call",
    "post_llm_call",
    "pre_api_request",
    "post_api_request",
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
    "subagent_stop",
    "pre_gateway_dispatch",
    "pre_approval_request",
    "post_approval_response",
    "on_llm_error",  # <-- ADD THIS LINE
}
```

### 2. Invoke `on_llm_error` in `run_agent.py`

**File**: `run_agent.py` (line ~4286 in `AIAgent.chat()`)

```python
def chat(self, message: str, **kwargs) -> str:
    result = self.run_conversation(message, **kwargs)

    # --- ADD THIS BLOCK ---
    # Hard failure: invoke on_llm_error hook
    if result.get("failed"):
        try:
            from hermes_cli.plugins import invoke_hook
            hook_results = invoke_hook(
                "on_llm_error",
                error_info=result.get("error_info", {}),
                error_message=result.get("error", ""),
                provider=self.provider,
                model=self.model,
                session_id=self.session_id or "",
            )
            for hook_result in hook_results:
                if isinstance(hook_result, str) and hook_result:
                    result["final_response"] = hook_result
                    break
        except Exception as exc:
            logger.warning("on_llm_error hook failed: %s", exc)
    # --- END OF BLOCK ---

    return result["final_response"]
```

## Why This Location?

- `chat()` is the unified exit point for all conversations
- All hard failures in `conversation_loop.py` (15+ return points) converge here
- Single interception point covers all error paths
- No need to modify `conversation_loop.py` directly

## Applying the Patch

### Option 1: Manual Edit

1. Open `hermes_cli/plugins.py` and add `"on_llm_error"` to `VALID_HOOKS`
2. Open `run_agent.py` and add the hook invocation in `chat()`

### Option 2: Submit PR to Hermes

If the Hermes team accepts this contribution, the patch will be included in a future release.

## Graceful Degradation

Without the host patch:
- Plugin still works via `transform_llm_output` (covers ~20% of errors)
- Hard failures show raw error messages
- No crashes or errors

With the host patch:
- Full error coverage (100%)
- All errors transformed to user-friendly messages
- Seamless integration

## Testing the Patch

After applying:
```bash
# Verify hook is registered
hermes plugins list | grep error-handler

# Test with a rate limit error
hermes chat --test-rate-limit

# Check logs
hermes logs --plugin error-handler
```
