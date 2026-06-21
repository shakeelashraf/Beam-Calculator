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
    if results and results.get("a"):
        a_mm = results["a"]; c_mm = results["c"]
        if a_mm <= hf and is_T:
            ax.add_patch(patches.Rectangle((0, h-a_mm), b, a_mm,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
        else:
            sb_x = 0 if not is_T else web_ox
            sb_w = bw if is_T else bw
            sb_x = 0 if not is_T else 0
            ax.add_patch(patches.Rectangle((0, h-a_mm), (b if (is_T and a_mm<=hf) else bw), a_mm,
                         facecolor=COMP_COL, alpha=0.55, edgecolor="none"))
        ax.axhline(y=h-c_mm, color=NA_COL, linestyle="--", linewidth=1.4,
                   xmin=(web_ox-10)/ (b+20) if is_T else 0, xmax=1)
        ax.plot([web_ox-8, web_ox+bw+8], [h-c_mm, h-c_mm],
               color=NA_COL, linestyle="--", linewidth=1.4)
        ax.text(web_ox+bw+12, h-c_mm, f"N.A.  c={c_mm:.0f}mm",
               color=NA_COL, fontsize=8, fontweight="bold", va="center")

    def draw_bars(n_bars, db, depth_from_top, color, label, label_below=True):
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
        As_lbl = n_bars * math.pi*(db/2)**2
        offset = -(db/2+22) if label_below else (db/2+18)
        ax.text(bw/2 + web_ox, y+offset, f"{label}  As={As_lbl:.0f}mm\u00b2",
               color=color, fontsize=7.5, fontweight="bold", ha="center",
               bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1))

    if nb_top > 0:
        draw_bars(nb_top, db_top, d_top, STEEL_TOP,
                 f"{nb_top}\u2013{_bar_name(db_top)}", label_below=False)
    if nb2 > 0 and d2 > 0:
        draw_bars(nb2, db2, d2, STEEL, f"{nb2}\u2013{_bar_name(db2)} (L2)")
    draw_bars(nb1, db1, d1, STEEL, f"{nb1}\u2013{_bar_name(db1)} (L1)")

    # ── Dimensions ────────────────────────────────────────────────────────
    ax.annotate("", xy=(bw+web_ox+28, 0), xytext=(bw+web_ox+28, h),
               arrowprops=dict(arrowstyle="<->", color="#374151", lw=1))
    ax.text(bw+web_ox+34, h/2, f"h={h:.0f}", rotation=90, va="center",
           fontsize=8, color="#374151")

    ax.annotate("", xy=(web_ox, -22), xytext=(web_ox+bw, -22),
               arrowprops=dict(arrowstyle="<->", color="#374151", lw=1))
    ax.text(web_ox+bw/2, -34, f"bw={bw:.0f}", ha="center",
           fontsize=8, color="#374151")

    if is_T:
        ax.annotate("", xy=(0, -50), xytext=(b, -50),
                   arrowprops=dict(arrowstyle="<->", color="#64748B", lw=0.8))
        ax.text(b/2, -62, f"bf={b:.0f}", ha="center", fontsize=7.5, color="#64748B")
        leg_label_y = -76
    else:
        leg_label_y = -46

    if Av > 0:
        ax.text(web_ox+bw/2, leg_label_y, f"{n_legs}-leg stirrups @ {params.get('s',0):.0f}mm",
               color=STIRRUP_C, fontsize=7.5, ha="center", style="italic")

    pad_x = max(60, b*0.18); pad_y_top = 40
    pad_y_bot = (95 if is_T else 65)
    ax.set_xlim(-pad_x, b + pad_x + 40)
    ax.set_ylim(-pad_y_bot, h + pad_y_top)

    plt.tight_layout()
    return fig


def _bar_name(db):
    REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
                   "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}
    for k,v in REBAR_SIZES.items():
        if abs(v-db) < 0.5: return k
    return f"\u2300{db:.1f}"
