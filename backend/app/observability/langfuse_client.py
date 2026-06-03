"""
Langfuse client for tracking agent execution with detailed observability
"""
from langfuse import observe
from app.config import LANGFUSE_ENABLED, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
import functools
import os
import json
from typing import Any, Callable

# Try to import langfuse_context, but make it optional for advanced features
try:
    from langfuse.decorators import langfuse_context
    HAS_LANGFUSE_CONTEXT = True
except ImportError:
    HAS_LANGFUSE_CONTEXT = False
    langfuse_context = None

# Initialize Langfuse via environment variables (required for @observe decorator)
_init_attempted = False


def init_langfuse():
    """Initialize Langfuse by setting environment variables."""
    global _init_attempted
    
    if _init_attempted:
        return
    
    _init_attempted = True
    
    # Check if we have credentials
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        print("⚠️ Langfuse: Missing credentials")
        return
    
    if not LANGFUSE_ENABLED:
        print("ℹ️ Langfuse: Disabled")
        return
    
    try:
        # Set environment variables for Langfuse @observe decorator
        os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
        os.environ["LANGFUSE_HOST"] = LANGFUSE_HOST
        
        print(f"✅ Langfuse initialized: {LANGFUSE_HOST}")
        
    except Exception as e:
        print(f"❌ Langfuse initialization failed: {e}")


# Initialize on module load
init_langfuse()


def trace_agent(agent_name: str):
    """
    Decorator to trace agent execution with Langfuse using @observe decorator.
    
    Usage:
        @trace_agent("ActivityAgent")
        async def run_activity_agent(db, user_id, message):
            ...
    """
    def decorator(func):
        if not LANGFUSE_ENABLED:
            # Return unwrapped function if Langfuse is disabled
            return func
        
        # Apply Langfuse @observe decorator
        observed_func = observe(name=agent_name, as_type="generation")(func)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the observed function
            result = await observed_func(*args, **kwargs)
            return result
        
        return wrapper
    return decorator


def trace_tool_call(tool_name: str, input_data: dict) -> Any:
    """
    Create a span for individual tool calls within an agent.
    
    Usage:
        with trace_tool_call("parse_activity_message", {"message": message}):
            result = parse_activity_message_tool(message)
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return _NoOpContext()
    
    try:
        span = langfuse_context.current_observation().span(
            name=tool_name,
            input=input_data
        )
        return span
    except Exception:
        return _NoOpContext()


def trace_llm_call(model: str, input_messages: list, metadata: dict = None):
    """
    Create a generation span for LLM calls to track token usage.
    
    Usage:
        generation = trace_llm_call(
            model="gpt-4",
            input_messages=[{"role": "user", "content": "..."}],
            metadata={"temperature": 0.7}
        )
        # After LLM call:
        generation.end(
            output=response,
            usage={"input": 100, "output": 50, "total": 150}
        )
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return _NoOpContext()
    
    try:
        generation = langfuse_context.current_observation().generation(
            name=f"llm_call_{model}",
            model=model,
            input=input_messages,
            metadata=metadata or {}
        )
        return generation
    except Exception:
        return _NoOpContext()


def trace_agent_handoff(from_agent: str, to_agent: str, input_data: dict):
    """
    Create a span for agent-to-agent handoffs.
    
    Usage:
        with trace_agent_handoff("Orchestrator", "ActivityAgent", {"message": msg}):
            result = await activity_agent.run(message)
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return _NoOpContext()
    
    try:
        span = langfuse_context.current_observation().span(
            name=f"handoff_{from_agent}_to_{to_agent}",
            input=input_data,
            metadata={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "handoff_type": "agent_delegation"
            }
        )
        return span
    except Exception:
        return _NoOpContext()


def add_trace_metadata(key: str, value: Any):
    """
    Add metadata to the current trace.
    
    Usage:
        add_trace_metadata("user_id", 123)
        add_trace_metadata("session_id", "abc-123")
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return
    
    try:
        langfuse_context.update_current_trace(
            metadata={key: value}
        )
    except Exception:
        pass


def add_trace_tags(tags: list[str]):
    """
    Add tags to the current trace for filtering.
    
    Usage:
        add_trace_tags(["water-logging", "activity", "success"])
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return
    
    try:
        langfuse_context.update_current_trace(tags=tags)
    except Exception:
        pass


def set_trace_user(user_id: str | int):
    """
    Set the user ID for the current trace.
    
    Usage:
        set_trace_user(123)
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return
    
    try:
        langfuse_context.update_current_trace(user_id=str(user_id))
    except Exception:
        pass


def set_trace_session(session_id: str):
    """
    Set the session ID for the current trace.
    
    Usage:
        set_trace_session("user_123_session_456")
    """
    if not LANGFUSE_ENABLED or not HAS_LANGFUSE_CONTEXT:
        return
    
    try:
        langfuse_context.update_current_trace(session_id=session_id)
    except Exception:
        pass


class _NoOpContext:
    """No-op context manager when Langfuse is disabled."""
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def end(self, **kwargs):
        pass
    
    def update(self, **kwargs):
        pass


def wrap_tool_with_tracing(tool_func: Callable, tool_name: str) -> Callable:
    """
    Wrap a tool function to automatically trace its execution.
    
    Usage:
        @function_tool
        def my_tool(arg1, arg2):
            return tool_implementation(arg1, arg2)
        
        # Wrap it:
        traced_tool = wrap_tool_with_tracing(my_tool, "my_tool")
    """
    if not LANGFUSE_ENABLED:
        return tool_func
    
    @functools.wraps(tool_func)
    def wrapper(*args, **kwargs):
        # Prepare input data
        input_data = {
            "args": [str(arg) for arg in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()}
        }
        
        span = trace_tool_call(tool_name, input_data)
        try:
            result = tool_func(*args, **kwargs)
            if hasattr(span, 'end'):
                span.end(output=result)
            return result
        except Exception as e:
            if hasattr(span, 'end'):
                span.end(output={"error": str(e)}, level="ERROR")
            raise
    
    return wrapper
