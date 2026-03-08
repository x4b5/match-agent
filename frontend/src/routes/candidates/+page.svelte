<script lang="ts">
  import type { PageData } from "./$types";
  import { toasts } from "$lib/toast";

  let { data } = $props<{ data: PageData }>();

  let candidates = $state(data.candidates || []);
  let newCandidateName = $state("");
  let isCreating = $state(false);
  let searchQuery = $state("");
  let sortOption = $state("alpha-asc");
  let filterProfile = $state("all");
  let generatingNames: Set<string> = $state(new Set());
  let confirmingDelete: string | null = $state(null);

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
        { method: "POST" },
      );
      if (res.ok) {
        toasts.add(`Kandidaat "${newCandidateName}" aangemaakt`, "success");
        newCandidateName = "";
        await refreshCandidates();
      } else {
        toasts.add("Fout bij aanmaken kandidaat", "error");
      }
    } finally {
      isCreating = false;
    }
  }

  async function deleteCandidate(name: string) {
    const res = await fetch(`/api/candidates/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (res.ok) {
      toasts.add(`"${name}" verwijderd`, "success");
      confirmingDelete = null;
      await refreshCandidates();
    } else {
      toasts.add("Fout bij verwijderen", "error");
    }
  }

  async function refreshCandidates() {
    const res = await fetch("/api/candidates/");
    candidates = await res.json();
  }

  async function generateProfile(name: string) {
    generatingNames = new Set([...generatingNames, name]);
    try {
      const res = await fetch(
        `/api/candidates/${encodeURIComponent(name)}/generate-profile`,
        { method: "POST" },
      );
      if (!res.ok) {
        toasts.add("Fout bij starten generatie", "error");
        return;
      }
      toasts.add(`Profiel generatie gestart voor "${name}"`, "info");
      const poll = setInterval(async () => {
        const data = await fetch("/api/candidates/").then((r) => r.json());
        const updated = data.find((c: any) => c.naam === name);
        if (updated?.has_profile) {
          clearInterval(poll);
          candidates = data;
          generatingNames = new Set(
            [...generatingNames].filter((n) => n !== name),
          );
          toasts.add(`Profiel voor "${name}" is klaar!`, "success");
        }
      }, 3000);
      setTimeout(() => {
        clearInterval(poll);
        if (generatingNames.has(name)) {
          generatingNames = new Set(
            [...generatingNames].filter((n) => n !== name),
          );
          toasts.add(
            `Time-out bij generatie van "${name}". Probeer opnieuw.`,
            "warning",
          );
        }
      }, 300000);
    } catch {
      toasts.add("Fout bij starten generatie", "error");
      generatingNames = new Set([...generatingNames].filter((n) => n !== name));
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
      {#if isCreating}
        <span
          class="material-icons spin"
          style="font-size: 1rem; vertical-align: middle;">autorenew</span
        > Bezig...
      {:else}
        <span
          class="material-icons"
          style="font-size: 1rem; vertical-align: middle;">add</span
        > Aanmaken
      {/if}
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
    <div class="card empty-state">
      <span class="material-icons">person_search</span>
      <h3>Nog geen kandidaten</h3>
      <p>Maak hierboven een nieuw dossier aan om te starten.</p>
    </div>
  {:else if filteredCandidates.length === 0}
    <div class="card empty-state">
      <span class="material-icons">search_off</span>
      <h3>Geen resultaten</h3>
      <p>Geen kandidaten gevonden voor "{searchQuery}"</p>
    </div>
  {:else}
    {#each filteredCandidates as candidate, i}
      <div
        class="card stagger-item"
        style="display: flex; justify-content: space-between; align-items: center; animation-delay: {i *
          50}ms;"
      >
        <div>
          <h2
            style="margin: 0; font-size: 1.2rem; display: flex; align-items: center; gap: 10px;"
          >
            {candidate.naam}
            {#if candidate.has_profile}
              <span class="badge badge-success">✓ Profiel</span>
            {:else}
              <span class="badge badge-warning">⚠ Ontbreekt</span>
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
        <div style="display: flex; gap: 10px; align-items: center;">
          {#if confirmingDelete === candidate.naam}
            <div class="confirm-bar">
              <span>Verwijderen?</span>
              <button
                class="btn-confirm-yes"
                onclick={() => deleteCandidate(candidate.naam)}>Ja</button
              >
              <button
                class="btn-confirm-no"
                onclick={() => (confirmingDelete = null)}>Nee</button
              >
            </div>
          {:else}
            <button
              class="btn-primary"
              onclick={() => generateProfile(candidate.naam)}
              disabled={generatingNames.has(candidate.naam)}
            >
              {#if generatingNames.has(candidate.naam)}
                <span
                  class="material-icons spin"
                  style="font-size: 1rem; vertical-align: middle;"
                  >autorenew</span
                > Bezig...
              {:else}
                <span
                  class="material-icons"
                  style="font-size: 1rem; vertical-align: middle;"
                  >auto_awesome</span
                > Genereer
              {/if}
            </button>
            <button
              class="btn-icon-danger"
              onclick={() => (confirmingDelete = candidate.naam)}
              title="Verwijderen"
            >
              <span class="material-icons" style="font-size: 1.1rem;"
                >delete</span
              >
            </button>
          {/if}
        </div>
      </div>
    {/each}
  {/if}
</div>
