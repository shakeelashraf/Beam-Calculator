"""
Cross-section diagram renderer using matplotlib — returns a Figure
for embedding in the Streamlit app.

Uses a fixed virtual canvas with controlled, CAD-style scaling (rather
than relying on matplotlib's automatic equal-aspect whitespace behavior),
so the rendered beam resizes smoothly and predictably as bw/h/bf/hf change,
and dimension lines/labels always have guaranteed clearance regardless of
beam proportions.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

# Fixed virtual canvas (arbitrary units) — aspect ratio matches the figsize
# below exactly, so set_aspect('equal') fills the figure with no surprise
# whitespace letterboxing/pillarboxing as beam proportions change.
CANVAS_W, CANVAS_H = 420, 560
FIGSIZE = (4.2, 5.6)

# Fixed margins reserved around the drawn section, in canvas units.
# These never change regardless of beam size, so dimension lines/labels
# always have the same guaranteed clearance.
MARGIN_LEFT   = 55
MARGIN_RIGHT  = 80
MARGIN_TOP    = 25
MARGIN_BOTTOM = 95


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

    CONCRETE  = "#D1CBC0"
    CONCRETE_O= "#A89F93"
    STEEL     = "#1E293B"
    STEEL_TOP = "#7C3AED"
    STIRRUP_C = "#475569"
    COMP_COL  = "#93C5FD"
    NA_COL    = "#EF4444"

    # ── Controlled scale: fit the section into the fixed drawable area ──────
    outer_w = b if is_T else bw
    drawable_w = CANVAS_W - MARGIN_LEFT - MARGIN_RIGHT
    drawable_h = CANVAS_H - MARGIN_TOP - MARGIN_BOTTOM
    scale = min(drawable_w/outer_w, drawable_h/h)

    sec_w = outer_w*scale
    sec_h = h*scale
    # Origin: bottom-left of the OUTER bounding box (flange width for T-beams),
    # centered within the drawable area.
    ox = MARGIN_LEFT + (drawable_w - sec_w)/2
    oy = MARGIN_BOTTOM + (drawable_h - sec_h)/2

    def sx(mm):  return ox + mm*scale          # x measured from left edge of outer box
    def sy(mm):  return oy + mm*scale          # y measured from bottom of section

    web_ox_mm = (b - bw)/2 if is_T else 0       # web left edge, in mm, from outer-box left
    web_left  = sx(web_ox_mm)
    web_right = sx(web_ox_mm + bw)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(0, CANVAS_W)
    ax.set_ylim(0, CANVAS_H)

    # ── Concrete outline — single connected polygon for T-beams ────────────
    # (avoids a double-edge artifact at the flange/web junction that two
    # separate overlapping rectangles can produce)
    if is_T:
        flange_top    = sy(h)
        flange_bottom = sy(h-hf)
        verts = [
            (sx(0),           flange_top),
            (sx(b),           flange_top),
            (sx(b),           flange_bottom),
            (web_right,       flange_bottom),
            (web_right,       sy(0)),
            (web_left,        sy(0)),
            (web_left,        flange_bottom),
            (sx(0),           flange_bottom),
            (sx(0),           flange_top),
        ]
        poly = patches.Polygon(verts, closed=True, facecolor=CONCRETE,
                               edgecolor=CONCRETE_O, linewidth=1.5, joinstyle="miter")
        ax.add_patch(poly)
    else:
        ax.add_patch(patches.Rectangle((web_left, sy(0)), sec_w, sec_h,
                     facecolor=CONCRETE, edgecolor=CONCRETE_O, linewidth=1.5))

    # ── Stirrups ──────────────────────────────────────────────────────────
    n_legs = int(params.get("n_legs", 2))
    if Av > 0:
        inset = cover*scale
        ax.add_patch(patches.Rectangle(
            (web_left+inset, sy(cover)), bw*scale-2*inset, (h-2*cover)*scale,
            facecolor="none", edgecolor=STIRRUP_C, linewidth=2.0))

        extra_legs = n_legs - 2
        if extra_legs > 0:
            inner_left  = web_left + inset
            inner_right = web_right - inset
            n_gaps = extra_legs + 1
            for i in range(1, n_gaps):
                x = inner_left + i*(inner_right-inner_left)/n_gaps
                ax.plot([x, x], [sy(cover), sy(h-cover)],
                       color=STIRRUP_C, linewidth=1.8, solid_capstyle="butt")

    # ── Stress block + N.A. ───────────────────────────────────────────────
    na_label = None
    if results and results.get("a"):
        a_mm = results["a"]; c_mm = results["c"]
        if is_T and a_mm > hf:
            ax.add_patch(patches.Rectangle((sx(0), sy(h-hf)), sec_w, hf*scale,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
            ax.add_patch(patches.Rectangle((web_left, sy(h-a_mm)), bw*scale, (a_mm-hf)*scale,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
        elif is_T and a_mm <= hf:
            ax.add_patch(patches.Rectangle((sx(0), sy(h-a_mm)), sec_w, a_mm*scale,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
        else:
            ax.add_patch(patches.Rectangle((web_left, sy(h-a_mm)), sec_w, a_mm*scale,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))

        na_y = sy(h-c_mm)
        right_edge = sx(b) if is_T else web_right
        ax.plot([web_left-6, right_edge+6], [na_y, na_y],
               color=NA_COL, linestyle="--", linewidth=1.3)
        # Short inline marker only — full "c=XXmm" detail goes in the legend
        # below to avoid clipping/crowding near the canvas edge.
        ax.text(right_edge+9, na_y, "N.A.", color=NA_COL, fontsize=7.5,
               fontweight="bold", va="center", ha="left")
        na_label = f"Neutral axis depth   c = {c_mm:.0f} mm"

    # ── Bars (circles only — labels handled in the legend below) ──────────
    def draw_bars(n_bars, db, depth_from_top, color):
        if n_bars <= 0: return
        y = sy(h - depth_from_top)
        r_mm = db/2
        inner_left  = web_ox_mm + cover + dv_b + r_mm
        inner_right = web_ox_mm + bw - cover - dv_b - r_mm
        if n_bars == 1:
            xs_mm = [(inner_left+inner_right)/2]
        else:
            xs_mm = [inner_left + i*(inner_right-inner_left)/(n_bars-1) for i in range(n_bars)]
        r_scaled = max(r_mm*scale, 2.2)
        for x_mm in xs_mm:
            ax.add_patch(patches.Circle((sx(x_mm), y), r_scaled, facecolor=color,
                         edgecolor="white", linewidth=0.7, zorder=5))

    if nb_top > 0:
        draw_bars(nb_top, db_top, d_top, STEEL_TOP)
    if nb2 > 0 and d2 > 0:
        draw_bars(nb2, db2, d2, STEEL)
    draw_bars(nb1, db1, d1, STEEL)

    # ── Dimension lines ──────────────────────────────────────────────────────
    # h — vertical, to the right of the section. Arrow and label kept apart
    # by a fixed canvas-unit gap so they never touch regardless of scale.
    h_dim_x = sx(b if is_T else bw) + 22
    ax.annotate("", xy=(h_dim_x, sy(0)), xytext=(h_dim_x, sy(h)),
               arrowprops=dict(arrowstyle="<->", color="#374151", lw=1))
    ax.text(h_dim_x+10, (sy(0)+sy(h))/2, f"h = {h:.0f}", rotation=90,
           va="center", ha="left", fontsize=8, color="#374151")

    # bw — horizontal, directly below the web only, close to the section.
    bw_dim_y = sy(0) - 16
    ax.annotate("", xy=(web_left, bw_dim_y), xytext=(web_right, bw_dim_y),
               arrowprops=dict(arrowstyle="<->", color="#374151", lw=1))
    ax.text((web_left+web_right)/2, bw_dim_y-13, f"bw = {bw:.0f}",
           ha="center", va="top", fontsize=8, color="#374151")

    # bf — horizontal, full flange width, placed well below bw's label
    # (generous fixed gap — never overlaps regardless of beam size).
    if is_T:
        bf_dim_y = bw_dim_y - 34
        ax.annotate("", xy=(sx(0), bf_dim_y), xytext=(sx(b), bf_dim_y),
                   arrowprops=dict(arrowstyle="<->", color="#64748B", lw=0.9))
        ax.text((sx(0)+sx(b))/2, bf_dim_y-13, f"bf = {b:.0f}",
               ha="center", va="top", fontsize=7.5, color="#64748B")

    # ── Legend — figure-fraction coordinates, independent of beam scale ────
    # (keeps spacing consistent for any beam geometry, including wide
    # T-beams where the drawing scale itself is heavily compressed)
    legend_entries = []
    if na_label:
        legend_entries.append((NA_COL, na_label))
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
    line_frac = 0.032
    bottom_margin = 0.06 + n_lines*line_frac
    fig.subplots_adjust(bottom=bottom_margin, top=0.97, left=0.02, right=0.98)

    for i, (color, text) in enumerate(legend_entries):
        y_frac = bottom_margin - 0.025 - i*line_frac
        fig.text(0.04, y_frac, "\u25A0", color=color, fontsize=9,
                 fontweight="bold", va="center", ha="left", transform=fig.transFigure)
        fig.text(0.075, y_frac, text, color=color, fontsize=8,
                 fontweight="bold", va="center", ha="left", transform=fig.transFigure)

    return fig


def _bar_name(db):
    REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
                   "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}
    for k,v in REBAR_SIZES.items():
        if abs(v-db) < 0.5: return k
    return f"\u2300{db:.1f}"
