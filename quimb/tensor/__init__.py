"""Tensor and tensor network functionality."""

from .circuit import (
    Circuit,
    CircuitDense,
    CircuitMPS,
    CircuitPermMPS,
    Gate,
)
from .circuit_gen import (
    circ_ansatz_1D_brickwork,
    circ_ansatz_1D_rand,
    circ_ansatz_1D_zigzag,
    circ_qaoa,
)
from .contraction import (
    array_contract,
    contract_backend,
    contract_strategy,
    get_contract_backend,
    get_contract_strategy,
    get_symbol,
    get_tensor_linop_backend,
    inds_to_eq,
    set_contract_backend,
    set_contract_strategy,
    set_tensor_linop_backend,
    tensor_linop_backend,
)
from .geometry import (
    edges_1d_chain,
    edges_2d_hexagonal,
    edges_2d_kagome,
    edges_2d_square,
    edges_2d_triangular,
    edges_2d_triangular_rectangular,
    edges_3d_cubic,
    edges_3d_diamond,
    edges_3d_diamond_cubic,
    edges_3d_pyrochlore,
    edges_tree_rand,
)
from .interface import (
    jax_register_pytree,
    pack,
    unpack,
)
from .optimize import (
    TNOptimizer,
)
from .tensor_1d import (
    Dense1D,
    MatrixProductOperator,
    MatrixProductState,
    SuperOperator1D,
    TensorNetwork1D,
    TNLinearOperator1D,
    align_TN_1D,
    expec_TN_1D,
    gate_TN_1D,
    superop_TN_1D,
)
from .tensor_1d_compress import (
    enforce_1d_like,
    tensor_network_1d_compress,
)
from .tensor_1d_tebd import (
    NNI,
    TEBD,
    LocalHam1D,
)
from .tensor_2d import (
    PEPO,
    PEPS,
    TensorNetwork2D,
    gen_2d_bonds,
)
from .tensor_2d_tebd import (
    TEBD2D,
    FullUpdate,
    LocalHam2D,
    SimpleUpdate,
)
from .tensor_3d import (
    PEPS3D,
    TensorNetwork3D,
    gen_3d_bonds,
)
from .tensor_3d_tebd import (
    LocalHam3D,
)
from .tensor_arbgeom import (
    tensor_network_align,
    tensor_network_apply_op_op,
    tensor_network_apply_op_vec,
)
from .tensor_arbgeom_tebd import (
    LocalHamGen,
    SimpleUpdateGen,
    TEBDGen,
    edge_coloring,
)
from .tensor_builder import (
    MPS_COPY,
    HTN2D_classical_ising_partition_function,
    HTN3D_classical_ising_partition_function,
    HTN_classical_partition_function_from_edges,
    HTN_CP_from_sites_and_fill_fn,
    HTN_dual_from_edges_and_fill_fn,
    HTN_from_clauses,
    HTN_from_cnf,
    HTN_random_ksat,
    MPO_ham_heis,
    MPO_ham_ising,
    MPO_ham_mbl,
    MPO_ham_XY,
    MPO_identity,
    MPO_identity_like,
    MPO_product_operator,
    MPO_rand,
    MPO_rand_herm,
    MPO_zeros,
    MPO_zeros_like,
    MPS_computational_state,
    MPS_ghz_state,
    MPS_neel_state,
    MPS_product_state,
    MPS_rand_computational_state,
    MPS_rand_state,
    MPS_sampler,
    MPS_w_state,
    MPS_zero_state,
    NNI_ham_heis,
    NNI_ham_ising,
    NNI_ham_mbl,
    NNI_ham_XY,
    SpinHam,
    SpinHam1D,
    TN2D_classical_ising_partition_function,
    TN2D_corner_double_line,
    TN2D_embedded_classical_ising_partition_function,
    TN2D_empty,
    TN2D_from_fill_fn,
    TN2D_rand,
    TN2D_rand_hidden_loop,
    TN2D_rand_symmetric,
    TN2D_with_value,
    TN3D_classical_ising_partition_function,
    TN3D_corner_double_line,
    TN3D_empty,
    TN3D_from_fill_fn,
    TN3D_rand,
    TN3D_rand_hidden_loop,
    TN3D_with_value,
    TN_classical_partition_function_from_edges,
    TN_dimer_covering_from_edges,
    TN_from_edges_and_fill_fn,
    TN_from_edges_empty,
    TN_from_edges_rand,
    TN_from_edges_with_value,
    TN_from_sites_computational_state,
    TN_from_sites_product_state,
    TN_from_strings,
    TN_matching,
    TN_rand_from_edges,
    TN_rand_reg,
    TN_rand_tree,
    cnf_file_parse,
    convert_to_2d,
    convert_to_3d,
    ham_1d_heis,
    ham_1d_ising,
    ham_1d_mbl,
    ham_1d_XY,
    ham_2d_heis,
    ham_2d_ising,
    ham_2d_j1j2,
    ham_3d_heis,
    rand_phased,
    rand_tensor,
    random_ksat_instance,
)
from .tensor_core import (
    COPY_tensor,
    IsoTensor,
    PTensor,
    Tensor,
    TensorNetwork,
    bonds,
    bonds_size,
    connect,
    group_inds,
    new_bond,
    oset,
    rand_uuid,
    tensor_balance_bond,
    tensor_canonize_bond,
    tensor_compress_bond,
    tensor_contract,
    tensor_direct_product,
    tensor_fuse_squeeze,
    tensor_network_distance,
    tensor_network_fit_als,
    tensor_network_fit_autodiff,
    tensor_network_gate_inds,
    tensor_network_sum,
    tensor_split,
)
from .tensor_dmrg import (
    DMRG,
    DMRG1,
    DMRG2,
    DMRGX,
    MovingEnvironment,
)
from .tensor_mera import (
    MERA,
)

__all__ = (
    "align_TN_1D",
    "array_contract",
    "bonds_size",
    "bonds",
    "circ_ansatz_1D_brickwork",
    "circ_ansatz_1D_rand",
    "circ_ansatz_1D_zigzag",
    "circ_qaoa",
    "Circuit",
    "CircuitDense",
    "CircuitMPS",
    "CircuitPermMPS",
    "cnf_file_parse",
    "connect",
    "contract_backend",
    "contract_strategy",
    "convert_to_2d",
    "convert_to_3d",
    "COPY_tensor",
    "Dense1D",
    "DMRG",
    "DMRG1",
    "DMRG2",
    "DMRGX",
    "edge_coloring",
    "edges_1d_chain",
    "edges_2d_hexagonal",
    "edges_2d_kagome",
    "edges_2d_square",
    "edges_2d_triangular_rectangular",
    "edges_2d_triangular",
    "edges_3d_cubic",
    "edges_3d_diamond_cubic",
    "edges_3d_diamond",
    "edges_3d_pyrochlore",
    "edges_tree_rand",
    "enforce_1d_like",
    "expec_TN_1D",
    "FullUpdate",
    "gate_TN_1D",
    "Gate",
    "gen_2d_bonds",
    "gen_3d_bonds",
    "get_contract_backend",
    "get_contract_strategy",
    "get_symbol",
    "get_tensor_linop_backend",
    "group_inds",
    "ham_1d_heis",
    "ham_1d_ising",
    "ham_1d_mbl",
    "ham_1d_XY",
    "ham_2d_heis",
    "ham_2d_ising",
    "ham_2d_j1j2",
    "ham_3d_heis",
    "HTN_classical_partition_function_from_edges",
    "HTN_CP_from_sites_and_fill_fn",
    "HTN_dual_from_edges_and_fill_fn",
    "HTN_from_clauses",
    "HTN_from_cnf",
    "HTN_random_ksat",
    "HTN2D_classical_ising_partition_function",
    "HTN3D_classical_ising_partition_function",
    "inds_to_eq",
    "IsoTensor",
    "jax_register_pytree",
    "LocalHam1D",
    "LocalHam2D",
    "LocalHam3D",
    "LocalHamGen",
    "MatrixProductOperator",
    "MatrixProductState",
    "MERA",
    "MovingEnvironment",
    "MPO_ham_heis",
    "MPO_ham_ising",
    "MPO_ham_mbl",
    "MPO_ham_XY",
    "MPO_identity_like",
    "MPO_identity",
    "MPO_product_operator",
    "MPO_rand_herm",
    "MPO_rand",
    "MPO_zeros_like",
    "MPO_zeros",
    "MPS_computational_state",
    "MPS_COPY",
    "MPS_ghz_state",
    "MPS_neel_state",
    "MPS_product_state",
    "MPS_rand_computational_state",
    "MPS_rand_state",
    "MPS_sampler",
    "MPS_w_state",
    "MPS_zero_state",
    "new_bond",
    "NNI_ham_heis",
    "NNI_ham_ising",
    "NNI_ham_mbl",
    "NNI_ham_XY",
    "NNI",
    "oset",
    "pack",
    "PEPO",
    "PEPS",
    "PEPS3D",
    "PTensor",
    "rand_phased",
    "rand_tensor",
    "rand_uuid",
    "random_ksat_instance",
    "set_contract_backend",
    "set_contract_strategy",
    "set_tensor_linop_backend",
    "SimpleUpdate",
    "SimpleUpdateGen",
    "SpinHam",
    "SpinHam1D",
    "superop_TN_1D",
    "SuperOperator1D",
    "TEBD",
    "TEBD2D",
    "TEBDGen",
    "tensor_balance_bond",
    "tensor_canonize_bond",
    "tensor_compress_bond",
    "tensor_contract",
    "tensor_direct_product",
    "tensor_fuse_squeeze",
    "tensor_linop_backend",
    "tensor_network_1d_compress",
    "tensor_network_align",
    "tensor_network_apply_op_op",
    "tensor_network_apply_op_vec",
    "tensor_network_distance",
    "tensor_network_fit_als",
    "tensor_network_fit_autodiff",
    "tensor_network_gate_inds",
    "tensor_network_sum",
    "tensor_split",
    "Tensor",
    "TensorNetwork",
    "TensorNetwork1D",
    "TensorNetwork2D",
    "TensorNetwork3D",
    "TN_classical_partition_function_from_edges",
    "TN_dimer_covering_from_edges",
    "TN_from_edges_and_fill_fn",
    "TN_from_edges_empty",
    "TN_from_edges_rand",
    "TN_from_edges_with_value",
    "TN_from_sites_computational_state",
    "TN_from_sites_product_state",
    "TN_from_strings",
    "TN_matching",
    "TN_rand_from_edges",
    "TN_rand_reg",
    "TN_rand_tree",
    "TN2D_classical_ising_partition_function",
    "TN2D_corner_double_line",
    "TN2D_embedded_classical_ising_partition_function",
    "TN2D_empty",
    "TN2D_from_fill_fn",
    "TN2D_rand_hidden_loop",
    "TN2D_rand_symmetric",
    "TN2D_rand",
    "TN2D_with_value",
    "TN3D_classical_ising_partition_function",
    "TN3D_corner_double_line",
    "TN3D_empty",
    "TN3D_from_fill_fn",
    "TN3D_rand_hidden_loop",
    "TN3D_rand",
    "TN3D_with_value",
    "TNLinearOperator1D",
    "TNOptimizer",
    "unpack",
)
