"""Core functions for manipulating quantum objects.
"""
# TODO: move identity, trace to accel
# TODO: refactor eyepad -> itensor

import math
import itertools
import functools

import numpy as np
from numba import jit
from numpy.matlib import zeros
import scipy.sparse as sp

from .accel import (
    accel,
    matrixify,
    realify,
    issparse,
    isop,
    vdot,
    dot,
    prod,
    dot_dense,
    kron,
    kronpow,
    isvec
)


_SPARSE_CONSTRUCTORS = {"csr": sp.csr_matrix,
                        "bsr": sp.bsr_matrix,
                        "csc": sp.csc_matrix,
                        "coo": sp.coo_matrix}


def _sparse_matrix(data, stype="csr"):
    """Construct a sparse matrix of a particular format.

    Parameters
    ----------
        data: fed to scipy.sparse constructor
        stype: sparse type {'csr', 'csc', 'coo', 'bsr', ...}
    """
    return _SPARSE_CONSTRUCTORS[stype](data, dtype=complex)


def normalize(qob, inplace=True):
    """Normalize a quantum object

    Parameters
    ----------
        qob: dense or sparse, operator or vector
            Quantum object to normalize.
        inplace: bool
            Whether to act inplace on the given operator.
    """
    n_factor = qob.tr() if isop(qob) else overlap(qob, qob)**0.25
    if inplace:
        qob /= n_factor
        return qob
    return qob / n_factor


def chop(qob, tol=1.0e-15, inplace=True):
    """Set small values of an array to zero.

    Parameters
    ----------
        qob: dense or sparse, operator or vector
            Quantum object to chop
        tol: float
            Fraction of max(abs(qob)) to chop below.
        inplace: bool
            Whether to act on input array or return copy.
    """
    minm = np.abs(qob).max() * tol  # minimum value tolerated
    if not inplace:
        qob = qob.copy()
    if issparse(qob):
        qob.data.real[np.abs(qob.data.real) < minm] = 0.0
        qob.data.imag[np.abs(qob.data.imag) < minm] = 0.0
        qob.eliminate_zeros()
    else:
        qob.real[np.abs(qob.real) < minm] = 0.0
        qob.imag[np.abs(qob.imag) < minm] = 0.0
    return qob


def quimbify(data, qtype=None, normalized=False, chopped=False,
             sparse=None, stype=None):
    """Converts data to 'quantum' i.e. complex matrices, kets being columns.

    Parameters
    ----------
        data: array_like
            Matrix data
        qtype: {'ket', 'bra' or 'dop'}, optional
            Quantum object type output type.
        sparse: bool
            Whether to convert output to sparse a format.
        normalized: bool
            Whether to normalise the output.
        chopped: bool
            Whether to trim almost zero entries of the output.
        stype: {'csr', 'csc', 'bsr', 'coo'}
            Format of matrix if sparse, defaults to 'csr'.

    Returns
    -------
        x: numpy or scipy.sparse matrix.

    Notes
    -----
        1. Will unravel an array if 'ket' or 'bra' given.
        2. Will conjugate if 'bra' given.
        3. Will leave operators as is if 'dop' given, but construct one
            if vector given with the assumption that it was a ket.
    """

    sparse_input = issparse(data)
    sparse_output = ((sparse) or
                     (sparse_input and sparse is None) or
                     (sparse is None and stype))
    # Infer output sparse format from input if necessary
    if sparse_input and sparse_output and stype is None:
        stype = data.format

    if qtype is not None:
        # Must be dense to reshape
        data = np.asmatrix(data.A if sparse_input else data, dtype=complex)
        if qtype in {"k", "ket"}:
            data = data.reshape((prod(data.shape), 1))
        elif qtype in {"b", "bra"}:
            data = data.reshape((1, prod(data.shape))).conj()
        elif qtype in {"d", "r", "rho", "op", "dop"} and isvec(data):
            data = dot(quimbify(data, "k"), quimbify(data, "k").H)
    # Just cast as numpy matrix
    elif not sparse_output:
        data = np.asmatrix(data.A if sparse_input else data, dtype=complex)

    # Check if already sparse matrix, or wanted to be one
    if sparse_output:
        data = _sparse_matrix(data, (stype if stype is not None else "csr"))

    # Optionally normalize and chop small components
    if normalized:
        normalize(data, inplace=True)
    if chopped:
        chop(data, inplace=True)

    return data


qu = quimbify
ket = functools.partial(quimbify, qtype='ket')
bra = functools.partial(quimbify, qtype='bra')
dop = functools.partial(quimbify, qtype='dop')
sparse = functools.partial(quimbify, sparse=True)


def infer_size(p, base=2):
    """Infers the size of a state assumed to be made of qubits.
    """
    return int(math.log(max(p.shape), base))


@realify
@accel
def _trace_dense(op):  # pragma: no cover
    """Trace of matrix.
    """
    x = 0.0j
    for i in range(op.shape[0]):
        x += op[i, i]
    return x


@realify
def _trace_sparse(op):
    """Trace of sparse matrix.
    """
    return np.sum(op.diagonal())


def trace(op):
    """Trace of dense or sparse matrix.
    """
    return _trace_sparse(op) if issparse(op) else _trace_dense(op)


@matrixify
@accel
def _identity_dense(d):  # pragma: no cover
    """Returns a dense, complex identity of order d.
    """
    x = np.zeros((d, d), dtype=np.complex128)
    for i in range(d):
        x[i, i] = 1
    return x


def _identity_sparse(d, stype="csr"):
    """Returns a sparse, complex identity of order d.
    """
    return sp.eye(d, dtype=complex, format=stype)


def identity(d, sparse=False, stype="csr"):
    """Return identity of size d in complex format, optionally sparse.
    """
    return _identity_sparse(d, stype=stype) if sparse else _identity_dense(d)


eye = identity
speye = functools.partial(identity, sparse=True)


def _find_shape_of_nested_int_array(x):
    """Take a n-nested list/tuple of integers and find its array shape.
    """
    shape = [len(x)]
    sub_x = x[0]
    while not isinstance(sub_x, int):
        shape.append(len(sub_x))
        sub_x = sub_x[0]
    return tuple(shape)


def _dim_map_1d(sza, coos):
    for coo in coos:
        if 0 <= coo < sza:
            yield coo
        else:
            raise ValueError("One or more coordinates out of range.")


def _dim_map_1dtrim(sza, coos):
    return (coo for coo in coos if (0 <= coo < sza))


def _dim_map_1dcyclic(sza, coos):
    return (coo % sza for coo in coos)


def _dim_map_2dcyclic(sza, szb, coos):
    return (szb * (coo[0] % sza) + coo[1] % szb for coo in coos)


def _dim_map_2dtrim(sza, szb, coos):
    for coo in coos:
        x, y = coo
        if 0 <= x < sza and 0 <= y < szb:
            yield szb * x + y


def _dim_map_2d(sza, szb, coos):
    for coo in coos:
        x, y = coo
        if 0 <= x < sza and 0 <= y < szb:
            yield szb * x + y
        else:
            raise ValueError("One or more coordinates out of range.")


def _dim_map_nd(szs, coos, cyclic=False, trim=False):
    strides = [1]
    for sz in szs[-1:0:-1]:
        strides.insert(0, sz * strides[0])
    if cyclic:
        coos = ((c % sz for c, sz in zip(coo, szs)) for coo in coos)
    elif trim:
        coos = (c for c in coos if all(x == x % sz for x, sz in zip(c, szs)))
    elif not all(all(c == c % sz for c, sz in zip(coo, szs)) for coo in coos):
        raise ValueError("One or more coordinates out of range.")
    return (sum(c * m for c, m in zip(coo, strides)) for coo in coos)


_dim_mapper_methods = {(1, False, False): _dim_map_1d,
                       (1, False, True): _dim_map_1dtrim,
                       (1, True, False): _dim_map_1dcyclic,
                       (2, False, False): _dim_map_2d,
                       (2, False, True): _dim_map_2dtrim,
                       (2, True, False): _dim_map_2dcyclic}


def dim_map(dims, coos, cyclic=False, trim=False):
    """Maps multi-dimensional coordinates and indices to flat arrays in a
    regular way. Wraps or deletes coordinates beyond the system size
    depending on parameters `cyclic` and `trim`.

    Parameters
    ----------
        dims: multi-dim array of systems' internal dimensions
        coos: array of coordinate tuples to convert
        cyclic: whether to automatically wrap coordinates beyond system size or
            delete them.
        trim: if True, any coordinates beyond dimensions will be deleted,
            overidden by cyclic.

    Returns
    -------
        dims: flattened version of dims
        coos: indices mapped to flattened dims
    """
    # Figure out shape of dimensions given
    if isinstance(dims, np.ndarray):
        szs = dims.shape
        ndim = dims.ndim
    else:
        szs = _find_shape_of_nested_int_array(dims)
        ndim = len(szs)

    # Ensure `coos` in right format for 1d (i.e. not single tuples)
    if ndim == 1:
        if isinstance(coos, np.ndarray):
            coos = coos.ravel()
        elif not isinstance(coos[0], int):
            coos = (c[0] for c in coos)

    # Map coordinates to indices
    try:
        inds = _dim_mapper_methods[(ndim, cyclic, trim)](*szs, coos)
    except KeyError:
        inds = _dim_map_nd(szs, coos, cyclic, trim)

    # Ravel dims
    while ndim > 1:
        dims = itertools.chain.from_iterable(dims)
        ndim -= 1

    return tuple(dims), tuple(inds)


@jit(nopython=True)
def _dim_compressor(dims, inds):  # pragma: no cover
    """Helper function for `dim_compress` that does the heavy lifting.
    """
    blocksize_id = blocksize_op = 1
    autoplace_count = 0
    for i, dim in enumerate(dims):
        if dim < 0:
            if blocksize_op > 1:
                yield (blocksize_op, 1)
                blocksize_op = 1
            elif blocksize_id > 1:
                yield (blocksize_id, 0)
                blocksize_id = 1
            autoplace_count += dim
        elif i in inds:
            if blocksize_id > 1:
                yield (blocksize_id, 0)
                blocksize_id = 1
            elif autoplace_count < 0:
                yield (autoplace_count, 1)
                autoplace_count = 0
            blocksize_op *= dim
        else:
            if blocksize_op > 1:
                yield (blocksize_op, 1)
                blocksize_op = 1
            elif autoplace_count < 0:
                yield (autoplace_count, 1)
                autoplace_count = 0
            blocksize_id *= dim
    yield ((blocksize_op, 1) if blocksize_op > 1 else
           (blocksize_id, 0) if blocksize_id > 1 else
           (autoplace_count, 1))


def dim_compress(dims, inds):
    """Take some dimensions and target indices and compress both such, i.e.
    merge adjacent identity spaces.

    Parameters
    ----------
        dims: list of systems dimensions
        inds: list of target indices

    Returns
    -------
        dims, inds: new equivalent dimensions and matching indices
    """
    # TODO: turn off ind compress
    # TODO: put yield (autoplace_count, False) --- no need?
    # TODO: handle empty inds = () / [] etc.
    # TODO: don't compress auto (-ve.) so as to allow multiple operators
    if isinstance(inds, int):
        inds = (inds,)
    dims, inds = zip(*_dim_compressor(dims, inds))
    inds = tuple(i for i, b in enumerate(inds) if b)
    return dims, inds


def eyepad(ops, dims, inds, sparse=None, stype=None, coo_build=False):
    # TODO: rename? itensor, tensor
    # TODO: test 2d+ dims and coos
    # TODO: simplify  with compress coords?
    # TODO: allow -1 in dims to auto place *without* ind?
    """Tensor product, but padded with identites. Automatically
    placing a large operator over several dimensions is allowed and a list
    of operators can be given which are then applied cyclically.

    Parameters
    ----------
        ops: operator or list of operators to put into the tensor space.
        dims: dimensions of tensor space, use -1 to ignore dimension matching.
        inds: indices of the dimenions to place operators on.
        sparse: whether to construct the new operator in sparse form.

    Returns
    -------
        Operator such that ops act on dims[inds].

    *Notes:*
        1. if len(inds) > len(ops), then ops will be cycled over.
    """

    # Make sure `ops` islist
    if isinstance(ops, (np.ndarray, sp.spmatrix)):
        ops = (ops,)

    # Make sure dimensions and coordinates have been flattenened.
    if np.ndim(dims) > 1:
        dims, inds = dim_map(dims, inds)
    # Make sure `inds` is list
    elif np.ndim(inds) == 0:
        inds = (inds,)

    # Infer sparsity from list of ops
    if sparse is None:
        sparse = any(issparse(op) for op in ops)

    # Create a sorted list of operators with their matching index
    inds, ops = zip(*sorted(zip(inds, itertools.cycle(ops))))
    inds, ops = set(inds), iter(ops)

    # TODO: refactor this / just use dim_compress
    def gen_ops():
        cff_id = 1  # keeps track of compressing adjacent identities
        cff_ov = 1  # keeps track of overlaying op on multiple dimensions
        for ind, dim in enumerate(dims):
            if ind in inds:  # op should be placed here
                if cff_id > 1:  # need preceding identities
                    yield eye(cff_id, sparse=sparse, stype="coo")
                    cff_id = 1  # reset cumulative identity size
                if cff_ov == 1:  # first dim in placement block
                    op = next(ops)
                    sz_op = op.shape[0]
                if cff_ov * dim == sz_op or dim == -1:  # final dim-> place op
                    yield op
                    cff_ov = 1
                else:  # accumulate sub-dims
                    cff_ov *= dim
            elif cff_ov > 1:  # mid placing large operator
                cff_ov *= dim
            else:  # accumulate adjacent identites
                cff_id *= dim
        if cff_id > 1:  # trailing identities
            yield eye(cff_id, sparse=sparse, stype="coo")

    return kron(*gen_ops(), stype=stype, coo_build=coo_build)


@matrixify
def perm_pad(op, dims, inds):
    # TODO: multiple ops
    # TODO: coo map, coo compress
    # TODO: sparse??
    # TODO: use permute
    """Advanced tensor placement of operators that allows arbitrary ordering
    such as reversal and interleaving of identities.
    """
    dims, inds = np.asarray(dims), np.asarray(inds)
    n = len(dims)  # number of subsytems
    sz = prod(dims)  # Total size of system
    dims_in = dims[inds]
    sz_in = prod(dims_in)  # total size of operator space
    sz_out = sz // sz_in  # total size of identity space
    sz_op = op.shape[0]  # size of individual operator
    n_op = int(math.log(sz_in, sz_op))  # number of individual operators
    b = np.asarray(kronpow(op, n_op) & eye(sz_out))
    inds_out, dims_out = zip(*((i, x) for i, x in enumerate(dims)
                               if i not in inds))  # inverse of inds
    p = [*inds, *inds_out]  # current order of system
    dims_cur = (*dims_in, *dims_out)
    ip = np.empty(n, dtype=np.int)
    ip[p] = np.arange(n)  # inverse permutation
    return b.reshape((*dims_cur, *dims_cur))  \
            .transpose((*ip, *(ip + n)))  \
            .reshape((sz, sz))


@matrixify
def _permute_dense(p, dims, perm):
    """Permute the subsytems of a dense matrix.
    """
    p, perm = np.asarray(p), np.asarray(perm)
    d = prod(dims)
    if isop(p):
        return p.reshape((*dims, *dims)) \
                .transpose((*perm, *(perm + len(dims)))) \
                .reshape((d, d))
    return p.reshape(dims) \
            .transpose(perm) \
            .reshape((d, 1))


def _permute_sparse(a, dims, perm):
    """Permute the subsytems of a sparse matrix.
    """
    perm, dims = np.asarray(perm), np.asarray(dims)
    new_dims = dims[perm]
    # New dimensions & stride (i.e. product of preceding dimensions)
    odim_stride = np.multiply.accumulate(dims[::-1])[::-1] // dims
    ndim_stride = np.multiply.accumulate(new_dims[::-1])[::-1] // new_dims
    # Range of possible coordinates for each subsys
    coos = (tuple(range(dim)) for dim in dims)
    # Complete basis using coordinates for current and new dimensions
    basis = np.asarray(tuple(itertools.product(*coos, repeat=1)))
    oinds = np.sum(odim_stride * basis, axis=1)
    ninds = np.sum(ndim_stride * basis[:, perm], axis=1)
    # Construct permutation matrix and apply it to state
    perm_mat = sp.coo_matrix((np.ones(a.shape[0]), (ninds, oinds))).tocsr()
    if isop(a):
        return dot(dot(perm_mat, a), perm_mat.H)
    return dot(perm_mat, a)


def permute(a, dims, perm):
    """Permute the subsytems of state a.

    Parameters
    ----------
        p: state, vector or operator
        dims: dimensions of the system
        perm: new order of indexes range(len(dims))

    Returns
    -------
        pp: permuted state, vector or operator"""
    if issparse(a):
        return _permute_sparse(a, dims, perm)
    return _permute_dense(a, dims, perm)


def _ind_complement(inds, n):
    """Return the indices below `n` not contained in `inds`.
    """
    return tuple(i for i in range(n) if i not in inds)


def itrace(a, axes=(0, 1)):
    """General tensor trace, i.e. multiple contractions.

    Parameters
    ----------
        a: np.ndarray
            tensor to trace
        axes: (2,) int_like or (2,) array_like
            * (2,) int_like
              Perform trace on the two indices listed.
            * (2,) array_like
              Trace out first sequence indices with second sequence indices
    """
    # Single index pair to trace out
    if isinstance(axes[0], int):
        return np.trace(a, axis1=axes[0], axis2=axes[1])
    elif len(axes[0]) == 1:
        return np.trace(a, axis1=axes[0][0], axis2=axes[1][0])

    # Multiple index pairs to trace out
    gone = set()
    for axis1, axis2 in zip(*axes):
        # Modify indices to adjust for traced out dimensions
        mod1 = sum(x < axis1 for x in gone)
        mod2 = sum(x < axis2 for x in gone)
        gone |= {axis1, axis2}
        a = np.trace(a, axis1=axis1 - mod1, axis2=axis2 - mod2)
    return a


@matrixify
def _partial_trace_dense(p, dims, keep):
    """Perform partial trace.
    Parameters
    ----------
        p: state to perform partial trace on, vector or operator
        dims: list of subsystem dimensions
        keep: index of subsytems to keep
    Returns
    -------
        Density matrix of subsytem dimensions dims[keep]
    """
    if isinstance(keep, int):
        keep = (keep,)
    if isvec(p):  # p = psi
        p = np.asarray(p).reshape(dims)
        lose = _ind_complement(keep, len(dims))
        p = np.tensordot(p, p.conj(), (lose, lose))
        d = int(p.size**0.5)
        return p.reshape((d, d))
    else:
        p = np.asarray(p).reshape((*dims, *dims))
        total_dims = len(dims)
        lose = _ind_complement(keep, total_dims)
        lose2 = tuple(ind + total_dims for ind in lose)
        p = itrace(p, (lose, lose2))
    d = int(p.size**0.5)
    return p.reshape((d, d))


def _trace_lose(p, dims, coo_lose):
    """Simple partial trace where the single subsytem at `coo_lose`
    is traced out.
    """
    p = p if isop(p) else dot(p, p.H)
    dims = np.asarray(dims)
    e = dims[coo_lose]
    a = prod(dims[:coo_lose])
    b = prod(dims[coo_lose + 1:])
    rhos = zeros(shape=(a * b, a * b), dtype=np.complex128)
    for i in range(a * b):
        for j in range(i, a * b):
            i_i = e * b * (i // b) + (i % b)
            i_f = e * b * (i // b) + (i % b) + (e - 1) * b + 1
            j_i = e * b * (j // b) + (j % b)
            j_f = e * b * (j // b) + (j % b) + (e - 1) * b + 1
            rhos[i, j] = trace(p[i_i:i_f:b, j_i:j_f:b])
            if j != i:
                rhos[j, i] = rhos[i, j].conjugate()
    return rhos


def _trace_keep(p, dims, coo_keep):
    """Simple partial trace where the single subsytem
    at `coo_keep` is kept.
    """
    p = p if isop(p) else dot(p, p.H)
    dims = np.asarray(dims)
    s = dims[coo_keep]
    a = prod(dims[:coo_keep])
    b = prod(dims[coo_keep + 1:])
    rhos = zeros(shape=(s, s), dtype=np.complex128)
    for i in range(s):
        for j in range(i, s):
            for k in range(a):
                i_i = b * i + s * b * k
                i_f = b * i + s * b * k + b
                j_i = b * j + s * b * k
                j_f = b * j + s * b * k + b
                rhos[i, j] += trace(p[i_i:i_f, j_i:j_f])
            if j != i:
                rhos[j, i] = rhos[i, j].conjugate()
    return rhos


def _partial_trace_simple(p, dims, coos_keep):
    """Simple partial trace made up of consecutive single subsystem partial
    traces, augmented by 'compressing' the dimensions each time.
    """
    p = p if isop(p) else dot(p, p.H)
    dims, coos_keep = dim_compress(dims, coos_keep)
    if len(coos_keep) == 1:
        return _trace_keep(p, dims, *coos_keep)
    lmax = max(enumerate(dims),
               key=lambda ix: (ix[0] not in coos_keep) * ix[1])[0]
    p = _trace_lose(p, dims, lmax)
    dims = (*dims[:lmax], *dims[lmax + 1:])
    coos_keep = {(ind if ind < lmax else ind - 1) for ind in coos_keep}
    return _partial_trace_simple(p, dims, coos_keep)


def partial_trace(p, dims, coos):
    """Partial trace of a dense or sparse state.

    Parameters
    ----------
        p: state
        dims: list of dimensions of subsystems
        coos: coordinates of subsytems to keep

    Returns
    -------
        rhoab: density matrix of remaining subsytems,
    """
    if issparse(p):
        return _partial_trace_simple(p, dims, coos)
    return _partial_trace_dense(p, dims, coos)


_OVERLAP_METHODS = {
    (0, 0, 0): lambda a, b: abs(vdot(a, b))**2,
    (0, 1, 0): lambda a, b: vdot(a, dot_dense(b, a)),
    (1, 0, 0): lambda a, b: vdot(b, dot_dense(a, b)),
    (1, 1, 0): lambda a, b: _trace_dense(dot_dense(a, b)),
    (0, 0, 1): lambda a, b: abs(dot(a.H, b)[0, 0])**2,
    (0, 1, 1): realify(lambda a, b: dot(a.H, dot(b, a))[0, 0]),
    (1, 0, 1): realify(lambda a, b: dot(b.H, dot(a, b))[0, 0]),
    (1, 1, 1): lambda a, b: _trace_sparse(dot(a, b)),
}


def overlap(a, b):
    """Overlap between a and b, i.e. for vectors it will be the
    absolute overlap squared |<a|b><b|a>|, rather than <a|b>.
    """
    return _OVERLAP_METHODS[isop(a), isop(b), issparse(a) or issparse(b)](a, b)


# --------------------------------------------------------------------------- #
# MONKEY-PATCHES                                                              #
# --------------------------------------------------------------------------- #

# Normalise methods
nmlz = normalize
np.matrix.nmlz = nmlz
sp.csr_matrix.nmlz = nmlz

# Trace methods
tr = trace
np.matrix.tr = _trace_dense
sp.csr_matrix.tr = _trace_sparse
sp.csc_matrix.tr = _trace_sparse
sp.coo_matrix.tr = _trace_sparse
sp.bsr_matrix.tr = _trace_sparse

# Partial trace methods
ptr = partial_trace
np.matrix.ptr = _partial_trace_dense
sp.csr_matrix.ptr = _partial_trace_simple
sp.csc_matrix.ptr = _partial_trace_simple
sp.coo_matrix.ptr = _partial_trace_simple
sp.bsr_matrix.ptr = _partial_trace_simple
