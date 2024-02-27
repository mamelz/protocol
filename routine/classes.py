"""Module implementing routines: Callables to be invoked in the calculation."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inspect import _ParameterKind
    from typing import Callable
    from ..api import _System

import importlib.util
import os
from abc import ABC, abstractmethod
from inspect import signature, Parameter

from .errors import RoutineInitializationError
from ..settings import SETTINGS


_functions_path = os.path.abspath(SETTINGS.FUNCTIONS_PATH)
_functions_spec = importlib.util.spec_from_file_location(
   "functions", _functions_path)
_FUNCTIONS_MODULE = importlib.util.module_from_spec(_functions_spec)
_functions_spec.loader.exec_module(_FUNCTIONS_MODULE)


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
    def args(self):
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
    def positional_args(self) -> dict:
        return self._params_of_kind(Parameter.POSITIONAL_ONLY)

    @property
    def signature(self):
        return signature(self._function)


class Routine(ABC):
    """Callables representing routines to be executed in a schedule."""
    store: bool
    store_token: str
    tag: str
    type: str

    @abstractmethod
    def __init__(self, options: dict):
        if not options["type"] == self.type:
            raise ValueError(f"Wrong routine type: expected {self.type},"
                             f" got {options['type']}")

        self._options = options

    @abstractmethod
    def __call__(self, system: _System):
        pass

    @property
    def stage_idx(self):
        return self._stage_idx

    @stage_idx.setter
    def stage_idx(self, new):
        self._stage_idx = new

    def set_live_tracking(self, true_false):
        raise RuntimeError("Live tracking cannot be set for this"
                           " routine type.")


class RegularRoutine(Routine):
    type = "regular"

    def __init__(self, options, system: _System):
        super().__init__(options)
        try:
            self.tag = self._options["tag"]
        except KeyError:
            self.tag = "USER"

        self._live_tracking = self._options["live_tracking"]
        self._rfunction = RoutineFunction(self.name)
        self._make_rfunction_partial(system.sys_vars)
        self.store = self._options["store"]
        self._overwrite = self._rfunction.overwrite_psi

    def __call__(self, system):
        result = self._rfunction_partial(system.psi)
        if self._overwrite:
            system.psi = result

        return (self.store_token, result)

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

    def _make_rfunction_partial(self, system_pargs: dict) -> Callable:
        """Set all parameters of the function except for psi."""
        self._check_kwargs()
        rf_sig = self._rfunction.signature
        rf_params = rf_sig.parameters

        pos_args = [
            param for param in rf_params.values() if
            param.kind == param.POSITIONAL_ONLY
        ]
        args = [
            param for param in rf_params.values() if
            param.kind == param.VAR_POSITIONAL
        ]
        kwargs = [
            param for param in rf_params.values() if
            param.kind not in (param.VAR_POSITIONAL,
                               param.POSITIONAL_ONLY)
        ]

        pos_sig = rf_sig.replace(parameters=pos_args)
        non_pos_sig = rf_sig.replace(parameters=(*args, *kwargs))
        bound_params = non_pos_sig.bind(*self.passed_args,
                                        **self.passed_kwargs)

        bind_pargs = []
        pass_sys_pargs = []
        for param in pos_sig.parameters.values():
            if param.name != "psi":
                bind_pargs += [param]
                pass_sys_pargs += [system_pargs[param.name]]

        pos_sig = pos_sig.replace(parameters=bind_pargs)
        bound_pargs = pos_sig.bind(*pass_sys_pargs)

        # @functools.wraps(self._rfunction)
        def rfunction_partial(psi):
            return self._rfunction(psi, *bound_pargs.args,
                                   *bound_params.args,
                                   **bound_params.kwargs)

        self._rfunction_partial = rfunction_partial

    def set_live_tracking(self, true_false: bool):
        self._live_tracking = true_false


class EvolutionRegularRoutine(RegularRoutine):
    type = "evolution"


class MonitoringRoutine(RegularRoutine):
    type = "monitoring"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag = "MONITORING"


class PropagationRoutine(Routine):
    tag = "PROPAGATION"
    type = "propagation"
    live_tracking = False
    store = False
    store_token = "PROPAGATE"

    def __init__(self, options):
        super().__init__(options)
        self._step = self._options["step"]

    def __call__(self, system: _System):
        system.propagate(self._step)
        return

    @property
    def timestep(self):
        return self._step
