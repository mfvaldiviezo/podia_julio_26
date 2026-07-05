"""Routes package - Flask route handlers."""

from .main_routes import init_routes
from .test_routes import create_test_routes

__all__ = ['init_routes', 'create_test_routes']
