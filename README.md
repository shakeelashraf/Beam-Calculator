# CSA A23.3-19 Beam Analyzer — Streamlit Web App

A browser-based concrete beam design tool covering flexure, shear, torsion,
deflection, and detailing per CSA A23.3-19, with a downloadable textbook-style
PDF hand-calculation report.

## Files

```
app.py               ← main Streamlit app (UI)
engine.py            ← CSA A23.3-19 calculation engine (BeamAnalysis class)
pdf_report.py         ← textbook-style PDF report generator
section_diagram.py    ← matplotlib cross-section diagram
requirements.txt      ← Python dependencies
DejaVuSans*.ttf       ← fonts for PDF (Greek letters, sub/superscripts)
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Deploy to a shareable link (free — Streamlit Community Cloud)

1. **Create a GitHub repo** and push all the files above into it
   (must include the 4 `.ttf` font files alongside `app.py`).

2. **Go to** [share.streamlit.io](https://share.streamlit.io) and sign in
   with your GitHub account.

3. Click **"New app"**, select your repo, branch, and set the main file
   path to `app.py`.

4. Click **Deploy**. After a minute or two you'll get a public link like:

   ```
   https://your-app-name.streamlit.app
   ```

   Share that URL with anyone — no installation needed on their end, it
   runs entirely in the browser.

### Notes
- Free tier apps sleep after inactivity and wake on the next visit
  (~10–20 second cold start).
- If you update the code, just push to GitHub — Streamlit Cloud
  auto-redeploys.
- For a custom domain or private/internal access, look into Streamlit
  Cloud's paid tiers, or self-host on Render / Railway / a VPS using the
  same `requirements.txt` and `streamlit run app.py` command.

## Alternative: self-host anywhere

Any platform that can run a Python web process works (Render, Railway,
Fly.io, a VPS, etc.). The general pattern:

```bash
pip install -r requirements.txt
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```
