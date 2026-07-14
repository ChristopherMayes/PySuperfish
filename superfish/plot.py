from copy import copy
from typing import Any, cast

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import Colormap
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable

from .types import FishT7Data, PoissonT7Data, WallSegment


def get_cmap0() -> Colormap:
    """
    Get the default color map.

    Returns
    -------
    matplotlib.colors.Colormap
        The ``plasma`` color map with values below the range drawn white.
    """
    cmap0 = copy(plt.get_cmap("plasma"))
    cmap0.set_under("white")
    return cmap0


def add_t7data_to_axes(
    t7data: FishT7Data | PoissonT7Data,
    ax: Axes,
    field: str = "E",
    cmap: Colormap | None = None,
    vmin: float = 1e-19,
    scale: float = 1,
) -> Axes:
    """
    Add a field image from t7data to an axes.

    Parameters
    ----------
    t7data : FishT7Data or PoissonT7Data
        Parsed T7 data, as returned by
        :func:`superfish.parsers.parse_fish_t7` or
        :func:`superfish.parsers.parse_poisson_t7`.
    ax : matplotlib.axes.Axes
        Axes to draw on.
    field : str
        Field to plot. ``"E"`` or ``"B"`` magnitudes are computed from the
        r and z components when not present in ``t7data``.
    cmap : matplotlib.colors.Colormap, optional
        Color map. Defaults to :func:`get_cmap0`.
    vmin : float
        Minimum value for the color scale.
    scale : float
        Scales the extents, to account for different units.
        Example: ``scale=10`` will place this data in cm on a plot in mm.

    Returns
    -------
    matplotlib.axes.Axes
        The axes that was drawn on.
    """

    extent = (
        t7data["zmin"] * scale,
        t7data["zmax"] * scale,
        t7data["rmin"] * scale,
        t7data["rmax"] * scale,
    )

    if not cmap:
        cmap = get_cmap0()

    # The field key is dynamic, so bypass the TypedDict for lookups
    td = cast("dict[str, Any]", t7data)
    if field in ("E", "B") and field not in td:
        data = np.hypot(td[field + "r"], td[field + "z"])
    else:
        data = td[field]

    ax.imshow(np.flipud(data), extent=extent, cmap=cmap, vmin=vmin)

    return ax


def perp(
    x: np.ndarray,
    y: np.ndarray,
    scale: float | np.ndarray = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate lines perpendicular to the segments of a polyline.

    Parameters
    ----------
    x, y : ndarray
        Coordinates of the polyline vertices.
    scale : float or ndarray
        Length of the perpendicular lines. An array gives a per-segment
        length.

    Returns
    -------
    PX, PY : ndarray
        Endpoint coordinates of the perpendicular lines, each of shape
        ``(len(x) - 1, 2)``.

    Examples
    --------
    >>> X = np.array([1, 2, 3, 4, 8])
    >>> Y = np.array([4, 5, 6, 9, 10])
    >>> PX, PY = perp(X, Y)
    >>> fig, ax = plt.subplots()
    >>> ax.set_aspect('equal')
    >>> ax.plot(X, Y)
    >>> for i in range(len(PX)):
    ...    ax.plot(PX[i, :], PY[i, :])
    """
    dx = np.diff(x)
    dy = np.diff(y)
    norm = np.hypot(dx, dy)

    # perp
    px0 = x[:-1] + dx / 2
    py0 = y[:-1] + dy / 2
    px1 = px0 + dy / norm * scale
    py1 = py0 - dx / norm * scale

    return np.array([px0, px1]).T, np.array([py0, py1]).T


def add_wall_segment_to_axes(
    seg: WallSegment,
    ax: Axes,
    perp_scale: float = 0,
    max_field: float = 1,
    field: str = "E",
    cmap: Colormap | None = None,
    conv: float = 1,
) -> None:
    """
    Add a wall segment to an axes.

    Parameters
    ----------
    seg : WallSegment
        Parsed wall segment, as returned by
        :func:`superfish.parsers.parse_sfo_segment`.
    ax : matplotlib.axes.Axes
        Axes to draw on.
    perp_scale : float
        If > 0, the field strength is drawn as perpendicular lines of this
        maximum length.
    max_field : float
        Maximum field value, used to normalize the perpendicular line
        lengths and colors.
    field : str
        Wall field column to draw, e.g. ``"E"`` or ``"H"``.
    cmap : matplotlib.colors.Colormap, optional
        Color map for the perpendicular lines. Defaults to
        :func:`get_cmap0`.
    conv : float
        Unit conversion factor used by Superfish.
    """

    x = seg["wall"]["Z"] * conv
    y = seg["wall"]["R"] * conv

    # Wall segment
    ax.plot(x, y, color="black")

    if perp_scale:
        # Fetch the field
        F = seg["wall"][field] / max_field  # field, E or B

        scales = perp_scale * F[:-1]

        px, py = perp(x, y, scale=scales)

        if not cmap:
            cmap = get_cmap0()

        color = cmap(F[:-1])

        # Draw perp lines
        for i in range(len(px)):
            ax.plot(px[i, :], py[i, :], color=color[i])


def plot_wall(
    wall_segments: list[WallSegment],
    perp_scale: float = 0,
    field: str = "E",
    max_field: float | None = None,
    cmap: Colormap | None = None,
    ax: Axes | None = None,
    conv: float = 1,
    return_figure: bool = False,
    **kwargs: Any,
) -> Figure | None:
    """
    Plot the wall from wall segments.

    TODO: this is only for FISH problems so far

    Parameters
    ----------
    wall_segments : list of WallSegment
        Parsed wall segments, as returned in the ``wall_segments`` key of
        :func:`superfish.parsers.parse_sfo`.
    perp_scale : float
        If > 0, the field is plotted as perpendicular lines along the wall.
    field : str
        Wall field column to plot, e.g. ``"E"`` or ``"H"``.
    max_field : float, optional
        Maximum field for normalization. Defaults to the maximum over all
        segments.
    cmap : matplotlib.colors.Colormap, optional
        Color map for the field lines. Defaults to ``plasma``.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on. If not given, a new figure is created.
    conv : float
        Conversion factor to internal units (cm).
    return_figure : bool
        Return the figure object.
    **kwargs
        Passed to ``plt.subplots`` when creating a new figure.

    Returns
    -------
    matplotlib.figure.Figure or None
        The figure, if ``return_figure`` is True.
    """

    if not ax:
        fig, ax = plt.subplots(**kwargs)

    if not cmap:
        cmap = plt.get_cmap("plasma")

    if perp_scale and not max_field:
        max_field = np.array([seg["wall"][field].max() for seg in wall_segments]).max()
    else:
        max_field = 0

    for seg in wall_segments:
        add_wall_segment_to_axes(
            seg,
            ax,
            perp_scale=perp_scale,
            field=field,
            max_field=max_field,
            cmap=cmap,
            conv=conv,
        )

    # Labels and units
    units = wall_segments[0]["units"]

    ax.set_aspect("equal")
    if conv == 1:
        ax.set_xlabel("z " + units["Z"])
        ax.set_ylabel("r " + units["R"])

    else:
        ax.set_xlabel("z (cm)")
        ax.set_ylabel("r (cm)")

    if perp_scale == 0:
        if return_figure:
            return fig
        else:
            return

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)

    # Legend units
    field_unit = units[field]

    # Tweak for convenience
    if field_unit == "(V/m)" and max_field > 1e6:
        sc = 1e-6
        field_unit = "(MV/m)"
    elif field_unit == "(V/cm)" and max_field > 1e4:
        sc = 1e-4
        field_unit = "(MV/m)"

    else:
        sc = 1

    # Add legend
    norm = matplotlib.colors.Normalize(vmin=0, vmax=max_field * sc)
    fig.colorbar(
        matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="vertical",
        label=f"|{field}| max {field_unit}",
    )

    if return_figure:
        return fig


# plot_wall(SF.output['sfo']['wall_segments'], perp_scale=0, field='H', figsize=(20,8))
