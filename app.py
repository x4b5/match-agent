#!/usr/bin/env python3
"""Streamlit frontend voor PaperStrip met UX/UI verbeteringen."""

import json
import os
import subprocess
import time
import shutil

import requests
import streamlit as st
from database import init_db, bewaar_match, haal_matches_voor_vacature, haal_unieke_vacatures
init_db()

# --- Standaard Streamlit Pagina Configuratie ---
# MOET het eerste Streamlit commando in de file zijn!
st.set_page_config(
    page_title="PaperStrip",
    page_icon="icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css():
    css_pad = os.path.join(os.path.dirname(__file__), "static", "style.css")
    with open(css_pad, "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)



inject_custom_css()

from config import (
    KANDIDATEN_DIR,
    MATCH_MODI,
    MATCH_PROMPT,
    OLLAMA_MODEL,
    OLLAMA_URL,
    RAPPORT_DIR,
    SYSTEM_PROMPT,
    WERKGEVERSVRAGEN_DIR,
)
from paper_agent import (
    extract_naam_uit_cv,
    extract_vacature_titel,
    genereer_rapport,
    vraag_ollama,
    vraag_ollama_stream,
)
from profiel_agent import (
    laad_profiel_uit_map,
    genereer_profiel_voor_map,
    profileer_kandidaat,
    profileer_werkgeversvraag,
    vind_meest_recente_profiel,
    laad_ruwe_tekst_uit_map,
)

# --- Standaardwaarden in session state ---
if "ollama_url" not in st.session_state:
    st.session_state.ollama_url = OLLAMA_URL
if "ollama_model" not in st.session_state:
    st.session_state.ollama_model = OLLAMA_MODEL
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.3
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = SYSTEM_PROMPT
if "match_prompt" not in st.session_state:
    st.session_state.match_prompt = MATCH_PROMPT


# --- Helpers ---
def ollama_base_url() -> str:
    url = st.session_state.ollama_url
    if "/api/" in url:
        return url.split("/api/")[0]
    return url

@st.cache_data(ttl=10)
def check_ollama_status() -> tuple[bool, list[str]]:
    try:
        resp = requests.get(f"{ollama_base_url()}/api/tags", timeout=5)
        resp.raise_for_status()
        modellen = [m["name"] for m in resp.json().get("models", [])]
        return True, modellen
    except Exception:
        return False, []

@st.cache_data(ttl=5)
def lijst_mappen(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    mappen = []
    for f in sorted(os.listdir(directory)):
        if f.startswith("."):
            continue
        if os.path.isdir(os.path.join(directory, f)):
            mappen.append(f)
    return mappen

@st.cache_data(ttl=5)
def heeft_profiel(directory: str, map_naam: str) -> bool:
    pad = os.path.join(directory, map_naam)
    if not os.path.isdir(pad):
        return False
    return any(f.endswith(".json") for f in os.listdir(pad))

@st.cache_data(ttl=5)
def lijst_bestanden(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    return sorted([f for f in os.listdir(directory) if not f.startswith(".") and os.path.isfile(os.path.join(directory, f))])


# --- Dialogs voor veilige acties ---
@st.dialog("Weet je zeker dat je dit wilt verwijderen?")
def bevestig_verwijder_map(pad: str, map_naam: str):
    st.warning(f"Map '{map_naam}' en alle bestanden (inclusief profiel) worden definitief verwijderd.")
    if st.button("Verwijder definitief", type="primary", width="stretch"):
        try:
            shutil.rmtree(pad)
            st.cache_data.clear()
            st.toast(f"Map '{map_naam}' is verwijderd.", icon=":material/delete:")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij verwijderen: {e}")

@st.dialog("Weet je zeker dat je dit document wilt verwijderen?")
def bevestig_verwijder_doc(pad: str, bestandsnaam: str):
    st.warning(f"Document '{bestandsnaam}' wordt definitief verwijderd.")
    if st.button("Verwijder definitief", type="primary", width="stretch"):
        try:
            os.remove(pad)
            st.cache_data.clear()
            st.toast(f"'{bestandsnaam}' is verwijderd.", icon=":material/delete:")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij verwijderen: {e}")


# --- Pagina's (Functies) ---
def _status_dot(is_online: bool) -> str:
    """Geeft een HTML status-dot terug (pulsing groen of rood)."""
    kleur = "#00E676" if is_online else "#FF5252"
    glow = "rgba(0, 230, 118, 0.4)" if is_online else "rgba(255, 82, 82, 0.4)"
    label = "Online" if is_online else "Offline"
    return f"""<span style="
        display: inline-flex; align-items: center; gap: 8px;
        font-size: 0.75rem; font-weight: 700; color: {kleur};
        letter-spacing: 1.5px; text-transform: uppercase;
        padding: 4px 12px; border-radius: 20px;
        background: {'rgba(0,230,118,0.08)' if is_online else 'rgba(255,82,82,0.08)'};
        border: 1px solid {'rgba(0,230,118,0.2)' if is_online else 'rgba(255,82,82,0.2)'};
    "><span style="
        width: 8px; height: 8px; border-radius: 50%;
        background: {kleur};
        box-shadow: 0 0 8px {glow}, 0 0 16px {glow};
        animation: statusPulse 2s ease infinite;
        display: inline-block;
    "></span>{label}</span>"""


def ui_page_header(title: str, subtitle: str = None, icon: str = None):
    """Gezamenlijke header voor alle pagina's met premium styling."""
    icon_html = f'<span style="margin-right: 15px; font-size: 2.2rem;">{icon}</span>' if icon else ""
    subtitle_html = f'<p>{subtitle}</p>' if subtitle else ""

    st.markdown(f"""
    <div class="page-hero">
        <h1>{icon_html}{title}</h1>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)


def render_personality_radar(axes_data):
    """Render een radar chart voor personality axes."""
    try:
        from streamlit_echarts import st_echarts
    except (ImportError, Exception):
        st.warning("Visualisatie library (streamlit-echarts) niet beschikbaar of kon niet laden.")
        return
        
    if not axes_data or not isinstance(axes_data, dict):
        return
    
    keys = list(axes_data.keys())
    values = [axes_data.get(k, 0) for k in keys]
    
    # Zorg dat alle waarden getallen zijn
    clean_values = []
    for v in values:
        try:
            clean_values.append(float(v))
        except (ValueError, TypeError):
            clean_values.append(0.0)

    options = {
        "backgroundColor": "transparent",
        "radar": {
            "indicator": [{"name": k, "max": 100} for k in keys],
            "radius": "65%",
            "axisName": {"color": "rgba(255, 255, 255, 0.6)", "fontSize": 10},
            "splitArea": {"show": False},
            "axisLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.2)"}},
            "splitLine": {"lineStyle": {"color": "rgba(255, 255, 255, 0.1)"}}
        },
        "series": [{
            "name": "Match Profiel",
            "type": "radar",
            "data": [{
                "value": clean_values,
                "name": "Kandidaat",
                "areaStyle": {"color": "rgba(0, 229, 255, 0.2)"},
                "lineStyle": {"color": "#00E5FF", "width": 2},
                "itemStyle": {"color": "#00E5FF"}
            }]
        }]
    }
    st_echarts(options=options, height="250px", key=f"radar_{hash(str(axes_data))}")


def pagina_dashboard():
    ui_page_header("Dashboard", "Overzicht van je matching-omgeving", "📊")

    online, modellen = check_ollama_status()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown(_status_dot(online), unsafe_allow_html=True)
            if online:
                st.metric("Ollama", "Actief", delta="Verbonden")
            else:
                st.metric("Ollama", "Inactief", delta="Geen verbinding", delta_color="inverse")
    with col2:
        with st.container(border=True):
            st.metric("Actief Model", st.session_state.ollama_model)
    with col3:
        with st.container(border=True):
            if online:
                st.metric("Modellen", len(modellen))
            else:
                st.metric("Modellen", "—")

    # Ollie starten / stoppen
    if not online:
        if st.button("Ollama starten", type="primary"):
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with st.spinner("Ollama starten..."):
                for _ in range(15):
                    time.sleep(1)
                    if check_ollama_status()[0]:
                        st.toast("Ollama is gestart!", icon=":material/rocket_launch:")
                        time.sleep(0.5)
                        st.rerun()
                        break
    else:
        if st.button("Ollama stoppen"):
            subprocess.run(["pkill", "-f", "ollama"], capture_output=True)
            st.toast("Ollama is gestopt.", icon=":material/stop_circle:")
            time.sleep(1)
            st.rerun()

    st.divider()

    st.subheader("Data Overzicht")
    colA, colB, colC = st.columns(3)
    
    cvs = lijst_mappen(KANDIDATEN_DIR)
    vacatures = lijst_mappen(WERKGEVERSVRAGEN_DIR)
    rapporten = lijst_bestanden(RAPPORT_DIR)
    
    cvs_aantal = len(cvs)
    vacs_aantal = len(vacatures)
    cvs_profiel_aantal = sum(1 for c in cvs if heeft_profiel(KANDIDATEN_DIR, c))
    vacs_profiel_aantal = sum(1 for v in vacatures if heeft_profiel(WERKGEVERSVRAGEN_DIR, v))
    cvs_geen_profiel = cvs_aantal - cvs_profiel_aantal
    vacs_geen_profiel = vacs_aantal - vacs_profiel_aantal

    with colA:
        with st.container(border=True):
            st.metric("Kandidaten", cvs_aantal, delta=f"{cvs_profiel_aantal} met LLM-profiel", delta_color="normal")
    with colB:
        with st.container(border=True):
            st.metric("Werkgeversvragen", vacs_aantal, delta=f"{vacs_profiel_aantal} met LLM-profiel", delta_color="normal")
    with colC:
        with st.container(border=True):
            st.metric("Gegenereerde Rapporten", len(rapporten))
            
    # Visuele Chart
    st.write("### Profiel Status")
    if cvs_profiel_aantal or cvs_geen_profiel or vacs_profiel_aantal or vacs_geen_profiel:
        import pandas as pd
        chart_data = pd.DataFrame({
            "Categorie": ["Kandidaten", "Kandidaten", "Werkgeversvragen", "Werkgeversvragen"],
            "Status": ["Met Profiel", "Zonder Profiel", "Met Profiel", "Zonder Profiel"],
            "Aantal": [cvs_profiel_aantal, cvs_geen_profiel, vacs_profiel_aantal, vacs_geen_profiel]
        })
        st.bar_chart(
            chart_data,
            x="Categorie",
            y="Aantal",
            color="Status",
            horizontal=True,
        )
    else:
        st.info("Nog geen data beschikbaar voor de grafiek. Voeg kandidaten en werkgeversvragen toe.")

    # Keyboard shortcut hints
    st.markdown("""
    <div style="
        margin-top: 2rem; padding: 12px 0;
        border-top: 1px solid rgba(255,255,255,0.04);
        text-align: center;
    ">
        <span class="kbd-hint"><kbd>⌘</kbd><kbd>K</kbd> Kandidaten</span>
        <span class="kbd-hint"><kbd>⌘</kbd><kbd>M</kbd> Match</span>
        <span class="kbd-hint"><kbd>⌘</kbd><kbd>R</kbd> Rapporten</span>
    </div>
    <div style="
        text-align: center; margin-top: 1rem;
        font-size: 0.65rem; color: rgba(240,242,245,0.15);
        letter-spacing: 1px;
    ">Alle data blijft 100% lokaal op je machine</div>
    """, unsafe_allow_html=True)


def _beheer_bestanden(directory: str, label: str):
    ui_page_header(label, "Beheer dossiers, documenten en LLM-profielen", "📁")

    if not os.path.isdir(directory):
        st.warning(f"Map niet gevonden: {directory}")
        return

    profileer_fn = profileer_kandidaat if "kandidaten" in directory.lower() else profileer_werkgeversvraag
    mappen = lijst_mappen(directory)

    # --- Sorteer staat initialisatie ---
    sort_key_pref = f"sort_key_{label}"
    sort_desc_pref = f"sort_desc_{label}"
    if sort_key_pref not in st.session_state:
        st.session_state[sort_key_pref] = "Naam / ID"
    if sort_desc_pref not in st.session_state:
        st.session_state[sort_desc_pref] = False

    # ── Actie-balk: Nieuw dossier aanmaken ──
    with st.expander(":material/add: Nieuw dossier aanmaken", expanded=False):
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            nieuwe_map = st.text_input("Naam voor nieuwe map/dossier", key=f"nieuwe_map_{label}", placeholder="Bijv. jan_jansen", label_visibility="collapsed")
        with col_btn:
            maak_aan = st.button(":material/add: Aanmaken", key=f"maak_map_{label}", type="primary", width="stretch")
        if maak_aan and nieuwe_map:
            veilige_naam = "".join(c for c in nieuwe_map if c.isalnum() or c in ('_', '-')).strip()
            nieuw_pad = os.path.join(directory, veilige_naam)
            if not os.path.exists(nieuw_pad):
                os.makedirs(nieuw_pad)
                st.cache_data.clear()
                st.toast(f"Map '{veilige_naam}' succesvol aangemaakt!", icon=":material/check_circle:")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Map bestaat al.")

    # ── Batch profiel-generatie ──
    mappen_zonder_profiel = [m for m in mappen if not heeft_profiel(directory, m)]
    if mappen_zonder_profiel:
        if st.button(f":material/auto_awesome: Genereer alle ontbrekende profielen ({len(mappen_zonder_profiel)})", key=f"batch_gen_{label}", type="primary"):
            with st.status(f"Batch profiel-generatie ({len(mappen_zonder_profiel)} dossiers)...", expanded=True) as batch_status:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                geslaagd = 0
                mislukt = 0
                
                with ThreadPoolExecutor(max_workers=min(3, len(mappen_zonder_profiel))) as pool:
                    futures = {pool.submit(genereer_profiel_voor_map, os.path.join(directory, m), profileer_fn): m for m in mappen_zonder_profiel}
                    for idx, future in enumerate(as_completed(futures), 1):
                        m_naam = futures[future]
                        st.write(f":material/sync: [{idx}/{len(mappen_zonder_profiel)}] Analyseren: **{m_naam}**...")
                        try:
                            resultaat = future.result()
                            if isinstance(resultaat, dict):
                                geslaagd += 1
                                st.write(f":material/check_circle: {m_naam} — profiel gereed")
                            else:
                                mislukt += 1
                                st.warning(f"{m_naam}: {resultaat}")
                        except Exception as e:
                            mislukt += 1
                            st.error(f"{m_naam}: Onverwachte fout: {e}")

                st.cache_data.clear()
                batch_status.update(label=f"Batch klaar: {geslaagd} geslaagd, {mislukt} mislukt", state="complete", expanded=False)
                st.toast(f"Batch profiel-generatie voltooid: {geslaagd} geslaagd", icon=":material/check_circle:")
                time.sleep(1)
                st.rerun()

    # ── Filter / Zoekenbalk ──
    filter_tekst = st.text_input(":material/search: Filter op naam", key=f"filter_{label}", placeholder="Typ om te zoeken...", label_visibility="collapsed")
    
    if filter_tekst:
        mappen = [m for m in mappen if filter_tekst.lower() in m.lower()]

    # ── Data Overzicht Tabel ──
    if mappen:
        # Data voorbereiden voor sorteren
        tabel_data = []
        for v in mappen:
            pad = os.path.join(directory, v)
            bestanden_in_map = [f for f in os.listdir(pad) if not f.startswith(".") and not f.endswith(".json") and os.path.isfile(os.path.join(pad, f))]
            aantal_docs = len(bestanden_in_map)
            heeft_prof = heeft_profiel(directory, v)
            
            laatst_gen_tijd = 0
            laatst_gen_str = "N.v.t."
            if heeft_prof:
                for f in os.listdir(pad):
                    if f.endswith(".json"):
                        laatst_gen_tijd = os.path.getmtime(os.path.join(pad, f))
                        laatst_gen_str = time.strftime('%d-%m %H:%M', time.localtime(laatst_gen_tijd))
                        break
            
            profiel = laad_profiel_uit_map(pad)
            betrouwbaarheid = profiel.get("profiel_betrouwbaarheid", 0) if profiel else 0
            
            tabel_data.append({
                "naam": v,
                "docs": aantal_docs,
                "status": heeft_prof,
                "betrouwbaarheid": betrouwbaarheid,
                "laatst_gen_tijd": laatst_gen_tijd,
                "laatst_gen_str": laatst_gen_str,
                "pad": pad
            })

        # Sorteer logica
        s_key = st.session_state[sort_key_pref]
        s_desc = st.session_state[sort_desc_pref]
        
        if s_key == "Naam / ID":
            tabel_data.sort(key=lambda x: x["naam"].lower(), reverse=s_desc)
        elif s_key == "Docs":
            tabel_data.sort(key=lambda x: x["docs"], reverse=s_desc)
        elif s_key == "Status":
            tabel_data.sort(key=lambda x: x["status"], reverse=s_desc)
        elif s_key == "Betrouwbaarheid":
            tabel_data.sort(key=lambda x: x["betrouwbaarheid"], reverse=s_desc)
        elif s_key == "Laatst Gen.":
            tabel_data.sort(key=lambda x: x["laatst_gen_tijd"], reverse=s_desc)

        # Custom Table Header met sorteer-knoppen
        h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.5, 0.8, 1.5, 2.2, 1.5, 1.5])
        
        def sort_button(label_text, key_name):
            icon = ""
            if st.session_state[sort_key_pref] == key_name:
                icon = " 🔽" if st.session_state[sort_desc_pref] else " 🔼"
            if st.button(f"{label_text}{icon}", key=f"sort_{label}_{key_name}", use_container_width=True):
                if st.session_state[sort_key_pref] == key_name:
                    st.session_state[sort_desc_pref] = not st.session_state[sort_desc_pref]
                else:
                    st.session_state[sort_key_pref] = key_name
                    st.session_state[sort_desc_pref] = False
                st.rerun()

        with h_col1: sort_button("Naam / ID", "Naam / ID")
        with h_col2: sort_button("Docs", "Docs")
        with h_col3: sort_button("Status", "Status")
        with h_col4: sort_button("Betrouwbaarheid", "Betrouwbaarheid")
        with h_col5: sort_button("Laatst Gen.", "Laatst Gen.")
        with h_col6: st.markdown("<p style='text-align:center;margin:0;padding-top:8px;font-size:0.8rem;font-weight:bold;'>Acties</p>", unsafe_allow_html=True)
        st.divider()

        for item in tabel_data:
            v = item["naam"]
            pad = item["pad"]
            aantal_docs = item["docs"]
            heeft_prof = item["status"]
            laatst_gegenereerd = item["laatst_gen_str"]

            # Row container (simulated with columns)
            r_col1, r_col2, r_col3, r_col4, r_col5, r_col6 = st.columns([2.5, 0.8, 1.5, 2.0, 1.5, 1.7])
            
            with r_col1:
                st.markdown(f"**{v}**")
            
            with r_col2:
                st.markdown(f"`{aantal_docs}`")
            
            with r_col3:
                if heeft_prof:
                    st.markdown(":green[:material/check_circle: Profiel]")
                else:
                    st.markdown(":orange[:material/warning: Geen profiel]")

            with r_col4:
                if heeft_prof:
                    score = item["betrouwbaarheid"]
                    kleur = "red" if score < 40 else "orange" if score < 75 else "green"
                    st.markdown(f":{kleur}[**{score}%**]")
                else:
                    st.markdown("—")
            
            with r_col5:
                st.markdown(f"<p style='font-size: 0.8rem; margin: 0; padding-top: 4px; color: rgba(240,242,245,0.4);'>{laatst_gegenereerd}</p>", unsafe_allow_html=True)

            with r_col6:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(":material/auto_awesome:", key=f"btn_gen_{label}_{v}", help=f"Genereer profiel voor {v}", type="primary"):
                        with st.spinner(f"Analyseren van {v}..."):
                            nieuw_profiel = genereer_profiel_voor_map(pad, profileer_fn)
                            if isinstance(nieuw_profiel, dict):
                                st.cache_data.clear()
                                st.toast(f"Profiel voor '{v}' gegenereerd!", icon=":material/check_circle:")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Fout bij genereren voor {v}: {nieuw_profiel}")
                with c2:
                    if st.button(":material/delete:", key=f"btn_del_{label}_{v}", help=f"Verwijder dossier {v}", type="secondary"):
                        bevestig_verwijder_map(pad, v)
            
            # Subtiele scheidingslijn tussen rijen
            st.markdown('<div style="margin: 2px 0; opacity: 0.1; border-bottom: 1px solid white;"></div>', unsafe_allow_html=True)
    elif filter_tekst:
        st.info(f"Geen mappen gevonden die voldoen aan het filter '{filter_tekst}'.")
    else:
        st.info(f"Geen {label.lower()}-mappen gevonden. Maak een nieuw dossier aan via de knop hierboven.")
        return

    st.divider()

    # ── Dossier Selectie ──
    _item_label = label.lower().rstrip('en') if label.lower().endswith('en') else label.lower()
    doel_map = st.selectbox(f"Selecteer een {_item_label} om te beheren:", mappen, key=f"edit_map_{label}")

    if not doel_map:
        return

    doel_pad = os.path.join(directory, doel_map)
    profiel = laad_profiel_uit_map(doel_pad)
    bestanden = [f for f in os.listdir(doel_pad) if not f.startswith(".") and not f.endswith(".json") and os.path.isfile(os.path.join(doel_pad, f))]

    # ── Dossier Header met status & acties ──
    st.markdown(f"""
    <div style="
        display: flex; align-items: center; gap: 10px;
        margin: 0.8rem 0 0.4rem 0;
    ">
        <span style="
            font-size: 1.3rem; font-weight: 700;
            color: rgba(240, 242, 245, 0.9);
        ">{doel_map}</span>
        <span style="
            font-size: 0.7rem; font-weight: 600;
            padding: 3px 10px; border-radius: 12px;
            letter-spacing: 0.5px; text-transform: uppercase;
            background: {'rgba(0,230,118,0.15)' if profiel else 'rgba(255,171,0,0.15)'};
            color: {'#00E676' if profiel else '#FFAB00'};
            border: 1px solid {'rgba(0,230,118,0.3)' if profiel else 'rgba(255,171,0,0.3)'};
        ">{'✓ Profiel actief' if profiel else '⚠ Geen profiel'}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabbladen: Documenten / Profiel / Acties ──
    tab_docs, tab_profiel, tab_acties = st.tabs([":material/description: Documenten", ":material/psychology: LLM Profiel", ":material/settings: Acties"])

    with tab_docs:
        # Upload sectie
        uploaded = st.file_uploader(
            "Upload een document",
            type=["txt", "docx", "pdf", "csv", "eml", "md", "json"],
            key=f"upload_{label}",
        )
        if uploaded:
            doel = os.path.join(doel_pad, uploaded.name)
            with open(doel, "wb") as f:
                f.write(uploaded.getvalue())
            st.cache_data.clear()
            st.toast(f"'{uploaded.name}' geüpload naar {doel_map}!", icon=":material/check_circle:")
            time.sleep(1)
            st.rerun()

        # Documenten lijst
        if bestanden:
            st.caption(f"{len(bestanden)} document{'en' if len(bestanden) != 1 else ''} in dit dossier")
            for bf in bestanden:
                bf_pad = os.path.join(doel_pad, bf)
                col_doc, col_del = st.columns([5, 1])
                with col_doc:
                    extensie = bf.split('.')[-1].upper()
                    if bf.endswith(".txt") or bf.endswith(".md") or bf.endswith(".csv"):
                        with open(bf_pad, encoding="utf-8") as bf_in:
                            with st.expander(f":material/description: {bf}"):
                                st.code(bf_in.read(), language=None)
                    else:
                        st.markdown(f":material/attachment: **{bf}** `{extensie}`")
                with col_del:
                    if st.button(":material/delete:", key=f"del_doc_{doel_map}_{bf}", help=f"Verwijder {bf}"):
                        bevestig_verwijder_doc(bf_pad, bf)
        else:
            st.info("Nog geen documenten. Upload er een via het veld hierboven.")

    with tab_profiel:
        col_gen, col_score, col_spacer = st.columns([1, 1, 1.5])
        with col_gen:
            if st.button(":material/auto_awesome: Hergenereer", type="primary", key=f"gen_{label}", use_container_width=True):
                with st.spinner("LLM is aan het analyseren..."):
                    nieuw_profiel = genereer_profiel_voor_map(doel_pad, profileer_fn)
                    if isinstance(nieuw_profiel, dict):
                        st.cache_data.clear()
                        st.toast("Profiel succesvol gegenereerd!", icon=":material/check_circle:")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Kan profiel niet genereren: {nieuw_profiel}")
        
        with col_score:
            if profiel:
                score = profiel.get("profiel_betrouwbaarheid", 0)
                kleur = "#FF5252" if score < 40 else "#FFAB00" if score < 75 else "#00E676"
                st.markdown(f"""
                <div style="
                    background: {kleur}22; border: 1px solid {kleur}44;
                    padding: 6px 15px; border-radius: 8px; text-align: center;
                ">
                    <span style="font-size: 0.7rem; color: rgba(255,255,255,0.6); display: block; text-transform: uppercase;">Betrouwbaarheid</span>
                    <span style="font-size: 1.1rem; font-weight: 800; color: {kleur};">{score}%</span>
                </div>
                """, unsafe_allow_html=True)

        if profiel:
            # Inline profiel editor
            with st.expander(":material/edit: Profiel bewerken", expanded=False):
                profiel_tekst = st.text_area(
                    "Bewerk het JSON profiel:",
                    value=json.dumps(profiel, indent=2, ensure_ascii=False),
                    height=400,
                    key=f"edit_profiel_{label}_{doel_map}"
                )
                if st.button(":material/save: Opslaan", key=f"save_profiel_{label}", type="primary"):
                    try:
                        bewerkt_profiel = json.loads(profiel_tekst)
                        profiel_pad = vind_meest_recente_profiel(doel_pad)
                        if profiel_pad:
                            with open(profiel_pad, "w", encoding="utf-8") as f:
                                json.dump(bewerkt_profiel, f, ensure_ascii=False, indent=2)
                            st.cache_data.clear()
                            st.toast("Profiel opgeslagen!", icon=":material/check_circle:")
                            time.sleep(1)
                            st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Ongeldige JSON: {e}")
            st.json(profiel)

            # --- Sectie: Profiel Verrijken ---
            vervolgvragen = profiel.get("vervolgvragen", [])
            if vervolgvragen:
                st.divider()
                st.subheader(":material/edit_note: Profiel Verrijken")
                st.info("De AI heeft de volgende vragen om dit profiel betrouwbaarder te maken. Beantwoord ze hieronder om het profiel te verfijnen.")
                
                with st.form(key=f"enrich_form_{label}_{doel_map}"):
                    antwoorden = {}
                    for idx, vraag in enumerate(vervolgvragen):
                        antwoorden[vraag] = st.text_area(vraag, key=f"ans_{label}_{idx}")
                    
                    if st.form_submit_button(":material/auto_fix: Profiel Verfijnen", type="primary"):
                        if any(antwoorden.values()):
                            extra_tekst = "\n\n--- EXTRA INFORMATIE (VERRIJKING) ---\n"
                            for v, a in antwoorden.items():
                                if a.strip():
                                    extra_tekst += f"Vraag: {v}\nAntwoord: {a}\n\n"
                            
                            # Sla antwoorden op als een nieuw tekstbestand
                            verrijking_pad = os.path.join(doel_pad, f"verrijking_{int(time.time())}.txt")
                            with open(verrijking_pad, "w", encoding="utf-8") as f:
                                f.write(extra_tekst)
                            
                            with st.spinner("Profiel opnieuw genereren met nieuwe informatie..."):
                                nieuw_profiel = genereer_profiel_voor_map(doel_pad, profileer_fn)
                                if isinstance(nieuw_profiel, dict):
                                    st.cache_data.clear()
                                    st.toast("Profiel succesvol verfijnd!", icon=":material/auto_fix:")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"Fout bij verfijnen: {nieuw_profiel}")
                        else:
                            st.warning("Vul minimaal één antwoord in om te verfijnen.")
        else:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem 0; color: rgba(240,242,245,0.35);">
                <div style="font-size: 2rem; margin-bottom: 8px;">🧠</div>
                <div style="font-size: 0.85rem;">Nog geen profiel beschikbaar</div>
                <div style="font-size: 0.75rem; margin-top: 4px; color: rgba(240,242,245,0.2);">Klik op 'Genereer Profiel' om er één te maken op basis van de documenten.</div>
                <div class="loading-skeleton" style="width: 80%; margin: 16px auto 4px auto;"></div>
                <div class="loading-skeleton" style="width: 60%; margin: 0 auto;"></div>
            </div>
            """, unsafe_allow_html=True)

    with tab_acties:
        st.markdown("**Dossier verwijderen**")
        st.caption("Dit verwijdert het volledige dossier inclusief alle documenten en het profiel.")
        if st.button(":material/delete_forever: Verwijder Dossier", type="secondary", key=f"del_{label}"):
            bevestig_verwijder_map(doel_pad, doel_map)


def pagina_kandidaten_beheer():
    _beheer_bestanden(KANDIDATEN_DIR, "Kandidaten")


def pagina_werkgeversvragen_beheer():
    _beheer_bestanden(WERKGEVERSVRAGEN_DIR, "Werkgeversvragen")


def pagina_match():
    ui_page_header("Match starten", "Lanceer een nieuwe AI-gebaseerde match-analyse", "🎯")

    cvs = lijst_mappen(KANDIDATEN_DIR)
    vacatures = lijst_mappen(WERKGEVERSVRAGEN_DIR)

    if not cvs:
        st.warning(f"Geen kandidaten gevonden in de map structuur: {KANDIDATEN_DIR}")
        return
    if not vacatures:
        st.warning(f"Geen werkgeversvragen gevonden in de map structuur: {WERKGEVERSVRAGEN_DIR}")
        return

    cvs_beschikbaar = [c for c in cvs if heeft_profiel(KANDIDATEN_DIR, c)]
    vacs_beschikbaar = [v for v in vacatures if heeft_profiel(WERKGEVERSVRAGEN_DIR, v)]

    with st.container(border=True):
        st.subheader("Match Configuratie")
        
        alle_modi = MATCH_MODI
        modus_keys = list(alle_modi.keys())
        gekozen_modus = st.radio("Kies de analysemodus voor de AI:", modus_keys,
                                  format_func=lambda k: f"{alle_modi[k]['label']} — {alle_modi[k]['beschrijving']}",
                                  horizontal=True,
                                  key="match_modus")

        with st.popover(":material/tune: Geavanceerde Match Opties"):
            st.markdown("Pas specifieke LLM instellingen aan voor deze match reeks.")
            online, modellen = check_ollama_status()
            if online and modellen:
                huidige_index = modellen.index(st.session_state.ollama_model) if st.session_state.ollama_model in modellen else 0
                gekozen_model = st.selectbox("LLM Model", modellen, index=huidige_index, key="pop_model")
                if gekozen_model != st.session_state.ollama_model:
                    st.session_state.ollama_model = gekozen_model
            temp = st.slider("Temperature (Creativiteit)", 0.0, 1.0, st.session_state.temperature, 0.05, key="pop_temp")
            if temp != st.session_state.temperature:
                st.session_state.temperature = temp

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if not cvs_beschikbaar:
                st.error("Geen kandidaten gevonden met een .json profiel.")
                st.info("Ga naar Kandidaten beheren en genereer profielen.")
            # Selectie knoppen
            _c1, _c2, _c3 = st.columns([1, 1, 2])
            with _c1:
                if st.button("Alles", key="sel_all_cvs", help="Selecteer alle kandidaten"):
                    st.session_state.match_cvs = cvs_beschikbaar
                    st.rerun()
            with _c2:
                if st.button("Wissen", key="clr_cvs", help="Wis selectie"):
                    st.session_state.match_cvs = []
                    st.rerun()
            gekozen_cvs = st.multiselect("Selecteer kandidaten (met profiel)", cvs_beschikbaar, default=cvs_beschikbaar, key="match_cvs")
        with col2:
            if not vacs_beschikbaar:
                st.error("Geen werkgeversvragen gevonden met een .json profiel.")
                st.info("Ga naar Werkgeversvragen beheren en genereer profielen.")
            _v1, _v2, _v3 = st.columns([1, 1, 2])
            with _v1:
                if st.button("Alles", key="sel_all_vacs", help="Selecteer alle werkgeversvragen"):
                    st.session_state.match_vacatures = vacs_beschikbaar
                    st.rerun()
            with _v2:
                if st.button("Wissen", key="clr_vacs", help="Wis selectie"):
                    st.session_state.match_vacatures = []
                    st.rerun()
            gekozen_vacatures = st.multiselect("Selecteer werkgeversvragen (met profiel)", vacs_beschikbaar, default=vacs_beschikbaar, key="match_vacatures")

        if not gekozen_cvs or not gekozen_vacatures:
            st.info("Selecteer minimaal één kandidaat en één werkgeversvraag om te starten.")
            return

        totaal = len(gekozen_cvs) * len(gekozen_vacatures)
        st.write(f"Totaal uit te voeren AI-analyses: **{totaal}**")
        
        start_button = st.button(":material/play_arrow: Start Matching Proces", type="primary", width="stretch")

    if start_button:
        os.makedirs(RAPPORT_DIR, exist_ok=True)
        
        alle_resultaten = []
        analyse_tijden = []  # Bijhouden van duur per analyse voor tijdschatting
        
        with st.status(":material/memory: AI Matching is bezig...", expanded=True) as status:
            stap = 0
            totaal_start = time.time()
            
            for cv_map in gekozen_cvs:
                cv_pad = os.path.join(KANDIDATEN_DIR, cv_map)
                cv_profiel = laad_profiel_uit_map(cv_pad)
                if not cv_profiel:
                    st.write(f":material/warning: Geen profiel voor kandidaat: {cv_map}")
                    continue
                    
                naam = cv_profiel.get("naam", cv_map)
                matches_voor_kandidaat = []
                cv_profiel_json = json.dumps(cv_profiel, indent=2, ensure_ascii=False)

                for vac_map in gekozen_vacatures:
                    vac_pad = os.path.join(WERKGEVERSVRAGEN_DIR, vac_map)
                    vac_eisen = laad_profiel_uit_map(vac_pad)
                    if not vac_eisen:
                        st.write(f":material/warning: Geen profiel voor vacature: {vac_map}")
                        continue
                        
                    vac_titel = vac_eisen.get("titel", vac_map)

                    stap += 1
                    
                    # Tijdschatting berekenen
                    geschatte_tekst = ""
                    if analyse_tijden:
                        gem_duur = sum(analyse_tijden) / len(analyse_tijden)
                        resterende_analyses = totaal - stap + 1
                        geschatte_rest = gem_duur * resterende_analyses
                        if geschatte_rest >= 60:
                            geschatte_tekst = f" — geschatte resterende tijd: ~{int(geschatte_rest // 60)} min {int(geschatte_rest % 60)} sec"
                        else:
                            geschatte_tekst = f" — geschatte resterende tijd: ~{int(geschatte_rest)} sec"
                    
                    elapsed = time.time() - totaal_start
                    elapsed_str = f"{int(elapsed // 60)}:{int(elapsed % 60):02d}"
                    
                    st.write(f":material/sync: Analyse {stap}/{totaal}: **{naam}** vs **{vac_titel}** — ⏱️ {elapsed_str}{geschatte_tekst}")

                    stream_container = st.empty()
                    stream_tekst = ""
                    resultaat = None
                    analyse_start = time.time()
                    vac_eisen_json = json.dumps(vac_eisen, indent=2, ensure_ascii=False)

                    # RAG-lite: Haal ruwe tekst op voor diepte-analyse
                    cv_input_tekst = cv_profiel_json
                    vac_input_tekst = vac_eisen_json
                    
                    if gekozen_modus == "diepte_analyse":
                        with st.spinner("Ophalen van ruwe documenttekst voor diepe analyse..."):
                            cv_raw = laad_ruwe_tekst_uit_map(cv_pad)
                            vac_raw = laad_ruwe_tekst_uit_map(vac_pad)
                            # Injecteer ruwe tekst (beperkt tot ~4000 karakters om context te sparen)
                            cv_input_tekst = f"{cv_profiel_json}\n\n--- RUWE DOCUMENT CONTEXT ---\n{cv_raw[:4000]}"
                            vac_input_tekst = f"{vac_eisen_json}\n\n--- RUWE VACATURE CONTEXT ---\n{vac_raw[:4000]}"

                    for event in vraag_ollama_stream(
                        cv_input_tekst, vac_input_tekst,
                        url=st.session_state.ollama_url,
                        model=st.session_state.ollama_model,
                        temperature=st.session_state.temperature,
                        modus=gekozen_modus,
                    ):
                        if event["type"] == "token":
                            stream_tekst += event["data"]
                            # Laat een subtiele indicatie zien van activiteit
                            if len(stream_tekst) % 20 == 0:
                                stream_container.markdown(f"⌛ *AI analyseert diepgaand...* `{len(stream_tekst)} tokens`")
                        elif event["type"] == "result":
                            resultaat = event["data"]
                        elif event["type"] == "warning":
                            st.warning(event["data"])
                        elif event["type"] == "error":
                            resultaat = event["data"]
                            st.error(f"Fout: {event['data']}")

                    analyse_duur = time.time() - analyse_start
                    analyse_tijden.append(analyse_duur)
                    stream_container.empty()

                    if resultaat and isinstance(resultaat, dict):
                        resultaat["vacature_titel"] = vac_titel
                        resultaat["kandidaat_naam"] = naam
                        resultaat["analyse_duur_sec"] = round(analyse_duur, 1)
                        alle_resultaten.append(resultaat)
                        matches_voor_kandidaat.append(resultaat)
                        st.write(f":material/check_circle: Klaar in {analyse_duur:.1f}s — Match: {resultaat.get('match_percentage', '?')}%")
            
                # Rapport opslaan per kandidaat als z'n matches klaar zijn
                if matches_voor_kandidaat:
                     rapport = genereer_rapport(naam, matches_voor_kandidaat)
                     rapport_naam = f"rapport_{cv_map}.txt"
                     rapport_pad = os.path.join(RAPPORT_DIR, rapport_naam)
                     with open(rapport_pad, "w", encoding="utf-8") as f:
                         f.write(rapport)
                     # JSON rapport opslaan voor vergelijkingsview
                     json_rapport_naam = f"rapport_{cv_map}.json"
                     json_rapport_pad = os.path.join(RAPPORT_DIR, json_rapport_naam)
                     with open(json_rapport_pad, "w", encoding="utf-8") as f:
                         json.dump({"kandidaat": naam, "resultaten": matches_voor_kandidaat}, f, ensure_ascii=False, indent=2)
                     
                     # DB Opslag
                     try:
                         for resv in matches_voor_kandidaat:
                              percentage = resv.get("match_percentage", 0)
                              vac_t = resv.get("vacature_titel", "Onbekend")
                              bewaar_match(naam, cv_map, vac_t, "n/a", percentage, gekozen_modus, resv)
                     except Exception as e:
                         st.error(f"Fout bij opslaan in database: {e}")

                     st.write(f":material/description: Bestanden opgeslagen: `{rapport_naam}` + `{json_rapport_naam}`")

            totaal_duur = time.time() - totaal_start
            if totaal_duur >= 60:
                duur_str = f"{int(totaal_duur // 60)} min {int(totaal_duur % 60)} sec"
            else:
                duur_str = f"{totaal_duur:.1f} sec"
            status.update(label=f"Matching voltooid in {duur_str}! ✨", state="complete", expanded=False)
            st.toast("Matching succesvol voltooid", icon=":material/celebration:")
            st.balloons()
        
        # Rendern van de UI resultaten Outside of the status box
        st.divider()
        st.markdown(f"""
        <div style="margin-bottom: 1.5rem;">
            <h2 style="
                background: linear-gradient(135deg, #00E5FF, #2979FF, #7C4DFF);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                font-weight: 800; margin-bottom: 4px; font-size: 1.8rem;
                filter: drop-shadow(0 0 15px rgba(0, 229, 255, 0.25));
            ">Resultaten Overzicht</h2>
            <p style="color: rgba(240,242,245,0.35); font-size: 0.8rem; margin: 0;
                letter-spacing: 0.5px;">{len(alle_resultaten)} {'analyse' if len(alle_resultaten) == 1 else 'analyses'} voltooid</p>
        </div>
        """, unsafe_allow_html=True)
        
        alle_resultaten.sort(key=lambda r: r.get("match_percentage", 0), reverse=True)
        for res in alle_resultaten:
            pct = res.get("match_percentage", 0)

            # Kleur-gecodeerde glow op basis van match score
            if pct >= 70:
                score_kleur = "#00E676"
                glow_kleur = "rgba(0, 230, 118, 0.25)"
                border_kleur = "rgba(0, 230, 118, 0.4)"
                badge_class = "high"
                badge_label = "Sterke Match"
                ring_track = "rgba(0, 230, 118, 0.1)"
            elif pct >= 40:
                score_kleur = "#FFD740"
                glow_kleur = "rgba(255, 215, 64, 0.2)"
                border_kleur = "rgba(255, 215, 64, 0.35)"
                badge_class = "medium"
                badge_label = "Potentie"
                ring_track = "rgba(255, 215, 64, 0.1)"
            else:
                score_kleur = "#B388FF"
                glow_kleur = "rgba(124, 77, 255, 0.2)"
                border_kleur = "rgba(124, 77, 255, 0.35)"
                badge_class = "low"
                badge_label = "Verkennen"
                ring_track = "rgba(124, 77, 255, 0.1)"

            # SVG score ring berekening
            ring_radius = 54
            ring_circumference = 2 * 3.14159 * ring_radius
            ring_offset = ring_circumference * (1 - pct / 100)

            reliability = res.get('match_betrouwbaarheid', 'Onbekend')
            rel_color = "#FFD740" if reliability == "Gemiddeld" else ("#00E676" if reliability == "Hoog" else "#FF5252")

            with st.container(border=True):
                # Header met SVG ring + titel
                st.markdown(f"""
                <div class="match-card-header">
                    <div class="score-ring-container" style="--ring-glow: {glow_kleur};">
                        <svg width="130" height="130" viewBox="0 0 130 130">
                            <circle cx="65" cy="65" r="{ring_radius}" fill="none"
                                stroke="{ring_track}" stroke-width="8" />
                            <circle cx="65" cy="65" r="{ring_radius}" fill="none"
                                stroke="{score_kleur}" stroke-width="8"
                                stroke-linecap="round"
                                stroke-dasharray="{ring_circumference}"
                                stroke-dashoffset="{ring_offset}"
                                style="transition: stroke-dashoffset 1.5s cubic-bezier(0.25, 0.8, 0.25, 1);" />
                        </svg>
                        <div class="score-ring-label">
                            <div class="score-value" style="color: {score_kleur};
                                filter: drop-shadow(0 0 8px {glow_kleur});">{pct}%</div>
                            <div class="score-unit">Match</div>
                        </div>
                    </div>
                    <div class="match-card-title">
                        <h3>{res['kandidaat_naam']}</h3>
                        <div class="match-subtitle">vs {res['vacature_titel']}</div>
                        <div style="margin-top: 8px; display: flex; gap: 8px;">
                            <span class="match-badge {badge_class}">{badge_label}</span>
                            <span style="
                                font-size: 0.65rem; padding: 2px 8px; border-radius: 4px;
                                background: {rel_color}1A; color: {rel_color}; border: 1px solid {rel_color}33;
                                font-weight: 600; text-transform: uppercase;"
                                title="Betrouwbaarheid van de match op basis van beschikbare info">
                                {reliability}
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.progress(pct / 100)

                col_match, col_ontb, col_radar = st.columns([2, 2, 3])
                with col_match:
                    st.markdown(":green[**:material/check: Matchende punten**]")
                    for p in res.get("matchende_punten", []):
                        st.markdown(f":green[- {p}]")
                with col_ontb:
                    st.markdown(":red[**:material/close: Ontbrekende punten**]")
                    for p in res.get("ontbrekende_punten", []):
                        st.markdown(f":red[- {p}]")
                    
                    if res.get("overbruggings_advies"):
                        st.markdown(":blue[**:material/school: Overbruggingsadvies**]")
                        for a in res.get("overbruggings_advies", []):
                            st.markdown(f":blue[- {a}]")
                
                with col_radar:
                    if "personality_axes" in res:
                        render_personality_radar(res["personality_axes"])

                if res.get("vervolgvragen"):
                    with st.expander(":material/contact_support: **Kritieke vervolgvragen** (om dossier completer te maken)", expanded=res.get('match_betrouwbaarheid') == 'Laag'):
                        for vq in res["vervolgvragen"]:
                            st.markdown(f"❓ {vq}")

                with st.expander("Lees uitgebreide onderbouwing"):
                    if res.get("verrassings_element"):
                        st.markdown(f"""**💡 Verrassings-element:**""")
                        st.info(f"{res['verrassings_element']}")
                    if res.get("cultuur_fit"):
                        st.markdown(f"**🌟 Cultuur Fit:**\n{res['cultuur_fit']}")
                    if res.get("groeipotentieel"):
                        st.markdown(f"**🌱 Groeipotentieel:**\n{res['groeipotentieel']}")
                    if res.get("risico_mitigatie"):
                        st.markdown(f"**🛡️ Risico-mitigatie:**\n{res['risico_mitigatie']}")
                    if res.get("aandachtspunten"):
                        st.markdown(f"**⚠️ Aandachtspunten:**\n{res['aandachtspunten']}")
                    if res.get("gedeelde_waarden"):
                        st.markdown("**🤝 Gedeelde Waarden:**")
                        for w in res["gedeelde_waarden"]:
                            st.markdown(f"- {w}")
                    if res.get("gespreksstarters"):
                        st.markdown("**🎤 Gespreksstarters voor de recruiter:**")
                        for idx, vraag in enumerate(res["gespreksstarters"], 1):
                            st.markdown(f"{idx}. {vraag}")
                    if res.get("onderbouwing"):
                        st.markdown("**📄 Onderbouwing:**")
                        st.info(f"{res['onderbouwing']}")
                    if res.get("boodschap_aan_kandidaat"):
                        st.markdown("---")
                        st.markdown("**💬 Boodschap aan de kandidaat:**")
                        st.success(f"{res['boodschap_aan_kandidaat']}")
                    
                    # Analyse-duur tonen
                    if res.get("analyse_duur_sec"):
                        st.caption(f"⏱️ Analyse duurde {res['analyse_duur_sec']}s")
                    
                    if not any(k in res for k in ["cultuur_fit", "groeipotentieel", "aandachtspunten", "gedeelde_waarden", "onderbouwing", "verrassings_element", "gespreksstarters", "boodschap_aan_kandidaat"]):
                        st.write("Geen verdere onderbouwing opgegeven.")


def pagina_rapporten():
    ui_page_header("Rapporten", "Overzicht van alle gegenereerde match-rapporten", "📄")

    if not os.path.isdir(RAPPORT_DIR):
        st.info("Nog geen rapporten gegenereerd.")
        return

    alle_rapporten = lijst_bestanden(RAPPORT_DIR)
    if not alle_rapporten:
        st.info("Nog geen rapporten gevonden.")
        return

    # ── Filter / zoekbalk ──
    rapport_filter = st.text_input(":material/search: Zoek rapport", key="filter_rapporten", placeholder="Typ om te zoeken...", label_visibility="collapsed")
    if rapport_filter:
        rapporten = [r for r in alle_rapporten if rapport_filter.lower() in r.lower()]
    else:
        rapporten = alle_rapporten

    if not rapporten:
        st.info(f"Geen rapporten gevonden voor '{rapport_filter}'.")
        return

    # Dataframe overzicht
    st.write(f"Overzicht van {'gefilterde' if rapport_filter else 'alle'} lokaal opgeslagen match-rapporten.")

    table_data = []
    for rapport in rapporten:
        pad = os.path.join(RAPPORT_DIR, rapport)
        tijd = os.path.getmtime(pad)
        table_data.append({
            "Rapport Naam": rapport,
            "Aangemaakt op": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tijd))
        })
    st.dataframe(table_data, width="stretch", hide_index=True)
    
    st.divider()
    
    with st.container(border=True):
        st.subheader("Rapport Inzien & Downloaden")
        gekozen_rapport = st.selectbox("Selecteer een rapport:", rapporten)
        if gekozen_rapport:
            pad = os.path.join(RAPPORT_DIR, gekozen_rapport)
            with open(pad, encoding="utf-8") as f:
                inhoud = f.read()
            
            c1, c2, c3 = st.columns([1, 1, 3])
            with c1:
                st.download_button(
                    label=":material/download: TXT",
                    data=inhoud,
                    file_name=gekozen_rapport,
                    mime="text/plain",
                    type="primary",
                    width="stretch"
                )
            with c2:
                # HTML export van het rapport
                html_inhoud = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{gekozen_rapport}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;background:#0a0e18;color:#f0f2f5;}}
pre{{white-space:pre-wrap;line-height:1.6;}}</style></head>
<body><pre>{inhoud}</pre></body></html>"""
                st.download_button(
                    label=":material/download: HTML",
                    data=html_inhoud,
                    file_name=gekozen_rapport.replace(".txt", ".html"),
                    mime="text/html",
                    width="stretch"
                )

            with st.expander("Bekijk geformatteerd rapport:", expanded=True):
                st.markdown(inhoud)


def pagina_vergelijking():
    ui_page_header("Vergelijking", "Kandidaten gerankt op match-percentage per werkgeversvraag", "📊")

    if not os.path.isdir(RAPPORT_DIR):
        st.info("Nog geen rapporten beschikbaar. Start eerst een match.")
        return

    # Laad unieke vacatures uit DB
    werkgeversvragen = haal_unieke_vacatures()
    if not werkgeversvragen:
        # Fallback naar oude JSON bestanden als DB leeg is (voor backward compatibility)
        json_rapporten = [f for f in os.listdir(RAPPORT_DIR) if f.endswith(".json")]
        if not json_rapporten:
            st.info("Nog geen rapporten beschikbaar. Start eerst een match.")
            return

        alle_resultaten = []
        for rapport_bestand in json_rapporten:
            pad = os.path.join(RAPPORT_DIR, rapport_bestand)
            try:
                with open(pad, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for res in data.get("resultaten", []):
                    res["kandidaat"] = data.get("kandidaat", rapport_bestand)
                    alle_resultaten.append(res)
            except Exception:
                continue
        werkgeversvragen = sorted(set(r.get("vacature_titel", "Onbekend") for r in alle_resultaten))
    else:
        alle_resultaten = None # Gebruik DB queries

    gekozen_vraag = st.selectbox("Selecteer een werkgeversvraag:", werkgeversvragen)
    if not gekozen_vraag:
        return

    # Filter en sorteer via DB of fallback
    if alle_resultaten is None:
        gefilterd_db = haal_matches_voor_vacature(gekozen_vraag)
        gefilterd = []
        for r in gefilterd_db:
            try:
                res_dict = json.loads(r["resultaat_json"])
                res_dict["kandidaat_naam"] = r["kandidaat_naam"]
                res_dict["match_percentage"] = r["match_percentage"]
                gefilterd.append(res_dict)
            except Exception:
                continue
    else:
        gefilterd = [r for r in alle_resultaten if r.get("vacature_titel") == gekozen_vraag]
        gefilterd.sort(key=lambda r: r.get("match_percentage", 0), reverse=True)

    if not gefilterd:
        st.info("Geen resultaten voor deze werkgeversvraag.")
        return

    st.write(f"**{len(gefilterd)} kandidaten** gerankt voor: *{gekozen_vraag}*")

    import pandas as pd

    # Ranking tabel
    tabel = []
    for i, res in enumerate(gefilterd, 1):
        pct = res.get("match_percentage", 0)
        tabel.append({
            "#": i,
            "Kandidaat": res.get("kandidaat_naam", res.get("kandidaat", "?")),
            "Match %": pct,
            "Matchende punten": ", ".join(res.get("matchende_punten", [])[:3]),
            "Verrassings-element": (res.get("verrassings_element", "") or "")[:100],
        })

    df = pd.DataFrame(tabel)
    st.dataframe(df, hide_index=True, use_container_width=True)

    # CSV export
    csv_data = df.to_csv(index=False)
    st.download_button(
        label=":material/download: Download als CSV",
        data=csv_data,
        file_name=f"ranking_{gekozen_vraag.replace(' ', '_')[:30]}.csv",
        mime="text/csv",
    )

    # Visuele score rings per kandidaat
    st.divider()
    for res in gefilterd:
        pct = res.get("match_percentage", 0)
        naam = res.get("kandidaat_naam", res.get("kandidaat", "?"))

        if pct >= 70:
            score_kleur = "#00E676"
            glow_kleur = "rgba(0, 230, 118, 0.25)"
            ring_track = "rgba(0, 230, 118, 0.1)"
            badge_class = "high"
            badge_label = "Sterke Match"
        elif pct >= 40:
            score_kleur = "#FFD740"
            glow_kleur = "rgba(255, 215, 64, 0.2)"
            ring_track = "rgba(255, 215, 64, 0.1)"
            badge_class = "medium"
            badge_label = "Potentie"
        else:
            score_kleur = "#B388FF"
            glow_kleur = "rgba(124, 77, 255, 0.2)"
            ring_track = "rgba(124, 77, 255, 0.1)"
            badge_class = "low"
            badge_label = "Verkennen"

        ring_radius = 40
        ring_circumference = 2 * 3.14159 * ring_radius
        ring_offset = ring_circumference * (1 - pct / 100)

        with st.container(border=True):
            st.markdown(f"""
            <div class="match-card-header">
                <div class="score-ring-container" style="--ring-glow: {glow_kleur};">
                    <svg width="100" height="100" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="{ring_radius}" fill="none" stroke="{ring_track}" stroke-width="6" />
                        <circle cx="50" cy="50" r="{ring_radius}" fill="none" stroke="{score_kleur}" stroke-width="6"
                            stroke-linecap="round" stroke-dasharray="{ring_circumference}" stroke-dashoffset="{ring_offset}" />
                    </svg>
                    <div class="score-ring-label">
                        <div class="score-value" style="color: {score_kleur}; font-size: 1.4rem;">{pct}%</div>
                    </div>
                </div>
                <div class="match-card-title">
                    <h3>{naam}</h3>
                    <div style="margin-top: 4px;"><span class="match-badge {badge_class}">{badge_label}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Details"):
                col_match, col_ontb = st.columns(2)
                with col_match:
                    st.markdown(":green[**Matchende punten**]")
                    for p in res.get("matchende_punten", []):
                        st.markdown(f":green[- {p}]")
                with col_ontb:
                    st.markdown(":red[**Ontbrekende punten**]")
                    for p in res.get("ontbrekende_punten", []):
                        st.markdown(f":red[- {p}]")
                if res.get("onderbouwing"):
                    st.info(res["onderbouwing"])


def pagina_instellingen():
    ui_page_header("Instellingen", "Configureer LLM parameters en systeem prompts", "⚙️")
    
    with st.container(border=True):
        st.subheader("Ollama Configuratie")
        col1, col2 = st.columns(2)
        
        with col1:
            nieuwe_url = st.text_input("Ollama URL", value=st.session_state.ollama_url)
            if nieuwe_url != st.session_state.ollama_url:
                st.session_state.ollama_url = nieuwe_url
                st.toast("URL bijgewerkt!", icon=":material/check_circle:")
                time.sleep(0.5)
                st.rerun()

        with col2:
            online, modellen = check_ollama_status()
            if online and modellen:
                huidige_index = modellen.index(st.session_state.ollama_model) if st.session_state.ollama_model in modellen else 0
                gekozen_model = st.selectbox("Model", modellen, index=huidige_index)
                if gekozen_model != st.session_state.ollama_model:
                    st.session_state.ollama_model = gekozen_model
                    st.toast("Model ingesteld!", icon=":material/check_circle:")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.text_input("Model (handmatig)", value=st.session_state.ollama_model, key="model_handmatig", on_change=lambda: st.session_state.update(ollama_model=st.session_state.model_handmatig))
                if not online:
                    st.warning("Ollama is niet bereikbaar — modellen konden niet worden opgehaald.")

        temp = st.slider("Temperature (Creativiteit van de LLM)", 0.0, 1.0, st.session_state.temperature, 0.05)
        if temp != st.session_state.temperature:
            st.session_state.temperature = temp

    with st.container(border=True):
        st.subheader("Prompt Templates")
        nieuw_system = st.text_area("System prompt", st.session_state.system_prompt, height=250)
        if nieuw_system != st.session_state.system_prompt:
            st.session_state.system_prompt = nieuw_system

        nieuw_match = st.text_area("Match prompt", st.session_state.match_prompt, height=400)
        if nieuw_match != st.session_state.match_prompt:
            st.session_state.match_prompt = nieuw_match

        st.caption(":material/info: Let op: Wijzigingen in prompts en instellingen hier gelden alleen voor deze sessie. Bewerk `config.py` om ze permanent te maken voor volgende opstarts.")


def pagina_over_paperstrip():
    ui_page_header("Over PaperStrip", "Waarom we naar potentieel kijken in plaats van alleen CV's", "✨")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        ### De filosofie achter PaperStrip
        PaperStrip is niet je standaard CV-matching tool. Onze visie is dat de meeste selectieprocessen te veel gefocust zijn op het verleden (diploma's, functietitels) en te weinig op de **toekomst** (potentieel, karakter, passie).

        Met behulp van geavanceerde lokale AI analyseren we kandidaten op basis van hun **persoonlijkheid en drijfveren**. We zoeken naar de "verborgen match": een kandidaat die op papier misschien niet de perfecte fit lijkt, maar qua karakter en werkstijl exact is wat een team nodig heeft.

        ### Waarom dit werkt:
        *   **Potentieel boven Ervaring**: We tippen kandidaten voor rollen die ze zelf misschien niet hadden overwogen.
        *   **Karakter-gedreven**: We matchen op waarden en cultuur-fit.
        *   **Verrassende Inzichten**: De AI ontdekt kwaliteiten die niet expliciet in een tekst staan, maar wel afgeleid kunnen worden uit iemands verhaal.
        """)

    with col2:
        with st.container(border=True):
            st.markdown("### 🔒 Privacy & AVG")
            st.info("""
            **PaperStrip is 100% lokaal.**
            In tegenstelling tot bijna alle andere AI-tools, verlaat jouw data deze computer nooit tijdens de analyse.
            
            *   **Geen Cloud**: De AI (Ollama) draait op jouw eigen hardware.
            *   **Jouw Data**: Alles wordt opgeslagen in je eigen iCloud of lokale map.
            *   **AVG-Proof**: Geen verwerking door externe AI-leveranciers.
            """)

    st.divider()
    
    st.markdown("### Hoe het werkt")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 1. Dossiers")
        st.caption("Upload documenten (CV's, vacatures, e-mails).")
    with c2:
        st.markdown("#### 2. Profileren")
        st.caption("De AI vertaalt ruwe tekst naar een rijk persoonlijkheidsprofiel.")
    with c3:
        st.markdown("#### 3. Matchen")
        st.caption("Ontdek de diepere fit op basis van karakter en waarden.")


# --- Sidebar Branding ---
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1.2rem 0.8rem 0.8rem 0.8rem; margin-bottom: 0.5rem; position: relative; overflow: hidden; border-radius: 16px; background: rgba(0,0,0,0.2);">
        <div style="position: absolute; top:0; left:0; right:0; bottom:0; background: repeating-linear-gradient(rgba(0,255,255,0.03) 0px, transparent 1px, transparent 2px); pointer-events: none; z-index: 10;"></div>
        <img src="data:image/png;base64,""" + __import__('base64').b64encode(open('icon.png', 'rb').read()).decode() + """" style="
            width: 64px; height: 64px;
            border-radius: 12px;
            display: inline-block;
            margin-bottom: 16px;
            filter: drop-shadow(0 0 20px rgba(0, 229, 255, 0.5)) contrast(1.1);
            border: 1px solid rgba(0, 229, 255, 0.3);
            position: relative;
            z-index: 2;
        " />
        <div class="branding-text" style="
            font-size: 1.8rem;
            font-weight: 900;
            letter-spacing: 6px;
            margin-bottom: 10px;
            font-family: 'Space Grotesk', sans-serif;
            position: relative;
            z-index: 2;
        ">PAPERSTRIP</div>
        <div style="
            font-size: 0.65rem;
            color: rgba(240, 242, 245, 0.6);
            letter-spacing: 2px;
            font-weight: 400;
            text-transform: uppercase;
            line-height: 1.4;
            position: relative;
            z-index: 2;
        ">Dossier Intelligence · Match Discovery</div>
        <div style="
            display: flex; justify-content: center; gap: 8px; margin-top: 10px; position: relative; z-index: 2;
        ">
            <span style="font-size: 0.5rem; color: #00E5FF; border: 1px solid rgba(0,229,255,0.3); padding: 1px 6px; border-radius: 4px; background: rgba(0,229,255,0.05);">v1.2 PRO</span>
            <span style="font-size: 0.5rem; color: rgba(240, 242, 245, 0.3); padding: 1px 4px;">SYSTEM OK</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# --- Pagina Navigatie inrichten (Streamlit v1.36+) ---

pg_dash = st.Page(pagina_dashboard, title="Dashboard", icon=":material/dashboard:", default=True)
pg_match = st.Page(pagina_match, title="Match Starten", icon=":material/target:")
pg_kand = st.Page(pagina_kandidaten_beheer, title="Kandidaten", icon=":material/group:")
pg_werk = st.Page(pagina_werkgeversvragen_beheer, title="Werkgeversvragen", icon=":material/business:")
pg_rapp = st.Page(pagina_rapporten, title="Rapporten Inzien", icon=":material/description:")
pg_verg = st.Page(pagina_vergelijking, title="Vergelijking", icon=":material/leaderboard:")
pg_inst = st.Page(pagina_instellingen, title="Instellingen", icon=":material/settings:")
pg_over = st.Page(pagina_over_paperstrip, title="Over PaperStrip", icon=":material/info:")

pg = st.navigation({
    "Overzicht": [pg_dash, pg_match],
    "Beheer": [pg_kand, pg_werk],
    "Analyse": [pg_rapp, pg_verg],
    "Over PaperStrip": [pg_over],
    "Systeem": [pg_inst]
})

# Versie badge is nu geïntegreerd in de sidebar branding hierboven

# Run de geselecteerde pagina
pg.run()
