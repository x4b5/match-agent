<script lang="ts">
  import type { PageData } from "./$types";

  let { data } = $props<{ data: PageData }>();

  let candidates = $state(data.candidates || []);
  let newCandidateName = $state("");
  let isCreating = $state(false);
  let searchQuery = $state("");
  let sortOption = $state("alpha-asc");
  let filterProfile = $state("all");
  let generatingNames: Set<string> = $state(new Set());
  let expandedName: string | null = $state(null);
  let uploadingName: string | null = $state(null);

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
    generatingNames = new Set([...generatingNames, name]);
    try {
      const res = await fetch(
        `/api/candidates/${encodeURIComponent(name)}/generate-profile`,
        { method: "POST" },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        alert(data?.detail || "Fout bij starten generatie");
        generatingNames = new Set([...generatingNames].filter((n) => n !== name));
        return;
      }
      const result = await res.json();
      const taskId = result.task_id;

      // Poll task status
      const poll = setInterval(async () => {
        if (taskId) {
          const taskRes = await fetch(`/api/tasks/${taskId}`);
          const task = await taskRes.json();
          if (task.status === "done") {
            clearInterval(poll);
            await refreshCandidates();
            generatingNames = new Set([...generatingNames].filter((n) => n !== name));
          } else if (task.status === "failed") {
            clearInterval(poll);
            alert(task.error || "Profielgeneratie mislukt.");
            generatingNames = new Set([...generatingNames].filter((n) => n !== name));
          }
        } else {
          const data = await fetch("/api/candidates/").then((r) => r.json());
          const updated = data.find((c: any) => c.naam === name);
          if (updated?.has_profile) {
            clearInterval(poll);
            candidates = data;
            generatingNames = new Set([...generatingNames].filter((n) => n !== name));
          }
        }
      }, 3000);

      setTimeout(() => {
        clearInterval(poll);
        generatingNames = new Set([...generatingNames].filter((n) => n !== name));
      }, 300000);
    } catch {
      alert("Fout bij starten generatie");
      generatingNames = new Set([...generatingNames].filter((n) => n !== name));
    }
  }

  function toggleExpand(name: string) {
    expandedName = expandedName === name ? null : name;
  }

  async function uploadFile(name: string, event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;
    uploadingName = name;
    try {
      for (const file of input.files) {
        const formData = new FormData();
        formData.append("file", file);
        await fetch(`/api/candidates/${encodeURIComponent(name)}/upload`, {
          method: "POST",
          body: formData,
        });
      }
      await refreshCandidates();
    } catch {
      alert("Fout bij uploaden");
    } finally {
      uploadingName = null;
      input.value = "";
    }
  }

  async function deleteDocument(name: string, filename: string) {
    if (!confirm(`${filename} verwijderen?`)) return;
    const res = await fetch(
      `/api/candidates/${encodeURIComponent(name)}/document/${encodeURIComponent(filename)}`,
      { method: "DELETE" },
    );
    if (res.ok) await refreshCandidates();
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
      <div class="card">
        <div
          style="display: flex; justify-content: space-between; align-items: center; cursor: pointer;"
          onclick={() => toggleExpand(candidate.naam)}
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
                      : 'var(--neon-pink)'};">{candidate.profile_score}%</strong
                >
              {/if}
            </div>
          </div>
          <div style="display: flex; gap: 10px;" onclick={(e) => e.stopPropagation()}>
            <button
              class="btn-primary"
              onclick={() => generateProfile(candidate.naam)}
              disabled={generatingNames.has(candidate.naam)}
            >
              {#if generatingNames.has(candidate.naam)}
                <span class="material-icons spin" style="font-size: 1rem; vertical-align: middle;">autorenew</span> Bezig...
              {:else}
                <span class="material-icons" style="font-size: 1rem; vertical-align: middle;">auto_awesome</span> Genereer
              {/if}
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

        {#if expandedName === candidate.naam}
          <div
            style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--glass-border);"
          >
            <h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">
              <span class="material-icons" style="font-size: 1rem; vertical-align: middle;">folder</span>
              Documenten
            </h4>

            {#if candidate.docs?.length}
              <div style="display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1rem;">
                {#each candidate.docs as doc}
                  <div
                    style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.8rem; background: var(--surface-0); border-radius: var(--radius-sm); border: 1px solid var(--glass-border);"
                  >
                    <span style="font-size: 0.85rem; color: var(--text-primary);">
                      <span class="material-icons" style="font-size: 0.9rem; vertical-align: middle; margin-right: 4px;">description</span>
                      {doc}
                    </span>
                    <button
                      class="btn-secondary"
                      style="padding: 0.2rem 0.5rem; font-size: 0.75rem; color: var(--neon-pink); border-color: rgba(255,64,129,0.3);"
                      onclick={() => deleteDocument(candidate.naam, doc)}
                    >
                      <span class="material-icons" style="font-size: 0.85rem; vertical-align: middle;">close</span>
                    </button>
                  </div>
                {/each}
              </div>
            {:else}
              <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
                Geen documenten. Upload hieronder.
              </p>
            {/if}

            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <label
                class="btn-secondary"
                style="cursor: pointer; display: inline-flex; align-items: center; gap: 4px;"
              >
                <span class="material-icons" style="font-size: 1rem;">upload_file</span>
                {#if uploadingName === candidate.naam}
                  Uploaden...
                {:else}
                  Upload document
                {/if}
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.csv,.md,.eml"
                  multiple
                  style="display: none;"
                  onchange={(e) => uploadFile(candidate.naam, e)}
                  disabled={uploadingName === candidate.naam}
                />
              </label>
              <span style="font-size: 0.75rem; color: var(--text-secondary);">
                PDF, DOCX, TXT, CSV, MD, EML
              </span>
            </div>
          </div>
        {/if}
      </div>
    {/each}
  {/if}
</div>
