#!/usr/bin/env python3
"""netviz.py — the network diagram (no Streamlit dependency, so it's unit-testable).

Encodings: topology shape (from the verified Zollman adjacency); node size =
researchers; node fill = agreeableness (red low/anti-herd → blue high/consensus,
colourblind-safe and never gold, so the active highlight always pops); node
outline + number = institute identity (same colours as the live feed headers);
edge thickness = briefing exchanges (network rounds); inner rings = internal
rounds. Fixed-archetype mode draws each node as a Disruptor/Architect/Shield
tri-wedge. Each figure carries its own legend so screenshots are self-contained.
"""

from __future__ import annotations

import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Wedge, FancyArrowPatch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import network as net  # verified Zollman topologies

ARCH_COLORS = ["#e0574f", "#4f8fe0", "#5fbf6f"]  # Disruptor / Architect / Shield
GOLD = "#f5b301"                                  # active-node highlight
PANEL_BG = "#161a20"                              # matches the app theme's card colour
FG = "#e8eaed"                                    # light text on the dark panels

# Stable per-institute accent colours: node outline + number here, and the turn
# headers in the app's live feed. Chosen away from the red↔blue agreeableness
# fill and the gold active ring; readable on the feed's dark background.
INST_COLORS = ["#9467bd", "#17becf", "#2ca02c", "#e377c2",
               "#8c564b", "#bcbd22", "#7f7f7f", "#ff7f0e"]


def agree_color(agree):
    """Agreeableness fill: low = warm red (anti-herd), high = cool blue (consensus)."""
    return plt.cm.coolwarm(1.0 - agree / 100.0)


def _on_fill(rgba):
    """Ring/detail colour that stays visible on a given node fill (coolwarm's
    midpoint is nearly white, so white rings vanish there)."""
    lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
    return "#333333" if lum > 0.62 else "#f5f5f5"


def layout(topology, n):
    if n == 1:
        return [(0.0, 0.0)]
    if topology == "wheel":
        pts = [(0.0, 0.0)]
        for k in range(n - 1):
            a = 2 * math.pi * k / (n - 1)
            pts.append((math.cos(a), math.sin(a)))
        return pts
    if topology == "line":
        return [(-1 + 2 * i / (n - 1), 0.0) for i in range(n)]
    return [(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)]


def network_figure(topology, n, agree, size, net_rounds, inst_rounds, fixed, active=None):
    adj = net.NETWORKS[topology](n)
    pos = layout(topology, n)
    fig, ax = plt.subplots(figsize=(4.6, 4.6), dpi=150)
    fig.patch.set_facecolor(PANEL_BG)
    ax.set_facecolor(PANEL_BG)
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-2.2, 1.45)  # band below the graph for the legend
    ax.set_aspect("equal")
    ax.axis("off")

    ew = 1.0 + 2.2 * net_rounds  # edge thickness ∝ briefing exchanges
    for i in range(n):
        for j in range(i + 1, n):
            if adj[i][j]:
                ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]],
                        color="#9aa0a6", lw=ew, alpha=0.75, zorder=1, solid_capstyle="round")

    node_r = 0.11 + 0.045 * (size - 2)           # size ∝ researchers
    node_color = agree_color(agree)              # fill ∝ agreeableness
    detail = _on_fill(node_color)
    ring_fracs = [0.72, 0.50, 0.28][:max(0, inst_rounds)]  # inner rings ∝ internal rounds

    for i, (x, y) in enumerate(pos):
        accent = INST_COLORS[i % len(INST_COLORS)]
        if fixed:
            for k, col in enumerate(ARCH_COLORS):
                ax.add_patch(Wedge((x, y), node_r, 90 + k * 120, 90 + (k + 1) * 120,
                                   facecolor=col, edgecolor="#222", lw=1.0, zorder=2))
            ax.add_patch(Circle((x, y), node_r, fill=False,
                                edgecolor=accent, lw=2.2, zorder=4))
        else:
            ax.add_patch(Circle((x, y), node_r, facecolor=node_color,
                                 edgecolor=accent, lw=2.2, zorder=2))
            for f in ring_fracs:
                ax.add_patch(Circle((x, y), node_r * f, fill=False,
                                    edgecolor=detail, lw=1.3, alpha=0.9, zorder=3))
        # institute number — matches the feed headers in the app
        ax.text(x, y, str(i), ha="center", va="center", zorder=8,
                fontsize=8.5 + 1.5 * (size - 2), fontweight="bold", color="#ffffff",
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#222222")])

    # active node: gold highlight + directed report-arrows to its neighbours
    # (complete graph → arrows to everyone; sparse → arrows to neighbours only)
    if active is not None and 0 <= active < n:
        ax0, ay0 = pos[active]
        ax.add_patch(Circle((ax0, ay0), node_r * 1.4, fill=False,
                            edgecolor=GOLD, lw=3.2, zorder=6))
        for j in range(n):
            if j != active and adj[active][j]:
                x1, y1 = pos[j]
                dx, dy = x1 - ax0, y1 - ay0
                d = math.hypot(dx, dy) or 1.0
                ux, uy = dx / d, dy / d
                start = (ax0 + ux * node_r * 1.1, ay0 + uy * node_r * 1.1)
                end = (x1 - ux * node_r * 1.25, y1 - uy * node_r * 1.25)
                ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                             mutation_scale=15, color=GOLD, lw=2.2,
                             zorder=5, shrinkA=0, shrinkB=0))

    # in-figure legend, so a screenshot of the diagram explains itself
    def _dot(col, label, edge="#222", msize=11, mew=1.4):
        return Line2D([], [], marker="o", ls="", markersize=msize, markerfacecolor=col,
                      markeredgecolor=edge, markeredgewidth=mew, label=label)
    if fixed:
        handles = [_dot(c, l) for c, l in zip(ARCH_COLORS, ("Disruptor", "Architect", "Shield"))]
    else:
        handles = [_dot(agree_color(0), "low A · anti-herd"),
                   _dot(agree_color(100), "high A · consensus"),
                   _dot("none", "rings = internal rounds", edge="#666")]
    handles += [_dot("none", "active — sharing report", edge=GOLD, msize=13, mew=2.6),
                Line2D([], [], color="#9aa0a6", lw=4.5, label="edges = briefing exchanges")]
    ax.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
              fontsize=8.5, columnspacing=1.1, handletextpad=0.45, labelspacing=0.45,
              borderaxespad=0.0, labelcolor=FG)
    fig.tight_layout(pad=0.2)
    return fig


def logo_figure():
    """Three 6-node research networks — dense (complete), sparse (line, drawn as a
    zigzag path), and cycle — as a wordmark for the app header. Transparent bg."""
    fig, axes = plt.subplots(1, 3, figsize=(3.9, 1.25), dpi=200)
    fig.patch.set_alpha(0)
    zig = [(-1.15 + 2.30 * i / 5, 0.55 if i % 2 == 0 else -0.55) for i in range(6)]
    circ = layout("cycle", 6)
    for ax, (topo, pos) in zip(axes, [("complete", circ), ("line", zig), ("cycle", circ)]):
        adj = net.NETWORKS[topo](6)
        ax.set_xlim(-1.38, 1.38)
        ax.set_ylim(-1.38, 1.38)
        ax.set_aspect("equal")
        ax.axis("off")
        for i in range(6):
            for j in range(i + 1, 6):
                if adj[i][j]:
                    ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]],
                            color="#9aa0a6", lw=1.3, alpha=0.9, zorder=1,
                            solid_capstyle="round")
        for (x, y) in pos:
            ax.add_patch(Circle((x, y), 0.20, facecolor=GOLD,
                                edgecolor="#1a1a1a", lw=0.9, zorder=2))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01, wspace=0.12)
    return fig


TOPO_MARK = {"cycle": "o", "wheel": "s", "complete": "^", "line": "D"}


def compare_figure(runs):
    """Scatter final-round diversity (and correctness, if any) vs the agreeableness dial,
    across saved runs — so you can see outcomes shift as you turn the dials."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    fig.patch.set_facecolor(PANEL_BG)
    ax.set_facecolor(PANEL_BG)
    have_gt = any(r.get("corr_final") is not None for r in runs)
    ax2 = ax.twinx() if have_gt else None
    div_c, corr_c = "#e07a6b", "#6badde"  # lightened for the dark panel
    seen = set()
    for r in runs:
        mk = TOPO_MARK.get(r["topology"], "o")
        lbl = r["topology"] if r["topology"] not in seen else None
        seen.add(r["topology"])
        ax.scatter(r["A"], r["div_final"], marker=mk, s=70, c=div_c,
                   edgecolors="#222", zorder=3, label=lbl)
        if ax2 is not None and r.get("corr_final") is not None:
            ax2.scatter(r["A"], r["corr_final"], marker=mk, s=60, facecolors="none",
                        edgecolors=corr_c, linewidths=1.6, zorder=3)
    ax.set_xlabel("agreeableness dial", color=FG)
    ax.set_ylabel("diversity (bits) ●", color=div_c)
    ax.set_xlim(-5, 105)
    ax.grid(alpha=0.2)
    ax.tick_params(colors=FG)
    for sp in ax.spines.values():
        sp.set_color("#3a4450")
    if ax2 is not None:
        ax2.set_ylabel("correctness ○", color=corr_c)
        ax2.set_ylim(-0.05, 1.05)
        ax2.tick_params(colors=FG)
        for sp in ax2.spines.values():
            sp.set_color("#3a4450")
    leg = ax.legend(title="topology", fontsize=8, loc="best", labelcolor=FG,
                    facecolor=PANEL_BG, edgecolor="#3a4450")
    leg.get_title().set_color(FG)
    fig.tight_layout()
    return fig


if __name__ == "__main__":  # smoke test: render every topology to PNG
    out = pathlib.Path(__file__).resolve().parent / "_netviz_test"
    out.mkdir(exist_ok=True)
    for topo in ("cycle", "wheel", "complete", "line"):
        for fixed in (False, True):
            f = network_figure(topo, 5, 20, 4, 3, 2, fixed, active=1)
            f.savefig(out / f"{topo}_{'fixed' if fixed else 'dial'}.png", dpi=80)
            plt.close(f)
    f = network_figure("cycle", 4, 50, 3, 2, 1, False)  # pale mid-A fill, no active
    f.savefig(out / "cycle_midA.png", dpi=80)
    plt.close(f)
    f = logo_figure()
    f.savefig(out / "logo.png", transparent=True)
    plt.close(f)
    print("netviz OK — rendered", len(list(out.glob('*.png'))), "diagrams to", out)
