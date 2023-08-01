"""Module for user-implemented backend-dependent functions."""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from inspect import _ParameterKind

import importlib.util
from inspect import signature, Parameter
import os
import sys
from typing import Callable

from ..settings import SETTINGS

_functions_path = os.path.abspath(SETTINGS.FUNCTIONS_PATH)
_functions_spec = importlib.util.spec_from_file_location(
   "functions", _functions_path)
_functions_module = importlib.util.module_from_spec(_functions_spec)
sys.modules["functions"] = _functions_module
_functions_spec.loader.exec_module(_functions_module)


def FETCH(name: str):
    return getattr(_functions_module, name)


class RoutineFunction:
    """Thin class for functions with consistent signature"""
    @classmethod
    def fromFunctionName(cls, function_name):
        return cls(FETCH(function_name))

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
    def signature(self):
        return signature(self._function)

    @property
    def positional_args(self) -> dict:
        return self._params_of_kind(Parameter.POSITIONAL_ONLY)

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