"""Cachable backend-dependent functions."""
from functools import lru_cache
import numpy as np
from myquimb import ikron, spin_operator, rotation


@lru_cache(maxsize=2)
def total_sz_op(L: int, ikron_sparse=True, **ikron_kwargs):
    def local_sz_gen():
        for site_idx in range(L):
            yield ikron(spin_operator("z"), (2,)*L, site_idx,
                        sparse=ikron_sparse,
                        **ikron_kwargs)

    return sum(local_sz_gen())


@lru_cache(maxsize=20)
def rotation_op(L: int, phi: float, xyz: str, site_idx: int,
                ikron_sparse: bool = True, ikron_stype: str = "csr",
                ikron_coo_build: bool = True, **ikron_kwargs):
    rotation_op = ikron(rotation(phi * np.pi, xyz=xyz, sparse=True),
                        (2,) * L,
                        [site_idx],
                        sparse=ikron_sparse,
                        stype=ikron_stype,
                        coo_build=ikron_coo_build,
                        **ikron_kwargs)
    return rotation_op
