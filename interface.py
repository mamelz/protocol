"""Module containing interfaces for the time-resolved state and propagator"""
from __future__ import annotations

import inspect

from abc import ABC, abstractmethod
from typing import Mapping, Any


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


class System:
    """Class representing the time-dependent quantum system.

    Each schedule is associated with exactly one time-dependent system. The
    `System` object encapsulates all the information about the time evolution
    of the system, i.e. at any system time, the quantum state and the
    hamiltonian are known. It also provides the methods necessary to propagate
    the system in time.

    """

    @staticmethod
    def _validate_hamiltonian(hamiltonian):
        """Check hamiltonian for correct signature, if callable."""
        if not inspect.isfunction(hamiltonian):
            return

        sig = inspect.signature(hamiltonian)
        if len(sig.parameters.keys()) != 1:
            raise TypeError("Callable hamiltonians must take"
                            " exactly one argument.")
        return

    def __init__(self, initial_time: float, initial_state, hamiltonian,
                 propagator: Propagator, label: str = None):
        """Construct new physical system.

        The system is constructed from initial time, initial state, the
        hamiltonian and an object implementing the Propagator interface. A
        time-dependent hamiltonian must be passed to the constructor as a
        callable taking the time as only argument. Optionally, a label for
        the schedule can be set.
        """
        if not isinstance(propagator, Propagator) and hamiltonian is not None:
            TypeError("Propagator does not implement interface.")
        if hamiltonian is None and propagator is not None:
            raise ValueError("Propagator can only be passed with"
                             " hamiltonian.")

        self._initial_time = initial_time
        self.psi = initial_state
        self._validate_hamiltonian(hamiltonian)
        self._ham = hamiltonian
        self._propagator = propagator
        self.has_propagator = self._propagator is not None
        if self.has_propagator:
            self._propagator.initialize_time(initial_time, initial_state)
        self._sys_params: Mapping = None
        self.label = label

    @property
    def is_stationary(self):
        """True, if the hamiltonian is time-independent."""
        return inspect.isfunction(self._ham)

    @property
    def time(self):
        return self._propagator.time

    def propagate(self, timestep):
        """Propagate the system by timestep."""
        if not self.has_propagator:
            raise RuntimeError("No propagator was set for this system.")
        self.psi = self._propagator.propagate(self.psi, timestep)
        return

    def set_system_parameters(self, parameters: Mapping):
        self._sys_params = parameters
