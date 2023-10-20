import pytest

import quimb as qu
import quimb.tensor as qtn
from quimb.experimental.belief_propagation.l1bp import contract_l1bp
from quimb.experimental.belief_propagation.d2bp import contract_d2bp


@pytest.mark.parametrize("dtype", ["float32", "complex64"])
def test_contract_tree_exact(dtype):
    tn = qtn.TN_rand_tree(10, 3, seed=42, dtype=dtype)
    Z_ex = tn.contract()
    Z_bp = contract_l1bp(tn)
    assert Z_ex == pytest.approx(Z_bp, rel=5e-6)


@pytest.mark.parametrize("dtype", ["float32", "complex64"])
@pytest.mark.parametrize("damping", [0.0, 0.1])
def test_contract_loopy_approx(dtype, damping):
    tn = qtn.TN2D_rand(3, 4, 5, dtype=dtype, dist="uniform")
    Z_ex = tn.contract()
    Z_bp = contract_l1bp(tn, damping=damping)
    assert Z_ex == pytest.approx(Z_bp, rel=0.1)


@pytest.mark.parametrize("dtype", ["float32", "complex64"])
@pytest.mark.parametrize("damping", [0.0, 0.1])
def test_contract_double_loopy_approx(dtype, damping):
    peps = qtn.PEPS.rand(4, 3, 2, seed=42, dtype=dtype)
    tn = peps.H & peps
    Z_ex = tn.contract()
    Z_bp1 = contract_l1bp(tn, damping=damping)
    assert Z_bp1 == pytest.approx(Z_ex, rel=0.3)
    # compare with 2-norm BP on the peps directly
    Z_bp2 = contract_d2bp(peps)
    assert Z_bp1 == pytest.approx(Z_bp2, rel=5e-6)


@pytest.mark.parametrize("dtype", ["float32", "complex64"])
def test_contract_tree_triple_sandwich_exact(dtype):
    edges = qtn.edges_tree_rand(20, 3, seed=42)
    ket = qtn.TN_from_edges_rand(
        edges,
        3,
        phys_dim=2,
        seed=42,
        site_ind_id="k{}",
        dtype=dtype,
    )
    op = qtn.TN_from_edges_rand(
        edges,
        2,
        phys_dim=2,
        seed=42,
        site_ind_id=("k{}", "b{}"),
        dtype=dtype,
    )
    bra = qtn.TN_from_edges_rand(
        edges,
        3,
        phys_dim=2,
        seed=42,
        site_ind_id="b{}",
        dtype=dtype,
    )
    tn = bra.H | op | ket
    Z_ex = tn.contract()
    Z_bp = contract_l1bp(tn)
    assert Z_ex == pytest.approx(Z_bp, rel=5e-6)


@pytest.mark.parametrize("dtype", ["float32", "complex64"])
@pytest.mark.parametrize("damping", [0.0, 0.1])
def test_contract_tree_triple_sandwich_loopy_approx(dtype, damping):
    edges = qtn.edges_2d_hexagonal(2, 3)
    ket = qtn.TN_from_edges_rand(
        edges,
        3,
        phys_dim=2,
        seed=42,
        site_ind_id="k{}",
        dtype=dtype,
        # make the wavefunction postive to make easier
        dist="uniform",
    )
    ket /= (ket.H @ ket) ** 0.5

    G_ket = ket.gate(qu.pauli("Z"), [(1, 1, "A")], propagate_tags="sites")
    tn = ket.H | G_ket
    Z_ex = tn.contract()
    Z_bp = contract_l1bp(tn, damping=damping)
    assert Z_bp == pytest.approx(Z_ex, rel=0.5)


def test_contract_cluster_approx():
    tn = qtn.TN2D_classical_ising_partition_function(8, 8, 0.4, h=0.2)
    f_ex = qu.log(tn.contract())
    f_bp = qu.log(contract_l1bp(tn))
    assert f_bp == pytest.approx(f_ex, rel=0.3)
    cluster_tags = []
    for i in range(0, 8, 2):
        for j in range(0, 8, 2):
            cluster_tag = f"C{i},{j}"
            tn[i, j].add_tag(cluster_tag)
            tn[i, j + 1].add_tag(cluster_tag)
            tn[i + 1, j].add_tag(cluster_tag)
            tn[i + 1, j + 1].add_tag(cluster_tag)
            cluster_tags.append(cluster_tag)
    f_bp2 = qu.log(contract_l1bp(tn, site_tags=cluster_tags))
    assert f_bp == pytest.approx(f_ex, rel=0.1)
    assert abs(1 - f_ex / f_bp2) < abs(1 - f_ex / f_bp)