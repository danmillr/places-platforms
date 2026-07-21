"""Sanity-check maps for the Subspotting extraction.

Outputs:
- reception_map.png       — 4 per-carrier panels (viridis)
- reception_overview.png  — one big panel: how many carriers had reception per station
"""

from __future__ import annotations
import pathlib, json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"

CARRIER_COLORS = {
    "att":     "#067ab4",
    "tmobile": "#e20074",
    "verizon": "#ff0000",
    "sprint":  "#ffe100",
}

# Approx NYC bounds
XLIM = (-74.05, -73.70)
YLIM = (40.55, 40.92)


def load_features():
    return json.loads((DATA / "stations_reception.geojson").read_text())["features"]


def _style_ax(ax, title):
    ax.set_title(title, fontsize=11)
    ax.set_aspect(1.35)
    ax.set_xlim(*XLIM); ax.set_ylim(*YLIM)
    ax.set_facecolor("#1b1b33")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#666")


def make_per_carrier(features):
    fig, axes = plt.subplots(2, 2, figsize=(16, 18), facecolor="white")
    sc = None
    for ax, carrier in zip(axes.flat, ["att", "tmobile", "verizon", "sprint"]):
        xs = [f["geometry"]["coordinates"][0] for f in features]
        ys = [f["geometry"]["coordinates"][1] for f in features]
        vs = [f["properties"][f"{carrier}_reception_frac"] for f in features]
        vs = np.array(vs)

        # Draw all stations lightly first
        ax.scatter(xs, ys, c="#333", s=6, alpha=0.6, edgecolors="none")
        # Overlay stations with reception in the carrier's brand color
        mask = vs > 0.15
        sc = ax.scatter(
            np.array(xs)[mask], np.array(ys)[mask],
            c=vs[mask], cmap=_carrier_cmap(carrier),
            s=40, vmin=0, vmax=1, edgecolors="white", linewidths=0.3,
        )
        _style_ax(ax, f"{carrier.upper()}  ({(vs > 0.5).sum()} stations w/ majority reception)")

    cax = fig.add_axes([0.92, 0.15, 0.012, 0.7])
    cb = fig.colorbar(sc, cax=cax)
    cb.set_label("Reception fraction (0=none, 1=full)", fontsize=10)
    fig.suptitle("Subspotting 2017 — subway station cell reception by carrier",
                 fontsize=16, fontweight="bold", y=0.94)
    fig.subplots_adjust(right=0.9, top=0.9, bottom=0.04, wspace=0.03, hspace=0.08)
    out = DATA / "reception_map.png"
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor="white")
    print(f"Wrote {out}")
    plt.close(fig)


def _carrier_cmap(carrier):
    base = CARRIER_COLORS[carrier]
    return mcolors.LinearSegmentedColormap.from_list(
        f"cmap_{carrier}", ["#2a2a3a", base, "#ffffff"], N=256
    )


def make_overview(features):
    fig, ax = plt.subplots(figsize=(14, 15), facecolor="white")
    xs = [f["geometry"]["coordinates"][0] for f in features]
    ys = [f["geometry"]["coordinates"][1] for f in features]
    n = np.array([f["properties"]["n_carriers_majority"] for f in features])

    cmap = mcolors.ListedColormap(["#3a3a4a", "#e20074", "#e2a000", "#7cd200", "#00e2b8"])
    sc = ax.scatter(xs, ys, c=n, cmap=cmap, vmin=-0.5, vmax=4.5,
                    s=55, edgecolors="white", linewidths=0.4)
    _style_ax(ax, "")

    cb = fig.colorbar(sc, ax=ax, ticks=[0,1,2,3,4], shrink=0.6, pad=0.02)
    cb.set_label("# of carriers with majority reception at station", fontsize=11)
    cb.set_ticklabels(["0 (none)", "1", "2", "3", "4 (all)"])

    ax.text(-74.02, 40.90, "Bronx",     color="#bbb", fontsize=13, fontweight="bold")
    ax.text(-74.02, 40.80, "Manhattan", color="#bbb", fontsize=13, fontweight="bold")
    ax.text(-73.83, 40.75, "Queens",    color="#bbb", fontsize=13, fontweight="bold")
    ax.text(-73.98, 40.62, "Brooklyn",  color="#bbb", fontsize=13, fontweight="bold")

    fig.suptitle("Subspotting 2017 — how many carriers had reception at each subway station",
                 fontsize=15, fontweight="bold", y=0.93)
    fig.text(0.5, 0.06,
             "Circles = MTA subway stations. Colored dots = at least one carrier had signal there. "
             "Grey dots = no carrier had majority signal in the 2017 artifact. "
             "Data as of Jan 2017; Transit Wireless completed rollout across the system 2017–2021.",
             ha="center", fontsize=9, color="#333", wrap=True)
    fig.subplots_adjust(left=0.03, right=0.94, top=0.9, bottom=0.10)
    out = DATA / "reception_overview.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Wrote {out}")
    plt.close(fig)


def main():
    features = load_features()
    make_per_carrier(features)
    make_overview(features)


if __name__ == "__main__":
    main()
