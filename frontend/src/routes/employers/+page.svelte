<script lang="ts">
  import type { PageData } from "./$types";
  import { toasts } from "$lib/toast";
  import DossierCompleetheidEnrichment from "$lib/components/DossierCompleetheidEnrichment.svelte";

  let { data } = $props<{ data: PageData }>();

  let employers = $state(data.employers || []);
  let newEmployerName = $state("");
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
        const res = await fetch(`/api/employers/${encodeURIComponent(name)}`);
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
        `/api/employers/${encodeURIComponent(name)}/profile`,
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
        await refreshEmployers();
      } else {
        toasts.add("Fout bij opslaan profiel", "error");
      }
    } catch (e) {
      toasts.add("Ongeldige JSON — controleer de syntax", "error");
    } finally {
      isSaving = false;
    }
  }

  async function createEmployer() {
    if (!newEmployerName.trim()) return;
    isCreating = true;
    try {
      const res = await fetch(
        `/api/employers/?name=${encodeURIComponent(newEmployerName)}`,
        { method: "POST" },
      );
      if (res.ok) {
        toasts.add(
          `Werkgeversvraag "${newEmployerName}" aangemaakt`,
          "success",
        );
        newEmployerName = "";
        await refreshEmployers();
      } else {
        toasts.add("Fout bij aanmaken werkgeversvraag", "error");
      }
    } finally {
      isCreating = false;
    }
  }

  async function deleteEmployer(name: string) {
    const res = await fetch(`/api/employers/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (res.ok) {
      toasts.add(`"${name}" verwijderd`, "success");
      confirmingDelete = null;
      if (expandedName === name) expandedName = null;
      delete detailCache[name];
      await refreshEmployers();
    } else {
      toasts.add("Fout bij verwijderen", "error");
    }
  }

  async function refreshEmployers() {
    const res = await fetch("/api/employers/");
    employers = await res.json();
  }

  async function generateProfile(name: string) {
    generatingNames = new Set([...generatingNames, name]);
    try {
      const res = await fetch(
        `/api/employers/${encodeURIComponent(name)}/generate-profile`,
        { method: "POST" },
      );
      if (!res.ok) {
        toasts.add("Fout bij starten generatie", "error");
        return;
      }
      toasts.add(`Profiel generatie gestart voor "${name}"`, "info");
      const poll = setInterval(async () => {
        const data = await fetch("/api/employers/").then((r) => r.json());
        const updated = data.find((e: any) => e.naam === name);
        if (updated?.has_profile) {
          clearInterval(poll);
          employers = data;
          generatingNames = new Set(
            [...generatingNames].filter((n) => n !== name),
          );
          delete detailCache[name];
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

  function renderValue(val: any): string {
    if (val === null || val === undefined) return "—";
    if (Array.isArray(val)) return val.join(", ");
    if (typeof val === "object") return JSON.stringify(val, null, 2);
    return String(val);
  }

  const SKIP_KEYS = new Set(["_waarschuwingen"]);
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
          <option value="score-desc">Dossiercompleetheid (Hoog-Laag)</option>
          <option value="score-asc">Dossiercompleetheid (Laag-Hoog)</option>
        </select>
      </div>
    </div>
  {/if}

  {#if employers.length === 0}
    <div class="card empty-state">
      <span class="material-icons">business_center</span>
      <h3>Nog geen werkgeversvragen</h3>
      <p>Maak hierboven een nieuw dossier aan om te starten.</p>
    </div>
  {:else if filteredEmployers.length === 0}
    <div class="card empty-state">
      <span class="material-icons">search_off</span>
      <h3>Geen resultaten</h3>
      <p>Geen werkgeversvragen gevonden voor "{searchQuery}"</p>
    </div>
  {:else}
    {#each filteredEmployers as employer, i}
      <div class="card stagger-item" style="animation-delay: {i * 50}ms;">
        <div
          style="display: flex; justify-content: space-between; align-items: center;"
        >
          <div
            class="card-header-clickable"
            onclick={() => toggleDetail(employer.naam)}
            role="button"
            tabindex="0"
            onkeydown={(e) => e.key === "Enter" && toggleDetail(employer.naam)}
          >
            <h2
              style="margin: 0; font-size: 1.2rem; display: flex; align-items: center; gap: 10px; transition: color 0.3s;"
            >
              <span
                class="material-icons"
                style="font-size: 1rem; color: var(--text-secondary); transition: transform 0.3s; transform: rotate({expandedName ===
                employer.naam
                  ? '90'
                  : '0'}deg);">chevron_right</span
              >
              {employer.naam}
              {#if employer.has_profile}
                <span class="badge badge-success">✓ Profiel</span>
              {:else}
                <span class="badge badge-warning">⚠ Ontbreekt</span>
              {/if}
            </h2>
            <div
              style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.5rem; margin-left: 1.6rem;"
            >
              {employer.doc_count} documenten
              {#if employer.has_profile}
                | Dossiercompleetheid: <strong
                  style="color: {employer.profile_score > 75
                    ? 'var(--neon-green)'
                    : employer.profile_score > 40
                      ? '#FFAB00'
                      : 'var(--neon-pink)'}">{employer.profile_score}%</strong
                >
              {/if}
              <span
                style="margin-left: 0.5rem; font-size: 0.7rem; color: var(--text-secondary); opacity: 0.6;"
              >
                — klik om {expandedName === employer.naam
                  ? "te sluiten"
                  : "details te bekijken"}
              </span>
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            {#if confirmingDelete === employer.naam}
              <div class="confirm-bar">
                <span>Verwijderen?</span>
                <button
                  class="btn-confirm-yes"
                  onclick={() => deleteEmployer(employer.naam)}>Ja</button
                >
                <button
                  class="btn-confirm-no"
                  onclick={() => (confirmingDelete = null)}>Nee</button
                >
              </div>
            {:else}
              <button
                class="btn-primary"
                onclick={() => generateProfile(employer.naam)}
                disabled={generatingNames.has(employer.naam)}
              >
                {#if generatingNames.has(employer.naam)}
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
                onclick={() => (confirmingDelete = employer.naam)}
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
        <div class="detail-panel" class:open={expandedName === employer.naam}>
          {#if expandedName === employer.naam}
            {@const detail = detailCache[employer.naam]}
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
                {#if editingName === employer.naam}
                  <button
                    class="btn-edit"
                    class:saving={isSaving}
                    onclick={() => saveProfile(employer.naam)}
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
                    onclick={() => startEditing(employer.naam)}
                  >
                    <span class="material-icons" style="font-size: 0.9rem;"
                      >edit</span
                    > Bewerken
                  </button>
                {/if}
              </div>

              {#if editingName === employer.naam}
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
                  <span class="material-icons">business</span> Profielgegevens
                </div>
                <table class="profile-table">
                  <tbody>
                    {#each Object.entries(detail.profile_data) as [key, value]}
                      {#if !SKIP_KEYS.has(key)}
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

                {#if detail.vervolgvragen && detail.vervolgvragen.length > 0 && editingName !== employer.naam}
                  <DossierCompleetheidEnrichment
                    questions={detail.vervolgvragen}
                    name={employer.naam}
                    docType="employers"
                    onSuccess={(result) => {
                      detailCache[employer.naam] = {
                        ...detail,
                        profile_data: result.profiel,
                        profile_score: result.nieuwe_score,
                        vervolgvragen: result.vervolgvragen,
                      };
                      // Update the main list as well
                      const idx = employers.findIndex(
                        (e: any) => e.naam === employer.naam,
                      );
                      if (idx !== -1) {
                        employers[idx].profile_score = result.nieuwe_score;
                        employers[idx].has_profile = true;
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
