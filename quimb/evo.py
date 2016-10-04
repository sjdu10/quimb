""" Contains an evolution class, QuEvo to efficiently manage time evolution of
quantum states according to schrodingers' equation, and related functions."""

# TODO: set/update pt * ***************************************************** #
# TODO: test known lindlbad evolution *************************************** #
# TODO: solout method with funcyt ******************************************* #
# TODO: QuEvoTimeDepend ***************************************************** #

import numpy as np
from scipy.integrate import complex_ode
from .accel import isop, ldmul, rdmul, explt
from .accel import issparse, _dot_dense
from .core import qu, eye
from .solve import eigsys, norm


# --------------------------------------------------------------------------- #
# Quantum evolution equations                                                 #
# --------------------------------------------------------------------------- #

def schrodinger_eq_ket(ham, all_dense=False):
    """ Wavefunction schrodinger equation.

    Parameters
    ----------
        ham: time-independant hamiltonian governing evolution
        all_dense: eplicitly use dense optimized dot product

    Returns
    -------
        psi_dot(t, y): function to calculate psi_dot(t) at psi(t). """
    if all_dense:
        def psi_dot(_, y):
            return -1.0j * _dot_dense(ham, y)
    else:
        def psi_dot(_, y):
            return -1.0j * (ham @ y)
    return psi_dot


def schrodinger_eq_dop(ham, all_dense=False):
    """ Density operator schrodinger equation, but with flattened input/output.
    Note that this assumes both `ham` and `rho` are hermitian in order to speed
    up the commutator, non-hermitian hamiltonians as used to model loss should
    be treated explicilty or with `schrodinger_eq_dop_vec`.

    Parameters
    ----------
        ham: time-independant hamiltonian governing evolution
        all_dense: eplicitly use dense optimized dot product

    Returns
    -------
        rho_dot(t, y): function to calculate rho_dot(t) at rho(t), input and
            output both in ravelled (1D form). """
    d = ham.shape[0]
    if all_dense:
        def rho_dot(_, y):
            hrho = _dot_dense(ham, y.reshape(d, d))
            return -1.0j * (hrho - hrho.T.conj()).reshape(-1)
    else:
        def rho_dot(_, y):
            hrho = ham @ y.reshape(d, d)
            return -1.0j * (hrho - hrho.T.conj()).reshape(-1)
    return rho_dot


def schrodinger_eq_dop_vec(ham):
    """ Density operator schrodinger equation, but with flattened input/output
    and vectorised superoperation mode (no reshaping required).

    Parameters
    ----------
        ham: time-independant hamiltonian governing evolution

    Returns
    -------
        rho_dot(t, y): function to calculate rho_dot(t) at rho(t), input and
            output both in ravelled (1D form). """
    d = ham.shape[0]
    sparse = issparse(ham)
    I = eye(d, sparse=sparse)
    evo_superop = -1.0j * ((ham & I) - (I & ham.T))

    def rho_dot(_, y):
        return evo_superop @ y
    return rho_dot


def lindblad_eq(ham, ls, gamma, all_dense=False):
    """ Lindblad equation, but with flattened input/output.

    Parameters
    ----------
        ham: time-independant hamiltonian governing evolution
        ls: lindblad operators
        gamma: dampening strength
        all_dense: eplicitly use dense optimized dot product

    Returns
    -------
        rho_dot(t, y): function to calculate rho_dot(t) at rho(t), input and
            output both in ravelled (1D form). """
    d = ham.shape[0]
    lls = tuple(l.H @ l for l in ls)

    if all_dense:
        def gen_l_terms(rho):
            for l, ll in zip(ls, lls):
                yield (_dot_dense(l, _dot_dense(rho, l.H)) -
                       0.5 * (_dot_dense(rho, ll) + _dot_dense(ll, rho)))

        def rho_dot(_, y):
            rho = y.reshape(d, d)
            rho_d = _dot_dense(ham, rho)
            rho_d -= rho_d.T.conj()
            rho_d *= -1.0j
            rho_d += gamma * sum(gen_l_terms(rho))
            return np.asarray(rho_d).reshape(-1)
    else:
        def gen_l_terms(rho):
            for l, ll in zip(ls, lls):
                yield (l @ rho @ l.H) - 0.5 * ((rho @ ll) + (ll @ rho))

        def rho_dot(_, y):
            rho = y.reshape(d, d)
            rho_d = ham @ rho
            rho_d -= rho_d.T.conj()
            rho_d *= -1.0j
            rho_d += gamma * sum(gen_l_terms(rho))
            return np.asarray(rho_d).reshape(-1)
    return rho_dot


def lindblad_eq_vec(ham, ls, gamma, sparse=False):
    """ Lindblad equation, but with flattened input/output and vectorised
    superoperation mode (no reshaping required).

    Parameters
    ----------
        ham: time-independant hamiltonian governing evolution
        ls: lindblad operators
        gamma: dampening strength

    Returns
    -------
        rho_dot(t, y): function to calculate rho_dot(t) at rho(t), input and
            output both in ravelled (1D form). """
    d = ham.shape[0]
    ham_sparse = issparse(ham) or sparse
    I = eye(d, sparse=ham_sparse)
    evo_superop = -1.0j * ((ham & I) - (I & ham.T))

    def gen_lb_terms():
        for l in ls:
            lb_sparse = issparse(l) or sparse
            I = eye(d, sparse=lb_sparse)
            yield ((l & l.conj()) - 0.5*((I & (l.H @ l).T) + ((l.H @ l) & I)))
    evo_superop += gamma * sum(gen_lb_terms())

    def rho_dot(_, y):
        return evo_superop @ y
    return rho_dot


def calc_evo_eq(isdop, issparse, isopen=False):
    """ Choose an appropirate dynamical equation to evolve with. """
    eq_chooser = {
        (0, 0, 0): schrodinger_eq_ket,
        (0, 1, 0): schrodinger_eq_ket,
        (1, 0, 0): schrodinger_eq_dop,
        (1, 1, 0): schrodinger_eq_dop_vec,
        (1, 0, 1): lindblad_eq,
        (1, 1, 1): lindblad_eq_vec,
    }
    return eq_chooser[(isdop, issparse, isopen)]


# --------------------------------------------------------------------------- #
# Quantum Evolution Class                                                     #
# --------------------------------------------------------------------------- #

class QuEvo(object):
    """A class for evolving quantum systems according to schro equation
    Note that vector states are converted to kets always.
    """

    def __init__(self, p0, ham, solve=False, t0=0, small_step=False):
        """Parameters
        ----------
            p0: inital state, either vector or operator
            ham: Governing Hamiltonian, can be tuple (eigvals, eigvecs)
            solve: whether to immediately solve hamiltonian
            t0: initial time (i.e. time of state p0)
            small_step: if integrating, whether to use a low or high order
                integrator to give naturally small or large steps.

        Members
        -------
            t: current time
            pt: current state
        """
        super(QuEvo, self).__init__()

        self.p0 = qu(p0)
        self._t = self.t0 = t0
        self.isdop = isop(self.p0)  # Density operator evolution?
        self.d = p0.shape[0]  # Hilbert space dimension

        # Hamiltonian
        if solve or isinstance(ham, (tuple, list)):
            self._solve_ham(ham)
        else:  # Use definite integration
            self._start_integrator(ham, small_step)

    def _solve_ham(self, ham):
        """Solve the supplied hamiltonian and find the initial state in the
        energy eigenbasis for quick evolution later.
        """
        try:  # See if already set from tuple
            self.evals, self.evecs = ham
        except ValueError:
            self.evals, self.evecs = eigsys(ham.A)

        # Find initial state in energy eigenbasis at t0
        self.pe0 = (self.evecs.H @ self.p0 @ self.evecs if self.isdop else
                    self.evecs.H @ self.p0)
        self._pt = self.p0  # Current state (start with same as initial)

        # Set update method conditional on type of state
        self.update_to = (self._update_to_solved_dop if self.isdop else
                          self._update_to_solved_ket)
        self.solved = True

    def _start_integrator(self, ham, small_step):
        """Initialize a stepping integrator.
        """
        self.sparse_ham = issparse(ham)
        evo_eq = calc_evo_eq(self.isdop, self.sparse_ham)
        self.stepper = complex_ode(evo_eq(ham))
        int_mthd, step_fct = ('dopri5', 150) if small_step else ('dop853', 50)
        first_step = norm(ham, 'f') / step_fct
        self.stepper.set_integrator(int_mthd, nsteps=0, first_step=first_step)
        self.stepper.set_initial_value(self.p0.A.reshape(-1), self.t0)
        self.update_to = self._update_to_integrate
        self.solved = False

    # Methods for updating the simulation ----------------------------------- #

    def _update_to_solved_ket(self, t):
        """Update simulation consisting of a solved hamiltonian and a
        wavefunction to time `t`.
        """
        self._t = t
        lt = explt(self.evals, t - self.t0)
        self._pt = _dot_dense(self.evecs, ldmul(lt, self.pe0))

    def _update_to_solved_dop(self, t):
        """Update simulation consisting of a solved hamiltonian and a
        density operator to time `t`.
        """
        self._t = t
        lt = explt(self.evals, t - self.t0)
        lvpvl = rdmul(ldmul(lt, self.pe0), lt.conj())
        self._pt = _dot_dense(self.evecs, _dot_dense(lvpvl, self.evecs.H))

    def _update_to_integrate(self, t):
        """Update simulation consisting of unsolved hamiltonian.
        """
        self.stepper.integrate(t)

    def at_times(self, ts):
        for t in ts:
            self.update_to(t)
            yield self.pt

    # Simulation properties ------------------------------------------------- #

    @property
    def t(self):
        """Current time of simulation.
        """
        return (self._t if self.solved else
                self.stepper.t)

    @property
    def pt(self):
        """Return the state of the system at the current time (t).
        """
        return (self._pt if self.solved else
                np.asmatrix(self.stepper.y.reshape(self.d, -1)))
