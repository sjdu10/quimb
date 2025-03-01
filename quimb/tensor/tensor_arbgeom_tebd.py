"""Tools for performing TEBD like algorithms on arbitrary lattices."""

import collections
import itertools
import random
from collections.abc import Iterable

from autoray import do, to_numpy

from ..core import eye, kron, qarray
from ..utils import (
    ExponentialGeometricRollingDiffMean,
    ensure_dict,
)
from ..utils import progbar as Progbar
from ..utils_plot import default_to_neutral_style
from .drawing import get_colors, get_positions
from .tensor_core import Tensor


def edge_coloring(
    edges,
    strategy="smallest_last",
    interchange=True,
    group=True,
):
    """Generate an edge coloring for the graph given by ``edges``, using
    ``networkx.coloring.greedy_color``.

    Parameters
    ----------
    edges : sequence[tuple[hashable, hashable]]
        The edges of the graph.
    strategy : str or callable, optional
        The strategy to use for coloring the edges. Can be:

            - 'largest_first'
            - 'smallest_last'
            - 'random_sequential'
            ...

    interchange : bool, optional
        Whether to use the interchange heuristic. Usually generates better
        colorings but can be slower.
    group : bool, optional
        Whether to group the edges by color or return a flat list.
    """
    import networkx as nx

    # find vertex coloring of line graph
    G = nx.Graph(tuple(edges))
    edge_colors = nx.coloring.greedy_color(
        nx.line_graph(G), strategy, interchange=interchange
    )

    # group the edges by color
    coloring = {}
    for edge, color in edge_colors.items():
        coloring.setdefault(color, []).append(edge)

    if group:
        return tuple(
            tuple(tuple(tuple(sorted(edge)) for edge in coloring[color]))
            for color in sorted(coloring)
        )
    else:
        # flatten sorted groups
        return tuple(
            tuple(sorted(edge))
            for color in sorted(coloring)
            for edge in coloring[color]
        )


class LocalHamGen:
    """Representation of a local hamiltonian defined on a general graph. This
    combines all two site and one site terms into a single interaction per
    lattice pair, and caches operations on the terms such as getting their
    exponential. The sites (nodes) should be hashable and comparable.

    Parameters
    ----------
    H2 : dict[tuple[node], array_like]
        The interaction terms, with each key being an tuple of nodes defining
        an edge and each value the local hamilotonian term for those two nodes.
    H1 : array_like or dict[node, array_like], optional
        The one site term(s). If a single array is given, assume to be the
        default onsite term for all terms. If a dict is supplied,
        the keys should represent specific coordinates like
        ``(i, j)`` with the values the array representing the local term for
        that site. A default term for all remaining sites can still be supplied
        with the key ``None``.

    Attributes
    ----------
    terms : dict[tuple, array_like]
        The total effective local term for each interaction (with single site
        terms appropriately absorbed). Each key is a pair of coordinates
        ``site_a, site_b`` with ``site_a < site_b``.
    """

    def __init__(self, H2, H1=None):
        # caches for not repeating operations / duplicating tensors
        self._op_cache = collections.defaultdict(dict)

        self.terms = dict(H2)

        # convert qarrays (mostly useful for working with jax)
        for key, X in self.terms.items():
            if isinstance(X, qarray):
                self.terms[key] = self._convert_from_qarray_cached(X)

        self.sites = tuple(
            sorted(set(itertools.chain.from_iterable(self.terms)))
        )

        # first combine terms to ensure coo1 < coo2
        for where in tuple(filter(bool, self.terms)):
            coo1, coo2 = where
            if coo1 < coo2:
                continue

            # pop and flip the term
            X12 = self._flip_cached(self.terms.pop(where))

            # add to, or create, term with flipped coos
            new_where = coo2, coo1
            if new_where in self.terms:
                self.terms[new_where] = self._add_cached(
                    self.terms[new_where], X12
                )
            else:
                self.terms[new_where] = X12

        # make a directory of which single sites are covered by which terms
        #     - to merge them into later
        self._sites_to_covering_terms = collections.defaultdict(list)
        for where in self.terms:
            site_a, site_b = where
            self._sites_to_covering_terms[site_a].append(where)
            self._sites_to_covering_terms[site_b].append(where)

        # parse one site terms
        if H1 is None:
            H1s = dict()
        elif hasattr(H1, "shape"):
            # set a default site term
            H1s = {None: H1}
        else:
            H1s = dict(H1)

        # convert qarrays (mostly useful for working with jax)
        for key, X in H1s.items():
            if isinstance(X, qarray):
                H1s[key] = self._convert_from_qarray_cached(X)

        # possibly set the default single site term
        default_H1 = H1s.pop(None, None)
        if default_H1 is not None:
            for site in self.sites:
                H1s.setdefault(site, default_H1)

        # now absorb the single site terms evenly into the two site terms
        for site, H in H1s.items():
            # get interacting terms which cover the site
            pairs = self._sites_to_covering_terms[site]
            num_pairs = len(pairs)
            if num_pairs == 0:
                raise ValueError(
                    f"There are no two site terms to add this single site "
                    f"term to - site {site} is not coupled to anything."
                )

            # merge the single site term in equal parts into all covering pairs
            H_tensoreds = (self._op_id_cached(H), self._id_op_cached(H))
            for pair in pairs:
                H_tensored = H_tensoreds[pair.index(site)]
                self.terms[pair] = self._add_cached(
                    self.terms[pair], self._div_cached(H_tensored, num_pairs)
                )

    @property
    def nsites(self):
        """The number of sites in the system."""
        return len(self.sites)

    def items(self):
        """Iterate over all terms in the hamiltonian. This is mostly for
        convenient compatibility with ``compute_local_expectation``.
        """
        return self.terms.items()

    def _convert_from_qarray_cached(self, x):
        cache = self._op_cache["convert_from_qarray"]
        key = id(x)
        if key not in cache:
            cache[key] = x.toarray()
        return cache[key]

    def _flip_cached(self, x):
        cache = self._op_cache["flip"]
        key = id(x)
        if key not in cache:
            d = int(x.size ** (1 / 4))
            xf = do("reshape", x, (d, d, d, d))
            xf = do("transpose", xf, (1, 0, 3, 2))
            xf = do("reshape", xf, (d * d, d * d))
            cache[key] = xf
        return cache[key]

    def _add_cached(self, x, y):
        cache = self._op_cache["add"]
        key = (id(x), id(y))
        if key not in cache:
            cache[key] = x + y
        return cache[key]

    def _div_cached(self, x, y):
        cache = self._op_cache["div"]
        key = (id(x), y)
        if key not in cache:
            cache[key] = x / y
        return cache[key]

    def _op_id_cached(self, x):
        cache = self._op_cache["op_id"]
        key = id(x)
        if key not in cache:
            xn = to_numpy(x)
            d = int(xn.size**0.5)
            Id = eye(d, dtype=xn.dtype)
            XI = do("array", kron(xn, Id), like=x)
            cache[key] = XI
        return cache[key]

    def _id_op_cached(self, x):
        cache = self._op_cache["id_op"]
        key = id(x)
        if key not in cache:
            xn = to_numpy(x)
            d = int(xn.size**0.5)
            Id = eye(d, dtype=xn.dtype)
            IX = do("array", kron(Id, xn), like=x)
            cache[key] = IX
        return cache[key]

    def _expm_cached(self, G, x):
        cache = self._op_cache["expm"]
        key = (id(G), x)
        if key not in cache:
            ndim_G = do("ndim", G)
            need_to_reshape = ndim_G != 2
            if need_to_reshape:
                shape_orig = do("shape", G)
                G = do(
                    "fuse",
                    G,
                    range(0, ndim_G // 2),
                    range(ndim_G // 2, ndim_G),
                )

            U = do("scipy.linalg.expm", G * x)

            if need_to_reshape:
                U = do("reshape", U, shape_orig)

            cache[key] = U

        return cache[key]

    def get_gate(self, where):
        """Get the local term for pair ``where``, cached."""
        return self.terms[tuple(sorted(where))]

    def get_gate_expm(self, where, x):
        """Get the local term for pair ``where``, matrix exponentiated by
        ``x``, and cached.
        """
        return self._expm_cached(self.get_gate(where), x)

    def apply_to_arrays(self, fn):
        """Apply the function ``fn`` to all the arrays representing terms."""
        for k, x in self.terms.items():
            self.terms[k] = fn(x)

    def get_auto_ordering(self, order="sort", **kwargs):
        """Get an ordering of the terms to use with TEBD, for example. The
        default is to sort the coordinates then greedily group them into
        commuting sets.

        Parameters
        ----------
        order : {'sort', None, 'random', str}
            How to order the terms *before* greedily grouping them into
            commuting (non-coordinate overlapping) sets:

                - ``'sort'`` will sort the coordinate pairs first.
                - ``None`` will use the current order of terms which should
                  match the order they were supplied to this ``LocalHam2D``
                  instance.
                - ``'random'`` will randomly shuffle the coordinate pairs
                  before grouping them - *not* the same as returning a
                  completely random order.
                - ``'random-ungrouped'`` will randomly shuffle the coordinate
                  pairs but *not* group them at all with respect to
                  commutation.

            Any other option will be passed as a strategy to
            :func:`networkx.coloring.greedy_color` to generate the ordering.

        Returns
        -------
        list[tuple[node]]
            Sequence of coordinate pairs.
        """
        if order is None:
            pairs = self.terms
        elif order == "sort":
            pairs = sorted(self.terms)
        elif order == "random":
            pairs = list(self.terms)
            random.shuffle(pairs)
        elif order == "random-ungrouped":
            pairs = list(self.terms)
            random.shuffle(pairs)
            return pairs
        else:
            return edge_coloring(self.terms, order, group=False, **kwargs)

        pairs = {x: None for x in pairs}

        cover = set()
        ordering = list()
        while pairs:
            for pair in tuple(pairs):
                ij1, ij2 = pair
                if (ij1 not in cover) and (ij2 not in cover):
                    ordering.append(pair)
                    pairs.pop(pair)
                    cover.add(ij1)
                    cover.add(ij2)
            cover.clear()

        return ordering

    def __repr__(self):
        s = "<LocalHamGen(nsites={}, num_terms={})>"
        return s.format(self.nsites, len(self.terms))

    @default_to_neutral_style
    def draw(
        self,
        ordering="sort",
        show_norm=True,
        figsize=None,
        fontsize=8,
        legend=True,
        ax=None,
        **kwargs,
    ):
        """Plot this Hamiltonian as a network.

        Parameters
        ----------
        ordering : {'sort', None, 'random'}, optional
            An ordering of the termns, or an argument to be supplied to
            :meth:`quimb.tensor.tensor_arbgeom_tebd.LocalHamGen.get_auto_ordering`
            to generate this automatically.
        show_norm : bool, optional
            Show the norm of each term as edge labels.
        figsize : None or tuple[int], optional
            Size of the figure, defaults to size of Hamiltonian.
        fontsize : int, optional
            Font size for norm labels.
        legend : bool, optional
            Whether to show the legend of which terms are in which group.
        ax : None or matplotlib.Axes, optional
            Add to a existing set of axes.
        """
        import matplotlib.pyplot as plt
        import networkx as nx

        if figsize is None:
            L = self.nsites**0.5 + 1
            figsize = (L, L)

        ax_supplied = ax is not None
        if not ax_supplied:
            fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
            ax.axis("off")
            ax.set_aspect("equal")
        else:
            fig = None

        if ordering is None or isinstance(ordering, str):
            ordering = self.get_auto_ordering(ordering, **kwargs)

        G = nx.Graph()
        seen = set()
        n = 0
        edge_labels = dict()
        for where in ordering:
            site_a, site_b = where
            if (site_a in seen) or (site_b in seen):
                # start a new group
                seen = {site_a, site_b}
                n += 1
            else:
                seen.add(site_a)
                seen.add(site_b)

            nrm = do("linalg.norm", self.terms[where])
            edge_labels[where] = f"{nrm:.2f}"
            G.add_edge(site_a, site_b, norm=nrm, group=n)

        num_groups = n + 1
        colors = get_colors(range(num_groups))

        pos = get_positions(None, G)

        # do the plotting
        nx.draw_networkx_edges(
            G,
            pos=pos,
            width=tuple(2 * x[2]["norm"] ** 0.5 for x in G.edges(data=True)),
            edge_color=tuple(
                colors[x[2]["group"]] for x in G.edges(data=True)
            ),
            alpha=0.8,
            ax=ax,
        )
        nx.draw_networkx_edge_labels(
            G,
            pos=pos,
            edge_labels=edge_labels,
            font_size=fontsize,
            font_color=(0.5, 0.5, 0.5),
            bbox=dict(alpha=0),
            ax=ax,
        )
        nx.draw_networkx_labels(
            G,
            pos,
            font_color=(0.2, 0.2, 0.2),
            font_size=fontsize,
            font_weight="bold",
            ax=ax,
        )

        # create legend
        if legend:
            handles = []
            for color in colors.values():
                handles += [
                    plt.Line2D(
                        [0],
                        [0],
                        marker="o",
                        color=color,
                        linestyle="",
                        markersize=10,
                    )
                ]

            lbls = [f"Group {i + 1}" for i in range(num_groups)]

            ax.legend(
                handles,
                lbls,
                ncol=max(round(len(handles) / 20), 1),
                loc="center left",
                bbox_to_anchor=(1, 0.5),
            )

        return fig, ax

    graph = draw


class TEBDGen:
    """Generic class for performing time evolving block decimation on an
    arbitrary graph, i.e. applying the exponential of a Hamiltonian using
    a product formula that involves applying local exponentiated gates only.
    """

    def __init__(
        self,
        psi0,
        ham,
        tau=0.01,
        D=None,
        cutoff=1e-10,
        imag=True,
        gate_opts=None,
        ordering=None,
        second_order_reflect=False,
        compute_energy_every=None,
        compute_energy_final=True,
        compute_energy_opts=None,
        compute_energy_fn=None,
        compute_energy_per_site=False,
        tol=None,
        callback=None,
        keep_best=False,
        progbar=True,
    ):
        self.imag = imag
        if not imag:
            raise NotImplementedError("Real time evolution not tested yet.")

        self.state = psi0
        self.ham = ham
        self.progbar = progbar
        self.callback = callback

        # default time step to use
        self.tau = tau
        self.last_tau = 0.0

        # parse gate application options
        if D is None:
            D = self._psi.max_bond()
        self.gate_opts = ensure_dict(gate_opts)
        self.gate_opts["max_bond"] = D
        self.gate_opts.setdefault("cutoff", cutoff)
        self.gate_opts.setdefault("contract", "reduce-split")

        # parse energy computation options
        self.compute_energy_opts = ensure_dict(compute_energy_opts)

        self.compute_energy_every = compute_energy_every
        self.compute_energy_final = compute_energy_final
        self.compute_energy_fn = compute_energy_fn
        self.compute_energy_per_site = bool(compute_energy_per_site)
        self.tol = tol

        if ordering is None:

            def dynamic_random():
                return self.ham.get_auto_ordering("random_sequential")

            self.ordering = dynamic_random
        elif isinstance(ordering, str):
            self.ordering = self.ham.get_auto_ordering(ordering)
        elif callable(ordering):
            self.ordering = ordering
        else:
            self.ordering = tuple(ordering)

        self.second_order_reflect = second_order_reflect

        # storage
        self._n = 0
        self.its = []
        self.taus = []
        self.energies = []
        self.energy_diffs = []
        self.egrdm = ExponentialGeometricRollingDiffMean()

        self.keep_best = bool(keep_best)
        self.best = dict(energy=float("inf"), state=None, it=None)
        self.stop = False

    def sweep(self, tau):
        r"""Perform a full sweep of gates at every pair.

        .. math::

            \psi \rightarrow \prod_{\{ij\}} \exp(-\tau H_{ij}) \psi

        """
        if callable(self.ordering):
            ordering = self.ordering()
        else:
            ordering = self.ordering

        if self.second_order_reflect:
            ordering = tuple(ordering) + tuple(reversed(ordering))
            factor = 2.0
        else:
            factor = 1.0

        layer = set()

        for where in ordering:
            if any(coo in layer for coo in where):
                # starting a new non-commuting layer
                self.postlayer()
                layer = set(where)
            else:
                # add to the current layer
                layer.update(where)

            if callable(tau):
                self.last_tau = tau(where)
            else:
                self.last_tau = tau

            G = self.ham.get_gate_expm(where, -self.last_tau / factor)

            self.gate(G, where)

        self.postlayer()

    def _set_progbar_description(self, pbar):
        desc = f"n={self._n}, tau={float(self.last_tau):.2g}"
        if getattr(self, "gauge_diffs", None):
            desc += f", max|dS|={self.gauge_diffs[-1]:.2g}"
        if self.energies:
            desc += f", energy~{float(self.energies[-1]):.6g}"
        pbar.set_description(desc)

    def evolve(self, steps, tau=None, progbar=None):
        """Evolve the state with the local Hamiltonian for ``steps`` steps with
        time step ``tau``.
        """
        if tau is not None:
            if isinstance(tau, Iterable):
                taus = itertools.chain(tau, itertools.repeat(tau[-1]))
            else:
                self.tau = tau
                taus = itertools.repeat(tau)

        if progbar is None:
            progbar = self.progbar

        pbar = Progbar(total=steps, disable=not progbar)

        try:
            for i, tau in zip(range(steps), taus):
                # anything required by both energy and sweep
                self.presweep(i)

                # possibly compute the energy
                should_compute_energy = bool(self.compute_energy_every) and (
                    i % self.compute_energy_every == 0
                )
                if should_compute_energy:
                    self._check_energy()
                    self._set_progbar_description(pbar)

                    # check for convergence
                    self.stop = (self.tol is not None) and (
                        self.energy_diffs[-1] < self.tol
                    )

                if self.stop:
                    # maybe stop pre sweep
                    self.stop = False
                    break

                # actually perform the gates
                self.sweep(tau)
                self.postsweep(i)

                self._n += 1
                pbar.update()
                self._set_progbar_description(pbar)

                if self.callback is not None:
                    if self.callback(self):
                        break

                if self.stop:
                    # maybe stop post sweep
                    self.stop = False
                    break

            # possibly compute the energy
            if self.compute_energy_final:
                self._check_energy()
                self._set_progbar_description(pbar)

        except KeyboardInterrupt:
            # allow the user to interupt early
            pass
        finally:
            pbar.close()

    @property
    def state(self):
        """Return a copy of the current state."""
        return self.get_state()

    @state.setter
    def state(self, psi):
        self.set_state(psi)

    @property
    def n(self):
        """The number of sweeps performed."""
        return self._n

    @property
    def D(self):
        """The maximum bond dimension."""
        return self.gate_opts["max_bond"]

    @D.setter
    def D(self, value):
        """The maximum bond dimension."""
        self.gate_opts["max_bond"] = round(value)

    def _check_energy(self):
        """Logic for maybe computing the energy if needed."""
        if self.its and (self._n == self.its[-1]):
            # only compute if haven't already
            return self.energies[-1]

        if self.compute_energy_fn is not None:
            en = self.compute_energy_fn(self)
        else:
            en = self.compute_energy()

        if self.compute_energy_per_site:
            en = en / self.ham.nsites

        self.its.append(self._n)
        self.taus.append(float(self.last_tau))

        # update the energy and possibly the best state
        self.energies.append(float(en))
        if self.keep_best and en < self.best["energy"]:
            self.best["energy"] = en
            self.best["state"] = self.state
            self.best["it"] = self._n

        # update the energy difference mean and possibly marked converged
        self.egrdm.update(float(en))
        self.energy_diffs.append(self.egrdm.value)

        if self.tol is not None:
            self.stop = self.energy_diffs[-1] < self.tol

        return self.energies[-1]

    @property
    def energy(self):
        """Return the energy of current state, computing it only if necessary."""
        return self._check_energy()

    # ------- abstract methods that subclasses might want to override ------- #

    def get_state(self):
        """The default method for retrieving the current state - simply a copy.
        Subclasses can override this to perform additional transformations.
        """
        return self._psi.copy()

    def set_state(self, psi):
        """The default method for setting the current state - simply a copy.
        Subclasses can override this to perform additional transformations.
        """
        self._psi = psi.copy()

    def presweep(self, i):
        """Perform any computations required before the sweep (and energy
        computation). For the basic TEBD update is nothing.
        """
        pass

    def postlayer(self):
        """Perform any computations required after each layer of commuting
        gates. For the basic update this is nothing.
        """
        pass

    def postsweep(self, i):
        """Perform any computations required after the sweep (but before
        the energy computation). For the basic update this is nothing.
        """
        pass

    def gate(self, U, where):
        """Perform single gate ``U`` at coordinate pair ``where``. This is the
        the most common method to override.
        """
        self._psi.gate_(U, where, **self.gate_opts)

    def compute_energy(self):
        """Compute and return the energy of the current state. Subclasses can
        override this with a custom method to compute the energy.
        """
        return self._psi.compute_local_expectation_cluster(
            terms=self.ham.terms, **self.compute_energy_opts
        )

    @default_to_neutral_style
    def plot(
        self,
        zoom="auto",
        xscale="symlog",
        xscale_linthresh=20,
        color_energy=(0.0, 0.5, 1.0),
        color_gauge_diff=(1.0, 0.5, 0.0),
        hlines=(),
        figsize=(8, 4),
    ):
        """Plot an overview of the evolution of the energy and gauge diffs.

        Parameters
        ----------
        zoom : int or 'auto', optional
            The number of iterations to zoom in on, or 'auto' to automatically
            choose a reasonable zoom level.
        xscale : {'linear', 'log', 'symlog'}, optional
            The x-axis scale, for the upper plot of the entire evolution.
        xscale_linthresh : float, optional
            The linear threshold for the upper symlog scale.
        color_energy : str or tuple, optional
            The color to use for the energy plot.
        color_gauge_diff : str or tuple, optional
            The color to use for the gauge diff plot.
        hlines : dict, optional
            Add horizontal lines to the plot, with keys as labels and values
            as the y-values.
        figsize : tuple, optional
            The size of the figure.

        Returns
        -------
        fig, axs : matplotlib.Figure, tuple[matplotlib.Axes]
        """
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.ticker import ScalarFormatter
        from matplotlib.colors import hsv_to_rgb

        def set_axis_color(ax, which, color):
            ax.spines[which].set_visible(True)
            ax.spines[which].set_color(color)
            ax.yaxis.label.set_color(color)
            ax.tick_params(axis="y", colors=color, which="both")

        x_en = np.array(self.its)
        y_en = np.array(self.energies)
        x_gd = np.arange(1, len(self.gauge_diffs) + 1)
        y_gd = np.array(self.gauge_diffs)

        if zoom is not None:
            if zoom == "auto":
                zoom = min(200, self.n // 2)
        nz = self.n - zoom

        fig, axs = plt.subplots(nrows=2, figsize=figsize)

        # plotted zoomed out
        # energy
        axl = axs[0]
        axl.plot(x_en, y_en, marker="|", color=color_energy)
        axl.set_xscale(xscale, linthresh=xscale_linthresh)
        axl.set_ylabel("Energy")
        axl.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        set_axis_color(axl, "left", color_energy)
        # gauge diff
        axr = axl.twinx()
        axr.plot(
            x_gd,
            y_gd,
            linestyle="--",
            color=color_gauge_diff,
        )
        axr.set_ylabel("Max gauge diff")
        axr.set_yscale("log")
        set_axis_color(axr, "right", color_gauge_diff)

        axl.axvline(
            nz,
            color=(0.5, 0.5, 0.5, 0.5),
            linestyle="-",
            linewidth=1,
        )

        # plotted zoomed in
        # energy
        iz = min(range(len(x_en)), key=lambda i: x_en[i] < nz)
        axl = axs[1]
        axl.plot(x_en[iz:], y_en[iz:], marker="|", color=color_energy)
        axl.set_ylabel("Energy")
        axl.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        set_axis_color(axl, "left", color_energy)
        axl.set_xlabel("Iteration")
        # gauge diff
        iz = min(range(len(x_gd)), key=lambda i: x_gd[i] < nz)
        axr = axl.twinx()
        axr.plot(
            x_gd[iz:],
            y_gd[iz:],
            linestyle="--",
            color=color_gauge_diff,
        )
        axr.set_ylabel("Max gauge diff")
        axr.set_yscale("log")
        set_axis_color(axr, "right", color_gauge_diff)

        if hlines:
            hlines = dict(hlines)
            for i, (label, value) in enumerate(hlines.items()):
                color = hsv_to_rgb([(0.45 - (0.08 * i)) % 1.0, 0.7, 0.6])
                axs[0].axhline(value, color=color, ls=":", label=label)
                axs[1].axhline(value, color=color, ls=":", label=label)
                axs[0].text(
                    1, value, label, color=color, va="bottom", ha="left"
                )
                axs[1].text(
                    nz, value, label, color=color, va="bottom", ha="left"
                )

        return fig, axs

    def __repr__(self):
        s = "<{}(n={}, tau={}, D={})>"
        return s.format(self.__class__.__name__, self.n, self.tau, self.D)


class SimpleUpdateGen(TEBDGen):
    """Simple update for arbitrary geometry hamiltonians.

    Parameters
    ----------
    psi0 : TensorNetworkGenVector
        The initial state.
    ham : LocalHamGen
        The local hamiltonian.
    tau : float, optional
        The default time step to use.
    D : int, optional
        The maximum bond dimension, by default the current maximum bond of
        ``psi0``.
    cutoff : float, optional
        The singular value cutoff to use when applying gates.
    imag : bool, optional
        Whether to evolve in imaginary time (default) or real time.
    gate_opts : dict, optional
        Other options to supply to the gate application method,
        :meth:`quimb.tensor.tensor_arbgeom.TensorNetworkGenVector.gate_simple_`.
    ordering : None, str or callable, optional
        The ordering of the terms to apply, by default this will be determined
        automatically.
    second_order_reflect : bool, optional
        Whether to use a second order Trotter decomposition by reflecting the
        ordering.
    compute_energy_every : int, optional
        Compute the energy every this many steps.
    compute_energy_final : bool, optional
        Whether to compute the energy at the end.
    compute_energy_opts : dict, optional
        Options to supply to the energy computation method,
        :func:`quimb.tensor.tensor_arbgeom.TensorNetworkGenVector.compute_local_expectation_cluster`.
    compute_energy_fn : callable, optional
        A custom function to compute the energy, with signature ``fn(su)``,
        where ``su`` is this instance.
    compute_energy_per_site : bool, optional
        Whether to compute the energy per site.
    tol : float, optional
        If not ``None``, stop when either energy difference falls below this
        value, or maximum singluar value changes fall below this value.
    equilibrate_every : int, optional
        Equilibrate the gauges every this many steps.
    equilibrate_start : bool, optional
        Whether to equilibrate the gauges at the start, regardless of
        ``equilibrate_every``.
    equilibrate_opts : dict, optional
        Default options to supply to the gauge equilibration method, see
        :meth:`quimb.tensor.tensor_core.TensorNetwork.gauge_all_simple`. By
        default `max_iterations` is set to 100 and `tol` to 1e-3.
    callback : callable, optional
        A function to call after each step, with signature ``fn(su)``.
    keep_best : bool, optional
        Whether to keep track of the best state and energy.
    progbar : bool, optional
        Whether to show a progress bar during evolution.
    """

    def __init__(
        self,
        psi0,
        ham,
        tau=0.01,
        D=None,
        cutoff=1e-10,
        imag=True,
        gate_opts=None,
        ordering=None,
        second_order_reflect=False,
        compute_energy_every=None,
        compute_energy_final=True,
        compute_energy_opts=None,
        compute_energy_fn=None,
        compute_energy_per_site=False,
        tol=None,
        equilibrate_every=0,
        equilibrate_start=True,
        equilibrate_opts=None,
        callback=None,
        keep_best=False,
        progbar=True,
    ):
        self.equilibrate_every = equilibrate_every
        self.equilibrate_start = bool(equilibrate_start)
        self.equilibrate_opts = equilibrate_opts or {}
        self.equilibrate_opts.setdefault("max_iterations", 100)
        self.equilibrate_opts.setdefault("tol", 1e-3)

        self.gauges_prev = None
        self.gauge_diffs = []

        return super().__init__(
            psi0,
            ham,
            tau=tau,
            D=D,
            cutoff=cutoff,
            imag=imag,
            gate_opts=gate_opts,
            ordering=ordering,
            second_order_reflect=second_order_reflect,
            compute_energy_every=compute_energy_every,
            compute_energy_final=compute_energy_final,
            compute_energy_opts=compute_energy_opts,
            compute_energy_fn=compute_energy_fn,
            compute_energy_per_site=compute_energy_per_site,
            tol=tol,
            callback=callback,
            keep_best=keep_best,
            progbar=progbar,
        )

    def gate(self, G, where):
        """Application of a single gate ``G`` at ``where``."""
        self._psi.gate_simple_(G, where, gauges=self.gauges, **self.gate_opts)

        if self.equilibrate_every == "gate":
            tags = [self._psi.site_tag(x) for x in where]
            tids = self._psi._get_tids_from_tags(tags, "any")
            self.equilibrate(touched_tids=tids)

    def equilibrate(self, **kwargs):
        """Equilibrate the gauges with the current state (like evolving with
        tau=0).
        """
        # allow overriding of default options
        kwargs = {**self.equilibrate_opts, **kwargs}
        self._psi.gauge_all_simple_(gauges=self.gauges, **kwargs)

    def postlayer(self):
        """Performed after each layer of commuting gates."""
        if self.equilibrate_every == "layer":
            self.equilibrate()

    def postsweep(self, i):
        """Performed after every full sweep."""
        should_equilibrate = (
            # str settings are equilibrated elsewhere
            (not isinstance(self.equilibrate_every, str))
            and (self.equilibrate_every > 0)
            and (i % self.equilibrate_every == 0)
        )

        if should_equilibrate:
            self.equilibrate()

        # check gauges for convergence / progbar
        if self.gauges_prev is not None:
            sdiffs = []
            for k, g in self.gauges.items():
                g_prev = self.gauges_prev[k]
                try:
                    sdiff = do("linalg.norm", g - g_prev)
                except ValueError:
                    # gauge has changed size
                    sdiff = 1.0
                sdiffs.append(sdiff)

            max_sdiff = max(sdiffs)
            self.gauge_diffs.append(max_sdiff)

            if self.tol is not None and (max_sdiff < self.tol):
                self.stop = True

        self.gauges_prev = self.gauges.copy()

    def normalize(self):
        """Normalize the state and simple gauges."""
        self._psi.normalize_simple(self.gauges)

    def compute_energy(self):
        """Default estimate of the energy."""
        return self._psi.compute_local_expectation_cluster(
            terms=self.ham.terms,
            gauges=self.gauges,
            **self.compute_energy_opts,
        )

    def get_state(self, absorb_gauges=True):
        """Return the current state, possibly absorbing the gauges.

        Parameters
        ----------
        absorb_gauges : bool or "return", optional
            Whether to absorb the gauges into the state or not. If `True`, a
            standard PEPS is returned with the gauges absorbed. If `False``,
            the gauges are added to the tensor network but uncontracted. If
            "return", the gauges are returned separately.

        Returns
        -------
        psi : TensorNetwork
            The current state.
        gauges : dict
            The current gauges, if ``absorb_gauges == "return"``.
        """
        psi = self._psi.copy()

        if absorb_gauges == "return":
            return psi, self.gauges.copy()

        if absorb_gauges:
            psi.gauge_simple_insert(self.gauges)
        else:
            for ix, g in self.gauges.items():
                psi |= Tensor(g, inds=[ix])

        return psi

    def set_state(self, psi, gauges=None):
        """Set the current state and possibly the gauges."""
        self._psi = psi.copy()
        if gauges is None:
            self.gauges = {}
            self._psi.gauge_all_simple_(max_iterations=1, gauges=self.gauges)
        else:
            self.gauges = dict(gauges)

        if self.equilibrate_start:
            self.equilibrate()
