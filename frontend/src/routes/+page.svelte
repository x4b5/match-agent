<script lang="ts">
  import type { PageData } from "./$types";
  export let data: PageData;

  $: online = data.ollama?.online || false;
  $: models = data.ollama?.models || [];
  $: candidatesCount = data.candidates?.length || 0;
  $: employersCount = data.employers?.length || 0;

  $: candidatesProfiled =
    data.candidates?.filter((c) => c.has_profile).length || 0;
  $: employersProfiled =
    data.employers?.filter((e) => e.has_profile).length || 0;

  $: candidatesPercent =
    candidatesCount > 0
      ? Math.round((candidatesProfiled / candidatesCount) * 100)
      : 0;
  $: employersPercent =
    employersCount > 0
      ? Math.round((employersProfiled / employersCount) * 100)
      : 0;
</script>

<div class="page-hero">
  <h1>
    <span class="material-icons" style="font-size: 2.2rem; margin-right: 15px;"
      >bar_chart</span
    > Dashboard
  </h1>
  <p>Overzicht van je matching-omgeving</p>
</div>

{#if data.error}
  <div
    style="background: rgba(255,82,82,0.1); border: 1px solid rgba(255,82,82,0.3); padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; color: #ff5252; display: flex; align-items: center; gap: 10px;"
  >
    <span class="material-icons">error_outline</span>
    <div><strong>Opgelet:</strong> {data.error}</div>
  </div>
{/if}

<div class="grid-3" style="margin-bottom: 2rem;">
  <!-- Ollama Status -->
  <div class="card">
    <div
      style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;"
    >
      <div class="status-dot-container {online ? 'online' : 'offline'}">
        <span class="status-dot"></span>
        {online ? "Online" : "Offline"}
      </div>
      <span class="material-icons" style="color: var(--text-secondary);"
        >dns</span
      >
    </div>
    <div
      style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;"
    >
      Ollama
    </div>
    <div class="metric-value">{online ? "Actief" : "Inactief"}</div>
  </div>

  <!-- Active Model -->
  <div class="card">
    <div
      style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;"
    >
      Actieve Modellen
    </div>
    <div class="metric-value" style="font-size: 2.2rem;">
      {models.length > 0 ? models.length : "—"}
    </div>
    {#if models.length > 0}
      <div
        style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-secondary);"
      >
        Beschikbaar: {models.join(", ")}
      </div>
    {/if}
  </div>

  <!-- Storage -->
  <div class="card">
    <div
      style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem;"
    >
      Systeem Lokatie
    </div>
    <div class="metric-value" style="font-size: 2.2rem;">Lokaal</div>
    <div
      style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-secondary);"
    >
      Geen cloud afhankelijkheden.
    </div>
  </div>
</div>

<h2 style="font-size: 1.3rem; margin-bottom: 1rem;">Data Overzicht</h2>

<div class="grid-2">
  <!-- Candidates Overview -->
  <div class="card">
    <div
      style="display: flex; justify-content: space-between; align-items: start;"
    >
      <div>
        <div
          style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;"
        >
          Kandidaten
        </div>
        <div class="metric-value">{candidatesCount}</div>
      </div>
      <span
        class="material-icons"
        style="font-size: 2.5rem; color: rgba(255,255,255,0.1);">group</span
      >
    </div>
    <div style="margin-top: 1rem;">
      <div
        style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;"
      >
        <span style="font-size: 0.8rem; color: var(--text-secondary);">
          <span
            class="material-icons"
            style="font-size: 1rem; vertical-align: middle;">auto_awesome</span
          >
          {candidatesProfiled} met LLM-profiel
        </span>
        <span
          style="font-size: 0.75rem; color: {candidatesPercent > 0
            ? 'var(--neon-green)'
            : 'var(--text-secondary)'}; font-weight: 600;"
        >
          {candidatesPercent}%
        </span>
      </div>
      <div class="progress-bar">
        <div
          class="progress-bar-fill"
          style="width: {candidatesPercent}%;"
        ></div>
      </div>
    </div>
  </div>

  <!-- Employers Overview -->
  <div class="card">
    <div
      style="display: flex; justify-content: space-between; align-items: start;"
    >
      <div>
        <div
          style="font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;"
        >
          Werkgeversvragen
        </div>
        <div class="metric-value">{employersCount}</div>
      </div>
      <span
        class="material-icons"
        style="font-size: 2.5rem; color: rgba(255,255,255,0.1);">business</span
      >
    </div>
    <div style="margin-top: 1rem;">
      <div
        style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;"
      >
        <span style="font-size: 0.8rem; color: var(--text-secondary);">
          <span
            class="material-icons"
            style="font-size: 1rem; vertical-align: middle;">auto_awesome</span
          >
          {employersProfiled} met LLM-profiel
        </span>
        <span
          style="font-size: 0.75rem; color: {employersPercent > 0
            ? 'var(--neon-green)'
            : 'var(--text-secondary)'}; font-weight: 600;"
        >
          {employersPercent}%
        </span>
      </div>
      <div class="progress-bar">
        <div
          class="progress-bar-fill"
          style="width: {employersPercent}%;"
        ></div>
      </div>
    </div>
  </div>
</div>

<!-- Quick Actions -->
<h2 style="font-size: 1.3rem; margin-top: 2rem; margin-bottom: 1rem;">
  Snelkoppelingen
</h2>
<div class="grid-3">
  <a href="/candidates" class="quick-action">
    <span class="material-icons">person_add</span>
    <span>Kandidaat toevoegen</span>
  </a>
  <a href="/employers" class="quick-action">
    <span class="material-icons">post_add</span>
    <span>Werkgeversvraag toevoegen</span>
  </a>
  <a href="/match" class="quick-action">
    <span class="material-icons">play_circle</span>
    <span>Nieuwe match starten</span>
  </a>
</div>
