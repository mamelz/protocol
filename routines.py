"""Module implementing routines: Callables to be invoked in the calculation."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import Protocol
    from .graph import GraphNodeBase
    from .interface import TimedState

from abc import ABC, abstractmethod
from typing import Callable

from .backend import RoutineFunction
from .types_ import FrozenDict


class RoutineABC(ABC):
    _ROUTINE_MANDATORY_KEYS: tuple[str]
    # optional options with default values
    _ROUTINE_OPTIONAL_KEYS: dict[str]

    @abstractmethod
    def __call__(self, tstate: TimedState):
        pass

    @abstractmethod
    def __init__(self, node: GraphNodeBase, protocol: Protocol):
        self._node = node
        self._protocol = protocol
        self.options = {}
        self.live_tracking = False
        for key in self._ROUTINE_MANDATORY_KEYS:
            try:
                option = self._node.options[key]
            except KeyError:
                option = self._protocol.getOptions(key)
            self.options[key] = option
        for key in self._ROUTINE_OPTIONAL_KEYS.keys():
            try:
                option = self._node.options[key]
            except KeyError:
                option = self._ROUTINE_OPTIONAL_KEYS[key]
            self.options[key] = option

    @property
    def name(self) -> str:
        return self.options["name"]

    @property
    @abstractmethod
    def store_token(self):
        pass

    def enableLiveTracking(self):
        self.live_tracking = True

    def disableLiveTracking(self):
        self.live_tracking = False


class RegularRoutine(RoutineABC):
    """Class for arbitrary, non-propagating manipulations on the state."""
    _ROUTINE_MANDATORY_KEYS = ("name", "io_options", "sys_params", "kwargs")
    _ROUTINE_OPTIONAL_KEYS = {"output": True, "store_token": None}

    def __init__(self, node: GraphNodeBase, protocol: Protocol):
        super().__init__(node, protocol)
        if "TYPE" not in node._options:
            self._TYPE = "IRREGULAR"
        else:
            self._TYPE = node._options["TYPE"]
        self._rfunction = RoutineFunction.fromFunctionName(self.name)
        self._rfunction_partial = self._make_rfunction_partial()

    @property
    def store_token(self):
        if self.options["store_token"] is not None:
            return self.options["store_token"]
        else:
            return self.options["name"]

    def _make_rfunction_partial(self) -> Callable:
        """Sets all parameters of the function except for 'psi'"""
        args = []
        for key in self._rfunction.positional_args.keys():
            if key == "psi":
                continue
            args += [FrozenDict(self.options[key])]
        args = tuple(args)

        # all other arguments are passed as kwargs
        kwargs: dict = FrozenDict(self.options["kwargs"])

        for key in kwargs.keys():
            if key in self._rfunction.mandatory_args.keys():
                continue
            if key in self._rfunction.optional_args.keys():
                continue
            raise ValueError(
                f"Unknown keyword argument '{key}' found in {self._node}")

        partial_sig = self._rfunction.signature

        if "psi" not in partial_sig.parameters:
            bound_arguments = partial_sig.bind(*args, **kwargs)
            bound_arguments.apply_defaults()

            def _wrapped_func(_):
                return self._rfunction(*bound_arguments.args,
                                       **bound_arguments.kwargs)
            return _wrapped_func

        else:
            partial_parameters = [partial_sig.parameters[param] for param
                                  in partial_sig.parameters if param != "psi"]
            partial_sig = partial_sig.replace(parameters=partial_parameters)
            bound_arguments = partial_sig.bind(*args, **kwargs)
            bound_arguments.apply_defaults()

            def _wrapped_func(psi):
                return self._rfunction(psi,
                                       *bound_arguments.args,
                                       **bound_arguments.kwargs)
            return _wrapped_func

    def __call__(self, tstate: TimedState):
        result = self._rfunction_partial(tstate.psi)
        if self._rfunction.overwrite_psi:
            tstate.psi = result
        if not self.options["output"]:
            return
        if result is not None:
            return (self.store_token, result)
        return


class PropagationRoutine(RoutineABC):
    """Class for time propagation steps of the state."""
    _ROUTINE_MANDATORY_KEYS = ("name", "step")
    _ROUTINE_OPTIONAL_KEYS = {}
    _TYPE = "PROPAGATE"

    def __init__(self, node: GraphNodeBase, protocol: Protocol):
        super().__init__(node, protocol)
        assert self.name == "PROPAGATE"
        self.timestep = self.options["step"]

    @property
    def store_token(self):
        return "PROPAGATE"

    def __call__(self, tstate: TimedState):
        tstate.propagate(self.timestep)
        return
