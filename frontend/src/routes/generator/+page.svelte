<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { toasts } from "$lib/toast";
  import PIIGenerationWizard from "$lib/components/PIIGenerationWizard.svelte";
  import { fade, slide } from "svelte/transition";

  let dossiers: any[] = $state([]);
  let isLoading = $state(false);
  let selectedType = $state(page.url.searchParams.get("type") || "candidates");
  let selectedName = $state(page.url.searchParams.get("name") || "");
  let showWizard = $state(false);
  let searchQuery = $state("");

  let filteredDossiers = $derived(
    searchQuery.trim()
      ? dossiers.filter((d: any) => {
          const q = searchQuery.toLowerCase();
          if (d.naam.toLowerCase().includes(q)) return true;
          if (d.tags?.some((t: string) => t.toLowerCase().includes(q))) return true;
          return false;
        })
      : dossiers
  );

  onMount(async () => {
    await loadDossiers();
    if (selectedName) {
      showWizard = true;
    }
  });

  async function loadDossiers() {
    isLoading = true;
    try {
      const res = await fetch(`/api/${selectedType}`);
      if (res.ok) {
        dossiers = await res.json();
      }
    } catch (e) {
      toasts.add("Kon dossiers niet laden.", "error");
    } finally {
      isLoading = false;
    }
  }

  $effect(() => {
    if (selectedType) {
      loadDossiers();
    }
  });

  function startGeneration(name: string) {
    selectedName = name;
    showWizard = true;
  }

  function onWizardSuccess() {
    toasts.add("Generatie succesvol gestart!", "success");
    showWizard = false;
  }
</script>

<div class="generator-container" in:fade>
  <div class="page-hero">
    <h1 style="color: var(--neon-green);">
      <span class="material-icons" style="font-size: 2.2rem; margin-right: 15px; color: var(--neon-green);">auto_awesome</span>
      Profiel Generator
    </h1>
    <p>Selecteer een dossier of maak een nieuwe om een PII-veilig profiel te genereren.</p>
  </div>

  <div class="selection-grid">
    <div class="type-selector">
      <button 
        class="type-btn" 
        class:active={selectedType === 'candidates'} 
        onclick={() => { selectedType = 'candidates'; selectedName = ''; searchQuery = ''; }}
      >
        <span class="material-icons">group</span>
        Kandidaten
      </button>
      <button 
        class="type-btn" 
        class:active={selectedType === 'employers'} 
        onclick={() => { selectedType = 'employers'; selectedName = ''; searchQuery = ''; }}
      >
        <span class="material-icons">business</span>
        Werkgeversvragen
      </button>
    </div>

    <div class="dossier-list-container">
      <div class="list-header">
        <h2>Dossiers ({filteredDossiers.length}{searchQuery ? ` / ${dossiers.length}` : ''})</h2>
        <button class="btn-new" onclick={() => { selectedName = ''; showWizard = true; }}>
          <span class="material-icons">add</span> Nieuw Dossier
        </button>
      </div>

      <div class="search-bar">
        <span class="material-icons search-icon">search</span>
        <input
          type="text"
          class="search-input"
          placeholder="Zoek op naam..."
          bind:value={searchQuery}
        />
        {#if searchQuery}
          <button class="search-clear" onclick={() => searchQuery = ''}>
            <span class="material-icons">close</span>
          </button>
        {/if}
      </div>

      {#if isLoading}
        <div class="loading-state">
          <span class="material-icons spin">autorenew</span>
          <p>Dossiers laden...</p>
        </div>
      {:else if filteredDossiers.length === 0}
        <div class="empty-state">
          <span class="material-icons">folder_off</span>
          <p>{searchQuery ? 'Geen dossiers gevonden voor deze zoekopdracht.' : 'Geen dossiers gevonden voor dit type.'}</p>
        </div>
      {:else}
        <div class="list-grid">
          {#each filteredDossiers as dossier}
            <div 
              class="dossier-card" 
              class:selected={selectedName === dossier.naam}
              onclick={() => startGeneration(dossier.naam)}
              role="presentation"
            >
              <div class="card-info">
                <span class="material-icons folder-icon">folder</span>
                <div class="card-text">
                  <span class="dossier-name">{dossier.naam}</span>
                  <span class="dossier-meta">{dossier.doc_count} documenten | {dossier.has_profile ? 'Heeft profiel' : 'Geen profiel'}</span>
                  {#if dossier.tags?.length}
                    <div class="card-tags">
                      {#each dossier.tags as tag}
                        <span class="card-tag">{tag}</span>
                      {/each}
                    </div>
                  {/if}
                </div>
              </div>
              <span class="material-icons arrow">chevron_right</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>

{#if showWizard}
  <PIIGenerationWizard 
    docType={selectedType as "candidates" | "employers"} 
    name={selectedName}
    onClose={() => showWizard = false}
    onSuccess={onWizardSuccess}
  />
{/if}

<style>
  .generator-container {
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .selection-grid {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .type-selector {
    display: flex;
    gap: 1rem;
    background: rgba(255, 255, 255, 0.03);
    padding: 0.5rem;
    border-radius: 12px;
    border: 1px solid var(--glass-border);
    width: fit-content;
  }

  .type-btn {
    padding: 0.6rem 1.2rem;
    border: none;
    background: transparent;
    color: var(--text-secondary);
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  }

  .type-btn.active {
    background: var(--neon-green);
    color: #0c111d;
    box-shadow: 0 4px 15px rgba(0, 230, 118, 0.2);
  }

  .dossier-list-container {
    background: var(--surface-1);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.5rem;
  }

  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .list-header h2 {
    margin: 0;
    font-size: 1.1rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .btn-new {
    background: rgba(0, 230, 118, 0.1);
    border: 1px solid var(--neon-green);
    color: var(--neon-green);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 5px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.2s;
  }

  .btn-new:hover {
    background: var(--neon-green);
    color: #0c111d;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid var(--glass-border);
    border-radius: 10px;
    padding: 0.5rem 0.8rem;
    margin-bottom: 1.5rem;
    transition: border-color 0.2s;
  }

  .search-bar:focus-within {
    border-color: var(--neon-green);
  }

  .search-icon {
    color: var(--text-secondary);
    font-size: 1.2rem;
  }

  .search-input {
    flex: 1;
    background: none;
    border: none;
    outline: none;
    color: #fff;
    font-size: 0.9rem;
  }

  .search-input::placeholder {
    color: var(--text-secondary);
    opacity: 0.6;
  }

  .search-clear {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
    transition: color 0.2s;
  }

  .search-clear:hover {
    color: var(--neon-pink);
  }

  .list-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }

  .dossier-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 1.2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: all 0.2s;
  }

  .dossier-card:hover {
    background: rgba(255, 255, 255, 0.06);
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .dossier-card.selected {
    border-color: var(--neon-green);
    background: rgba(0, 230, 118, 0.05);
  }

  .card-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .folder-icon {
    font-size: 2rem;
    color: var(--text-secondary);
    opacity: 0.5;
  }

  .card-text {
    display: flex;
    flex-direction: column;
  }

  .dossier-name {
    font-weight: 600;
    color: #fff;
  }

  .dossier-meta {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
  }

  .card-tag {
    font-size: 0.65rem;
    padding: 1px 6px;
    background: rgba(0, 229, 255, 0.08);
    border: 1px solid rgba(0, 229, 255, 0.15);
    border-radius: 4px;
    color: var(--neon-cyan);
  }

  .arrow {
    color: var(--text-secondary);
    opacity: 0.3;
  }

  .loading-state, .empty-state {
    padding: 3rem;
    text-align: center;
    color: var(--text-secondary);
  }
</style>
