"""Module containing interfaces for the time-resolved state and propagator"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Propagator(ABC):
    """Interface representing a propagator.

    The implementation must be a callable and should take 3 arguments:
    state, time (float), timestep (float).
    It returns the state after time evolution of one timestep.
    """

    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return hasattr(__subclass, "__call__")

    @abstractmethod
    def __call__(self, state: Any, time: float, timestep: float) -> Any:
        """Propagate state from (time) to (time + timestep) and return state.
        """
        raise NotImplementedError
