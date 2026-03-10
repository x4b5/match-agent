<script lang="ts">
  import type { PageData } from "./$types";
  import { toasts } from "$lib/toast";
  import DossierCompleetheidEnrichment from "$lib/components/DossierCompleetheidEnrichment.svelte";

  let { data } = $props<{ data: PageData }>();

  let candidates = $state(data.candidates || []);
  let newCandidateName = $state("");
  let isCreating = $state(false);
  let searchQuery = $state("");
  let sortOption = $state("alpha-asc");
  let filterProfile = $state("all");
  let generatingNames: Set<string> = $state(new Set());
  let confirmingDelete: string | null = $state(null);
  let expandedName: string | null = $state(null);
  let editingName: string | null = $state(null);
  let editJson = $state("");
  let isSaving = $state(false);
  let detailCache: Record<string, any> = $state({});
  let taskDetails: Record<string, { progress: string; percent: number }> =
    $state({});

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

  async function toggleDetail(name: string) {
    if (expandedName === name) {
      expandedName = null;
      editingName = null;
      return;
    }
    expandedName = name;
    editingName = null;
    if (!detailCache[name]) {
      try {
        const res = await fetch(`/api/candidates/${encodeURIComponent(name)}`);
        if (res.ok) {
          detailCache[name] = await res.json();
        }
      } catch {
        toasts.add("Kon details niet ophalen", "error");
      }
    }
  }

  function startEditing(name: string) {
    const detail = detailCache[name];
    if (detail?.profile_data) {
      editJson = JSON.stringify(detail.profile_data, null, 2);
    } else {
      editJson = "{}";
    }
    editingName = name;
  }

  function cancelEditing() {
    editingName = null;
    editJson = "";
  }

  async function saveProfile(name: string) {
    isSaving = true;
    try {
      const parsed = JSON.parse(editJson);
      const res = await fetch(
        `/api/candidates/${encodeURIComponent(name)}/profile`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed),
        },
      );
      if (res.ok) {
        toasts.add(`Profiel van "${name}" opgeslagen`, "success");
        detailCache[name] = {
          ...detailCache[name],
          profile_data: parsed,
          has_profile: true,
        };
        editingName = null;
        await refreshCandidates();
      } else {
        toasts.add("Fout bij opslaan profiel", "error");
      }
    } catch (e) {
      toasts.add("Ongeldige JSON — controleer de syntax", "error");
    } finally {
      isSaving = false;
    }
  }

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
      if (expandedName === name) expandedName = null;
      delete detailCache[name];
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
      const responseData = await res.json();
      const taskId = responseData.task_id;
      toasts.add(`Profiel generatie gestart voor "${name}"`, "info");

      const poll = setInterval(async () => {
        const taskRes = await fetch(`/api/tasks/${taskId}`);
        if (!taskRes.ok) return;
        const taskData = await taskRes.json();

        // Update task details for visual feedback
        taskDetails[name] = {
          progress: taskData.progress || "In behandeling...",
          percent: taskData.progress_percent || 0,
        };

        if (taskData.status === "done" || taskData.status === "failed") {
          clearInterval(poll);
          generatingNames = new Set(
            [...generatingNames].filter((n) => n !== name),
          );
          delete taskDetails[name];

          if (taskData.status === "failed") {
            toasts.add(
              `Generatie mislukt: ${taskData.error || "Onbekende fout"}`,
              "error",
            );
            return;
          }

          const data = await fetch("/api/candidates/").then((r) => r.json());
          candidates = data;
          delete detailCache[name];

          // Herlaad detail als het panel open staat
          if (expandedName === name) {
            try {
              const res = await fetch(
                `/api/candidates/${encodeURIComponent(name)}`,
              );
              if (res.ok) {
                detailCache[name] = await res.json();
              }
            } catch {}
          }
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
      delete taskDetails[name];
    }
  }

  function renderValue(val: any): string {
    if (val === null || val === undefined) return "—";
    if (Array.isArray(val)) return val.join(", ");
    if (typeof val === "object") return JSON.stringify(val, null, 2);
    return String(val);
  }

  const SKIP_KEYS = new Set(["_waarschuwingen", "last_generated"]);

  // Labels voor Big Five en Learning Agility dimensies
  const GEDRAG_LABELS: Record<string, string> = {
    openheid: "Openheid",
    conscientieusheid: "Conscientieusheid",
    extraversie: "Extraversie",
    vriendelijkheid: "Vriendelijkheid",
    neuroticisme: "Neuroticisme",
  };
  const LEERVERMOGEN_LABELS: Record<string, string> = {
    mental_agility: "Mental Agility",
    people_agility: "People Agility",
    change_agility: "Change Agility",
    results_agility: "Results Agility",
    self_awareness: "Self-Awareness",
  };

  // Pijler-keys die apart gerenderd worden
  const PILLAR_KEYS = new Set(["gedrag", "leervermogen"]);
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
          <option value="score-desc">Dossiercompleetheid (Hoog-Laag)</option>
          <option value="score-asc">Dossiercompleetheid (Laag-Hoog)</option>
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
      <div class="card stagger-item" style="animation-delay: {i * 50}ms;">
        <div
          style="display: flex; justify-content: space-between; align-items: center;"
        >
          <div
            class="card-header-clickable"
            onclick={() => toggleDetail(candidate.naam)}
            role="button"
            tabindex="0"
            onkeydown={(e) => e.key === "Enter" && toggleDetail(candidate.naam)}
          >
            <h2
              style="margin: 0; font-size: 1.2rem; display: flex; align-items: center; gap: 10px; transition: color 0.3s;"
            >
              <span
                class="material-icons"
                style="font-size: 1rem; color: var(--text-secondary); transition: transform 0.3s; transform: rotate({expandedName ===
                candidate.naam
                  ? '90'
                  : '0'}deg);">chevron_right</span
              >
              {candidate.naam}
              {#if candidate.has_profile}
                <span class="badge badge-success">✓ Profiel</span>
              {:else}
                <span class="badge badge-warning">⚠ Ontbreekt</span>
              {/if}
            </h2>
            <div
              style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.5rem; margin-left: 1.6rem;"
            >
              {candidate.doc_count} documenten
              {#if candidate.has_profile}
                | Dossiercompleetheid: {#if candidate.profile_score != null}<strong
                    style="color: {candidate.profile_score > 75
                      ? 'var(--neon-green)'
                      : candidate.profile_score > 40
                        ? '#FFAB00'
                        : 'var(--neon-pink)'}"
                    >{candidate.profile_score}%</strong
                  >{:else}<span
                    style="color: var(--text-secondary); font-style: italic;"
                    >Onbekend</span
                  >{/if}
              {/if}
              {#if candidate.profile_data?.last_generated}
                | <span style="opacity: 0.8;"
                  >{new Date(
                    candidate.profile_data.last_generated,
                  ).toLocaleDateString("nl-NL", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}</span
                >
              {/if}
              <span
                style="margin-left: 0.5rem; font-size: 0.7rem; color: var(--text-secondary); opacity: 0.6;"
              >
                — klik om {expandedName === candidate.naam
                  ? "te sluiten"
                  : "details te bekijken"}
              </span>
            </div>
            {#if generatingNames.has(candidate.naam) && taskDetails[candidate.naam]}
              <div style="margin-top: 1rem; margin-left: 1.6rem;">
                <div
                  style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;"
                >
                  <span
                    style="font-size: 0.75rem; color: var(--neon-cyan); font-weight: 500;"
                  >
                    {taskDetails[candidate.naam].progress}
                  </span>
                  <span
                    style="font-size: 0.75rem; color: var(--neon-cyan); font-weight: 600;"
                  >
                    {taskDetails[candidate.naam].percent}%
                  </span>
                </div>
                <div class="progress-bar" style="height: 4px;">
                  <div
                    class="progress-bar-fill"
                    style="width: {taskDetails[candidate.naam].percent}%;"
                  ></div>
                </div>
              </div>
            {/if}
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

        <!-- Expandable detail panel -->
        <div class="detail-panel" class:open={expandedName === candidate.naam}>
          {#if expandedName === candidate.naam}
            {@const detail = detailCache[candidate.naam]}
            {#if !detail}
              <div style="text-align: center; padding: 2rem;">
                <span
                  class="material-icons spin"
                  style="font-size: 1.5rem; color: var(--neon-cyan);"
                  >autorenew</span
                >
                <p style="margin-top: 0.5rem; font-size: 0.85rem;">
                  Details laden...
                </p>
              </div>
            {:else if !detail.profile_data}
              <div
                style="text-align: center; padding: 1.5rem; color: var(--text-secondary);"
              >
                <span
                  class="material-icons"
                  style="font-size: 2rem; opacity: 0.3;">description</span
                >
                <p style="margin-top: 0.5rem; font-size: 0.85rem;">
                  Nog geen profiel gegenereerd. Klik op "Genereer" om een
                  profiel aan te maken.
                </p>
              </div>
            {:else}
              <div
                style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-bottom: 1rem;"
              >
                {#if editingName === candidate.naam}
                  <button
                    class="btn-edit"
                    class:saving={isSaving}
                    onclick={() => saveProfile(candidate.naam)}
                  >
                    {#if isSaving}
                      <span
                        class="material-icons spin"
                        style="font-size: 0.9rem;">autorenew</span
                      > Opslaan...
                    {:else}
                      <span class="material-icons" style="font-size: 0.9rem;"
                        >save</span
                      > Opslaan
                    {/if}
                  </button>
                  <button class="btn-edit" onclick={cancelEditing}>
                    <span class="material-icons" style="font-size: 0.9rem;"
                      >close</span
                    > Annuleren
                  </button>
                {:else}
                  <button
                    class="btn-edit"
                    onclick={() => startEditing(candidate.naam)}
                  >
                    <span class="material-icons" style="font-size: 0.9rem;"
                      >edit</span
                    > Bewerken
                  </button>
                {/if}
              </div>

              {#if editingName === candidate.naam}
                <textarea class="profile-editor" bind:value={editJson}
                ></textarea>
              {:else}
                {#if detail.docs && detail.docs.length > 0}
                  <div class="detail-section-title">
                    <span class="material-icons">folder</span> Documenten
                  </div>
                  <div
                    style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;"
                  >
                    {#each detail.docs as doc}
                      <span class="doc-chip">
                        <span class="material-icons" style="font-size: 0.8rem;"
                          >insert_drive_file</span
                        >
                        {doc}
                      </span>
                    {/each}
                  </div>
                {/if}

                <div class="detail-section-title">
                  <span class="material-icons">person</span> Profielgegevens
                </div>

                <!-- Gedrag (Big Five) -->
                {#if detail.profile_data.gedrag}
                  <div class="detail-section-title" style="margin-top: 1rem; font-size: 0.85rem;">
                    <span class="material-icons" style="font-size: 1rem;">psychology</span> Gedrag (Big Five)
                  </div>
                  <table class="profile-table">
                    <tbody>
                      {#each Object.entries(detail.profile_data.gedrag) as [dim, val]}
                        <tr>
                          <th style="width: 160px;">{GEDRAG_LABELS[dim] || dim}</th>
                          <td>
                            {#if typeof val === "object" && val !== null}
                              <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div style="display: flex; gap: 2px; flex-shrink: 0;">
                                  {#each Array(5) as _, i}
                                    <span style="width: 14px; height: 14px; border-radius: 3px; display: inline-block; background: {i < (val.score || 0) ? 'var(--neon-cyan)' : 'var(--bg-secondary)'}; opacity: {i < (val.score || 0) ? 1 : 0.3};"></span>
                                  {/each}
                                </div>
                                <span style="font-size: 0.8rem;">{val.toelichting || '—'}</span>
                              </div>
                            {:else}
                              {renderValue(val)}
                            {/if}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                {/if}

                <!-- Leervermogen (Learning Agility) -->
                {#if detail.profile_data.leervermogen}
                  <div class="detail-section-title" style="margin-top: 1rem; font-size: 0.85rem;">
                    <span class="material-icons" style="font-size: 1rem;">school</span> Leervermogen (Learning Agility)
                  </div>
                  <table class="profile-table">
                    <tbody>
                      {#each Object.entries(detail.profile_data.leervermogen) as [dim, val]}
                        <tr>
                          <th style="width: 160px;">{LEERVERMOGEN_LABELS[dim] || dim}</th>
                          <td>
                            {#if typeof val === "object" && val !== null}
                              <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div style="display: flex; gap: 2px; flex-shrink: 0;">
                                  {#each Array(5) as _, i}
                                    <span style="width: 14px; height: 14px; border-radius: 3px; display: inline-block; background: {i < (val.score || 0) ? 'var(--neon-green)' : 'var(--bg-secondary)'}; opacity: {i < (val.score || 0) ? 1 : 0.3};"></span>
                                  {/each}
                                </div>
                                <span style="font-size: 0.8rem;">{val.toelichting || '—'}</span>
                              </div>
                            {:else}
                              {renderValue(val)}
                            {/if}
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                {/if}

                <!-- Overige velden -->
                <table class="profile-table" style="margin-top: 0.5rem;">
                  <tbody>
                    {#each Object.entries(detail.profile_data) as [key, value]}
                      {#if !SKIP_KEYS.has(key) && !PILLAR_KEYS.has(key)}
                        <tr>
                          <th>{key.replace(/_/g, " ")}</th>
                          <td>
                            {#if Array.isArray(value)}
                              {#if value.length === 0}
                                <span
                                  style="color: var(--text-secondary); font-style: italic;"
                                  >—</span
                                >
                              {:else if typeof value[0] === "object"}
                                <pre
                                  style="margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; white-space: pre-wrap;">{JSON.stringify(
                                    value,
                                    null,
                                    2,
                                  )}</pre>
                              {:else}
                                {value.join(", ")}
                              {/if}
                            {:else if typeof value === "object" && value !== null}
                              <pre
                                style="margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; white-space: pre-wrap;">{JSON.stringify(
                                  value,
                                  null,
                                  2,
                                )}</pre>
                            {:else}
                              {renderValue(value)}
                            {/if}
                          </td>
                        </tr>
                      {/if}
                    {/each}
                  </tbody>
                </table>

                {#if (detail.vervolgvragen?.length > 0 || detail.cultuur_vragen?.length > 0 || detail.stellingen?.length > 0) && editingName !== candidate.naam}
                  <DossierCompleetheidEnrichment
                    questions={detail.vervolgvragen}
                    cultuurQuestions={detail.cultuur_vragen}
                    stellingen={detail.stellingen}
                    name={candidate.naam}
                    docType="candidates"
                    onSuccess={(result) => {
                      detailCache[candidate.naam] = {
                        ...detail,
                        profile_data: result.profiel,
                        profile_score: result.nieuwe_score,
                        vervolgvragen: result.vervolgvragen,
                        cultuur_vragen: result.cultuur_vragen,
                        stellingen: result.stellingen,
                      };
                      // Update the main list as well
                      const idx = candidates.findIndex(
                        (c: any) => c.naam === candidate.naam,
                      );
                      if (idx !== -1) {
                        candidates[idx].profile_score = result.nieuwe_score;
                        candidates[idx].has_profile = true;
                      }
                    }}
                  />
                {/if}
              {/if}
            {/if}
          {/if}
        </div>
      </div>
    {/each}
  {/if}
</div>
