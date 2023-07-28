"""Module containing interfaces for the time-resolved state and propagator"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np


class _PropagatorFactory(ABC):
    """Helper class for type checking propagator factory methods."""
    @abstractmethod
    def __call__(self, *args, **kwargs) -> Propagator:
        pass


class Propagator(ABC):
    """Interface representing a propagator."""
    _MANDATORY_ATTRIBUTES = ("__call__", "set_t0", "_psi")

    @classmethod
    def register_object(cls, custom_object):
        for att_key in cls._MANDATORY_ATTRIBUTES:
            if not hasattr(custom_object, att_key):
                raise TypeError("Object not compatible with interface.")
        cls.register(type(custom_object))
        return

    @abstractmethod
    def __init__(self):
        self._psi = None

    @abstractmethod
    def __call__(self, time: float, timestep: float) -> np.ndarray:
        pass

    @abstractmethod
    def set_t0(self):
        pass


@dataclass
class TimedState(ABC):
    """Interface representing the time-resolved quantum state"""
    time: float
    psi: np.ndarray
    label = None

    @classmethod
    def register_class(cls, custom_tstate_class):
        if hasattr(custom_tstate_class, "time") and hasattr(
                custom_tstate_class, "psi"):
            if isinstance(custom_tstate_class.time, float) and isinstance(
                    custom_tstate_class.psi, np.ndarray):
                cls.register(custom_tstate_class)
                return custom_tstate_class
        raise TypeError

    @classmethod
    def register_object(cls, custom_tstate_object):
        if hasattr(custom_tstate_object, "time") and hasattr(
                custom_tstate_object, "psi"):
            if isinstance(custom_tstate_object.time, float) and isinstance(
                    custom_tstate_object.psi, np.ndarray):
                cls.register(type(custom_tstate_object))
                return custom_tstate_object
        raise TypeError

    @abstractmethod
    def propagate(self, timestep) -> None:
        pass

    @abstractmethod
    def set_t0(self, t0):
        pass


class UserTState(TimedState):
    @classmethod
    def fromPropagator(cls, time, psi,
                       propagator: Propagator,
                       label=None):
        obj = cls(time, psi, lambda _: None, label=label)
        obj._propagator = propagator
        return obj

    def __init__(self, time: float, psi: np.ndarray,
                 propagator_factory: _PropagatorFactory,
                 label=None):
        self.time = time
        self.psi = psi
        self.label = label
        self._propagator = propagator_factory(self.psi)
        Propagator.register_object(self._propagator)
        if not isinstance(self._propagator, Propagator):
            raise TypeError("Given propagator is not an"
                            " instance of the interface")

    def _setPsi(self, new_psi: np.ndarray):
        self.psi = new_psi
        self._propagator._psi = self.psi
        return

    def propagate(self, timestep) -> None:
        self._propagator._psi = self.psi
        self.psi = self._propagator(self.time, timestep)
        self.time += timestep
        return

    def set_t0(self, t0):
        self.time = t0
        self._propagator.set_t0(t0)
