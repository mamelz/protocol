"""Module implementing routines: Callables to be invoked in the calculation."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from inspect import _ParameterKind
    from typing import Callable
    from .schedule import System

import importlib.util
import functools
import os
from abc import ABC, abstractmethod
from inspect import signature, Parameter

from .settings import SETTINGS


_functions_path = os.path.abspath(SETTINGS.FUNCTIONS_PATH)
_functions_spec = importlib.util.spec_from_file_location(
   "functions", _functions_path)
_FUNCTIONS_MODULE = importlib.util.module_from_spec(_functions_spec)
# sys.modules["functions"] = _functions_module
_functions_spec.loader.exec_module(_FUNCTIONS_MODULE)


class RoutineInitializationError(Exception):
    message = "Error during initialization of routine."

    def __init__(self, message=None):
        if message is not None:
            self.message = message
        super().__init__()


class RoutineFunction:
    """Callable representing a function, the core of a routine."""
    _FUNCTIONS_MODULE = _FUNCTIONS_MODULE

    def __init__(self, routine_name):
        self._name = routine_name
        if self._name == "_return_state":
            self._function = lambda psi, /: psi
        else:
            self._function = getattr(self._FUNCTIONS_MODULE, routine_name)

        if hasattr(self._function, "overwrite_psi"):
            self.overwrite_psi = self._function.overwrite_psi
        else:
            self.overwrite_psi = False

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

    def _params_of_kind(self, kind: _ParameterKind) -> dict[str, Parameter]:
        return {key: param for key, param in
                self.signature.parameters.items() if param.kind
                == kind}

    @property
    def args(self) -> NotImplemented:
        """Return the *args of the function."""
        raise NotImplementedError

    @property
    def kwargs(self) -> dict:
        """Return all parameters that can be passed by dict unpacking"""
        return {
            **self._params_of_kind(Parameter.VAR_POSITIONAL),
            **self._params_of_kind(Parameter.POSITIONAL_OR_KEYWORD),
            **self._params_of_kind(Parameter.KEYWORD_ONLY),
            **self._params_of_kind(Parameter.VAR_KEYWORD)
        }

    @property
    def mandatory_args(self) -> dict:
        """Return all parameters that have no default values."""
        result = {}
        for key, param in self._params_of_kind(
                Parameter.POSITIONAL_OR_KEYWORD).items():
            if param.default == Parameter.empty:
                result[key] = param
        for key, param in self._params_of_kind(
                Parameter.KEYWORD_ONLY).items():
            if param.default == Parameter.empty:
                result[key] = param
        return result

    @property
    def optional_args(self) -> dict:
        """Return all parameters that have default values."""
        result = {}
        for key, param in self._params_of_kind(
                Parameter.POSITIONAL_OR_KEYWORD).items():
            if param.default != Parameter.empty:
                result[key] = param
        for key, param in self._params_of_kind(
                Parameter.KEYWORD_ONLY).items():
            if param.default != Parameter.empty:
                result[key] = param
        return result

    @property
    def positional_args(self) -> dict:
        return self._params_of_kind(Parameter.POSITIONAL_ONLY)

    @property
    def signature(self):
        return signature(self._function)


class Routine(ABC):
    """Callables representing routines to be executed in a schedule."""
    tag: str
    type: str

    @abstractmethod
    def __init__(self, options: dict):
        if not options["type"] == self.type:
            raise ValueError(f"Wrong routine type: expected {self.type},"
                             f" got {options['type']}")

        self._options = options

    @abstractmethod
    def __call__(self, system: System):
        pass

    @property
    def stage_idx(self):
        return self._stage_idx

    @stage_idx.setter
    def stage_idx(self, new):
        self._stage_idx = new


class RegularRoutine(Routine):
    tag = "USER"
    type = "regular"

    def __init__(self, options):
        super().__init__(options)
        self._live_tracking = self._options["live_tracking"]
        self._rfunction = RoutineFunction(self.name)
        self._make_rfunction_partial()
        self._output = self._options["output"]
        self._overwrite = self._rfunction.overwrite_psi

    def __call__(self, system: System) -> tuple[str, Any]:
        pos_args = (system.psi, *system.positional_args)
        result = self._rfunction_partial(*pos_args)
        if self._overwrite:
            system.psi = result
        if not self._output:
            return
        if result is not None:
            return (self.store_token, result)
        return

    @property
    def live_tracking(self):
        return self._live_tracking

    @property
    def name(self):
        return self._options["routine_name"]

    @property
    def passed_args(self) -> list | tuple:
        return self._options["args"]

    @property
    def passed_kwargs(self) -> dict:
        return self._options["kwargs"]

    @property
    def store_token(self):
        if self._options["store_token"] is not None:
            return self._options["store_token"]
        else:
            return self.name

    def _check_kwargs(self):
        """Check for unknown keyword arguments."""
        unknown = set()
        for key in self.passed_kwargs:
            if key not in self._rfunction.kwargs:
                unknown.add(key)
        if any(unknown):
            raise RoutineInitializationError(
                f"Unknown keyword arguments: {unknown}.")
        return

    def _make_rfunction_partial(self) -> Callable:
        """Set all parameters of the function except for positional-only."""
        self._check_kwargs()
        rf_sig = self._rfunction.signature
        rf_params = rf_sig.parameters

        pos_args = [
            param for param in rf_params.values() if
            param.kind == param.POSITIONAL_ONLY
        ]
        self._n_pos_args = len(pos_args)
        kw_params = [
            param for key, param in rf_params.items() if key not in
            self._rfunction.positional_args
            ]

        partial_sig = rf_sig.replace(parameters=kw_params)
        bound_arguments = partial_sig.bind_partial(**self.passed_kwargs)
        bound_arguments.apply_defaults()
        self._rfunction_partial = functools.partial(
            self._rfunction, *bound_arguments.args, **bound_arguments.kwargs)

    def disable_live_tracking(self):
        self._live_tracking = False

    def enable_live_tracking(self):
        self._live_tracking = True


class EvolutionRegularRoutine(RegularRoutine):
    tag = "USER"
    type = "evolution"


class MonitoringRoutine(RegularRoutine):
    tag = "MONITORING"
    type = "monitoring"


class PropagationRoutine(Routine):
    tag = "PROPAGATION"
    type = "propagation"
    live_tracking = False
    store_token = "PROPAGATE"

    def __init__(self, options):
        super().__init__(options)

    def __call__(self, system: System):
        system.propagate(self._options["step"])
        return

    @property
    def timestep(self):
        return self._options["step"]
