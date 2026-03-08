<script lang="ts">
  import type { PageData } from "./$types";

  let { data } = $props<{ data: PageData }>();

  let employers = $state(data.employers || []);
  let newEmployerName = $state("");
  let isCreating = $state(false);
  let searchQuery = $state("");
  let sortOption = $state("alpha-asc");
  let filterProfile = $state("all");

  let filteredEmployers = $derived(
    (() => {
      let result = employers.filter((e: any) =>
        e.naam.toLowerCase().includes(searchQuery.toLowerCase()),
      );
      if (filterProfile === "present")
        result = result.filter((e: any) => e.has_profile);
      if (filterProfile === "missing")
        result = result.filter((e: any) => !e.has_profile);

      return result.sort((a: any, b: any) => {
        if (sortOption === "alpha-asc") return a.naam.localeCompare(b.naam);
        if (sortOption === "alpha-desc") return b.naam.localeCompare(a.naam);
        if (sortOption === "score-desc")
          return (b.profile_score || 0) - (a.profile_score || 0);
        if (sortOption === "score-asc")
          return (a.profile_score || 0) - (b.profile_score || 0);
        return 0;
      });
    })(),
  );

  async function createEmployer() {
    if (!newEmployerName.trim()) return;
    isCreating = true;
    try {
      const res = await fetch(
        `/api/employers/?name=${encodeURIComponent(newEmployerName)}`,
        {
          method: "POST",
        },
      );
      if (res.ok) {
        newEmployerName = "";
        await refreshEmployers();
      } else {
        alert("Fout bij aanmaken");
      }
    } finally {
      isCreating = false;
    }
  }

  async function deleteEmployer(name: string) {
    if (!confirm(`Weet je zeker dat je ${name} wilt verwijderen?`)) return;
    const res = await fetch(`/api/employers/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (res.ok) await refreshEmployers();
  }

  async function refreshEmployers() {
    const res = await fetch("/api/employers/");
    employers = await res.json();
  }

  async function generateProfile(name: string) {
    const res = await fetch(
      `/api/employers/${encodeURIComponent(name)}/generate-profile`,
      { method: "POST" },
    );
    if (res.ok) {
      alert("Profiel generatie gestart in de achtergrond.");
    } else {
      alert("Fout bij starten generatie");
    }
  }
</script>

<div class="page-hero">
  <h1>
    <span class="material-icons" style="font-size: 2.2rem; margin-right: 15px;"
      >business</span
    > Werkgeversvragen Beheren
  </h1>
  <p>Beheer vacatures en profielen voor werkgeversvragen.</p>
</div>

<div class="card">
  <h3 style="margin-bottom: 1rem;">
    <span class="material-icons" style="vertical-align: middle;"
      >add_circle</span
    > Nieuw dossier aanmaken
  </h3>
  <div style="display: flex; gap: 1rem;">
    <input
      type="text"
      class="input-field"
      style="flex: 1;"
      placeholder="Bijv. backend_developer_acme"
      bind:value={newEmployerName}
      onkeydown={(e) => e.key === "Enter" && createEmployer()}
    />
    <button class="btn-primary" onclick={createEmployer} disabled={isCreating}>
      {isCreating ? "Bezig..." : "Aanmaken"}
    </button>
  </div>
</div>

<div style="margin-top: 2rem;">
  {#if employers.length > 0}
    <div
      style="margin-bottom: 1.5rem; display: flex; flex-wrap: wrap; align-items: center; gap: 1rem;"
    >
      <div
        style="display: flex; align-items: center; gap: 0.5rem; flex: 1; min-width: 250px;"
      >
        <span
          class="material-icons"
          style="color: var(--text-secondary); font-size: 1.8rem;">search</span
        >
        <input
          type="text"
          class="input-field"
          style="flex: 1;"
          placeholder="Zoek werkgeversvraag op naam..."
          bind:value={searchQuery}
        />
      </div>

      <div
        style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;"
      >
        <select
          class="input-field"
          bind:value={filterProfile}
          style="min-width: 150px; padding: 0.6rem 1rem;"
        >
          <option value="all">Alle profielen</option>
          <option value="present">Profiel aanwezig</option>
          <option value="missing">Profiel ontbreekt</option>
        </select>

        <select
          class="input-field"
          bind:value={sortOption}
          style="min-width: 150px; padding: 0.6rem 1rem;"
        >
          <option value="alpha-asc">Alfabetisch (A-Z)</option>
          <option value="alpha-desc">Alfabetisch (Z-A)</option>
          <option value="score-desc">Betrouwbaarheid (Hoog-Laag)</option>
          <option value="score-asc">Betrouwbaarheid (Laag-Hoog)</option>
        </select>
      </div>
    </div>
  {/if}

  {#if employers.length === 0}
    <div
      class="card"
      style="text-align: center; color: var(--text-secondary); padding: 2rem;"
    >
      Geen werkgeversvragen gevonden. Maak een nieuw dossier aan.
    </div>
  {:else if filteredEmployers.length === 0}
    <div
      class="card"
      style="text-align: center; color: var(--text-secondary); padding: 2rem;"
    >
      Geen werkgeversvragen gevonden voor "{searchQuery}".
    </div>
  {:else}
    {#each filteredEmployers as employer}
      <div
        class="card"
        style="display: flex; justify-content: space-between; align-items: center;"
      >
        <div>
          <h2
            style="margin: 0; font-size: 1.2rem; display: flex; align-items: center; gap: 10px;"
          >
            {employer.naam}
            {#if employer.has_profile}
              <span
                class="status-dot-container online"
                style="font-size: 0.6rem;">✓ Profiel</span
              >
            {:else}
              <span
                class="status-dot-container offline"
                style="font-size: 0.6rem; color: #FFAB00; border-color: rgba(255,171,0,0.3); background: rgba(255,171,0,0.15);"
                >⚠ Ontbreekt</span
              >
            {/if}
          </h2>
          <div
            style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.5rem;"
          >
            {employer.doc_count} documenten
            {#if employer.has_profile}
              | Betrouwbaarheid: <strong
                style="color: {employer.profile_score > 75
                  ? 'var(--neon-green)'
                  : employer.profile_score > 40
                    ? '#FFAB00'
                    : 'var(--neon-pink)'}">{employer.profile_score}%</strong
              >
            {/if}
          </div>
        </div>
        <div style="display: flex; gap: 10px;">
          <button
            class="btn-primary"
            onclick={() => generateProfile(employer.naam)}
          >
            <span
              class="material-icons"
              style="font-size: 1rem; vertical-align: middle;"
              >auto_awesome</span
            > Genereer
          </button>
          <button
            class="btn-secondary"
            onclick={() => deleteEmployer(employer.naam)}
            style="color: var(--neon-pink); border-color: rgba(255,64,129,0.3);"
          >
            <span
              class="material-icons"
              style="font-size: 1rem; vertical-align: middle;">delete</span
            >
          </button>
        </div>
      </div>
    {/each}
  {/if}
</div>
