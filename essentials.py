from abc import ABC, abstractmethod
from typing import Any
import sys


class Performable(ABC):
    """Interface representing an object that can be performed."""

    @abstractmethod
    def __init__(self):
        self._output_str_prefix = None

    @abstractmethod
    def perform(self):
        pass

    @abstractmethod
    def build(self):
        pass

    def _print_with_prefix(self, out_str):
        if self._output_str_prefix is not None:
            out = " | ".join([self._output_str_prefix, out_str])
        else:
            out = out_str

        print(out)
        sys.stdout.flush()


class Propagator(ABC):
    """Interface representing a propagator.

    A callable with the signature:

    [state (Any), time (float), timestep (float)] -> state (Any)

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


class System:
    """Class representing the time-dependent quantum system.

    Each schedule is associated with exactly one time-dependent system. The
    `System` object encapsulates all the information about the time evolution
    of the system, i.e. at any system time, the quantum state and the
    hamiltonian are known. It also provides the methods necessary to propagate
    the system in time.
    """

    def __init__(self, start_time: float,
                 initial_state,
                 sys_vars: dict = {},
                 propagator: Propagator = None):
        """Construct new physical system.

        The system is constructed from initial time, initial state and system
        parameters.
        Optionally, an instance of the `Propagator` interface can be passed.

        Args:
            start_time (float): The start time of the system.
            initial_state (Any): The initial state.
            sys_vars (dict): Dictionary containing system variables entering as
                positional arguments for routines.
            propagator (Propagator, optional): An instance of the Propagator
                interface. Defaults to None.

        Raises:
            TypeError: Raised, when the propagator does not implement the
                interface.
        """
        if propagator is not None:
            if not isinstance(propagator, Propagator):
                raise TypeError("Propagator does not implement interface.")
            self._propagator = propagator

        self._time = start_time
        self.psi = initial_state
        self.sys_vars = sys_vars

    @property
    def time(self):
        return self._time

    def propagate(self, timestep):
        """Propagate the system by timestep."""
        if not hasattr(self, "_propagator"):
            raise RuntimeError("No propagator was set.")
        self.psi = self._propagator(self.psi, self._time, timestep)
        self._time += timestep
        return
