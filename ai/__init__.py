"""AI Engineering Assistant package.

A thin coordination layer that sits ABOVE the engineering application. It only
reads existing services, snapshot and workflow state - it performs no
engineering calculations, no snapshot mutation and no database writes. All
insight comes from the existing services.
"""
