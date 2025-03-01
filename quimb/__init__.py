"""
Quantum Information for Many-Body calculations.
"""
try:
    # -- Distribution mode --
    # import from _version.py generated by setuptools_scm during release
    from ._version import version as __version__
except ImportError:
    # -- Source mode --
    try:
        # use setuptools_scm to get the current version from src using git
        from setuptools_scm import get_version as _gv
        from pathlib import Path as _Path

        __version__ = _gv(_Path(__file__).parent.parent)
    except ImportError:
        # setuptools_scm is not available, use a default version
        __version__ = "0.0.0+unknown"

import warnings

# some useful math
from math import cos, exp, log, log2, log10, pi, sin, sqrt, tan

# Functions for calculating properties
from .calc import (
    bell_decomp,
    concurrence,
    correlation,
    cprint,
    decomp,
    dephase,
    ent_cross_matrix,
    entropy,
    entropy_subsys,
    fidelity,
    heisenberg_energy,
    is_degenerate,
    is_eigenvector,
    kraus_op,
    logarithmic_negativity,
    logneg,
    logneg_subsys,
    measure,
    mutinf,
    mutinf_subsys,
    mutual_information,
    negativity,
    one_way_classical_information,
    page_entropy,
    partial_transpose,
    pauli_correlations,
    pauli_decomp,
    projector,
    purify,
    qid,
    quantum_discord,
    schmidt_gap,
    simulate_counts,
    tr_sqrt,
    tr_sqrt_subsys,
    trace_distance,
)

# Core functions
from .core import (
    bra,
    chop,
    dag,
    dim_compress,
    dim_map,
    dop,
    dot,
    expec,
    expectation,
    explt,
    eye,
    get_thread_pool,
    identity,
    ikron,
    infer_size,
    isbra,
    isdense,
    isherm,
    isket,
    isop,
    ispos,
    isreal,
    issparse,
    isvec,
    itrace,
    ket,
    kron,
    kronpow,
    ldmul,
    mul,
    nmlz,
    normalize,
    outer,
    partial_trace,
    permute,
    pkron,
    prod,
    ptr,
    qarray,
    qu,
    quimbify,
    rdmul,
    rdot,
    sparse,
    speye,
    tr,
    trace,
    vdot,
)

# Evolution class and methods
from .evo import Evolution

# Generating objects
from .gen.operators import (
    CNOT,
    Rx,
    Ry,
    Rz,
    S_gate,
    T_gate,
    U_gate,
    Wsqrt,
    Xsqrt,
    Ysqrt,
    Zsqrt,
    ccX,
    ccY,
    ccZ,
    controlled,
    controlled_swap,
    create,
    cswap,
    cX,
    cY,
    cZ,
    destroy,
    fredkin,
    fsim,
    fsimg,
    hadamard,
    ham_heis,
    ham_heis_2D,
    ham_hubbard_hardcore,
    ham_ising,
    ham_j1j2,
    ham_mbl,
    ham_XXZ,
    ham_XY,
    iswap,
    ncontrolled_gate,
    num,
    pauli,
    phase_gate,
    rotation,
    spin_operator,
    swap,
    toffoli,
    zspin_projector,
)
from .gen.rand import (
    gen_rand_haar_states,
    rand,
    rand_haar_state,
    rand_herm,
    rand_iso,
    rand_ket,
    rand_matrix,
    rand_matrix_product_state,
    rand_mera,
    rand_mix,
    rand_mps,
    rand_pos,
    rand_product_state,
    rand_rho,
    rand_seperable,
    rand_uni,
    randn,
    seed_rand,
    set_rand_bitgen,
)
from .gen.states import (
    basis_vec,
    bell_state,
    bloch_state,
    computational_state,
    down,
    ghz_state,
    graph_state_1d,
    levi_civita,
    minus,
    neel_state,
    perm_state,
    plus,
    singlet,
    singlet_pairs,
    thermal_state,
    up,
    w_state,
    werner_state,
    xminus,
    xplus,
    yminus,
    yplus,
    zminus,
    zplus,
)
from .linalg.approx_spectral import (
    approx_spectral_function,
    entropy_subsys_approx,
    logneg_subsys_approx,
    negativity_subsys_approx,
    tr_abs_approx,
    tr_exp_approx,
    tr_sqrt_approx,
    tr_xlogx_approx,
    xlogx,
)

# Linear algebra functions
from .linalg.base_linalg import (
    Lazy,
    bound_spectrum,
    eig,
    eigensystem,
    eigensystem_partial,
    eigh,
    eigh_window,
    eigvals,
    eigvalsh,
    eigvalsh_window,
    eigvecs,
    eigvecsh,
    eigvecsh_window,
    expm,
    expm_multiply,
    groundenergy,
    groundstate,
    norm,
    sqrtm,
    svd,
    svds,
)
from .linalg.mpi_launcher import can_use_mpi_pool, get_mpi_pool
from .linalg.rand_linalg import estimate_rank, rsvd
from .utils import (
    LRU,
    format_number_with_error,
    load_from_disk,
    oset,
    save_to_disk,
    tree_apply,
    tree_flatten,
    tree_map,
    tree_unflatten,
)
from .utils_plot import (
    NEUTRAL_STYLE,
    default_to_neutral_style,
    plot_multi_series_zoom,
)

warnings.filterwarnings("ignore", message="Caching is not available when ")


__all__ = [
    "approx_spectral_function",
    "basis_vec",
    "bell_decomp",
    "bell_state",
    "bloch_state",
    "bound_spectrum",
    "bra",
    "can_use_mpi_pool",
    "ccX",
    "ccY",
    "ccZ",
    "chop",
    "CNOT",
    "computational_state",
    "concurrence",
    "controlled_swap",
    "controlled",
    "correlation",
    "cos",
    "cprint",
    "create",
    "cswap",
    "cX",
    "cY",
    "cZ",
    "dag",
    "decomp",
    "default_to_neutral_style",
    "dephase",
    "destroy",
    "dim_compress",
    "dim_map",
    "dop",
    "dot",
    "down",
    "eig",
    "eigensystem_partial",
    "eigensystem",
    "eigh_window",
    "eigh",
    "eigvals",
    "eigvalsh_window",
    "eigvalsh",
    "eigvecs",
    "eigvecsh_window",
    "eigvecsh",
    "ent_cross_matrix",
    "entropy_subsys_approx",
    "entropy_subsys",
    "entropy",
    "estimate_rank",
    "Evolution",
    "exp",
    "expec",
    "expectation",
    "explt",
    "expm_multiply",
    "expm",
    "eye",
    "fidelity",
    "format_number_with_error",
    "fredkin",
    "fsim",
    "fsimg",
    "gen_rand_haar_states",
    "get_mpi_pool",
    "get_thread_pool",
    "ghz_state",
    "graph_state_1d",
    "groundenergy",
    "groundstate",
    "hadamard",
    "ham_heis_2D",
    "ham_heis",
    "ham_hubbard_hardcore",
    "ham_ising",
    "ham_j1j2",
    "ham_mbl",
    "ham_XXZ",
    "ham_XY",
    "heisenberg_energy",
    "identity",
    "ikron",
    "infer_size",
    "is_degenerate",
    "is_eigenvector",
    "isbra",
    "isdense",
    "isherm",
    "isket",
    "isop",
    "ispos",
    "isreal",
    "issparse",
    "isvec",
    "iswap",
    "itrace",
    "ket",
    "kraus_op",
    "kron",
    "kronpow",
    "Lazy",
    "ldmul",
    "levi_civita",
    "load_from_disk",
    "log",
    "log10",
    "log2",
    "logarithmic_negativity",
    "logneg_subsys_approx",
    "logneg_subsys",
    "logneg",
    "LRU",
    "measure",
    "minus",
    "mul",
    "mutinf_subsys",
    "mutinf",
    "mutual_information",
    "ncontrolled_gate",
    "neel_state",
    "negativity_subsys_approx",
    "negativity",
    "NEUTRAL_STYLE",
    "nmlz",
    "norm",
    "normalize",
    "num",
    "one_way_classical_information",
    "oset",
    "outer",
    "page_entropy",
    "partial_trace",
    "partial_transpose",
    "pauli_correlations",
    "pauli_decomp",
    "pauli",
    "perm_state",
    "permute",
    "phase_gate",
    "pi",
    "pkron",
    "plot_multi_series_zoom",
    "plus",
    "prod",
    "projector",
    "ptr",
    "purify",
    "qarray",
    "qid",
    "qu",
    "quantum_discord",
    "quimbify",
    "rand_haar_state",
    "rand_herm",
    "rand_iso",
    "rand_ket",
    "rand_matrix_product_state",
    "rand_matrix",
    "rand_mera",
    "rand_mix",
    "rand_mps",
    "rand_pos",
    "rand_product_state",
    "rand_rho",
    "rand_seperable",
    "rand_uni",
    "rand",
    "randn",
    "rdmul",
    "rdot",
    "rotation",
    "rsvd",
    "Rx",
    "Ry",
    "Rz",
    "S_gate",
    "save_to_disk",
    "schmidt_gap",
    "seed_rand",
    "set_rand_bitgen",
    "simulate_counts",
    "sin",
    "singlet_pairs",
    "singlet",
    "sparse",
    "speye",
    "spin_operator",
    "sqrt",
    "sqrtm",
    "svd",
    "svds",
    "swap",
    "T_gate",
    "tan",
    "thermal_state",
    "toffoli",
    "tr_abs_approx",
    "tr_exp_approx",
    "tr_sqrt_approx",
    "tr_sqrt_subsys",
    "tr_sqrt",
    "tr_xlogx_approx",
    "tr",
    "trace_distance",
    "trace",
    "tree_apply",
    "tree_flatten",
    "tree_map",
    "tree_unflatten",
    "U_gate",
    "up",
    "vdot",
    "w_state",
    "werner_state",
    "Wsqrt",
    "xlogx",
    "xminus",
    "xplus",
    "Xsqrt",
    "yminus",
    "yplus",
    "Ysqrt",
    "zminus",
    "zplus",
    "zspin_projector",
    "Zsqrt",
]
