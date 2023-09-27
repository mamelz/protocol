"""Module implementing routines: Callables to be invoked in the calculation."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from inspect import _ParameterKind
    from typing import Callable
    from .graph import GraphNodeBase
    from .schedule import Schedule, System

import importlib.util
import os
import sys

from inspect import signature, Parameter

from . import keywords
from .settings import SETTINGS
from .utils import FrozenDict


_functions_path = os.path.abspath(SETTINGS.FUNCTIONS_PATH)
_functions_spec = importlib.util.spec_from_file_location(
   "functions", _functions_path)
_functions_module = importlib.util.module_from_spec(_functions_spec)
sys.modules["functions"] = _functions_module
_functions_spec.loader.exec_module(_functions_module)


def _return_state(psi, /):
    return psi


def _fetch(name: str):
    if name == "_return_state":
        return _return_state
    return getattr(_functions_module, name)


class RoutineFunction:
    """
    Class for functions with consistent signature to be used as callables
    in routines.
    """
    @classmethod
    def fromFunctionName(cls, function_name):
        return cls(_fetch(function_name))

    def __init__(self, function: Callable):
        self.name = function.__name__
        self._function = function
        if hasattr(self._function, "overwrite_psi"):
            self.overwrite_psi = self._function.overwrite_psi
        else:
            self.overwrite_psi = False

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

    def _params_of_kind(self, kind: _ParameterKind) -> dict[str, Parameter]:
        return {key: param for key, param in
                signature(self._function).parameters.items() if param.kind
                == kind}

    @property
    def mandatory_args(self) -> dict:
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


class RegularRoutine:
    _MANDATORY_KWORDS = keywords._ROUTINE_KEYWORDS_MANDATORY
    _OPTIONAL_KWORDS = keywords._ROUTINE_KEYWORDS_OPTIONAL

    def __init__(self, node: GraphNodeBase, schedule: Schedule):
        self._node = node
        self._schedule = schedule
        self._set_mandatory_options()
        self._set_optional_options()
        self.options = dict(self._mandatory_options, **self._optional_options)
        self.options["sys_params"] = self._schedule.get_system_parameters()
        self._get_external_kwargs()
        self._rfunction = RoutineFunction.fromFunctionName(self.name)
        self._rfunction_partial = self._make_rfunction_partial()
        self.live_tracking = self._optional_options["live_tracking"]
        if "TYPE" not in self._node._options:
            self._TYPE = "IRREGULAR"
        else:
            self._TYPE = node._options["TYPE"]

    def __call__(self, system: System) -> tuple[str, Any]:
        result = self._rfunction_partial(system.psi)
        if self._rfunction.overwrite_psi:
            system.psi = result
        if not self.options["output"]:
            return
        if result is not None:
            return (self.store_token, result)
        return

    def _get_external_kwargs(self):
        for key, kwarg in self.kwargs.items():
            if kwarg == "EXTERNAL":
                self.kwargs[key] = self._node.external_options[self.name][key]
        return

    def _get_mandatory_key(self, key):
        try:
            option = self._node.options[key]
        except KeyError:
            option = self._schedule.get_global_option(key)
        return option

    def _get_optional_key(self, key):
        try:
            return self._node.options[key]
        except KeyError:
            return

    def _set_mandatory_options(self):
        self._mandatory_options = {}
        for key, dtype in self._MANDATORY_KWORDS.items():
            try:
                option = self._get_mandatory_key(key)
            except KeyError:
                raise KeyError(f"Missing mandatory routine option {key}")

            if not isinstance(option, dtype):
                raise TypeError(f"Routine option {key} has wrong type.")
            self._mandatory_options[key] = option

    def _set_optional_options(self):
        self._optional_options = self._OPTIONAL_KWORDS
        for key in self._OPTIONAL_KWORDS:
            option = self._get_optional_key(key)
            if option is not None:
                self._optional_options[key] = option

    def _make_rfunction_partial(self) -> Callable:
        """Sets all parameters of the function except for 'psi'"""
        args = ()
        for key in self._rfunction.positional_args.keys():
            if key == "psi":
                continue
            args += (FrozenDict(self.options[key]),)

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

            return lambda _: self._rfunction(*bound_arguments.args,
                                             **bound_arguments.kwargs)

        else:
            partial_parameters = [partial_sig.parameters[param] for param
                                  in partial_sig.parameters if param != "psi"]
            partial_sig = partial_sig.replace(parameters=partial_parameters)
            bound_arguments = partial_sig.bind(*args, **kwargs)
            bound_arguments.apply_defaults()

            return lambda psi: self._rfunction(psi, *bound_arguments.args,
                                               **bound_arguments.kwargs)

    @property
    def _raw_store_token(self):
        return self._optional_options["store_token"]

    @property
    def kwargs(self) -> dict:
        try:
            return self._mandatory_options["kwargs"]
        except KeyError:
            return

    @property
    def name(self):
        return self._mandatory_options["routine_name"]

    @property
    def stage_idx(self):
        return self._node.parent_of_rank(1).ID.local + 1

    @property
    def store_token(self):
        if self._raw_store_token != "":
            return self._raw_store_token
        else:
            return self.name

    def disable_live_tracking(self):
        self.live_tracking = False

    def enable_live_tracking(self):
        self.live_tracking = True


class EvolutionRegularRoutine(RegularRoutine):
    _MANDATORY_KWORDS = keywords._EVO_ROUTINE_KEYWORDS_MANDATORY


class PropagationRoutine:
    """Class for time propagation steps of the state."""
    _ROUTINE_MANDATORY_KEYS = ("name", "step")
    _TYPE = "PROPAGATE"
    live_tracking = False
    store_token = "PROPAGATE"

    def __init__(self, timestep, stage_idx):
        self.timestep = timestep
        self.stage_idx = stage_idx

    def __call__(self, system: System):
        system.propagate(self.timestep)
        return
