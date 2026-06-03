"""
Logging configuration for agent debugging
"""
import logging

# Use Python's standard logging - simple and clean
logger = logging.getLogger(__name__)

# Keep the helper functions for backward compatibility but make them no-ops
def log_agent_start(agent_name: str, user_id: int, message: str):
    pass

def log_agent_end(agent_name: str, response: str):
    pass

def log_tool_call(tool_name: str, params: dict):
    pass

def log_tool_result(tool_name: str, result: any):
    pass

def log_decision(decision_type: str, details: str):
    pass

def log_error(error_type: str, error: Exception):
    pass

def log_context(context_type: str, data: dict):
    pass

def log_flow_step(step_name: str, details: str):
    pass

def log_request_start(user_id: int, message: str):
    pass

def log_request_end(response: str):
    pass
