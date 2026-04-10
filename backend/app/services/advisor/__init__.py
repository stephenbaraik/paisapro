"""
AI Advisor package — modular architecture.

- prompt_engine.py: System prompt builder with context injection
- tools.py: Agentic tool definitions and execution
- advisor_service.py: Main service with streaming, caching, rate limiting
"""

from .prompt_engine import build_system_prompt
from .tools import TOOLS, execute_tool
from .advisor_service import get_advisor_response, stream_advisor_response

__all__ = [
    "build_system_prompt",
    "TOOLS",
    "execute_tool",
    "get_advisor_response",
    "stream_advisor_response",
]
