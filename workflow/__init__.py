"""Engineering Workflow Framework.

A coordination layer that sits ABOVE the engineering workspaces. It owns
navigation and session state only - it never performs engineering
calculations, validation, or snapshot mutation. Readiness is always obtained
from the existing workspaces/services.
"""
