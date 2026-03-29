"""
Workflow diagram generator using matplotlib.

Generates a professional multi-cluster flowchart matching the Fruition proposal style.
Produces PNG bytes suitable for embedding in a DOCX via python-docx add_picture().
"""
from __future__ import annotations

import io
import textwrap
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ── Colour palette ────────────────────────────────────────────────────────────
_PURPLE = "#5B2D8F"
_PURPLE_MID = "#7B4DAF"
_PURPLE_LIGHT = "#E8E0F0"
_GREEN = "#9CD326"
_ORANGE = "#F5A623"
_ORANGE_DARK = "#E65100"
_BLUE = "#2196F3"
_BLUE_LIGHT = "#E3F2FD"
_DARK = "#2D2D2D"
_WHITE = "#FFFFFF"
_GREY = "#7F7F7F"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wrap(text: str, width: int = 18) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def _rounded_box(
    ax: plt.Axes,
    x: float, y: float, w: float, h: float,
    facecolor: str,
    edgecolor: str = _WHITE,
    text: str = "",
    fontsize: float = 8.5,
    fontcolor: str = _WHITE,
    bold: bool = True,
    lw: float = 1.5,
) -> None:
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.08",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=lw,
        zorder=2,
    )
    ax.add_patch(box)
    if text:
        ax.text(
            x + w / 2, y + h / 2,
            _wrap(text, max(8, int(w * 5.5))),
            ha="center", va="center",
            fontsize=fontsize,
            color=fontcolor,
            fontweight="bold" if bold else "normal",
            multialignment="center",
            zorder=3,
        )


def _cluster_box(
    ax: plt.Axes,
    x: float, y: float, w: float, h: float,
    facecolor: str, edgecolor: str,
    label: str = "",
) -> None:
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.12",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=1.8,
        linestyle="--",
        alpha=0.25,
        zorder=1,
    )
    ax.add_patch(box)
    if label:
        ax.text(
            x + w / 2, y + h - 0.05,
            label,
            ha="center", va="top",
            fontsize=7.5,
            color=edgecolor,
            fontstyle="italic",
            fontweight="bold",
            zorder=3,
        )


def _simple_arrow(
    ax: plt.Axes,
    x1: float, y1: float,
    x2: float, y2: float,
    color: str = _PURPLE,
    label: str = "",
) -> None:
    """Draw a straight arrow using ax.annotate with arc3 (always works)."""
    ax.annotate(
        "",
        xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="->",
            color=color,
            lw=1.8,
            connectionstyle="arc3,rad=0",
        ),
        zorder=4,
    )
    if label:
        mx = (x1 + x2) / 2 + 0.15
        my = (y1 + y2) / 2
        ax.text(mx, my, label, fontsize=7, color=color, zorder=5,
                ha="left", va="center")


def _bent_arrow(
    ax: plt.Axes,
    x1: float, y1: float,
    x2: float, y2: float,
    color: str = _PURPLE,
    label: str = "",
) -> None:
    """Draw an L-shaped arrow using a line + arrow annotation."""
    # Draw elbow: vertical then horizontal (or vice versa)
    # Path: (x1,y1) → (x1, y2) → (x2, y2)
    ax.plot([x1, x1, x2], [y1, y2, y2], color=color, lw=1.8, zorder=4)
    ax.annotate(
        "",
        xy=(x2, y2), xytext=(x1, y2),
        arrowprops=dict(arrowstyle="->", color=color, lw=1.8),
        zorder=4,
    )
    if label:
        ax.text(x1 + 0.15, (y1 + y2) / 2, label, fontsize=7, color=color, zorder=5)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_workflow_diagram(spec: dict[str, Any]) -> bytes:
    """
    Generate a workflow diagram PNG from a specification dict.

    Expected spec keys:
        sources        list[str]   - Input source labels (top row)
        pipeline_title str         - Label for the main CRM/pipeline cluster
        pipeline_stages list[str]  - Sequential stages inside the pipeline (4-6)
        external_system str        - External system name ("" if none)
        external_label  str        - Brief label for external system role
        post_stages    list[str]   - Post-pipeline features/activities (3-4)
        reporting      list[str]   - Dashboard/reporting outputs (3 items)
        caption        str         - Caption line shown below the diagram

    Returns PNG image bytes.
    """
    sources: list[str] = spec.get("sources", [])
    pipeline_title: str = spec.get("pipeline_title", "Main Workflow")
    pipeline_stages: list[str] = spec.get("pipeline_stages", [])
    external_system: str = spec.get("external_system", "")
    external_label: str = spec.get("external_label", "Source of Truth")
    post_stages: list[str] = spec.get("post_stages", [])
    reporting: list[str] = spec.get("reporting", [])
    caption: str = spec.get("caption", "")

    # ── Canvas ────────────────────────────────────────────────────────────────
    fig_w, fig_h = 14.0, 9.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_facecolor(_WHITE)
    fig.patch.set_facecolor(_WHITE)

    # ── Layout constants ──────────────────────────────────────────────────────
    BOX_W_SRC = 3.0
    BOX_H_SRC = 0.58
    SRC_GAP = 0.35
    PIPE_X = 1.0
    PIPE_W = 3.8
    STAGE_H = 0.60
    STAGE_GAP = 0.14
    POST_X = 7.5
    POST_W = 3.8

    # ── Sources row (top) ─────────────────────────────────────────────────────
    pipe_start_y = 7.2  # top of pipeline cluster
    if sources:
        n = len(sources)
        total_src_w = n * BOX_W_SRC + (n - 1) * SRC_GAP
        src_x0 = (fig_w - total_src_w) / 2
        src_top = 8.8 - BOX_H_SRC

        _cluster_box(
            ax,
            src_x0 - 0.4, src_top - 0.35,
            total_src_w + 0.8, BOX_H_SRC + 0.6,
            _PURPLE_LIGHT, _PURPLE,
            label="Lead Sources",
        )
        for i, src in enumerate(sources):
            sx = src_x0 + i * (BOX_W_SRC + SRC_GAP)
            _rounded_box(ax, sx, src_top, BOX_W_SRC, BOX_H_SRC, _PURPLE, text=src, fontsize=8)

        # Arrow: source cluster centre → pipeline top
        src_center_x = src_x0 + total_src_w / 2
        _simple_arrow(ax, src_center_x, src_top, PIPE_X + PIPE_W / 2, pipe_start_y)

    # ── Pipeline stages (left column, vertical flow) ──────────────────────────
    n_stages = len(pipeline_stages)
    pipe_total_h = n_stages * STAGE_H + max(0, n_stages - 1) * STAGE_GAP
    pipe_bottom_y = pipe_start_y - pipe_total_h

    _cluster_box(
        ax,
        PIPE_X - 0.35, pipe_bottom_y - 0.45,
        PIPE_W + 0.7, pipe_total_h + 0.75,
        "#5B2D8F", _PURPLE,
        label=pipeline_title,
    )

    stage_y_list: list[float] = []
    for i, stage in enumerate(pipeline_stages):
        sy = pipe_start_y - i * (STAGE_H + STAGE_GAP) - STAGE_H
        stage_y_list.append(sy)
        fc = _GREEN if i == n_stages - 1 else _PURPLE_MID
        tc = _DARK if i == n_stages - 1 else _WHITE
        _rounded_box(ax, PIPE_X, sy, PIPE_W, STAGE_H, fc, text=stage, fontsize=8.5, fontcolor=tc)
        if i < n_stages - 1:
            _simple_arrow(
                ax,
                PIPE_X + PIPE_W / 2, sy,
                PIPE_X + PIPE_W / 2, sy - STAGE_GAP,
            )

    pipe_last_y = stage_y_list[-1] if stage_y_list else pipe_bottom_y
    pipe_center_x = PIPE_X + PIPE_W / 2
    pipe_mid_y = pipe_start_y - pipe_total_h / 2

    # ── External system (bottom-left) ─────────────────────────────────────────
    if external_system:
        ext_x = 0.3
        ext_box_h = 0.52
        ext_total = 2 * ext_box_h + 0.12
        ext_y_top = pipe_last_y - 1.5
        ext_y_bot = ext_y_top - ext_box_h - 0.12

        _cluster_box(
            ax,
            ext_x - 0.25, ext_y_bot - 0.3,
            3.0, ext_total + 0.6,
            "#FFF3E0", _ORANGE,
            label=external_system,
        )
        _rounded_box(ax, ext_x, ext_y_top, 2.5, ext_box_h,
                     _ORANGE, text="One-Way Sync", fontsize=8)
        _rounded_box(ax, ext_x, ext_y_bot, 2.5, ext_box_h,
                     _ORANGE_DARK, text=external_label, fontsize=8)

        # L-shaped arrow: pipeline last stage → external system
        _bent_arrow(
            ax,
            pipe_center_x, pipe_last_y,
            ext_x + 1.25, ext_y_top + ext_box_h,
            color=_ORANGE,
            label="One-Way\nSync",
        )

    # ── Post-pipeline column (right) ──────────────────────────────────────────
    if post_stages:
        n_post = len(post_stages)
        post_stage_h = 0.56
        post_gap = 0.14
        post_total_h = n_post * post_stage_h + max(0, n_post - 1) * post_gap
        post_top = pipe_start_y
        post_bottom = post_top - post_total_h

        _cluster_box(
            ax,
            POST_X - 0.35, post_bottom - 0.45,
            POST_W + 0.7, post_total_h + 0.75,
            _BLUE_LIGHT, _BLUE,
            label="Post-Implementation Operations",
        )
        for i, ps in enumerate(post_stages):
            sy = post_top - i * (post_stage_h + post_gap) - post_stage_h
            _rounded_box(ax, POST_X, sy, POST_W, post_stage_h, _BLUE, text=ps, fontsize=8.5)

        # Horizontal arrow: pipeline right edge → post-pipeline left edge
        # Drawn at mid-height of pipeline
        _simple_arrow(
            ax,
            PIPE_X + PIPE_W, pipe_mid_y,
            POST_X, post_top - post_total_h / 2,
        )
        ax.text(
            PIPE_X + PIPE_W + 0.15, pipe_mid_y + 0.12,
            "Activated",
            fontsize=7, color=_BLUE, zorder=5,
        )

        # ── Dashboards & Reporting (bottom-right) ─────────────────────────────
        if reporting:
            n_rep = len(reporting)
            rep_h = 0.50
            rep_gap = 0.12
            rep_total_h = n_rep * rep_h + max(0, n_rep - 1) * rep_gap
            rep_top = post_bottom - 1.25
            rep_bottom = rep_top - rep_total_h

            _cluster_box(
                ax,
                POST_X - 0.35, rep_bottom - 0.3,
                POST_W + 0.7, rep_total_h + 0.6,
                _PURPLE_LIGHT, _PURPLE,
                label="Dashboards & Reporting",
            )
            for i, rep in enumerate(reporting):
                ry = rep_top - i * (rep_h + rep_gap) - rep_h
                _rounded_box(
                    ax, POST_X, ry, POST_W, rep_h,
                    _PURPLE_LIGHT, edgecolor=_PURPLE,
                    text=rep, fontsize=8.5, fontcolor=_DARK, bold=False,
                )

            rep_center_x = POST_X + POST_W / 2
            _simple_arrow(ax, rep_center_x, post_bottom, rep_center_x, rep_top)

    # ── Caption ───────────────────────────────────────────────────────────────
    if caption:
        ax.text(
            fig_w / 2, 0.18,
            "\n".join(textwrap.wrap(caption, width=100)),
            ha="center", va="bottom",
            fontsize=8, color=_GREY,
            fontstyle="italic",
            multialignment="center",
            zorder=5,
        )

    # ── Export ────────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=_WHITE, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_fallback_diagram(stages: list[str]) -> bytes:
    """Simple horizontal flow for when no spec is available."""
    if not stages:
        stages = ["Discovery", "Design", "Build", "Testing", "Go-Live"]

    n = len(stages)
    fig_w = max(10.0, n * 2.2 + 1.0)
    fig, ax = plt.subplots(figsize=(fig_w, 2.5))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, 2.5)
    ax.axis("off")
    ax.set_facecolor(_WHITE)
    fig.patch.set_facecolor(_WHITE)

    box_w = 1.8
    box_h = 0.9
    gap = 0.4
    start_x = (fig_w - (n * box_w + (n - 1) * gap)) / 2
    y = 0.75

    for i, stage in enumerate(stages):
        x = start_x + i * (box_w + gap)
        fc = _GREEN if i == n - 1 else _PURPLE
        tc = _DARK if i == n - 1 else _WHITE
        _rounded_box(ax, x, y, box_w, box_h, fc, text=stage, fontsize=9, fontcolor=tc)
        if i < n - 1:
            _simple_arrow(ax, x + box_w, y + box_h / 2, x + box_w + gap, y + box_h / 2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=_WHITE, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
