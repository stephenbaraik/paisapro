"""
AI advisor — backward compatibility shim.

All logic has been moved to the modular advisor/ package.
This file exists so that any existing imports continue to work.
"""

from .advisor.advisor_service import get_advisor_response, stream_advisor_response
from .advisor.prompt_engine import build_system_prompt
from .advisor.tools import TOOLS, execute_tool

__all__ = [
    "get_advisor_response",
    "stream_advisor_response",
    "build_system_prompt",
    "TOOLS",
    "execute_tool",
]
