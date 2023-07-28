"""In this module, the backend-dependent functions are implemented by the user.
These functions will be available for routines to be initialized with.
Cachable functions should be implemented in the 'functions_cached' module.
"""
import numpy as np
import h5py
from inspect import signature

from myquimb import quimb
from myquimb.quimb import qarray, quimbify, expectation
from myquimb.hdf5_io import save_dataset_with_attributes

from . import functions_cached as cached


def overwrite_psi(func):
    """Decorator that sets a function to manipulate the input state."""
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    wrapped.__signature__ = signature(func)
    setattr(wrapped, "overwrite_psi", True)
    return wrapped


def bipent_arr(psi: qarray, sys_params: dict, /) -> np.ndarray:
    L = sys_params["L"]
    return np.array([quimb.entropy_subsys(psi,
                                          dims=(2,)*L,
                                          sysa=range(i+1)) * np.log(2)
                     for i in range(L-1)])


def bipent_center(psi: qarray, sys_params: dict, /) -> float:
    L = sys_params["L"]
    return quimb.entropy_subsys(
        psi, dims=(2,)*L, sysa=range(L // 2)) * np.log(2)


def total_sz(psi: qarray, sys_params: dict, /, **ikron_kwargs) -> float:
    L = sys_params["L"]
    return expectation(psi, cached.total_sz_op(L, **ikron_kwargs))


def psi(psi: qarray, /) -> qarray:
    return psi


@overwrite_psi
def rotate_local_spin(psi: qarray, sys_params, /,
                      site_idx, phi, xyz, *, sparse=True, ikron_sparse=True,
                      ikron_stype='csr',
                      ikron_coo_build=True, **ikron_kwargs) -> qarray:
    """Rotates local spin by angle phi around axis xyz"""
    L = sys_params["L"]
    _site_idx = (L + site_idx) % L
    rotation_op = cached.rotation_op(L, phi, xyz, _site_idx, ikron_sparse,
                                     ikron_stype, ikron_coo_build,
                                     **ikron_kwargs)
    return quimbify(rotation_op @ psi)


def save_observable(psi: qarray, io_options: dict, sys_params: dict, /,
                    label: str, observable_function_name: str,
                    group_name: str, overwrite_data, *,
                    attrs_dict=None, **kwargs) -> None:
    """Saves observable as hdf5 dataset. "observable_function_name"
    is name of function that calculates the content of the dataset.
    """
    ofile: h5py.File = io_options["ofile"]
    data_fn = globals()[observable_function_name]
    data = data_fn(psi=psi, sys_params=sys_params)
    group = ofile.require_group(group_name)
    save_dataset_with_attributes(group, label, data,
                                 overwrite_data=overwrite_data,
                                 attrs_dict=attrs_dict, **kwargs)
    return


def save_psi(psi: qarray, io_options: dict, /, label: str,
             group_name: str, *, attrs_dict=None, **kwargs) -> None:
    """Saves psi as hdf5 dataset."""
    ofile: h5py.File = io_options["ofile"]
    overwrite_data = io_options["overwrite_data"]
    group = ofile.require_group(group_name)
    save_dataset_with_attributes(group, label, psi.A,
                                 overwrite_data=overwrite_data,
                                 attrs_dict=attrs_dict, **kwargs)
    return


def message(text: str):
    print(text)
    return
