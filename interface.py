"""Module containing interfaces for the time-resolved state and propagator"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Propagator(ABC):
    """Interface representing a propagator."""

    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return (hasattr(__subclass, "propagate") and
                callable(__subclass.propagate) and
                hasattr(__subclass, "initialize_time") and
                callable(__subclass.initialize_time) and
                hasattr(__subclass, "time") and not
                callable(__subclass.time))

    @abstractmethod
    def __init__(self):
        self.time: float = None
        raise NotImplementedError

    @abstractmethod
    def initialize_time(self, initial_time: float, initial_state) -> None:
        """Initialize propagator with an initial time and initial state."""
        raise NotImplementedError

    @abstractmethod
    def propagate(self, state, timestep: float) -> Any:
        """Propagate state by timestep and return state."""
        raise NotImplementedError
