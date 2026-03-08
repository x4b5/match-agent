<script lang="ts">
  import type { PageData } from "./$types";

  let { data } = $props<{ data: PageData }>();

  let candidates = $state(data.candidates || []);
  let newCandidateName = $state("");
  let isCreating = $state(false);
  let searchQuery = $state("");
  let sortOption = $state("alpha-asc");
  let filterProfile = $state("all");

  let filteredCandidates = $derived(
    (() => {
      let result = candidates.filter((c: any) =>
        c.naam.toLowerCase().includes(searchQuery.toLowerCase()),
      );
      if (filterProfile === "present")
        result = result.filter((c: any) => c.has_profile);
      if (filterProfile === "missing")
        result = result.filter((c: any) => !c.has_profile);

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

  async function createCandidate() {
    if (!newCandidateName.trim()) return;
    isCreating = true;
    try {
      const res = await fetch(
        `/api/candidates/?name=${encodeURIComponent(newCandidateName)}`,
        {
          method: "POST",
        },
      );
      if (res.ok) {
        newCandidateName = "";
        await refreshCandidates();
      } else {
        alert("Fout bij aanmaken");
      }
    } finally {
      isCreating = false;
    }
  }

  async function deleteCandidate(name: string) {
    if (!confirm(`Weet je zeker dat je ${name} wilt verwijderen?`)) return;
    const res = await fetch(`/api/candidates/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (res.ok) await refreshCandidates();
  }

  async function refreshCandidates() {
    const res = await fetch("/api/candidates/");
    candidates = await res.json();
  }

  async function generateProfile(name: string) {
    const res = await fetch(
      `/api/candidates/${encodeURIComponent(name)}/generate-profile`,
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
      >group</span
    > Kandidaten Beheren
  </h1>
  <p>Beheer dossiers, documenten en LLM-profielen voor kandidaten.</p>
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
      placeholder="Bijv. jan_jansen"
      bind:value={newCandidateName}
      onkeydown={(e) => e.key === "Enter" && createCandidate()}
    />
    <button class="btn-primary" onclick={createCandidate} disabled={isCreating}>
      {isCreating ? "Bezig..." : "Aanmaken"}
    </button>
  </div>
</div>

<div style="margin-top: 2rem;">
  {#if candidates.length > 0}
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
          placeholder="Zoek kandidaat op naam..."
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

  {#if candidates.length === 0}
    <div
      class="card"
      style="text-align: center; color: var(--text-secondary); padding: 2rem;"
    >
      Geen kandidaten gevonden. Maak een nieuw dossier aan.
    </div>
  {:else if filteredCandidates.length === 0}
    <div
      class="card"
      style="text-align: center; color: var(--text-secondary); padding: 2rem;"
    >
      Geen kandidaten gevonden voor "{searchQuery}".
    </div>
  {:else}
    {#each filteredCandidates as candidate}
      <div
        class="card"
        style="display: flex; justify-content: space-between; align-items: center;"
      >
        <div>
          <h2
            style="margin: 0; font-size: 1.2rem; display: flex; align-items: center; gap: 10px;"
          >
            {candidate.naam}
            {#if candidate.has_profile}
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
            {candidate.doc_count} documenten
            {#if candidate.has_profile}
              | Betrouwbaarheid: <strong
                style="color: {candidate.profile_score > 75
                  ? 'var(--neon-green)'
                  : candidate.profile_score > 40
                    ? '#FFAB00'
                    : 'var(--neon-pink)'}">{candidate.profile_score}%</strong
              >
            {/if}
          </div>
        </div>
        <div style="display: flex; gap: 10px;">
          <button
            class="btn-primary"
            onclick={() => generateProfile(candidate.naam)}
          >
            <span
              class="material-icons"
              style="font-size: 1rem; vertical-align: middle;"
              >auto_awesome</span
            > Genereer
          </button>
          <button
            class="btn-secondary"
            onclick={() => deleteCandidate(candidate.naam)}
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
