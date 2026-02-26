"""
web/routes package
==================
Blueprint routes for main, demografi, and cost
"""

from .main import main_bp
from .demografi import demografi_bp
from .cost import cost_bp

__all__ = ['main_bp', 'demografi_bp', 'cost_bp']