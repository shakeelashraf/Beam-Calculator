"""
CSA A23.3-19 Textbook-Style Hand Calculation PDF Report Generator
Used by both the Streamlit web app and the desktop Tkinter app.
"""
import math, datetime, os
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
               "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}

def bar_name(db):
    for k,v in REBAR_SIZES.items():
        if abs(v-db)<0.5: return k
    return f"d={db:.1f}mm"

# ══════════════════════════════════════════════════════════════════════════════
#  TEXTBOOK-STYLE PDF REPORT
#  Layout: ruled paper look, formula line → substitution line → result box
# ══════════════════════════════════════════════════════════════════════════════
def generate_report(r, c, n, params, filepath):
    """
    Generates a hand-calculation style PDF resembling textbook worked examples.
    Each calculation step shows:
        Clause ref  |  Description
                    |  Formula (symbolic)
                    |  = substitution
                    |  = RESULT  [PASS/FAIL]
    """
    import math, datetime
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm

    # ── Page geometry ──────────────────────────────────────────────────────
    W, H   = letter
    LM     = 0.70 * inch   # left margin (inside ruling)
    RM     = W - 0.55*inch # right margin
    TM     = H - 1.05*inch # top margin (below header)
    BM     = 0.65*inch     # bottom margin (above footer)
    CW     = RM - LM       # content width

    # ── Colours ────────────────────────────────────────────────────────────
    C_INK    = colors.HexColor("#1a1a2e")
    C_NAVY   = colors.HexColor("#1E2A3A")
    C_BLUE   = colors.HexColor("#1D4ED8")
    C_GREEN  = colors.HexColor("#15803D")
    C_RED    = colors.HexColor("#B91C1C")
    C_AMBER  = colors.HexColor("#92400E")
    C_RULE   = colors.HexColor("#CBD5E1")   # horizontal rule lines
    C_MARGIN = colors.HexColor("#FECDD3")   # left margin line (red like graph paper)
    C_HLITE  = colors.HexColor("#EFF6FF")   # result highlight
    C_HBORD  = colors.HexColor("#BFDBFE")
    C_GREY   = colors.HexColor("#6B7280")
    C_LGREY  = colors.HexColor("#F8FAFC")

    DATE = datetime.date.today().strftime("%B %d, %Y")
    REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
                   "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}

    # ── Register DejaVu fonts (full Unicode: Greek, sub/superscripts, math) ──
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Look for fonts next to the script, then system paths
    _script_dir = os.path.dirname(os.path.abspath(filepath))
    _font_search = [
        _script_dir,
        os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else _script_dir,
        '/usr/share/fonts/truetype/dejavu/',
        '/Library/Fonts/',
        '/System/Library/Fonts/',
        os.path.expanduser('~/Library/Fonts/'),
        'C:/Windows/Fonts/',
    ]
    def _find_font(name):
        for d in _font_search:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        return None

    _dv     = _find_font('DejaVuSans.ttf')
    _dv_b   = _find_font('DejaVuSans-Bold.ttf')
    _dv_i   = _find_font('DejaVuSans-Oblique.ttf')
    _dv_bi  = _find_font('DejaVuSans-BoldOblique.ttf')

    if _dv:
        pdfmetrics.registerFont(TTFont('DV',    _dv))
        pdfmetrics.registerFont(TTFont('DV-B',  _dv_b  or _dv))
        pdfmetrics.registerFont(TTFont('DV-I',  _dv_i  or _dv))
        pdfmetrics.registerFont(TTFont('DV-BI', _dv_bi or _dv_b or _dv))
        _FN = 'DV'; _FN_B = 'DV-B'; _FN_I = 'DV-I'; _FN_BI = 'DV-BI'
    else:
        # Fallback to Helvetica if fonts not found
        _FN = 'Helvetica'; _FN_B = 'Helvetica-Bold'
        _FN_I = 'Helvetica-Oblique'; _FN_BI = 'Helvetica-BoldOblique'

    # ── Canvas & state ─────────────────────────────────────────────────────
    canv = rl_canvas.Canvas(filepath, pagesize=letter)
    state = {"page": 1, "y": TM}

    # ── Fonts ──────────────────────────────────────────────────────────────
    F_BODY   = (_FN,    9.5)
    F_BOLD   = (_FN_B,  9.5)
    F_ITALIC = (_FN_I,  9.5)
    F_SMALL  = (_FN,    8.0)
    F_H1     = (_FN_B, 11.5)
    F_H2     = (_FN_B, 10.0)
    F_TITLE  = (_FN_B, 15.0)
    F_CLAUSE = (_FN_I,  7.5)

    LINE_H      = 14.5
    SECTION_GAP = 18

    # ── Low-level drawing helpers ──────────────────────────────────────────
    def set_font(spec): canv.setFont(*spec)

    def _tw(s, font):
        return canv.stringWidth(s, font[0], font[1])

    def _draw_rich(x, y, txt, font=F_BODY, color=C_INK):
        """
        Draw txt with proper sub/superscripts by position-shifting smaller text.
        DejaVu renders Unicode directly (α β θ √ ² ³ ₁ etc.) so we only need
        to handle the ^{...} and _{...} markup for explicit positioning.

        Markup inside strings:
          _{abc}  → subscript run
          ^{abc}  → superscript run
        Everything else is drawn at normal baseline in the given font.
        """
        fname, fsize = font
        sub_sz  = fsize * 0.62
        sup_sz  = fsize * 0.62
        sub_dy  = -fsize * 0.20
        sup_dy  =  fsize * 0.36

        canv.setFillColor(color)
        i = 0; cx = x
        while i < len(txt):
            if txt[i] == '_' and i+1 < len(txt) and txt[i+1] == '{':
                end = txt.find('}', i+2)
                if end == -1: end = len(txt)
                seg = txt[i+2:end]; i = end+1
                canv.setFont(fname, sub_sz)
                canv.drawString(cx, y + sub_dy, seg)
                cx += canv.stringWidth(seg, fname, sub_sz)
            elif txt[i] == '^' and i+1 < len(txt) and txt[i+1] == '{':
                end = txt.find('}', i+2)
                if end == -1: end = len(txt)
                seg = txt[i+2:end]; i = end+1
                canv.setFont(fname, sup_sz)
                canv.drawString(cx, y + sup_dy, seg)
                cx += canv.stringWidth(seg, fname, sup_sz)
            else:
                # Collect normal run until next markup
                j = i+1
                while j < len(txt):
                    if txt[j] in ('^', '_') and j+1 < len(txt) and txt[j+1] == '{':
                        break
                    j += 1
                seg = txt[i:j]; i = j
                canv.setFont(fname, fsize)
                canv.drawString(cx, y, seg)
                cx += canv.stringWidth(seg, fname, fsize)
        return cx

    def _rich_width(txt, font=F_BODY):
        fname, fsize = font
        sub_sz = fsize * 0.62; sup_sz = fsize * 0.62
        i = 0; w = 0
        while i < len(txt):
            if txt[i] in ('^', '_') and i+1 < len(txt) and txt[i+1] == '{':
                end = txt.find('}', i+2)
                if end == -1: end = len(txt)
                seg = txt[i+2:end]; i = end+1
                sz = sub_sz if txt[i-len(seg)-2] == '_' else sup_sz
                # recompute: check the marker before '{'
                marker = txt[i - len(seg) - 3] if i - len(seg) - 3 >= 0 else '_'
                w += canv.stringWidth(seg, fname, sub_sz if marker == '_' else sup_sz)
            else:
                j = i+1
                while j < len(txt):
                    if txt[j] in ('^', '_') and j+1 < len(txt) and txt[j+1] == '{':
                        break
                    j += 1
                seg = txt[i:j]; i = j
                w += canv.stringWidth(seg, fname, fsize)
        return w

    def _rw(txt, font=F_BODY):
        """Robust rich-width by rendering to a scratch measurement."""
        # Simpler: strip markup tags and measure, then adjust
        import re
        plain = re.sub(r'[_^]\{[^}]*\}', lambda m: m.group(0)[2:-1], txt)
        fname, fsize = font
        sub_sz = fsize * 0.62
        # Walk properly
        w = 0; fname2, fsize2 = font
        i = 0
        while i < len(txt):
            if txt[i] in ('^','_') and i+1<len(txt) and txt[i+1]=='{':
                end = txt.find('}', i+2)
                if end==-1: end=len(txt)
                seg=txt[i+2:end]; i=end+1
                w += canv.stringWidth(seg, fname2, sub_sz)
            else:
                j=i+1
                while j<len(txt):
                    if txt[j] in ('^','_') and j+1<len(txt) and txt[j+1]=='{':
                        break
                    j+=1
                seg=txt[i:j]; i=j
                w += canv.stringWidth(seg, fname2, fsize2)
        return w

    def text(x, y, txt, font=F_BODY, color=C_INK, align="left"):
        """Draw Unicode text with _{sub} and ^{sup} markup support."""
        if align == "right":
            _draw_rich(x - _rw(txt, font), y, txt, font, color)
        elif align == "center":
            _draw_rich(x - _rw(txt, font)/2, y, txt, font, color)
        else:
            _draw_rich(x, y, txt, font, color)

    def rule(y, x1=LM, x2=RM, color=C_RULE, width=0.3):
        canv.setStrokeColor(color)
        canv.setLineWidth(width)
        canv.line(x1, y, x2, y)

    def margin_line():
        canv.setStrokeColor(C_MARGIN)
        canv.setLineWidth(0.5)
        canv.line(LM - 0.18*inch, BM, LM - 0.18*inch, TM + 2)

    def draw_header():
        # Top navy bar
        canv.setFillColor(C_NAVY)
        canv.rect(0, H - 0.72*inch, W, 0.72*inch, fill=1, stroke=0)
        text(LM, H - 0.28*inch,
             "CSA A23.3-19  |  Concrete Beam — Hand Calculation",
             F_H1, colors.white)
        text(RM, H - 0.28*inch,
             f"Page {state['page']}",
             F_BODY, colors.white, "right")
        # Sub-strip
        canv.setFillColor(colors.HexColor("#F0F4FF"))
        canv.rect(0, H - 0.98*inch, W, 0.26*inch, fill=1, stroke=0)
        text(LM, H - 0.85*inch,
             f"Simplified method  |  φ_c = 0.65  |  φ_s = 0.85  |  λ = 1.0",
             F_SMALL, C_GREY)
        text(RM, H - 0.85*inch, DATE, F_SMALL, C_GREY, "right")

    def draw_footer():
        canv.setFillColor(colors.HexColor("#F1F5F9"))
        canv.rect(0, 0, W, 0.55*inch, fill=1, stroke=0)
        canv.setStrokeColor(C_RULE)
        canv.setLineWidth(0.5)
        canv.line(0, 0.55*inch, W, 0.55*inch)
        text(LM, 0.20*inch,
             "For engineering review only — verify all inputs, assumptions, and results against project requirements.",
             F_SMALL, C_GREY)
        text(RM, 0.20*inch, f"Page {state['page']}", F_SMALL, C_GREY, "right")

    def new_page():
        draw_footer()
        canv.showPage()
        state["page"] += 1
        state["y"] = TM
        draw_header()
        margin_line()
        # Draw faint horizontal rules across the page (graph-paper feel)
        for ry in range(int(BM + LINE_H), int(TM), int(LINE_H)):
            rule(ry, LM - 0.18*inch, RM, C_RULE, 0.2)

    def ensure_space(needed):
        if state["y"] - needed < BM:
            new_page()

    def advance(h): state["y"] -= h

    # ── Content helpers ────────────────────────────────────────────────────
    def section_title(number, title):
        ensure_space(SECTION_GAP + 22)
        if state["y"] < TM - 0.1:
            advance(SECTION_GAP * 0.6)
        y = state["y"]
        # Background strip
        canv.setFillColor(C_NAVY)
        canv.rect(LM - 0.15*inch, y - 3, CW + 0.15*inch + 0.05*inch, 17, fill=1, stroke=0)
        text(LM, y + 1, f"  {number}.  {title.upper()}", F_H2, colors.white)
        advance(22)
        rule(state["y"], color=C_RULE, width=0.3)

    def subsection(title):
        ensure_space(20)
        advance(6)
        y = state["y"]
        canv.setFillColor(colors.HexColor("#EFF6FF"))
        canv.rect(LM - 0.05*inch, y - 2, CW + 0.05*inch, 14, fill=1, stroke=0)
        text(LM + 2, y + 1, title, F_BOLD, C_BLUE)
        advance(16)

    def given_row(label, value, unit=""):
        """Single given: label ......... value unit"""
        ensure_space(LINE_H + 2)
        y = state["y"]
        rule(y - LINE_H + 2, color=C_RULE, width=0.2)
        text(LM + 4, y - 10, label, F_BODY, C_INK)
        val_str = f"{value}  {unit}".strip()
        text(RM, y - 10, val_str, F_BOLD, C_NAVY, "right")
        # Dots
        canv.setFillColor(C_RULE)
        dot_x = LM + 4 + canv.stringWidth(label, *F_BODY) + 4
        val_w = canv.stringWidth(val_str, *F_BOLD)
        dot_end = RM - val_w - 6
        canv.setFont(*F_BODY)
        dots = "." * max(0, int((dot_end - dot_x) / canv.stringWidth(".", *F_BODY)))
        canv.setFillColor(C_RULE)
        canv.drawString(dot_x, y - 10, dots)
        advance(LINE_H)

    def blank(h=4): advance(h)

    INDENT_FORMULA = LM + 0.25*inch
    INDENT_SUB     = LM + 0.35*inch
    INDENT_RESULT  = LM + 0.45*inch

    def step(clause, description, formula, substitution, result,
             passed=None, note=None, result_unit=""):
        """
        One calculation step — textbook style:
          [clause]  Description
                    Formula  (symbolic)
                    = substitution
                    = RESULT   [PASS / FAIL]
        """
        # Estimate lines needed
        lines_needed = 4 + (1 if note else 0)
        ensure_space(lines_needed * LINE_H + 8)

        y = state["y"]

        # Clause ref in left margin area
        canv.setFont(*F_CLAUSE)
        canv.setFillColor(C_GREY)
        canv.drawRightString(LM - 0.22*inch, y - 9, clause)

        # Description line
        text(INDENT_FORMULA - 0.1*inch, y - 9, description, F_BOLD, C_INK)
        advance(LINE_H)

        # Formula line (italic, symbolic)
        text(INDENT_FORMULA, state["y"] - 9, formula, F_ITALIC, C_BLUE)
        advance(LINE_H)

        # Substitution line
        text(INDENT_SUB, state["y"] - 9, f"= {substitution}", F_BODY, C_INK)
        advance(LINE_H)

        # Result line with highlight box
        res_y = state["y"] - LINE_H + 2
        res_text = f"= {result}  {result_unit}".strip()
        rw = _rw(res_text, F_BOLD) + 14
        canv.setFillColor(C_HLITE)
        canv.setStrokeColor(C_HBORD)
        canv.setLineWidth(0.6)
        canv.roundRect(INDENT_RESULT - 4, res_y - 3, rw, 13, 2, fill=1, stroke=1)
        text(INDENT_RESULT, res_y + 0.5, res_text, F_BOLD, C_NAVY)

        # PASS / FAIL badge
        if passed is not None:
            badge_txt = "✓  PASS" if passed else "✗  FAIL"
            badge_col = C_GREEN if passed else C_RED
            bx = INDENT_RESULT + rw + 8
            bw2 = canv.stringWidth(badge_txt, "Helvetica-Bold", 8.5) + 10
            bg_col = colors.HexColor("#DCFCE7") if passed else colors.HexColor("#FEE2E2")
            canv.setFillColor(bg_col)
            canv.setStrokeColor(badge_col)
            canv.setLineWidth(0.7)
            canv.roundRect(bx, res_y - 3, bw2, 13, 2, fill=1, stroke=1)
            canv.setFont("Helvetica-Bold", 8.5)
            canv.setFillColor(badge_col)
            canv.drawString(bx + 5, res_y + 0.5, badge_txt)

        advance(LINE_H + 2)

        # Optional note
        if note:
            text(INDENT_RESULT, state["y"] - 9,
                 f"↳  {note}", F_SMALL, C_AMBER)
            advance(LINE_H)

        # Light rule after step
        rule(state["y"] - 2, color=C_RULE, width=0.2)
        advance(3)

    def info_line(txt, indent=0):
        ensure_space(LINE_H + 2)
        text(INDENT_FORMULA + indent, state["y"] - 9, txt, F_ITALIC, C_GREY)
        advance(LINE_H)

    def check_line(description, demand, capacity, passed):
        """Compact check row for summary."""
        ensure_space(LINE_H + 3)
        y = state["y"]
        rule(y - LINE_H + 1, color=C_RULE, width=0.2)
        badge = "✓  PASS" if passed else "✗  FAIL"
        col   = C_GREEN if passed else C_RED
        bg    = colors.HexColor("#DCFCE7") if passed else colors.HexColor("#FEE2E2")
        bw2   = canv.stringWidth(badge, "Helvetica-Bold", 8.5) + 10
        canv.setFillColor(bg); canv.setStrokeColor(col); canv.setLineWidth(0.6)
        canv.roundRect(RM - bw2, y - LINE_H + 2, bw2, 12, 2, fill=1, stroke=1)
        canv.setFont("Helvetica-Bold", 8.5); canv.setFillColor(col)
        canv.drawString(RM - bw2 + 5, y - LINE_H + 5, badge)
        text(LM + 4, y - 10, description, F_BODY, C_INK)
        text(LM + 2.5*inch, y - 10, demand,   F_SMALL, C_GREY)
        text(LM + 4.3*inch, y - 10, capacity, F_SMALL, C_NAVY)
        advance(LINE_H + 1)

    def draw_cross_section():
        """Inline cross-section sketch on the right side of Given Info."""
        bw     = r["bw"]; hh = r["h"]; is_T = r["is_T_beam"]
        bf     = r["b"];  hf = r["hf"]
        cover  = r["cover"]; dv_b = r["dv_bar"]
        nb1    = r["nb1"];  db1 = r["db1"]
        nb2    = r["nb2"];  db2 = r["db2"]
        nb_top = r["nb_top"]; db_top = r["db_top"]
        d1     = r["d1"]; d2 = r["d2"]
        d_top  = r["d_top"]

        DW, DH = 1.55*inch, 2.1*inch   # drawing area
        dx = RM - DW                    # top-left x of drawing
        dy = state["y"] - DH - 0.1*inch

        outer_w = bf if is_T else bw
        sc = min(DW / outer_w, DH / hh) * 0.85
        sw = outer_w*sc; sh = hh*sc
        ox = dx + (DW-sw)/2; oy = dy + (DH-sh)/2

        web_ox = ox + (bf-bw)/2*sc if is_T else ox

        # Shadow
        canv.setFillColor(colors.HexColor("#CBD5E1"))
        canv.rect(ox+3, oy-3, sw, sh, fill=1, stroke=0)

        # Concrete
        canv.setFillColor(colors.HexColor("#D1CBC0"))
        canv.setStrokeColor(colors.HexColor("#7C6F62"))
        canv.setLineWidth(1.2)
        if is_T:
            canv.rect(ox, oy+sh-hf*sc, sw, hf*sc, fill=1, stroke=1)
            canv.rect(web_ox, oy, bw*sc, (hh-hf)*sc, fill=1, stroke=1)
        else:
            canv.rect(ox, oy, sw, sh, fill=1, stroke=1)

        # Stirrups
        if r["Av"] > 0:
            ins = cover*sc
            canv.setStrokeColor(colors.HexColor("#374151"))
            canv.setLineWidth(max(1.0, min(dv_b*sc/2, 2.5)))
            canv.rect(web_ox+ins, oy+ins, bw*sc-2*ins, sh-2*ins, fill=0, stroke=1)

        # Stress block
        if r.get("a"):
            a_mm = r["a"]
            sb_h = a_mm*sc
            sb_x = ox if not is_T else (ox if a_mm<=hf else web_ox)
            sb_w = sw if not is_T else (sw if a_mm<=hf else bw*sc)
            canv.setFillColor(colors.HexColor("#93C5FD"))
            canv.setFillAlpha(0.55)
            canv.rect(sb_x, oy+sh-sb_h, sb_w, sb_h, fill=1, stroke=0)
            canv.setFillAlpha(1.0)
            # N.A.
            na_y = oy + sh - r["c"]*sc
            canv.setStrokeColor(colors.HexColor("#EF4444"))
            canv.setLineWidth(0.7); canv.setDash(3,2)
            canv.line(web_ox-4, na_y, web_ox+bw*sc+4, na_y)
            canv.setDash()

        def bars(n_b, db, depth, col):
            if n_b <= 0: return
            br = max(1.5, min(db*sc/2, 5))
            by = oy + sh - depth*sc
            il = web_ox + cover*sc + dv_b*sc + br
            ir = web_ox + bw*sc - cover*sc - dv_b*sc - br
            xs = [il] if n_b==1 else [il + i*(ir-il)/(n_b-1) for i in range(n_b)]
            canv.setFillColor(col); canv.setStrokeColor(colors.white); canv.setLineWidth(0.4)
            for bx in xs: canv.circle(bx, by, br, fill=1, stroke=1)

        bars(nb_top, db_top, d_top, colors.HexColor("#7C3AED"))
        if nb2 > 0: bars(nb2, db2, d2, colors.HexColor("#1E293B"))
        bars(nb1, db1, d1, colors.HexColor("#0F172A"))

        # Dimension callouts
        canv.setFont(*F_SMALL); canv.setFillColor(C_NAVY)
        # h arrow
        mid_x = ox - 0.12*inch
        canv.setStrokeColor(C_NAVY); canv.setLineWidth(0.5)
        canv.line(mid_x, oy, mid_x, oy+sh)
        canv.drawCentredString(mid_x - 12, oy+sh/2, f"h={int(hh)}")
        # bw arrow
        mid_y = oy - 0.12*inch
        canv.line(web_ox, mid_y, web_ox+bw*sc, mid_y)
        canv.drawCentredString(web_ox+bw*sc/2, mid_y-8, f"bw={int(bw)}")
        # Label
        canv.setFont("Helvetica-Bold", 7.5)
        canv.drawCentredString(dx+DW/2, dy - 8,
            "Cross-Section  (all dim. in mm)")
        return dy   # return top y used

    # ══════════════════════════════════════════════════════════════════════
    #  START DOCUMENT
    # ══════════════════════════════════════════════════════════════════════
    draw_header()
    margin_line()
    for ry in range(int(BM + LINE_H), int(TM), int(LINE_H)):
        rule(ry, LM - 0.18*inch, RM, C_RULE, 0.2)

    fc   = r["fc"]; fy = r["fy"]; fyt = r["fyt"]
    bw   = r["bw"]; h  = r["h"];  d   = r["d"]
    As   = r["As"]; Av = r["Av"]; s   = r["s"]
    Es   = 200000.0

    # ── TITLE BLOCK ───────────────────────────────────────────────────────
    advance(6)
    text(LM, state["y"] - 2,
         "REINFORCED CONCRETE BEAM  —  DESIGN CALCULATIONS",
         F_TITLE, C_NAVY)
    advance(18)
    ok = r["overall_pass"]
    badge_txt = "ALL CHECKS PASS" if ok else "CHECKS FAILED"
    badge_col = C_GREEN if ok else C_RED
    bg2 = colors.HexColor("#DCFCE7") if ok else colors.HexColor("#FEE2E2")
    bw3 = canv.stringWidth(badge_txt, "Helvetica-Bold", 10) + 16
    canv.setFillColor(bg2); canv.setStrokeColor(badge_col); canv.setLineWidth(1)
    canv.roundRect(LM, state["y"]-14, bw3, 16, 3, fill=1, stroke=1)
    canv.setFont("Helvetica-Bold", 10); canv.setFillColor(badge_col)
    canv.drawString(LM + 8, state["y"] - 10, badge_txt)
    advance(22)
    rule(state["y"], width=0.8, color=C_NAVY)
    advance(8)

    # ── SECTION 1: GIVEN ──────────────────────────────────────────────────
    section_title("1", "Given Information")
    advance(4)

    # Draw section sketch on the right, given data on left
    sketch_top_y = state["y"]
    SKETCH_W = 1.7*inch
    SKETCH_H = 2.2*inch

    # Given info — left column only (leave right for sketch)
    old_RM = RM
    RM_GIVEN = RM - SKETCH_W - 0.15*inch

    def given_row_narrow(label, value, unit=""):
        ensure_space(LINE_H + 2)
        y2 = state["y"]
        rule(y2 - LINE_H + 2, x1=LM, x2=RM_GIVEN, color=C_RULE, width=0.2)
        text(LM + 4, y2 - 10, label, F_BODY, C_INK)
        val_str = f"{value}  {unit}".strip()
        text(RM_GIVEN, y2 - 10, val_str, F_BOLD, C_NAVY, "right")
        advance(LINE_H)

    subsection("Materials")
    given_row_narrow("Concrete compressive strength  f'c", f"{fc}", "MPa")
    given_row_narrow("Steel yield strength  fy",            f"{fy}", "MPa")
    given_row_narrow("Stirrup yield  fyt",                  f"{fyt}", "MPa")
    given_row_narrow("Concrete modulus  Ec  (Cl. 8.6.2)",  f"{r['Ec']:.0f}", "MPa")
    given_row_narrow("Steel modulus  Es",                   "200 000", "MPa")
    advance(4)
    subsection("Section Geometry")
    given_row_narrow("Web width  bw",          f"{bw:.0f}", "mm")
    given_row_narrow("Total depth  h",          f"{h:.0f}",  "mm")
    given_row_narrow("Clear cover  cc",         f"{r['cover']:.0f}", "mm")
    if r["is_T_beam"]:
        given_row_narrow("Flange width  bf",    f"{r['b']:.0f}", "mm")
        given_row_narrow("Flange depth  hf",    f"{r['hf']:.0f}", "mm")
    advance(4)
    subsection("Reinforcement")
    b1n = bar_name(r['db1'])
    given_row_narrow(f"Bot. layer 1  ({r['nb1']}-{b1n})",
                     f"As1 = {r['As1']:.0f}", "mm^{2}")
    given_row_narrow(f"  Centroid  d1",          f"{r['d1']:.0f}", "mm from top")
    if r["nb2"] > 0:
        b2n = bar_name(r['db2'])
        given_row_narrow(f"Bot. layer 2  ({r['nb2']}-{b2n})",
                         f"As2 = {r['As2']:.0f}", "mm^{2}")
        given_row_narrow(f"  Centroid  d2",      f"{r['d2']:.0f}", "mm from top")
    given_row_narrow("Total tension steel  As",  f"{As:.0f}", "mm^{2}")
    given_row_narrow("Weighted eff. depth  d",   f"{d:.0f}", "mm")
    if r["nb_top"] > 0:
        btn = bar_name(r['db_top'])
        given_row_narrow(f"Top steel  ({r['nb_top']}-{btn})",
                         f"As' = {r['As_top']:.0f}", "mm^{2}")
    stir_sz = params.get("stir_size","?")
    n_legs  = params.get("n_legs", 2)
    given_row_narrow(f"Stirrups  ({n_legs}-leg {stir_sz} @ {s:.0f}mm)",
                     f"Av = {Av:.0f}", "mm^{2}")
    advance(4)
    subsection("Factored Loads")
    given_row_narrow("Factored moment  Mf",  f"{r['Mf']:.1f}", "kN·m")
    given_row_narrow("Factored shear  Vf",   f"{r['Vf']:.1f}", "kN")
    if r["Tf"] > 0:
        given_row_narrow("Factored torsion  Tf", f"{r['Tf']:.1f}", "kN·m")

    # Draw cross-section sketch in right margin of Given section
    sketch_bottom = state["y"] - 0.1*inch
    sketch_h_avail = sketch_top_y - sketch_bottom
    if sketch_h_avail > 0.8*inch:
        dw2, dh2 = SKETCH_W - 0.1*inch, min(SKETCH_H, sketch_h_avail)
        ox2 = RM - dw2 + 0.05*inch
        oy2 = sketch_bottom + (sketch_h_avail - dh2)/2

        # Draw box
        canv.setFillColor(colors.white)
        canv.setStrokeColor(C_RULE)
        canv.setLineWidth(0.5)
        canv.rect(ox2 - 4, oy2 - 4, dw2 + 8, dh2 + 8, fill=1, stroke=1)

        # Section schematic
        bw_s=r["bw"]; hh_s=r["h"]; is_T=r["is_T_beam"]
        bf_s=r["b"]; hf_s=r["hf"]; cov=r["cover"]; dvb=r["dv_bar"]
        outer = bf_s if is_T else bw_s
        sc = min(dw2/outer, dh2/hh_s)*0.78
        sw2=outer*sc; sh2=hh_s*sc
        sx0=ox2+(dw2-sw2)/2; sy0=oy2+(dh2-sh2)/2

        web_sx = sx0+(bf_s-bw_s)/2*sc if is_T else sx0
        canv.setFillColor(colors.HexColor("#CBD5E1"))
        canv.rect(sx0+2,sy0-2,sw2,sh2,fill=1,stroke=0)
        canv.setFillColor(colors.HexColor("#D1CBC0"))
        canv.setStrokeColor(colors.HexColor("#7C6F62")); canv.setLineWidth(1)
        if is_T:
            canv.rect(sx0,sy0+sh2-hf_s*sc,sw2,hf_s*sc,fill=1,stroke=1)
            canv.rect(web_sx,sy0,bw_s*sc,(hh_s-hf_s)*sc,fill=1,stroke=1)
        else:
            canv.rect(sx0,sy0,sw2,sh2,fill=1,stroke=1)
        if r["Av"]>0:
            ins=cov*sc
            canv.setStrokeColor(colors.HexColor("#374151")); canv.setLineWidth(1.2)
            canv.rect(web_sx+ins,sy0+ins,bw_s*sc-2*ins,sh2-2*ins,fill=0,stroke=1)
        if r.get("a"):
            sb_h2=r["a"]*sc
            canv.setFillColor(colors.HexColor("#93C5FD")); canv.setFillAlpha(0.5)
            sbx2=sx0 if not is_T else (sx0 if r["a"]<=hf_s else web_sx)
            sbw2=sw2 if not is_T else (sw2 if r["a"]<=hf_s else bw_s*sc)
            canv.rect(sbx2,sy0+sh2-sb_h2,sbw2,sb_h2,fill=1,stroke=0)
            canv.setFillAlpha(1)
            na_y2=sy0+sh2-r["c"]*sc
            canv.setStrokeColor(colors.HexColor("#EF4444")); canv.setLineWidth(0.6)
            canv.setDash(3,2)
            canv.line(web_sx-3,na_y2,web_sx+bw_s*sc+3,na_y2); canv.setDash()
        def bars2(nb,db,dep,col):
            if nb<=0: return
            br=max(1.2,min(db*sc/2,4.5))
            by2=sy0+sh2-dep*sc
            il2=web_sx+cov*sc+dvb*sc+br; ir2=web_sx+bw_s*sc-cov*sc-dvb*sc-br
            xs2=[il2] if nb==1 else [il2+i*(ir2-il2)/(nb-1) for i in range(nb)]
            canv.setFillColor(col); canv.setStrokeColor(colors.white); canv.setLineWidth(0.3)
            for bx2 in xs2: canv.circle(bx2,by2,br,fill=1,stroke=1)
        bars2(r["nb_top"],r["db_top"],r["d_top"],colors.HexColor("#7C3AED"))
        if r["nb2"]>0: bars2(r["nb2"],r["db2"],r["d2"],colors.HexColor("#1E293B"))
        bars2(r["nb1"],r["db1"],r["d1"],colors.HexColor("#0F172A"))

        # Labels
        canv.setFont("Helvetica", 6.5); canv.setFillColor(C_NAVY)
        canv.drawCentredString(ox2+dw2/2, oy2-14,
            f"{'T-Beam' if is_T else 'Rect.'}  {int(bw_s)}×{int(hh_s)} mm")
        if r.get("a"):
            canv.setFont("Helvetica",5.5); canv.setFillColor(colors.HexColor("#1D4ED8"))
            canv.drawString(sbx2+3, sy0+sh2-sb_h2/2, f"a={r['a']:.0f}")
            canv.setFillColor(colors.HexColor("#EF4444"))
            canv.drawString(web_sx+bw_s*sc+2, na_y2+1, f"c={r['c']:.0f}")

    advance(10)
    rule(state["y"], width=0.5, color=C_NAVY)

    # ── SECTION 2: MATERIAL FACTORS ───────────────────────────────────────
    section_title("2", "Material Factors  (Cl. 10.1.7 / 8.6.2)")
    advance(4)

    a1 = r["alpha1"]; b1_val = r["beta1"]; Ec = r["Ec"]
    step("Cl.10.1.7", "Stress-block intensity factor  α_{1}",
         "α_{1} = max( 0.85 − 0.0015·f'c,  0.67 )",
         f"max( 0.85 − 0.0015×{fc},  0.67 )",
         f"α_{{1}} = {a1:.4f}")
    step("Cl.10.1.7", "Stress-block depth factor  β_{{1}}",
         "β_{{1}} = max( 0.97 − 0.0025·f'c,  0.67 )",
         f"max( 0.97 − 0.0025×{fc},  0.67 )",
         f"β_{{1}} = {b1_val:.4f}")
    step("Cl.8.6.2", "Concrete modulus of elasticity  Ec",
         "Ec = (3300√f'c + 6900)·(wc/2300)^{{1.5}}",
         f"(3300×√{fc} + 6900)×(2400/2300)^{{1.5}}",
         f"Ec = {Ec:.0f} MPa")
    info_line(f"Modular ratio  n = Es/Ec = 200 000 / {Ec:.0f} = {n.get('n_ratio','—')}")

    # ── SECTION 3: FLEXURE ────────────────────────────────────────────────
    section_title("3", "Flexural Design  (Cl. 10.3 / 10.5)")
    advance(4)

    a_val = r["a"]; c_val = r["c"]; Mr = r["Mr"]

    if r["nb2"] > 0:
        step("Cl.10.3", "Weighted effective depth  d  (two layers)",
             "d = (As1·d1 + As2·d2) / As",
             f"({r['As1']:.0f}×{r['d1']:.0f} + {r['As2']:.0f}×{r['d2']:.0f}) / {As:.0f}",
             f"d = {d:.1f} mm")

    if r["is_T_beam"]:
        Cf_fl = a1*0.65*fc*(r['b']-bw)*r['hf']
        step("Cl.10.3.2", "Compression force in overhanging flanges  Cf",
             "Cf = α_{{1}}·φc·f'c·(bf − bw)·hf",
             f"{a1:.4f}×0.65×{fc}×({r['b']}−{bw})×{r['hf']}",
             f"Cf = {Cf_fl/1000:.1f} kN")
        req_kN = (0.85*fy*As - Cf_fl)/1000
        if r.get("flange_na")=="in web":
            step("Cl.10.3.2", "Web compression force  req = φs·fy·As − Cf",
                 "req = φs·fy·As − Cf",
                 f"0.85×{fy}×{As:.0f} − {Cf_fl:.0f}",
                 f"req = {req_kN:.1f} kN")
            step("Cl.10.3.2", "Stress-block depth  a  (N.A. in web)",
                 "a = req / (α_{1}·φc·f'c·bw)",
                 f"{req_kN*1000:.0f} / ({a1:.4f}×0.65×{fc}×{bw})",
                 f"a = {a_val} mm")
        else:
            step("Cl.10.3.2", "Stress-block depth  a  (N.A. in flange)",
                 "a = φs·fy·As / (α_{1}·φc·f'c·bf)",
                 f"0.85×{fy}×{As:.0f} / ({a1:.4f}×0.65×{fc}×{r['b']})",
                 f"a = {a_val} mm")
    else:
        step("Cl.10.3.2", "Equivalent stress-block depth  a",
             "a = φs·fy·As / (α_{1}·φc·f'c·bw)",
             f"0.85×{fy}×{As:.0f} / ({a1:.4f}×0.65×{fc}×{bw})",
             f"a = {a_val} mm")

    step("Cl.10.3.2", "Neutral axis depth  c",
         "c = a / β_{{1}}",
         f"{a_val} / {b1_val:.4f}",
         f"c = {c_val} mm")

    if r["is_T_beam"] and r.get("flange_na")=="in web":
        Cf_fl = a1*0.65*fc*(r['b']-bw)*r['hf']
        Cw    = a1*0.65*fc*bw*a_val
        mr_sub= f"({Cf_fl/1000:.1f})×({d}-{r['hf']}/2)x10^{{-3}} + ({Cw/1000:.1f})×({d}-{a_val}/2)x10^{{-3}}"
    else:
        mr_sub = f"0.85×{fy}×{As:.0f}×({d:.0f} − {a_val}/2) / 10^{{6}}"
    step("Cl.10.3.2", "Factored moment resistance  Mr",
         "Mr = φs·fy·As·(d − a/2)    [or T-beam sum of moments]",
         mr_sub,
         f"Mr = {Mr} kN·m", passed=c["flex"])

    eps_t_val = r["eps_t"]; eps_y_val = n.get("eps_y","0.00200")
    step("Cl.10.5.2", "Net tensile strain  εt  (ductility)",
         "εt = 0.0035·(d − c) / c",
         f"0.0035×({d:.0f} − {c_val}) / {c_val}",
         f"εt = {eps_t_val:.5f}  ≥  εy = {eps_y_val}", passed=c["ductile"])

    step("Cl.10.5.1", "Minimum tension steel  As,min",
         "As,min = max( 0.2√f'c/fy·bw·d,  1.4/fy·bw·d )",
         f"max( 0.2×√{fc}/{fy}×{bw}×{d:.0f},  1.4/{fy}×{bw}×{d:.0f} )",
         f"As,min = {r['As_min']:.0f} mm^{{2}}",
         passed=c["As_min"],
         note=f"As = {As:.0f} mm^{{2}}  {'≥' if c['As_min'] else '<'}  As,min = {r['As_min']:.0f} mm^{{2}}")

    c_max_val = 700*0.8*d/(700+fy)
    step("Cl.10.5.2", "Maximum tension steel  As,max",
         "c,max = 700·0.8·d / (700 + fy);  As,max = α_{1}·φc·f'c·bw·β_{1}·c,max / (φs·fy)",
         f"c,max = 700×0.8×{d:.0f} / (700+{fy})  =  {c_max_val:.1f} mm",
         f"As,max = {r['As_max']:.0f} mm^{{2}}",
         passed=c["As_max"],
         note=f"As = {As:.0f} mm^{{2}}  {'≤' if c['As_max'] else '>'}  As,max = {r['As_max']:.0f} mm^{{2}}")

    # ── SECTION 4: SHEAR ──────────────────────────────────────────────────
    section_title("4", "Shear Design  (Cl. 11.3  —  Simplified Method, θ = 35°)")
    advance(4)

    dv = r["dv"]
    step("Cl.11.3.2", "Effective shear depth  dv",
         "dv = max( 0.9·d,  0.72·h )",
         f"max( 0.9×{d:.0f},  0.72×{h} )  =  max( {0.9*d:.0f},  {0.72*h:.0f} )",
         f"dv = {dv} mm")

    info_line("Inclination angle:  θ = 35°  (simplified method, Cl. 11.3.6.2)")
    blank(4)

    has_stir = Av > 0 and s > 0
    beta_v   = r["beta_v"]
    if has_stir:
        step("Cl.11.3.6.2", "Factor β  (transverse reinforcement present)",
             "β = 0.18  (simplified, Cl. 11.3.6.2)",
             "Transverse reinf. provided  →  use simplified β",
             f"β = 0.18")
    else:
        step("Cl.11.3.6.3", "Factor β  (no transverse reinforcement)",
             "β = 230 / (1000 + dv)",
             f"230 / (1000 + {dv})",
             f"β = {beta_v:.4f}")

    Vc_sub = f"0.65×1.0×{beta_v}×√{fc}×{bw}×{dv}"
    step("Cl.11.3.4", "Concrete shear resistance  Vc",
         "Vc = φ_{{c}}·λ·β·√(f'c)·bw·dv",
         Vc_sub,
         f"Vc = {r['Vc']:.2f} kN")

    if has_stir:
        cot35 = 1.0/math.tan(math.radians(35))
        step("Cl.11.3.5", "Steel shear resistance  Vs",
             "Vs = φs·Av·fyt·dv·cot θ / s",
             f"0.85×{Av:.0f}×{fyt}×{dv}×cot 35° / {s:.0f}  =  0.85×{Av:.0f}×{fyt}×{dv}×{cot35:.3f}/{s:.0f}",
             f"Vs = {r['Vs']:.2f} kN")

        Vr_check = r["Vc"] + r["Vs"]
        step("Cl.11.3.3", "Maximum shear resistance  Vr,max",
             "Vr,max = 0.25·φc·f'c·bw·dv",
             f"0.25×0.65×{fc}×{bw}×{dv}",
             f"Vr,max = {r['Vr_max']:.2f} kN")
        step("Cl.11.3.3", "Total factored shear resistance  Vr",
             "Vr = min( Vc + Vs,  Vr,max )",
             f"min( {r['Vc']} + {r['Vs']},  {r['Vr_max']} )  =  min( {Vr_check:.2f},  {r['Vr_max']} )",
             f"Vr = {r['Vr']:.2f} kN  ≥  Vf = {r['Vf']:.2f} kN",
             passed=c["shear"])

        Av_min_req = 0.06*math.sqrt(fc)*bw*s/fyt
        step("Cl.11.2.8.1", "Minimum transverse reinforcement  Av,min",
             "Av,min = 0.06·√f'c·bw·s / fyt",
             f"0.06×√{fc}×{bw}×{s:.0f}/{fyt}",
             f"Av,min = {r['Av_min_s']:.1f} mm^{{2}}",
             passed=c["Av_min"],
             note=f"Av = {Av:.0f} mm^{{2}}  {'≥' if c['Av_min'] else '<'}  Av,min = {r['Av_min_s']:.1f} mm^{{2}}")

        smax_note = ("0.125φcf'cbwdv governs" if r["Vf"] > 0.125*0.65*fc*bw*dv
                     else "Low shear — use 0.7dv limit")
        step("Cl.11.3.8", "Maximum stirrup spacing  s,max",
             "s,max = min(0.35·dv, 300)  or  min(0.7·dv, 600)  depending on Vf",
             smax_note,
             f"s,max = {r['s_max']:.0f} mm",
             passed=c["s_max"],
             note=f"s = {s:.0f} mm  {'≤' if c['s_max'] else '>'}  s,max = {r['s_max']:.0f} mm")
    else:
        step("Cl.11.3.3", "Total factored shear resistance  Vr  (no stirrups)",
             "Vr = Vc",
             f"Vr = {r['Vc']:.2f} kN",
             f"Vr = {r['Vr']:.2f} kN  vs  Vf = {r['Vf']:.2f} kN",
             passed=c["shear"])
        info_line("⚠  No stirrups provided — verify minimum transverse reinf. per Cl. 11.2.8")

    # ── SECTION 5: TORSION ────────────────────────────────────────────────
    sec_num = 5
    if r["Tf"] > 0:
        section_title(str(sec_num), "Torsion Check  (Cl. 11.2.9)")
        advance(4)
        Acp = bw*h; Pcp = 2*(bw+h)
        Tcr_val = r["Tcr"]
        step("Cl.11.2.9.1", "Area and perimeter of gross section",
             "Acp = bw·h    Pcp = 2·(bw + h)",
             f"Acp = {bw}×{h} = {Acp:.0f} mm^{{2}}    Pcp = 2×({bw}+{h}) = {Pcp:.0f} mm",
             f"Acp = {Acp:.0f} mm^{{2}}   Pcp = {Pcp:.0f} mm")
        step("Cl.11.2.9.1", "Torsional cracking moment  Tcr",
             "Tcr = φc·λ·0.38·√f'c·(Acp^{2} / Pcp)",
             f"0.65x1.0x0.38x√({fc})x({Acp:.0f}^{{2}} / {Pcp:.0f})",
             f"Tcr = {Tcr_val} kN·m",
             passed=c["torsion_threshold"],
             note=f"Tf = {r['Tf']} kN·m  {'≤' if c['torsion_threshold'] else '>'} Tcr = {Tcr_val} kN·m  {'— torsion may be neglected' if c['torsion_threshold'] else '— full torsion design required (Cl. 11.3.9)'}")
        sec_num += 1

    # ── SECTION: DETAILING ────────────────────────────────────────────────
    section_title(str(sec_num), "Detailing Checks  (Cl. 7.5 / 7.9 / 10.6.4 / 12.2)")
    advance(4)

    step("Cl.7.9", "Clear cover to stirrups",
         "cc ≥ 40 mm  (beams, normal exposure)",
         f"Provided cc = {r['cover']} mm",
         f"cc = {r['cover']} mm  ≥  40 mm",
         passed=c["cover_ok"])

    step("Cl.7.6.5", "Minimum bar size",
         "db ≥ 11.3 mm  (10M minimum for beams)",
         f"db = {r['db1']:.1f} mm",
         f"db = {r['db1']:.1f} mm  ≥  11.3 mm",
         passed=c["bar_size_min"])

    sp_min = r["clear_sp_min"]
    step("Cl.7.5.1", "Minimum clear spacing between bars (layer 1)",
         "s,clear ≥ max( 1.4·db,  30 mm )",
         f"max( 1.4×{r['db1']:.1f},  30 )  =  max( {1.4*r['db1']:.1f},  30 )",
         f"s,min = {sp_min:.1f} mm")

    avail = bw - 2*r["cover"] - 2*r["dv_bar"]
    if r["nb1"] > 1:
        sp_sub = f"( {bw} − 2×{r['cover']} − 2×{r['dv_bar']:.1f} − {r['nb1']}×{r['db1']:.1f} ) / ({r['nb1']}−1)"
    else:
        sp_sub = f"{bw} − 2×{r['cover']} − 2×{r['dv_bar']:.1f} − {r['db1']:.1f}"
    step("Cl.7.5.1", "Actual clear spacing between bars (layer 1)",
         "s,clear = ( bw − 2·cc − 2·d_stir − n·db ) / (n−1)",
         sp_sub,
         f"s,clear = {r['clear_sp_actual']:.1f} mm  ≥  s,min = {sp_min:.1f} mm",
         passed=c["bar_spacing"])

    width_sub = f"{r['nb1']}×{r['db1']:.1f} + {r['nb1']-1}×{sp_min:.1f} + 2×{r['cover']} + 2×{r['dv_bar']:.1f}"
    step("Cl.7.5", "Check bars fit in single layer",
         "Width req'd = n·db + (n−1)·s,min + 2·cc + 2·d_stir",
         width_sub,
         f"Width req'd = {r['width_needed']:.0f} mm  vs  bw = {bw} mm",
         passed=c["bars_fit"])

    if r["nb2"] > 0 and r["layer_gap"] is not None:
        gap_min = r["layer_gap_min"]
        step("Cl.7.5.1", "Clear gap between bar layers",
             "gap ≥ max( 1.4·db,  30 mm )",
             f"max( 1.4×max({r['db1']:.1f},{r['db2']:.1f}),  30 )  =  {gap_min:.1f} mm",
             f"gap = {r['layer_gap']:.1f} mm  ≥  {gap_min:.1f} mm",
             passed=c["layer_gap_ok"])

    fs_s = 0.6*fy
    sp_crack_1 = 380*(280/fs_s) - 2.5*r['cover']
    sp_crack_2 = 300*(280/fs_s)
    step("Cl.10.6.4", "Crack-control maximum bar spacing",
         "s ≤ min[ 380·(280/fs) − 2.5·cc,   300·(280/fs) ]    fs = 0.6·fy",
         f"min[ 380×(280/{fs_s:.0f})−2.5×{r['cover']},   300×(280/{fs_s:.0f}) ] = min({sp_crack_1:.0f},{sp_crack_2:.0f})",
         f"s,max = {r['sp_crack_max']:.1f} mm  vs  s,act = {r['clear_sp_actual']:.1f} mm",
         passed=c["crack_spacing"])

    ld_basic = 0.45*(fy/(1.0*math.sqrt(fc)))*r["db1"]
    step("Cl.12.2", "Basic tension development length  ld",
         "ld = 0.45·k_{1}·k_{2}·k_{3}·k_{4}·(fy / λ√f'c)·db    [k-factors = 1.0]",
         f"0.45×1×1×1×1×({fy} / 1.0×√{fc})×{r['db1']:.1f}  =  max({ld_basic:.0f},300)",
         f"ld = {r['ld']:.0f} mm",
         note="Reduce per Cl. 12.2.4 where confinement / cover conditions are favourable")

    sec_num += 1

    # ── SECTION: DEFLECTION ───────────────────────────────────────────────
    section_title(str(sec_num), "Cracking & Deflection  (Cl. 9.8.2  —  Branson)")
    advance(4)

    Ig_val  = bw*h**3/12
    fr_val  = 0.6*math.sqrt(fc)
    Mcr_val = fr_val*Ig_val/(h/2)
    n_r     = n.get("n_ratio", Es/Ec)
    # kd from quadratic
    A_q=bw/2; B_q=n_r*As; C_q=-B_q*d
    kd = (-B_q+math.sqrt(B_q**2-4*A_q*C_q))/(2*A_q)

    step("Cl.9.8.2.3", "Gross moment of inertia  Ig",
         "Ig = bw·h^{{3}} / 12",
         f"{bw}x{h}^{{3}} / 12",
         f"Ig = {r['Ig']:.0f}x10^{{6}} mm^{{4}}")

    step("Cl.9.8.2.3", "Modulus of rupture  fr",
         "fr = 0.6·λ·√f'c",
         f"0.6×1.0×√{fc}",
         f"fr = {fr_val:.3f} MPa")

    step("Cl.9.8.2.3", "Cracking moment  Mcr",
         "Mcr = fr·Ig / yt    (yt = h/2  for rect. section)",
         f"{fr_val:.3f}×{r['Ig']:.0f}x10^{{6}} / ({h}/2)",
         f"Mcr = {r['Mcr']:.2f} kN·m")

    step("Cl.9.8.2.4", "Cracked section — neutral axis depth  kd  (transformed)",
         "bw/2·kd^{2} + n·As·kd − n·As·d = 0    (quadratic in kd)",
         f"{bw}/2·kd^{{2}} + {n_r:.2f}×{As:.0f}·kd − {n_r:.2f}×{As:.0f}×{d:.0f} = 0",
         f"kd = {kd:.1f} mm")

    Icr_val = bw*kd**3/3 + n_r*As*(d-kd)**2
    step("Cl.9.8.2.4", "Cracked moment of inertia  Icr",
         "Icr = bw·kd^{3}/3 + n·As·(d - kd)^{2}",
         f"{bw}×{kd:.1f}^{{3}}/3 + {n_r:.2f}×{As:.0f}×({d:.0f}−{kd:.1f})^{{2}}",
         f"Icr = {r['Icr']:.0f}x10^{{6}} mm^{{4}}")

    Ma    = r["Mf"]*1e6
    ratio = (Mcr_val/max(Ma,1))**3
    Ie_val= min(ratio*Ig_val+(1-ratio)*Icr_val, Ig_val)
    step("Cl.9.8.2.4", "Effective moment of inertia  Ie  (Branson)",
         "Ie = (Mcr/Ma)^{3}·Ig + [1−(Mcr/Ma)^{3}]·Icr  ≤  Ig",
         f"({r['Mcr']}/{r['Mf']})^{{3}}×{r['Ig']:.0f}x10^{{6}} + [1−({r['Mcr']}/{r['Mf']})^{{3}}]×{r['Icr']:.0f}x10^{{6}}",
         f"Ie = {r['Ie']:.0f}x10^{{6}} mm^{{4}}  {'(cracked — use Ie)' if r['Mf']>r['Mcr'] else '(uncracked — Ie = Ig)'}")
    sec_num += 1

    # ── SECTION: SUMMARY ──────────────────────────────────────────────────
    section_title(str(sec_num), "Summary of Results")
    advance(6)

    # Column headers
    y_hdr = state["y"]
    canv.setFillColor(colors.HexColor("#EFF6FF"))
    canv.rect(LM-2, y_hdr-LINE_H, CW+4, LINE_H, fill=1, stroke=0)
    canv.setFont(*F_BOLD); canv.setFillColor(C_NAVY)
    canv.drawString(LM+4,       y_hdr-11, "Check")
    canv.drawString(LM+2.6*inch, y_hdr-11, "Demand")
    canv.drawString(LM+4.4*inch, y_hdr-11, "Capacity")
    canv.drawRightString(RM,    y_hdr-11, "Status")
    advance(LINE_H + 2)
    rule(state["y"], width=0.5, color=C_NAVY)

    check_line("Flexure  Mr ≥ Mf",
               f"Mf = {r['Mf']} kN·m",    f"Mr = {r['Mr']} kN·m",    c["flex"])
    check_line("Ductility  εt ≥ εy",
               f"εy = {n.get('eps_y','—')}", f"εt = {r['eps_t']:.5f}",  c["ductile"])
    check_line("Min. steel  As ≥ As,min",
               f"As,min = {r['As_min']:.0f} mm^{{2}}", f"As = {As:.0f} mm^{{2}}", c["As_min"])
    check_line("Max. steel  As ≤ As,max",
               f"As,max = {r['As_max']:.0f} mm^{{2}}", f"As = {As:.0f} mm^{{2}}", c["As_max"])
    check_line("Shear  Vr ≥ Vf",
               f"Vf = {r['Vf']} kN",        f"Vr = {r['Vr']} kN",        c["shear"])
    if has_stir:
        check_line("Stirrups  Av ≥ Av,min",
                   f"Av,min = {r['Av_min_s']:.1f} mm^{{2}}", f"Av = {Av:.0f} mm^{{2}}", c["Av_min"])
        check_line(f"Stirrup spacing  s ≤ s,max",
                   f"s,max = {r['s_max']:.0f} mm",  f"s = {s:.0f} mm",     c["s_max"])
    check_line("Cover  cc ≥ 40 mm",
               "40 mm",                     f"cc = {r['cover']} mm",     c["cover_ok"])
    check_line("Bar size ≥ 10M",
               "db ≥ 11.3 mm",              f"db = {r['db1']:.1f} mm",   c["bar_size_min"])
    check_line("Bars fit in section",
               f"bw = {bw} mm",             f"need {r['width_needed']:.0f} mm", c["bars_fit"])
    check_line("Clear spacing ≥ min",
               f"min = {sp_min:.0f} mm",    f"act = {r['clear_sp_actual']:.1f} mm", c["bar_spacing"])
    check_line("Crack-control spacing",
               f"max = {r['sp_crack_max']:.0f} mm", f"act = {r['clear_sp_actual']:.1f} mm", c["crack_spacing"])
    if r["nb2"] > 0 and r["layer_gap"] is not None:
        check_line("Layer gap ≥ min",
                   f"min = {r['layer_gap_min']:.0f} mm", f"gap = {r['layer_gap']:.1f} mm", c["layer_gap_ok"])
    if r["Tf"] > 0:
        check_line("Torsion  Tf ≤ Tcr",
                   f"Tf = {r['Tf']} kN·m", f"Tcr = {r['Tcr']} kN·m", c["torsion_threshold"])

    advance(10)
    rule(state["y"], width=0.8, color=C_NAVY)
    advance(6)
    ensure_space(20)
    ok2 = r["overall_pass"]
    bg3 = colors.HexColor("#DCFCE7") if ok2 else colors.HexColor("#FEE2E2")
    col3= C_GREEN if ok2 else C_RED
    msg3= "ALL CHECKS PASSED" if ok2 else "ONE OR MORE CHECKS FAILED — REVIEW REQUIRED"
    bw4 = canv.stringWidth(f"  {'✓' if ok2 else '✗'}   {msg3}  ", "Helvetica-Bold", 11) + 8
    canv.setFillColor(bg3); canv.setStrokeColor(col3); canv.setLineWidth(1)
    canv.roundRect(LM, state["y"]-17, bw4, 19, 3, fill=1, stroke=1)
    canv.setFont("Helvetica-Bold", 11); canv.setFillColor(col3)
    canv.drawString(LM+8, state["y"]-13, f"{'✓' if ok2 else '✗'}   {msg3}")

    # ── FINISH ────────────────────────────────────────────────────────────
    draw_footer()
    canv.save()
    return filepath
