# flake8: noqa
"""Protocol: A simple workflow management system based on YAML"""
from .settings import SETTINGS
if not SETTINGS.check():
    raise ValueError("Package not configured yet.")

from .api import Protocol, Schedule
