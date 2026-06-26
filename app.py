"""
CSA A23.3-19 Concrete Beam Analyzer — Streamlit Web App
Flexure · Shear · Torsion · Deflection · Detailing
"""
import streamlit as st
import math
import io
import tempfile
import os

from engine import BeamAnalysis, REBAR_SIZES, REBAR_AREA, bar_name
from pdf_report import generate_report
from section_diagram import draw_section

st.set_page_config(
    page_title="CSA A23.3-19 Beam Analyzer",
    page_icon="🏗",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main > div { padding-top: 1.2rem; }
    .stMetric { background: #F8FAFC !important; border: 1px solid #E5E7EB;
                border-radius: 8px; padding: 10px; }
    /* Force readable text colors inside metric boxes regardless of
       light/dark theme — without this, dark mode inherits light text
       on the light-forced background above and the boxes look blank. */
    [data-testid="stMetric"] label,
    [data-testid="stMetricLabel"] { color: #6B7280 !important; }
    [data-testid="stMetricValue"] { color: #1E2A3A !important; }
    [data-testid="stMetricDelta"] { color: #1E2A3A !important; }
    .pass-banner { background:#DCFCE7; color:#15803D; padding:12px 18px;
                   border-radius:8px; font-weight:700; font-size:1.05rem;
                   border:1px solid #86EFAC; }
    .fail-banner { background:#FEE2E2; color:#B91C1C; padding:12px 18px;
                   border-radius:8px; font-weight:700; font-size:1.05rem;
                   border:1px solid #FCA5A5; }
    .check-pass { color:#15803D; font-weight:700; }
    .check-fail { color:#B91C1C; font-weight:700; }
    h1, h2, h3 { color:#1E2A3A; }
</style>
""", unsafe_allow_html=True)

st.title("CSA A23.3-19 Concrete Beam Analyzer")
st.caption("Flexure · Shear · Torsion · Deflection · Detailing  —  Simplified method, θ = 35°")

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — INPUTS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("Input Parameters")

    with st.expander("Materials", expanded=True):
        fc  = st.number_input("f'c — Concrete strength (MPa)", 15.0, 100.0, 30.0, 1.0)
        fy  = st.number_input("fy — Steel yield strength (MPa)", 300.0, 600.0, 400.0, 10.0)
        fyt = st.number_input("fyt — Stirrup yield strength (MPa)", 300.0, 600.0, 400.0, 10.0)

    with st.expander("Section Geometry", expanded=True):
        bw     = st.number_input("bw — Web width (mm)", 100.0, 2000.0, 300.0, 10.0)
        h      = st.number_input("h — Total depth (mm)", 150.0, 3000.0, 600.0, 10.0)
        cover  = st.number_input("Clear cover (mm)", 20.0, 100.0, 40.0, 5.0)

    with st.expander("🔲 T-Beam Flange (0 = rectangular)"):
        bf = st.number_input("bf — Flange width (mm)", 0.0, 4000.0, 0.0, 10.0)
        hf = st.number_input("hf — Flange depth (mm)", 0.0, 500.0, 0.0, 10.0)

    with st.expander("Transverse Steel (Stirrups)", expanded=True):
        n_legs    = st.number_input("Stirrup legs", 2, 8, 2, 1)
        stir_size = st.selectbox("Stirrup bar size", list(REBAR_SIZES.keys()), index=0)
        s         = st.number_input("s — Spacing (mm)", 0.0, 600.0, 200.0, 10.0)
        st.caption(f"→ Av = {n_legs*REBAR_AREA[stir_size]:.0f} mm²")

    with st.expander("Bottom Steel — Layer 1 (tension)", expanded=True):
        nb1   = st.number_input("Number of bars (Layer 1)", 1, 20, 4, 1)
        bar1  = st.selectbox("Bar size (Layer 1)", list(REBAR_SIZES.keys()), index=2)
        _dv_bar_preview = REBAR_SIZES[stir_size]
        # d1 = h - cover - stirrup diameter - bar1 diameter/2   (Cl. 7.5 geometry)
        _d1_preview = h - cover - _dv_bar_preview - REBAR_SIZES[bar1]/2
        st.caption(f"→ As1 = {nb1*REBAR_AREA[bar1]:.0f} mm²  |  d1 = {_d1_preview:.0f} mm  (auto, Cl. 7.5)")

    with st.expander("Bottom Steel — Layer 2 (0 bars = none)"):
        nb2   = st.number_input("Number of bars (Layer 2)", 0, 20, 0, 1)
        bar2  = st.selectbox("Bar size (Layer 2)", list(REBAR_SIZES.keys()), index=2)
        if nb2 > 0:
            _gap_min_preview = max(1.4*max(REBAR_SIZES[bar1], REBAR_SIZES[bar2]), 30.0)
            _d2_preview = _d1_preview - REBAR_SIZES[bar1]/2 - _gap_min_preview - REBAR_SIZES[bar2]/2
            st.caption(f"→ As2 = {nb2*REBAR_AREA[bar2]:.0f} mm²  |  d2 = {_d2_preview:.0f} mm  (auto, Cl. 7.5)")

    with st.expander("Top Steel — Compression (0 bars = none)"):
        nb_top  = st.number_input("Number of bars (Top)", 0, 20, 0, 1)
        bar_top = st.selectbox("Bar size (Top)", list(REBAR_SIZES.keys()), index=1)
        if nb_top > 0:
            st.caption(f"→ As' = {nb_top*REBAR_AREA[bar_top]:.0f} mm²")

    with st.expander("Factored Loads", expanded=True):
        Mf = st.number_input("Mf — Factored moment (kN·m)", 0.0, 10000.0, 200.0, 5.0)
        Vf = st.number_input("Vf — Factored shear (kN)", 0.0, 5000.0, 150.0, 5.0)
        Tf = st.number_input("Tf — Factored torsion (kN·m)", 0.0, 1000.0, 0.0, 1.0)

    st.markdown("---")
    analyze_clicked = st.button("ANALYZE", type="primary", use_container_width=True)


def build_params():
    db1 = REBAR_SIZES[bar1]; db2 = REBAR_SIZES[bar2]; db_top = REBAR_SIZES[bar_top]
    dv_bar = REBAR_SIZES[stir_size]
    Av = n_legs * REBAR_AREA[stir_size]
    As1 = nb1 * REBAR_AREA[bar1]
    As2 = nb2 * REBAR_AREA[bar2] if nb2 > 0 else 0
    As_top = nb_top * REBAR_AREA[bar_top] if nb_top > 0 else 0
    d_top_val = cover + dv_bar + db_top/2

    # ── Auto-calculate effective depths per CSA A23.3-19 Cl. 7.5 geometry ──
    # Layer 1 (lowest, controls cover): centroid measured from top of section
    d1_val = h - cover - dv_bar - db1/2

    # Layer 2 (above layer 1): clear vertical gap = max(1.4·max(db1,db2), 30mm)
    if nb2 > 0:
        gap_min = max(1.4*max(db1, db2), 30.0)
        d2_val = d1_val - db1/2 - gap_min - db2/2
    else:
        d2_val = 0.0

    return {
        "fc": fc, "fy": fy, "fyt": fyt,
        "bw": bw, "h": h, "cover": cover,
        "bf": bf, "hf": hf,
        "nb1": nb1, "db1": db1, "d1": d1_val,
        "nb2": nb2, "db2": db2, "d2": d2_val,
        "nb_top": nb_top, "db_top": db_top, "d_top": d_top_val,
        "As1": As1, "As2": As2, "As_top": As_top,
        "As": As1 + As2,
        "n_legs": n_legs, "dv_bar": dv_bar, "stir_size": stir_size,
        "Av": Av, "s": s,
        "Mf": Mf * 1e6, "Vf": Vf * 1e3, "Tf": Tf * 1e6,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
if "results" not in st.session_state:
    st.session_state.results = None
if "analyzed_params" not in st.session_state:
    st.session_state.analyzed_params = None

current_params = build_params()

# If the user has changed any input since the last Analyze click, the stored
# results (and diagram) are stale — clear them so the app falls back to the
# placeholder/preview view until Analyze is clicked again.
if (st.session_state.results is not None
        and st.session_state.analyzed_params is not None
        and current_params != st.session_state.analyzed_params
        and not analyze_clicked):
    st.session_state.results = None

if analyze_clicked:
    try:
        r, c, n = BeamAnalysis(current_params).run()
        st.session_state.results = (r, c, n, current_params)
        st.session_state.analyzed_params = current_params
    except Exception as e:
        st.error(f"Analysis error: {e}")
        st.session_state.results = None
        st.session_state.analyzed_params = None

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PANEL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.results is None:
    st.info("Enter parameters in the sidebar and click **ANALYZE** to begin.")
    # Show a live preview of the section as the user types
    try:
        fig = draw_section(current_params, None)
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Cross-Section Preview")
            st.pyplot(fig, use_container_width=True)
    except Exception:
        pass
else:
    r, c, n, params = st.session_state.results

    # ── Overall status banner ────────────────────────────────────────────────
    ok = r["overall_pass"]
    if ok:
        st.markdown('<div class="pass-banner">&#10003;  All Checks Passed</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="fail-banner">&#10007;  One or More Checks Failed</div>',
                    unsafe_allow_html=True)

    st.markdown("")

    col_diag, col_results = st.columns([1, 2], gap="large")

    # ── LEFT: Cross-section diagram ──────────────────────────────────────────
    with col_diag:
        st.subheader("Cross-Section")
        fig = draw_section(params, r)
        st.pyplot(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Hand Calculation Report")
        # Generate PDF on demand
        tmp_path = os.path.join(tempfile.gettempdir(), "beam_calc_report.pdf")
        try:
            generate_report(r, c, n, params, tmp_path)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name="beam_hand_calculation.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Could not generate PDF: {e}")

    # ── RIGHT: Results ────────────────────────────────────────────────────────
    with col_results:
        tabs = st.tabs(["Flexure", "Shear", "Torsion", "Detailing", "Deflection"])

        # ── FLEXURE TAB ──────────────────────────────────────────────────────
        with tabs[0]:
            c1, c2, c3 = st.columns(3)
            c1.metric("Mf — Factored Moment", f"{r['Mf']} kN·m")
            c2.metric("Mr — Resistance", f"{r['Mr']} kN·m")
            c3.metric("Utilisation", f"{100/r['flex_ratio']:.1f}%" if r['flex_ratio'] else "—")

            st.markdown(
f"""| Parameter | Value |
|---|---|
| Beam type | {"T-Beam" if r["is_T_beam"] else "Rectangular"} |
| a — Stress block depth | {r['a']} mm |
| c — Neutral axis depth | {r['c']} mm |
| εt — Net tensile strain | {r['eps_t']:.5f} |
| As — Total tension steel | {r['As']:.0f} mm² |
| d — Effective depth | {r['d']:.0f} mm |
""")

            if params.get("nb_top", 0) > 0:
                st.markdown("**Force equilibrium (T = Cc + Cs'):**")
                force_rows = [("T — Tension steel force", f"{r.get('T_kN','—')} kN")]
                if r.get("Cf_fl_kN"):
                    force_rows.append(("Cf — Flange overhang force", f"{r['Cf_fl_kN']} kN"))
                force_rows.append(("Cc — Concrete compression force", f"{r.get('Cc_kN','—')} kN"))
                force_rows.append(("Cs' — Net compression steel force", f"{r.get('Cs_net_kN',0)} kN"))
                force_md = "| Force | Value |\n|---|---|\n"
                for label, val in force_rows:
                    force_md += f"| {label} | {val} |\n"
                st.markdown(force_md)
                if "fs_prime" in r:
                    yield_status = "yields (fs'=fy)" if r.get("comp_yields") else "does NOT yield"
                    st.caption(f"Compression steel {yield_status} — fs' = {r['fs_prime']:.1f} MPa, εs' = {r.get('eps_s_prime',0):.5f}")
                else:
                    st.warning("Top steel is not engaged in compression for this loading "
                              "(neutral axis is above it, c ≤ d') — resolved as singly-reinforced.")

            def check_row(label, passed, detail=""):
                icon = "&#10003;" if passed else "&#10007;"
                cls  = "check-pass" if passed else "check-fail"
                st.markdown(f"{icon} <span class='{cls}'>{label}</span>  {detail}",
                           unsafe_allow_html=True)

            st.markdown("**Checks:**")
            check_row("Mr ≥ Mf  (Cl. 10.3.2)", c["flex"])
            check_row("Ductility εt ≥ εy  (Cl. 10.5.2)", c["ductile"])
            check_row("As ≥ As,min  (Cl. 10.5.1.2)", c["As_min"],
                      f"As,min = {r['As_min']:.0f} mm²")
            check_row("As ≤ As,max  (Cl. 10.5.2)", c["As_max"],
                      f"As,max = {r['As_max']:.0f} mm²")

        # ── SHEAR TAB ────────────────────────────────────────────────────────
        with tabs[1]:
            c1, c2, c3 = st.columns(3)
            c1.metric("Vf — Factored Shear", f"{r['Vf']} kN")
            c2.metric("Vr — Resistance", f"{r['Vr']} kN")
            c3.metric("Utilisation", f"{100/r['shear_ratio']:.1f}%" if r['shear_ratio'] else "—")

            st.markdown(
f"""| Parameter | Value |
|---|---|
| dv — Effective shear depth | {r['dv']} mm |
| θ — Angle (simplified) | {r['theta_v']:.0f}° |
| β — Factor | {r['beta_v']:.4f} |
| Vc — Concrete resistance | {r['Vc']} kN |
| Vs — Steel resistance | {r['Vs']} kN |
| Vr,max | {r['Vr_max']} kN |
""")
            st.caption(r.get("beta_method", ""))

            st.markdown("**Checks:**")
            check_row("Vr ≥ Vf  (Cl. 11.3.3)", c["shear"])
            if params["s"] > 0:
                check_row("Av ≥ Av,min  (Cl. 11.2.8.1)", c["Av_min"],
                         f"Av,min = {r['Av_min_s']:.1f} mm²")
                check_row(f"s ≤ s,max = {r['s_max']:.0f}mm  (Cl. 11.3.8)", c["s_max"])
            else:
                st.warning("No stirrups — verify min. transverse reinf. per Cl. 11.2.8")

        # ── TORSION TAB ──────────────────────────────────────────────────────
        with tabs[2]:
            if r["Tf"] > 0:
                c1, c2 = st.columns(2)
                c1.metric("Tf — Factored Torsion", f"{r['Tf']} kN·m")
                c2.metric("Tcr — Cracking Torque", f"{r['Tcr']} kN·m")
                check_row("Tf ≤ Tcr  (Cl. 11.2.9)", c["torsion_threshold"])
                if not c["torsion_threshold"]:
                    st.warning("Full torsion design required per Cl. 11.3.9 & 11.4 — "
                              "provide closed stirrups + longitudinal torsion reinforcement")
            else:
                st.info("No torsion specified (Tf = 0) — torsion design not required.")

        # ── DETAILING TAB ────────────────────────────────────────────────────
        with tabs[3]:
            detail_rows = [
                ("Clear cover provided",      f"{r['cover']} mm"),
                ("Clear spacing (actual)",    f"{r['clear_sp_actual']:.1f} mm"),
                ("Min. clear spacing",        f"{r['clear_sp_min']:.1f} mm"),
                ("Width needed (layer 1)",    f"{r['width_needed']:.0f} mm"),
                ("Development length ld",     f"{r['ld']:.0f} mm"),
            ]
            if r["nb2"] > 0:
                detail_rows.append(("Layer gap (actual)",   f"{r['layer_gap']:.1f} mm"))
                detail_rows.append(("Min. layer gap",       f"{r['layer_gap_min']:.1f} mm"))

            table_md = "| Parameter | Value |\n|---|---|\n"
            for label, val in detail_rows:
                table_md += f"| {label} | {val} |\n"
            st.markdown(table_md)

            st.markdown("**Checks:**")
            check_row("Cover ≥ 40mm  (Cl. 7.9)", c["cover_ok"])
            check_row("Bar size ≥ 10M  (Cl. 7.6.5)", c["bar_size_min"])
            check_row("Bars fit in single layer  (Cl. 7.5)", c["bars_fit"])
            check_row("Clear spacing ≥ min  (Cl. 7.5)", c["bar_spacing"])
            if r["nb2"] > 0:
                check_row("Layer gap ≥ min  (Cl. 7.5)", c["layer_gap_ok"])
            check_row("Crack-control spacing  (Cl. 10.6.4)", c["crack_spacing"])

        # ── DEFLECTION TAB ───────────────────────────────────────────────────
        with tabs[4]:
            c1, c2 = st.columns(2)
            c1.metric("Mcr — Cracking Moment", f"{r['Mcr']} kN·m")
            c2.metric("Mf — Applied Moment", f"{r['Mf']} kN·m")

            st.markdown(
f"""| Parameter | Value |
|---|---|
| Ig — Gross inertia | {r['Ig']:.0f} ×10⁶ mm⁴ |
| Icr — Cracked inertia | {r['Icr']:.0f} ×10⁶ mm⁴ |
| Ie — Effective inertia (Branson) | {r['Ie']:.0f} ×10⁶ mm⁴ |
""")
            cracked = r["Mf"] > r["Mcr"]
            if cracked:
                st.warning(f"Section CRACKED (Mf={r['Mf']} > Mcr={r['Mcr']} kN·m) — use Ie for deflection")
            else:
                st.success(f"Section UNCRACKED (Mf={r['Mf']} ≤ Mcr={r['Mcr']} kN·m) — use Ig")

st.markdown("---")
st.caption("CSA A23.3-19 Beam Analyzer  |  Simplified shear method, θ=35°  |  "
          "For engineering review only — verify all inputs and results.")
