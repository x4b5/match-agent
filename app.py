#!/usr/bin/env python3
"""Streamlit frontend voor Match Agent met UX/UI verbeteringen."""

import json
import os
import subprocess
import time
import shutil

import requests
import streamlit as st

# --- Standaard Streamlit Pagina Configuratie ---
# MOET het eerste Streamlit commando in de file zijn!
st.set_page_config(
    page_title="Match Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
from match_agent import (
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

def check_ollama_status() -> tuple[bool, list[str]]:
    try:
        resp = requests.get(f"{ollama_base_url()}/api/tags", timeout=5)
        resp.raise_for_status()
        modellen = [m["name"] for m in resp.json().get("models", [])]
        return True, modellen
    except Exception:
        return False, []

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

def heeft_profiel(directory: str, map_naam: str) -> bool:
    pad = os.path.join(directory, map_naam)
    if not os.path.isdir(pad):
        return False
    return any(f.endswith(".json") for f in os.listdir(pad))

def lijst_bestanden(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    return sorted([f for f in os.listdir(directory) if not f.startswith(".") and os.path.isfile(os.path.join(directory, f))])


# --- Dialogs voor veilige acties ---
@st.dialog("Weet je zeker dat je dit wilt verwijderen?")
def bevestig_verwijder_map(pad: str, map_naam: str):
    st.warning(f"Map '{map_naam}' en alle bestanden (inclusief profiel) worden definitief verwijderd.")
    if st.button("Verwijder definitief", type="primary", use_container_width=True):
        try:
            shutil.rmtree(pad)
            st.toast(f"Map '{map_naam}' is verwijderd.", icon="🗑️")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij verwijderen: {e}")

@st.dialog("Weet je zeker dat je dit document wilt verwijderen?")
def bevestig_verwijder_doc(pad: str, bestandsnaam: str):
    st.warning(f"Document '{bestandsnaam}' wordt definitief verwijderd.")
    if st.button("Verwijder definitief", type="primary", use_container_width=True):
        try:
            os.remove(pad)
            st.toast(f"'{bestandsnaam}' is verwijderd.", icon="🗑️")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Fout bij verwijderen: {e}")


# --- Pagina's (Functies) ---
def pagina_dashboard():
    st.title("📊 Dashboard")

    online, modellen = check_ollama_status()
    st.subheader("Systeem Status")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            if online:
                st.metric("Ollama", "Online", delta="Verbonden")
            else:
                st.metric("Ollama", "Offline", delta="- Geen verbinding", delta_color="inverse")
    with col2:
        with st.container(border=True):
            st.metric("Actief model", st.session_state.ollama_model)
    with col3:
        with st.container(border=True):
            if online:
                st.metric("Beschikbare modellen", len(modellen))
            else:
                st.metric("Beschikbare modellen", "—")

    # Ollie starten / stoppen
    if not online:
        if st.button("Ollama starten", type="primary"):
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with st.spinner("Ollama starten..."):
                for _ in range(15):
                    time.sleep(1)
                    if check_ollama_status()[0]:
                        st.toast("Ollama is gestart!", icon="🚀")
                        time.sleep(0.5)
                        st.rerun()
                        break
    else:
        if st.button("Ollama stoppen"):
            subprocess.run(["pkill", "-f", "ollama"], capture_output=True)
            st.toast("Ollama is gestopt.", icon="🛑")
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


def _beheer_bestanden(directory: str, label: str):
    st.title(f"📁 {label} Beheren")
    
    if not os.path.isdir(directory):
        st.warning(f"Map niet gevonden: {directory}")
        return

    profileer_fn = profileer_kandidaat if "kandidaten" in directory.lower() else profileer_werkgeversvraag

    # Data Overzicht in een Tabel
    mappen = lijst_mappen(directory)
    
    st.write("### Data Overzicht")
    if mappen:
        # Maak dataset voor DataFrame view
        table_data = []
        for v in mappen:
            pad = os.path.join(directory, v)
            aantal_docs = len([f for f in os.listdir(pad) if f.endswith((".txt", ".docx", ".pdf"))])
            heeft_prof = heeft_profiel(directory, v)
            table_data.append({
                "Naam / ID": v,
                "Aantal Documenten": aantal_docs,
                "Profiel Status": "✅ Aanwezig" if heeft_prof else "❌ Ontbreekt"
            })
        st.dataframe(table_data, use_container_width=True, hide_index=True)
    else:
        st.info(f"Geen {label.lower()}-mappen gevonden.")

    st.divider()
    
    tab_overzicht, tab_nieuw = st.tabs(["📋 Overzicht & Bewerken", "➕ Nieuw Dossier Aanmaken"])
    
    # Map toevoegen widget in aparte tab
    with tab_nieuw:
        with st.container(border=True):
            st.subheader(f"Nieuwe {label.lower()} toevoegen")
            nieuwe_map = st.text_input(f"Naam voor nieuwe map/dossier", key=f"nieuwe_map_{label}", placeholder="Bijv. jan_jansen")
            if st.button("Aanmaken", key=f"maak_map_{label}", type="primary"):
                if nieuwe_map:
                    veilige_naam = "".join(c for c in nieuwe_map if c.isalnum() or c in ('_', '-')).strip()
                    nieuw_pad = os.path.join(directory, veilige_naam)
                    if not os.path.exists(nieuw_pad):
                        os.makedirs(nieuw_pad)
                        st.toast(f"Map '{veilige_naam}' succesvol aangemaakt!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Map bestaat al.")

    # Beheren widget in Overzicht tab
    with tab_overzicht:
        if mappen:
            doel_map = st.selectbox(f"Selecteer een {label.lower()} om te beheren:", mappen, key=f"edit_map_{label}")
            
            # Specifieke details van de geselecteerde map
            if "doel_map" in locals() and doel_map:
                st.divider()
                st.subheader(f"Dossier details: {doel_map}")
                
                doel_pad = os.path.join(directory, doel_map)
                profiel = laad_profiel_uit_map(doel_pad)
                bestanden = [f for f in os.listdir(doel_pad) if f.endswith((".txt", ".docx", ".pdf"))]

                c_status, c_acties = st.columns([2, 1])
                with c_status:
                    if profiel:
                        st.success("✅ Gestructureerd LLM-profiel is actief.")
                    else:
                        st.warning("⚠️ Geen LLM-profiel aanwezig. Deze entiteit kan nog niet worden gematcht!")
                with c_acties:
                    if st.button("🗑️ Verwijder Dossier", use_container_width=True, type="secondary", key=f"del_{label}"):
                        bevestig_verwijder_map(doel_pad, doel_map)

                tab_docs, tab_profiel = st.tabs(["📄 Documenten", "🤖 LLM Profiel"])
                
                with tab_docs:
                    with st.container(border=True):
                        st.write("**Nieuw document uploaden**")
                        uploaded = st.file_uploader(
                            f"Kies .txt, .docx of .pdf",
                            type=["txt", "docx", "pdf"],
                            key=f"upload_{label}",
                            label_visibility="collapsed"
                        )
                        if uploaded:
                            doel = os.path.join(doel_pad, uploaded.name)
                            with open(doel, "wb") as f:
                                f.write(uploaded.getvalue())
                            st.toast(f"'{uploaded.name}' geüpload naar {doel_map}!", icon="✅")
                            time.sleep(1)
                            st.rerun()

                    st.markdown("**Huidige documenten:**")
                    if bestanden:
                        for bf in bestanden:
                            bf_pad = os.path.join(doel_pad, bf)
                            col_doc, col_del = st.columns([4, 1])
                            with col_doc:
                                if bf.endswith(".txt"):
                                    with open(bf_pad, encoding="utf-8") as bf_in:
                                        with st.expander(f"📄 {bf}"):
                                            st.text_area("Inhoud", bf_in.read(), height=150, disabled=True, label_visibility="collapsed")
                                else:
                                    with st.container(border=True):
                                        st.text(f"📄 {bf} (Binair doc: {bf.split('.')[-1].upper()})")
                            with col_del:
                                if st.button("✖ Verwijder", key=f"del_doc_{doel_map}_{bf}"):
                                    bevestig_verwijder_doc(bf_pad, bf)
                    else:
                        st.info("Geen documenten in dit dossier.")

                with tab_profiel:
                    if st.button("Genereer / Update Profiel (LLM)", type="primary", key=f"gen_{label}"):
                        with st.spinner("LLM is aan het analyseren..."):
                            nieuw_profiel = genereer_profiel_voor_map(doel_pad, profileer_fn)
                            if nieuw_profiel:
                                st.toast("Profiel succesvol gegenereerd!", icon="✅")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Kan profiel niet genereren. Documenten leesbaar?")
                    
                    if profiel:
                        st.json(profiel)
                    else:
                        st.write("Druk op de knop hierboven om een profiel te genereren gebaseerd op de documenten in dit dossier.")


def pagina_kandidaten_beheer():
    _beheer_bestanden(KANDIDATEN_DIR, "Kandidaten")


def pagina_werkgeversvragen_beheer():
    _beheer_bestanden(WERKGEVERSVRAGEN_DIR, "Werkgeversvragen")


def pagina_match():
    st.title("🎯 Match starten")

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

        with st.popover("⚙️ Geavanceerde Match Opties"):
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
            gekozen_cvs = st.multiselect("Selecteer kandidaten (met profiel)", cvs_beschikbaar, default=cvs_beschikbaar, key="match_cvs")
        with col2:
            if not vacs_beschikbaar:
                st.error("Geen werkgeversvragen gevonden met een .json profiel.")
                st.info("Ga naar Werkgeversvragen beheren en genereer profielen.")
            gekozen_vacatures = st.multiselect("Selecteer werkgeversvragen (met profiel)", vacs_beschikbaar, default=vacs_beschikbaar, key="match_vacatures")

        if not gekozen_cvs or not gekozen_vacatures:
            st.info("Selecteer minimaal één kandidaat en één werkgeversvraag om te starten.")
            return

        totaal = len(gekozen_cvs) * len(gekozen_vacatures)
        st.write(f"Totaal uit te voeren AI-analyses: **{totaal}**")
        
        start_button = st.button("🚀 Start Matching Proces", type="primary", use_container_width=True)

    if start_button:
        os.makedirs(RAPPORT_DIR, exist_ok=True)
        
        alle_resultaten = []
        
        with st.status("🧠 AI Matching is bezig...", expanded=True) as status:
            stap = 0
            for cv_map in gekozen_cvs:
                cv_pad = os.path.join(KANDIDATEN_DIR, cv_map)
                cv_profiel = laad_profiel_uit_map(cv_pad)
                if not cv_profiel:
                    st.write(f"⚠️ Geen profiel voor kandidaat: {cv_map}")
                    continue
                    
                naam = cv_profiel.get("naam", cv_map)
                matches_voor_kandidaat = []
                cv_profiel_json = json.dumps(cv_profiel, indent=2, ensure_ascii=False)

                for vac_map in gekozen_vacatures:
                    vac_pad = os.path.join(WERKGEVERSVRAGEN_DIR, vac_map)
                    vac_eisen = laad_profiel_uit_map(vac_pad)
                    if not vac_eisen:
                        st.write(f"⚠️ Geen profiel voor vacature: {vac_map}")
                        continue
                        
                    vac_titel = vac_eisen.get("titel", vac_map)

                    stap += 1
                    st.write(f"🔄 Analyseren: **{naam}** vs **{vac_titel}** ({stap}/{totaal})...")

                    stream_container = st.empty()
                    stream_tekst = ""
                    resultaat = None
                    vac_eisen_json = json.dumps(vac_eisen, indent=2, ensure_ascii=False)

                    for event in vraag_ollama_stream(
                        cv_profiel_json, vac_eisen_json,
                        url=st.session_state.ollama_url,
                        model=st.session_state.ollama_model,
                        temperature=st.session_state.temperature,
                        modus=gekozen_modus,
                    ):
                        if event["type"] == "token":
                            stream_tekst += event["data"]
                        elif event["type"] == "result":
                            resultaat = event["data"]
                        elif event["type"] == "error":
                            resultaat = event["data"]
                            st.error(f"Fout: {event['data']}")

                    stream_container.empty()

                    if resultaat and isinstance(resultaat, dict):
                        resultaat["vacature_titel"] = vac_titel
                        resultaat["kandidaat_naam"] = naam
                        alle_resultaten.append(resultaat)
                        matches_voor_kandidaat.append(resultaat)
            
                # Rapport opslaan per kandidaat als z'n matches klaar zijn
                if matches_voor_kandidaat:
                     rapport = genereer_rapport(naam, matches_voor_kandidaat)
                     rapport_naam = f"rapport_{cv_map}.txt"
                     rapport_pad = os.path.join(RAPPORT_DIR, rapport_naam)
                     with open(rapport_pad, "w", encoding="utf-8") as f:
                         f.write(rapport)
                     st.write(f"📝 Bestand opgeslagen: `{rapport_naam}`")

            status.update(label="Matching Succesvol Voltooid!", state="complete", expanded=False)
            st.toast("Matching succesvol voltooid", icon="🎉")
            st.balloons()
        
        # Rendern van de UI resultaten Outside of the status box
        st.divider()
        st.subheader("Resultaten Overzicht")
        
        for res in alle_resultaten:
            pct = res.get("match_percentage", 0)
            with st.container(border=True):
                st.markdown(f"### {res['kandidaat_naam']} 🤝 {res['vacature_titel']}")
                
                # Match score prominently with st.metric
                st.metric("Match Score", f"{pct}%")
                st.progress(pct / 100)
                
                col_match, col_ontb = st.columns(2)
                with col_match:
                    st.markdown(":green[**✅ Matchende punten**]")
                    for p in res.get("matchende_punten", []):
                        st.markdown(f":green[- {p}]")
                with col_ontb:
                    st.markdown(":red[**❌ Ontbrekende punten**]")
                    for p in res.get("ontbrekende_punten", []):
                        st.markdown(f":red[- {p}]")
                
                with st.expander("Lees uitgebreide onderbouwing"):
                    if res.get("onderbouwing"):
                        st.info(f"{res['onderbouwing']}")
                    else:
                        st.write("Geen verdere onderbouwing opgegeven.")


def pagina_rapporten():
    st.title("📄 Rapporten")

    if not os.path.isdir(RAPPORT_DIR):
        st.info("Nog geen rapporten gegenereerd.")
        return

    rapporten = lijst_bestanden(RAPPORT_DIR)
    if not rapporten:
        st.info("Nog geen rapporten gevonden.")
        return

    # Dataframe overzicht
    st.write("Overzicht van alle lokaal opgeslagen match-rapporten.")
    
    table_data = []
    for rapport in rapporten:
        pad = os.path.join(RAPPORT_DIR, rapport)
        tijd = os.path.getmtime(pad)
        table_data.append({
            "Rapport Naam": rapport,
            "Aangemaakt op": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tijd))
        })
    st.dataframe(table_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    with st.container(border=True):
        st.subheader("Rapport Inzien & Downloaden")
        gekozen_rapport = st.selectbox("Selecteer een rapport:", rapporten)
        if gekozen_rapport:
            pad = os.path.join(RAPPORT_DIR, gekozen_rapport)
            with open(pad, encoding="utf-8") as f:
                inhoud = f.read()
            
            c1, c2 = st.columns([1, 4])
            with c1:
                st.download_button(
                    label="⬇️ Download Rapport",
                    data=inhoud,
                    file_name=gekozen_rapport,
                    mime="text/plain",
                    type="primary",
                    use_container_width=True
                )
            
            with st.expander("Bekijk geformatteerd rapport:", expanded=True):
                st.markdown(inhoud)


def pagina_instellingen():
    st.title("⚙️ Instellingen")
    
    with st.container(border=True):
        st.subheader("Ollama Configuratie")
        col1, col2 = st.columns(2)
        
        with col1:
            nieuwe_url = st.text_input("Ollama URL", value=st.session_state.ollama_url)
            if nieuwe_url != st.session_state.ollama_url:
                st.session_state.ollama_url = nieuwe_url
                st.toast("URL bijgewerkt!", icon="✅")
                time.sleep(0.5)
                st.rerun()

        with col2:
            online, modellen = check_ollama_status()
            if online and modellen:
                huidige_index = modellen.index(st.session_state.ollama_model) if st.session_state.ollama_model in modellen else 0
                gekozen_model = st.selectbox("Model", modellen, index=huidige_index)
                if gekozen_model != st.session_state.ollama_model:
                    st.session_state.ollama_model = gekozen_model
                    st.toast("Model ingesteld!", icon="✅")
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
        nieuw_system = st.text_area("System prompt", st.session_state.system_prompt, height=150)
        if nieuw_system != st.session_state.system_prompt:
            st.session_state.system_prompt = nieuw_system

        nieuw_match = st.text_area("Match prompt", st.session_state.match_prompt, height=250)
        if nieuw_match != st.session_state.match_prompt:
            st.session_state.match_prompt = nieuw_match

        st.caption("ℹ️ Let op: Wijzigingen in prompts en instellingen hier gelden alleen voor deze sessie. Bewerk `config.py` om ze permanent te maken voor volgende opstarts.")


# --- Pagina Navigatie inrichten (Streamlit v1.36+) ---

pg_dash = st.Page(pagina_dashboard, title="Dashboard", icon="📊", default=True)
pg_match = st.Page(pagina_match, title="Match Starten", icon="🎯")
pg_kand = st.Page(pagina_kandidaten_beheer, title="Kandidaten Beheren", icon="🫂")
pg_werk = st.Page(pagina_werkgeversvragen_beheer, title="Werkgeversvragen Beheren", icon="🏢")
pg_rapp = st.Page(pagina_rapporten, title="Rapporten Inzien", icon="📄")
pg_inst = st.Page(pagina_instellingen, title="Instellingen", icon="⚙️")

pg = st.navigation({
    "Overzicht": [pg_dash, pg_match],
    "Beheer": [pg_kand, pg_werk],
    "Systeem": [pg_rapp, pg_inst]
})

# Run de geselecteerde pagina
pg.run()
