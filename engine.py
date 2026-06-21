"""
CSA A23.3-19 Beam Analysis Engine
Framework-agnostic — used by both the Streamlit web app and the desktop Tkinter app.
"""
import math

REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
               "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}
REBAR_AREA = {k: math.pi*(d/2)**2 for k, d in REBAR_SIZES.items()}

def bar_name(db):
    REBAR_SIZES = {"10M":11.3,"15M":16.0,"20M":19.5,"25M":25.2,
                   "30M":29.9,"35M":35.7,"45M":43.7,"55M":56.4}
    for k,v in REBAR_SIZES.items():
        if abs(v-db)<0.5: return k
    return f"d={db:.1f}mm"

#  A23.3-19 ENGINE
# ══════════════════════════════════════════════════════════════════════════════
PHI_C    = 0.65
PHI_S    = 0.85
LAMBDA_N = 1.0

def alpha1(fc): return max(0.85 - 0.0015*fc, 0.67)
def beta1(fc):  return max(0.97 - 0.0025*fc, 0.67)
def ec_mod(fc, wc=2400): return (3300*math.sqrt(fc)+6900)*(wc/2300)**1.5

class BeamAnalysis:
    def __init__(self, p):
        self.p = p
        self.results = {}
        self.checks  = {}
        self.notes   = {}

    def run(self):
        p=self.p; r=self.results; c=self.checks; n=self.notes
        fc=p["fc"]; fy=p["fy"]; fyt=p["fyt"]
        bw=p["bw"]; h=p["h"]
        bf  = p.get("bf", 0)
        b   = bf if bf > bw else bw
        hf  = p.get("hf", 0)
        Es  = 200000.0
        cover = p.get("cover", 40)
        dv_bar = p.get("dv_bar", 11.3)   # stirrup diameter

        # ── Bottom layer 1 (tension) ─────────────────────────────────────────
        nb1  = p.get("nb1", 4);   db1 = p.get("db1", 19.5)
        As1  = nb1 * math.pi*(db1/2)**2
        d1   = p.get("d1", h - cover - dv_bar - db1/2)   # centroid layer 1

        # ── Bottom layer 2 (optional) ────────────────────────────────────────
        nb2  = p.get("nb2", 0);   db2 = p.get("db2", 19.5)
        As2  = nb2 * math.pi*(db2/2)**2 if nb2 > 0 else 0.0
        d2   = p.get("d2", d1 - db1/2 - max(1.4*db1, 30) - db2/2) if nb2>0 else 0.0

        # Total tension steel and weighted effective depth
        As = As1 + As2
        if As2 > 0:
            d  = (As1*d1 + As2*d2) / As   # resultant effective depth
        else:
            d  = d1

        # ── Top steel (compression) ──────────────────────────────────────────
        nb_top  = p.get("nb_top", 0);  db_top = p.get("db_top", 19.5)
        As_top  = nb_top * math.pi*(db_top/2)**2 if nb_top > 0 else 0.0
        d_top   = cover + dv_bar + db_top/2   # centroid from top

        # ── Store for display / canvas ───────────────────────────────────────
        Av   = p.get("Av", 0); s = p.get("s", 0)
        Mf   = p["Mf"]; Vf = p["Vf"]; Tf = p.get("Tf", 0)

        r.update({"fc":fc,"fy":fy,"fyt":fyt,"bw":bw,"d":round(d,1),"h":h,
                  "cover":cover,"b":b,"hf":hf,
                  "As":round(As,1),"As1":round(As1,1),"As2":round(As2,1),
                  "As_top":round(As_top,1),
                  "nb1":nb1,"db1":db1,"d1":round(d1,1),
                  "nb2":nb2,"db2":db2,"d2":round(d2,1) if nb2>0 else 0,
                  "nb_top":nb_top,"db_top":db_top,"d_top":round(d_top,1),
                  "Av":Av,"s":s,"dv_bar":dv_bar})

        # ── Material ──────────────────────────────────────────────────────────
        a1=alpha1(fc); b1=beta1(fc); Ec=ec_mod(fc)
        r.update({"alpha1":a1,"beta1":b1,"Ec":Ec})
        n["n_ratio"] = round(Es/Ec, 2)

        # ── T-beam / rectangular ─────────────────────────────────────────────
        is_T = (b > bw) and (hf > 0); r["is_T_beam"] = is_T

        # Compression steel contribution (ignored in simplified approach — conservative)
        # Pure tension-controlled flexure
        if is_T:
            Cf_fl = a1*PHI_C*fc*(b-bw)*hf
            req   = PHI_S*fy*As - Cf_fl
            if req > 0:
                a_val   = req / (a1*PHI_C*fc*bw)
                Mr      = Cf_fl*(d-hf/2) + a1*PHI_C*fc*bw*a_val*(d-a_val/2)
                c_depth = a_val/b1; r["flange_na"] = "in web"
            else:
                a_val   = (PHI_S*fy*As) / (a1*PHI_C*fc*b)
                Mr      = PHI_S*fy*As*(d-a_val/2)
                c_depth = a_val/b1; r["flange_na"] = "in flange"
        else:
            a_val   = (PHI_S*fy*As) / (a1*PHI_C*fc*bw)
            Mr      = PHI_S*fy*As*(d-a_val/2); c_depth = a_val/b1

        r.update({"a":round(a_val,1), "c":round(c_depth,1), "Mr":round(Mr/1e6,2)})

        eps_t = 0.0035*(d-c_depth)/c_depth; eps_y = fy/Es
        r["eps_t"] = round(eps_t,5); n["eps_y"] = round(eps_y,5)
        c["ductile"] = eps_t >= eps_y

        As_min = max(0.2*math.sqrt(fc)/fy*bw*d, 1.4/fy*bw*d)
        r["As_min"] = round(As_min,1); c["As_min"] = As >= As_min

        c_max  = 0.0035*d / (0.0035+0.004)
        As_max = a1*PHI_C*fc*bw*b1*c_max / (PHI_S*fy)
        r["As_max"] = round(As_max,1); c["As_max"] = As <= As_max

        Mf_kNm=Mf/1e6; Mr_kNm=Mr/1e6
        r["Mf"] = round(Mf_kNm,2); c["flex"] = Mr_kNm >= Mf_kNm
        r["flex_ratio"] = round(Mr_kNm/Mf_kNm,3) if Mf_kNm>0 else None

        # ── Shear — simplified method θ=35°, β per Cl. 11.3.6 ───────────────
        # Cl. 11.3.2
        dv = max(0.9*d, 0.72*h); r["dv"] = round(dv,1)

        # β — Cl. 11.3.6.2 (with transverse reinf.): β = 0.18
        #   — Cl. 11.3.6.3 (without transverse reinf.): β = 230/(1000+sze)
        #     where sze = 300 mm assumed (aggregate ≥ 20 mm)
        has_stirrups = (Av > 0 and s > 0)
        theta_v = 35.0   # simplified, Cl. 11.3.6.2
        if has_stirrups:
            beta_v = 0.18                       # Cl. 11.3.6.2 simplified
            r["beta_method"] = "0.18  (Cl. 11.3.6.2 — transverse reinf. present)"
        else:
            beta_v = 230.0 / (1000.0 + dv)     # Cl. 11.3.6.3 — no transverse reinf.
            r["beta_method"] = f"230/(1000+dv)={beta_v:.4f}  (Cl. 11.3.6.3 — no transverse reinf., dv={dv:.0f}mm)"

        r["beta_v"]  = round(beta_v, 4)
        r["theta_v"] = theta_v

        Vc = PHI_C*LAMBDA_N*beta_v*math.sqrt(fc)*bw*dv
        r["Vc"] = round(Vc/1e3,2)
        Vs = (PHI_S*Av*fyt*dv*(1/math.tan(math.radians(theta_v)))/s) if has_stirrups else 0
        r["Vs"] = round(Vs/1e3,2)
        Vr_max = 0.25*PHI_C*fc*bw*dv
        Vr     = min(Vc+Vs, Vr_max)
        r.update({"Vr":round(Vr/1e3,2),"Vr_max":round(Vr_max/1e3,2),"Vf":round(Vf/1e3,2)})
        c["shear"]       = Vr/1e3 >= Vf/1e3
        r["shear_ratio"] = round(Vr/1e3/(Vf/1e3),3) if Vf>0 else None

        Av_min = 0.06*math.sqrt(fc)*bw*s/fyt if s>0 else 0
        r["Av_min_s"] = round(Av_min,1); c["Av_min"] = (Av>=Av_min) if s>0 else True
        s_max = min(0.35*dv,300) if Vf>0.125*PHI_C*fc*bw*dv else min(0.7*dv,600)
        r["s_max"] = round(s_max,1); c["s_max"] = (s<=s_max) if s>0 else True

        # ── Torsion ───────────────────────────────────────────────────────────
        if Tf > 0:
            Acp=bw*h; Pcp=2*(bw+h)
            Tcr=PHI_C*LAMBDA_N*0.38*math.sqrt(fc)*(Acp**2/Pcp)
            r["Tcr"]=round(Tcr/1e6,2); r["Tf"]=round(Tf/1e6,2)
            c["torsion_threshold"]=Tf<=Tcr
        else:
            r["Tcr"]=None; r["Tf"]=0; c["torsion_threshold"]=True

        # ── Deflection / cracking ─────────────────────────────────────────────
        Ig=bw*h**3/12; yt=h/2
        fr=0.6*LAMBDA_N*math.sqrt(fc); Mcr=fr*Ig/yt
        r["Mcr"]=round(Mcr/1e6,2); r["Ig"]=round(Ig/1e6,1)
        A_q=bw/2; B_q=(Es/Ec)*As; C_q=-B_q*d
        kd=(-B_q+math.sqrt(B_q**2-4*A_q*C_q))/(2*A_q)
        Icr=bw*kd**3/3+(Es/Ec)*As*(d-kd)**2
        r["Icr"]=round(Icr/1e6,1)
        ratio=(Mcr/max(Mf,1))**3
        Ie=min(ratio*Ig+(1-ratio)*Icr,Ig)
        r["Ie"]=round(Ie/1e6,1)

        # ── Detailing ─────────────────────────────────────────────────────────
        cover_min=40.0; r["cover_min"]=cover_min; c["cover_ok"]=cover>=cover_min

        # Min clear spacing Cl. 7.5.1: max(1.4·db, 30mm)
        clear_sp_min = max(1.4*db1, 30.0)
        r["clear_sp_min"] = round(clear_sp_min,1)
        avail = bw - 2*cover - 2*dv_bar
        clear_sp_actual = (avail - nb1*db1)/(nb1-1) if nb1>1 else avail-db1
        r["clear_sp_actual"] = round(clear_sp_actual,1)
        c["bar_spacing"] = clear_sp_actual >= clear_sp_min

        # 2-layer vertical gap check
        if nb2 > 0:
            gap_between = d1 - db1/2 - (d2 + db2/2)   # clear gap between layers
            gap_min     = max(1.4*max(db1,db2), 30.0)
            r["layer_gap"]     = round(gap_between,1)
            r["layer_gap_min"] = round(gap_min,1)
            c["layer_gap_ok"]  = gap_between >= gap_min
        else:
            r["layer_gap"]=None; r["layer_gap_min"]=None; c["layer_gap_ok"]=True

        # Crack control Cl. 10.6.4
        fs_service=0.6*fy; cc=cover
        sp_crack=min(380*(280/fs_service)-2.5*cc, 300*(280/fs_service))
        r["sp_crack_max"]=round(sp_crack,1)
        c["crack_spacing"]=(clear_sp_actual<=sp_crack) if nb1>1 else True

        # Bars fit in single layer
        width_needed=nb1*db1+(nb1-1)*clear_sp_min+2*cover+2*dv_bar
        r["width_needed"]=round(width_needed,1); c["bars_fit"]=width_needed<=bw

        # Min bar size Cl. 7.6.5
        c["bar_size_min"] = db1 >= 11.3

        # Development length Cl. 12.2
        ld_basic=0.45*(fy/(LAMBDA_N*math.sqrt(fc)))*db1
        r["ld"]=round(max(ld_basic,300.0),0)

        r["overall_pass"]=all(c.values())
        return r, c, n
