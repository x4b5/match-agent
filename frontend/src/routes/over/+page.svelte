<script lang="ts">
  // Optional: any state or logic needed for the About page
</script>

<div
  class="page-hero"
  style="text-align: center; border-bottom: none; margin-bottom: 3rem; margin-top: 2rem;"
>
  <h1 style="font-size: 3.5rem; letter-spacing: 4px; display: inline-block;">
    <span
      style="color: var(--neon-cyan); text-shadow: 0 0 20px rgba(0,229,255,0.4);"
      >MATCH</span
    >FLIX
  </h1>
  <p
    style="font-size: 1.2rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 3px; margin-top: 0.5rem;"
  >
    Agent Kompas
    <span
      style="display: block; font-size: 0.8rem; margin-top: 0.5rem; color: var(--neon-green);"
    >
      100% LOKAAL & AVG/GDPR-COMPLIANT
    </span>
  </p>
</div>

<div class="grid-2" style="max-width: 1000px; margin: 0 auto;">
  <div class="card element-container">
    <h2
      style="display: flex; align-items: center; gap: 10px; font-size: 1.3rem;"
    >
      <span class="material-icons" style="color: var(--neon-cyan);"
        >psychology</span
      >
      Lokale AI Kracht
    </h2>
    <p>
      Matchflix zet de kracht van geavanceerde Large Language Models (LLMs)
      lokaal in op je eigen machine via Ollama. Dit betekent dat geen enkele cv
      of vacaturetekst ooit je laptop of netwerk verlaat. Alle analyses,
      vectorembeddings en data-extracties gebeuren veilig op je eigen hardware.
    </p>
  </div>

  <div class="card element-container">
    <h2
      style="display: flex; align-items: center; gap: 10px; font-size: 1.3rem;"
    >
      <span class="material-icons" style="color: var(--neon-purple);"
        >verified_user</span
      >
      AVG/GDPR-Compliant
    </h2>
    <p>
      Bij de recruitment-operatie staat privacy voorop. Omdat MATCHFLIX een <strong
        >100% gesloten systeem</strong
      > is zonder cloud-afhankelijkheden, behoud je de volledige datasoevereiniteit
      over gevoelige persoonsgegevens uit documenten en sollicitaties.
    </p>
  </div>

  <div class="card element-container" style="grid-column: 1 / -1;">
    <h2
      style="display: flex; align-items: center; gap: 10px; font-size: 1.3rem;"
    >
      <span class="material-icons" style="color: var(--neon-blue);"
        >architecture</span
      >
      De Architectuur
    </h2>
    <p>
      De overstap naar een asynchrone FastAPI + SvelteKit architectuur
      garandeert een schaalbare flow. Modellen verwerken data efficiënt via
      queues om blokkades te minimaliseren. Tegelijkertijd streamt de frontend
      realtime de gegenereerde kandidaatprofielen terug naar je scherm.
    </p>
    <ul
      style="color: var(--text-secondary); line-height: 1.8; margin-top: 1rem;"
    >
      <li>
        <strong>Frontend:</strong> Svelte 5 (Vite) voor een interactieve UI zonder
        haperingen.
      </li>
      <li>
        <strong>Backend API:</strong> Python FastAPI met aiosqlite en sse-starlette
        voor server-sent-events.
      </li>
      <li>
        <strong>Intelligentie:</strong> Ollama API in de achtergrond voor het aansturen
        van open-source LLMs.
      </li>
    </ul>
  </div>
</div>
