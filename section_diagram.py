"""
Cross-section diagram renderer using matplotlib — returns a Figure
for embedding in the Streamlit app.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math


def draw_section(params, results=None):
    """
    Draws the beam cross-section: concrete outline, stirrups, bar layers,
    stress block and neutral axis (if results provided).
    Returns a matplotlib Figure.
    """
    bw    = params["bw"]
    h     = params["h"]
    cover = params.get("cover", 40)
    bf    = params.get("bf", 0)
    b     = bf if bf > bw else bw
    hf    = params.get("hf", 0)
    dv_b  = params.get("dv_bar", 11.3)
    Av    = params.get("Av", 0)
    is_T  = (b > bw) and (hf > 0)

    nb1, db1 = int(params.get("nb1", 4)), params.get("db1", 19.5)
    nb2, db2 = int(params.get("nb2", 0)), params.get("db2", 19.5)
    nb_top, db_top = int(params.get("nb_top", 0)), params.get("db_top", 19.5)
    d1 = params.get("d1", h - cover - dv_b - db1/2)
    d2 = params.get("d2", 0)
    d_top = params.get("d_top", cover + dv_b + db_top/2)

    fig, ax = plt.subplots(figsize=(4.2, 5.4))
    ax.set_aspect("equal")
    ax.axis("off")

    CONCRETE  = "#D1CBC0"
    CONCRETE_O= "#A89F93"
    STEEL     = "#1E293B"
    STEEL_TOP = "#7C3AED"
    STIRRUP_C = "#475569"
    COMP_COL  = "#93C5FD"
    NA_COL    = "#EF4444"

    web_ox = (b - bw) / 2 if is_T else 0

    # ── Concrete outline ──────────────────────────────────────────────────
    if is_T:
        ax.add_patch(patches.Rectangle((0, h-hf), b, hf,
                     facecolor=CONCRETE, edgecolor=CONCRETE_O, linewidth=1.5))
        ax.add_patch(patches.Rectangle((web_ox, 0), bw, h-hf,
                     facecolor=CONCRETE, edgecolor=CONCRETE_O, linewidth=1.5))
    else:
        ax.add_patch(patches.Rectangle((0, 0), bw, h,
                     facecolor=CONCRETE, edgecolor=CONCRETE_O, linewidth=1.5))

    # ── Stirrups ──────────────────────────────────────────────────────────
    n_legs = int(params.get("n_legs", 2))
    if Av > 0:
        # Outer closed stirrup (always drawn — accounts for 2 legs)
        ax.add_patch(patches.Rectangle(
            (web_ox+cover, cover), bw-2*cover, h-2*cover,
            facecolor="none", edgecolor=STIRRUP_C, linewidth=2.2))

        # Additional interior legs (for n_legs > 2) — evenly spaced
        # vertical ties between the top and bottom of the stirrup
        extra_legs = n_legs - 2
        if extra_legs > 0:
            inner_left  = web_ox + cover
            inner_right = web_ox + bw - cover
            # Evenly space the extra verticals between the two outer legs
            n_gaps = extra_legs + 1
            for i in range(1, n_gaps):
                x = inner_left + i * (inner_right - inner_left) / n_gaps
                ax.plot([x, x], [cover, h-cover],
                       color=STIRRUP_C, linewidth=2.0, solid_capstyle="butt")
        # Leg count label is added after all dimension lines are placed (see below)

    # ── Stress block + N.A. ───────────────────────────────────────────────
    section_right = b if is_T else bw   # rightmost edge of full section
    if results and results.get("a"):
        a_mm = results["a"]; c_mm = results["c"]
        if is_T and a_mm > hf:
            # N.A. in web: flange portion spans full flange width (depth hf),
            # web portion below spans web width only (depth a_mm - hf)
            ax.add_patch(patches.Rectangle((0, h-hf), b, hf,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
            ax.add_patch(patches.Rectangle((web_ox, h-a_mm), bw, a_mm-hf,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
        elif is_T and a_mm <= hf:
            # N.A. within the flange: full flange width only
            ax.add_patch(patches.Rectangle((0, h-a_mm), b, a_mm,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
        else:
            # Rectangular section
            ax.add_patch(patches.Rectangle((0, h-a_mm), bw, a_mm,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))

        # N.A. dashed line — spans the full section width with a small margin
        ax.plot([-8, section_right+8], [h-c_mm, h-c_mm],
               color=NA_COL, linestyle="--", linewidth=1.4)
        ax.text(section_right+12, h-c_mm, f"N.A.  c={c_mm:.0f}mm",
               color=NA_COL, fontsize=8, fontweight="bold", va="center")

    def draw_bars(n_bars, db, depth_from_top, color):
        """Draws bar circles only — labels are handled separately in the
        legend stack below, to avoid collisions when multiple layers or
        stirrup labels sit close together near the bottom of the section."""
        if n_bars <= 0: return
        y = h - depth_from_top
        inner_left  = web_ox + cover + dv_b + db/2
        inner_right = web_ox + bw - cover - dv_b - db/2
        if n_bars == 1:
            xs = [(inner_left+inner_right)/2]
        else:
            xs = [inner_left + i*(inner_right-inner_left)/(n_bars-1) for i in range(n_bars)]
        for x in xs:
            ax.add_patch(patches.Circle((x, y), db/2, facecolor=color,
                         edgecolor="white", linewidth=0.8, zorder=5))

    if nb_top > 0:
        draw_bars(nb_top, db_top, d_top, STEEL_TOP)
    if nb2 > 0 and d2 > 0:
        draw_bars(nb2, db2, d2, STEEL)
    draw_bars(nb1, db1, d1, STEEL)

    # ── Dimensions ────────────────────────────────────────────────────────
    ax.annotate("", xy=(section_right+28, 0), xytext=(section_right+28, h),
               arrowprops=dict(arrowstyle="<->", color="#374151", lw=1))
    ax.text(section_right+34, h/2, f"h={h:.0f}", rotation=90, va="center",
           fontsize=8, color="#374151")

    ax.annotate("", xy=(web_ox, -22), xytext=(web_ox+bw, -22),
               arrowprops=dict(arrowstyle="<->", color="#374151", lw=1))
    ax.text(web_ox+bw/2, -34, f"bw={bw:.0f}", ha="center",
           fontsize=8, color="#374151")

    lowest_dim_y = -34
    if is_T:
        ax.annotate("", xy=(0, -50), xytext=(b, -50),
                   arrowprops=dict(arrowstyle="<->", color="#64748B", lw=0.8))
        ax.text(b/2, -62, f"bf={b:.0f}", ha="center", fontsize=7.5, color="#64748B")
        lowest_dim_y = -62

    pad_x = max(85, b*0.18); pad_y_top = 40
    pad_y_bot = abs(lowest_dim_y) + 25
    ax.set_xlim(-pad_x, section_right + pad_x + 50)
    ax.set_ylim(-pad_y_bot, h + pad_y_top)

    # ── Legend stack — figure-fraction coordinates ──────────────────────────
    # Placed using fig.text() with transform=fig.transFigure rather than
    # data/axes coordinates. This is essential for T-beams: a wide flange
    # forces set_aspect('equal') to compress the rendered scale heavily,
    # which would otherwise squeeze data-coordinate text into overlapping
    # rows even though their Y-values are far apart. Figure-fraction
    # coordinates are completely independent of the data's aspect ratio,
    # so legend spacing stays consistent and readable for any beam geometry.
    legend_entries = []
    if nb_top > 0:
        legend_entries.append((STEEL_TOP,
            f"{nb_top}\u2013{_bar_name(db_top)} top   As'={nb_top*math.pi*(db_top/2)**2:.0f}mm\u00b2"))
    if nb2 > 0 and d2 > 0:
        legend_entries.append((STEEL,
            f"{nb2}\u2013{_bar_name(db2)} (layer 2)   As2={nb2*math.pi*(db2/2)**2:.0f}mm\u00b2"))
    legend_entries.append((STEEL,
        f"{nb1}\u2013{_bar_name(db1)} (layer 1)   As1={nb1*math.pi*(db1/2)**2:.0f}mm\u00b2"))
    if Av > 0:
        legend_entries.append((STIRRUP_C,
            f"{n_legs}-leg stirrups @ {params.get('s',0):.0f}mm"))

    n_lines = len(legend_entries)
    line_frac = 0.032               # vertical spacing per line, in figure fraction
    bottom_margin = 0.06 + n_lines*line_frac

    # Reserve bottom margin for the legend block (overrides tight_layout)
    fig.subplots_adjust(bottom=bottom_margin, top=0.97, left=0.02, right=0.98)

    for i, (color, text) in enumerate(legend_entries):
        y_frac = bottom_margin - 0.025 - i*line_frac
        fig.text(0.04, y_frac, "\u25A0", color=color, fontsize=9,
                 fontweight="bold", va="center", ha="left",
                 transform=fig.transFigure)
        fig.text(0.075, y_frac, text, color=color, fontsize=8,
                 fontweight="bold", va="center", ha="left",
                 transform=fig.transFigure)

    return fig


def _bar_name(db):
    REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
                   "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}
    for k,v in REBAR_SIZES.items():
        if abs(v-db) < 0.5: return k
    return f"\u2300{db:.1f}"
