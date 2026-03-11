<script lang="ts">
  import { toasts } from "$lib/toast";
  import { fade, scale, slide } from "svelte/transition";
  import { onMount } from "svelte";

  let {
    docType,
    name = "",
    onClose,
    onSuccess,
  } = $props<{
    docType: "candidates" | "employers";
    name?: string;
    onClose: () => void;
    onSuccess: (name: string) => void;
  }>();

  let step = $state(1);
  let rawText = $state("");
  let scrubbedText = $state("");
  let piiReport: Record<string, number> = $state({});
  let isScrubbing = $state(false);
  let isGenerating = $state(false);
  let provider = $state("local");
  let customName = $state(name);
  let hasExistingProfile = $state(false);
  let generationMode = $state("fresh"); // "fresh" or "enrich"
  let generationResult: any = $state(null);
  let generationError = $state("");
  let taskProgress = $state("");
  let taskPercent = $state(0);

  let availableDocs: string[] = $state([]);
  let selectedDocs: string[] = $state([]);
  let isLoadingDocs = $state(false);
  let dossierUuid = $state("");

  $effect(() => {
    if (name) customName = name;
  });

  onMount(async () => {
    if (name) {
      await fetchDossierData();
    }
  });

  async function fetchDossierData() {
    isLoadingDocs = true;
    try {
      const res = await fetch(`/api/${docType}/${encodeURIComponent(name)}`);
      if (res.ok) {
        const data = await res.json();
        availableDocs = data.docs || [];
        hasExistingProfile = !!data.profiel_dict;
        if (hasExistingProfile) {
          generationMode = "enrich";
        }
        if (data.id) {
          dossierUuid = data.id;
        }
        // Auto-select all by default if any exist
        selectedDocs = [...availableDocs];
      }
    } catch (e) {
      toasts.add("Kon dossiergegevens niet ophalen.", "error");
    } finally {
      isLoadingDocs = false;
    }
  }

  async function startScrubbing() {
    isScrubbing = true;
    try {
      let textToScrub = rawText;

      // If we have selected documents, extract their text first
      if (selectedDocs.length > 0 && name) {
        const extRes = await fetch(`/api/${docType}/${encodeURIComponent(name)}/extract-text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filenames: selectedDocs }),
        });
        if (extRes.ok) {
          const extData = await extRes.json();
          textToScrub = extData.tekst;
        } else {
          throw new Error("Extractie mislukt");
        }
      }

      if (!textToScrub.trim()) {
        toasts.add("Geen tekst gevonden om te scrubben.", "warning");
        return;
      }

      const scrubBody: Record<string, string> = { tekst: textToScrub };
      if (customName && dossierUuid) {
        scrubBody.naam = customName;
        scrubBody.uuid = dossierUuid;
      }
      const res = await fetch("/api/gdpr/scrub-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scrubBody),
      });
      const data = await res.json();
      scrubbedText = data.geschoonde_tekst;
      piiReport = data.rapport;
      
      toasts.add("Tekst gescrubd! Controleer het resultaat in Stap 2.", "success");
      step = 2;
    } catch (e) {
      toasts.add("Fout bij scrubben van tekst.", "error");
    } finally {
      isScrubbing = false;
    }
  }

  async function generateProfile() {
    if (!customName.trim()) {
      toasts.add("Voer een dossiernaam in.", "warning");
      return;
    }
    isGenerating = true;
    generationError = "";
    taskProgress = "Generatie starten...";
    taskPercent = 0;
    try {
      const endpoint = generationMode === "enrich"
        ? `/api/${docType}/${encodeURIComponent(customName)}/enrich-from-text`
        : `/api/${docType}/${encodeURIComponent(customName)}/generate-from-text`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tekst: scrubbedText,
          provider_type: provider,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const taskId = data.task_id;

        // Poll voor voortgang
        if (taskId) {
          await pollTask(taskId);
        } else {
          // Directe response (bijv. enrich endpoint)
          generationResult = data;
          step = 4;
          isGenerating = false;
        }
      } else {
        const err = await res.json();
        generationError = err.detail || "Fout bij verwerken.";
        toasts.add(generationError, "error");
        isGenerating = false;
      }
    } catch (e) {
      generationError = "Netwerkfout bij verwerken.";
      toasts.add(generationError, "error");
      isGenerating = false;
    }
  }

  async function pollTask(taskId: string) {
    const maxAttempts = 300; // 10 min bij 2s interval
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const res = await fetch(`/api/tasks/${taskId}`);
        if (!res.ok) continue;
        const task = await res.json();

        taskProgress = task.progress || "Bezig...";
        taskPercent = task.progress_percent || 0;

        if (task.status === "done") {
          // Haal het nieuwe profiel op
          const profileRes = await fetch(`/api/${docType}/${encodeURIComponent(customName)}`);
          if (profileRes.ok) {
            generationResult = await profileRes.json();
          }
          step = 4;
          isGenerating = false;
          return;
        } else if (task.status === "failed") {
          generationError = task.error || "Generatie mislukt.";
          toasts.add(generationError, "error");
          isGenerating = false;
          return;
        }
      } catch {
        // Netwerk fout, probeer opnieuw
      }
    }
    generationError = "Generatie duurde te lang.";
    toasts.add(generationError, "error");
    isGenerating = false;
  }

  function retryGeneration() {
    generationResult = null;
    generationError = "";
    step = 3;
  }

  function acceptResult() {
    onSuccess(customName);
    onClose();
  }

  function toggleDoc(doc: string) {
    if (selectedDocs.includes(doc)) {
      selectedDocs = selectedDocs.filter(d => d !== doc);
    } else {
      selectedDocs = [...selectedDocs, doc];
    }
  }
</script>

<div class="modal-backdrop" transition:fade onclick={onClose} role="presentation">
  <div class="modal-content" transition:scale onclick={(e) => e.stopPropagation()} role="presentation">
    <div class="modal-header">
      <div class="header-title">
        <span class="material-icons shield-icon">shield</span>
        <div class="title-text">
          <h2>PII-veilig Profiel Genereren</h2>
          <p class="subtitle">{name ? `Dossier: ${name}` : 'Nieuw Dossier'}</p>
        </div>
      </div>
      <button class="btn-close" onclick={onClose}>
        <span class="material-icons">close</span>
      </button>
    </div>

    <!-- Step Indicator -->
    <div class="step-indicator">
      {#each [1, 2, 3, 4] as s}
        <div class="step-item">
          <div class="step-dot" class:active={step >= s} class:current={step === s}>
            {#if step > s}
              <span class="material-icons" style="font-size: 1rem;">check</span>
            {:else}
              {s}
            {/if}
          </div>
          <span class="step-label" class:active={step >= s}>
            {s === 1 ? 'Scrubben' : s === 2 ? 'Controleren' : s === 3 ? 'Genereren' : 'Resultaat'}
          </span>
        </div>
        {#if s < 4}
          <div class="step-line" class:active={step > s}></div>
        {/if}
      {/each}
    </div>

    <div class="step-container">
      {#if step === 1}
        <div class="step-view" in:fade>
          <div class="step-header-compact">
            <span class="step-badge">STAP 1</span>
            <h3>PII Scrubbing</h3>
          </div>
          
          {#if name}
            <p class="step-instruction">Selecteer de documenten die je wilt gebruiken voor het profiel.</p>
            {#if isLoadingDocs}
              <div class="loading-state">
                <span class="material-icons spin">autorenew</span>
                <span>Documenten laden...</span>
              </div>
            {:else if availableDocs.length > 0}
              <div class="doc-list">
                {#each availableDocs as doc}
                  <div 
                    class="doc-item" 
                    class:selected={selectedDocs.includes(doc)}
                    onclick={() => toggleDoc(doc)}
                    role="presentation"
                  >
                    <span class="material-icons">{selectedDocs.includes(doc) ? 'check_box' : 'check_box_outline_blank'}</span>
                    <span class="doc-name">{doc}</span>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="empty-state">
                <span class="material-icons">folder_off</span>
                <p>Geen documenten gevonden in dit dossier.</p>
              </div>
            {/if}
            
            <div class="divider">
              <span>of</span>
            </div>
          {/if}

          <p class="step-instruction">Plak handmatig tekst (bijv. van een website of mail).</p>
          <textarea
            class="input-field wizard-textarea small"
            placeholder="Plak hier de tekst..."
            bind:value={rawText}
          ></textarea>
        </div>
      {:else if step === 2}
        <div class="step-view" in:fade>
          <div class="step-header-compact">
            <span class="step-badge">STAP 2</span>
            <h3>Controleren & Bewerken</h3>
          </div>
          <p class="step-instruction">De output van de PII scrubber staat hieronder. Bewerk waar nodig.</p>
          
          <div class="editor-container">
            <textarea
              class="input-field wizard-textarea"
              bind:value={scrubbedText}
              placeholder="Gescrubde tekst verschijnt hier..."
            ></textarea>
            
            {#if Object.keys(piiReport).length > 0}
              <div class="pii-sidebar" transition:slide>
                <div class="sidebar-header">
                  <span class="material-icons">visibility_off</span>
                  <span>Gemaskeerd ({Object.values(piiReport).reduce((a, b) => a + b, 0)})</span>
                </div>
                <div class="pii-tags">
                  {#each Object.entries(piiReport) as [categorie, aantal]}
                    <span class="pii-tag">{categorie}: {aantal}x</span>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        </div>
      {:else if step === 3}
        <div class="step-view" in:fade>
          <div class="step-header-compact">
            <span class="step-badge">STAP 3</span>
            <h3>Profiel Genereren</h3>
          </div>
          <p class="step-instruction">Kies je model en of je een nieuwe generatie wilt starten of het bestaande profiel wilt verrijken.</p>

          {#if hasExistingProfile}
            <div class="mode-selection">
              <button 
                class="mode-btn" 
                class:active={generationMode === 'enrich'} 
                onclick={() => generationMode = 'enrich'}
              >
                <span class="material-icons">merge_type</span>
                <div>
                  <span class="mode-title">Verrijken</span>
                  <p class="mode-desc">Voeg informatie toe aan bestaand profiel</p>
                </div>
              </button>
              <button 
                class="mode-btn" 
                class:active={generationMode === 'fresh'} 
                onclick={() => generationMode = 'fresh'}
              >
                <span class="material-icons">refresh</span>
                <div>
                  <span class="mode-title">Nieuwe Generatie</span>
                  <p class="mode-desc">Overschrijf het huidige profiel volledig</p>
                </div>
              </button>
            </div>
          {/if}

          <div class="input-group">
            <label class="input-label" for="wizard-name">Dossiernaam</label>
            <input
              id="wizard-name"
              type="text"
              class="input-field"
              bind:value={customName}
              placeholder="Bijv. Jan Jansen"
              disabled={hasExistingProfile && generationMode === 'enrich'}
            />
          </div>

          <div class="provider-selection">
            <div 
              class="provider-card" 
              class:active={provider === 'local'}
              onclick={() => provider = 'local'}
              role="presentation"
            >
              <div class="provider-info">
                <span class="material-icons">memory</span>
                <div class="provider-text">
                  <span class="provider-name">Lokaal (Ollama)</span>
                  <span class="provider-desc">100% Privé, iets trager</span>
                </div>
              </div>
              <div class="radio-circle"></div>
            </div>

            <div 
              class="provider-card" 
              class:active={provider === 'api'}
              onclick={() => provider = 'api'}
              role="presentation"
            >
              <div class="provider-info">
                <span class="material-icons">bolt</span>
                <div class="provider-text">
                  <span class="provider-name">Claude 3.7 Sonnet</span>
                  <span class="provider-desc">Extreem snel & slim (via API)</span>
                </div>
              </div>
              <div class="radio-circle"></div>
            </div>
          </div>

          {#if isGenerating}
            <div class="generation-progress" style="margin-top: 1.5rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 0.8rem; color: var(--neon-cyan); font-weight: 500;">{taskProgress}</span>
                <span style="font-size: 0.8rem; color: var(--neon-cyan); font-weight: 600;">{taskPercent}%</span>
              </div>
              <div class="progress-bar" style="height: 4px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden;">
                <div style="height: 100%; width: {taskPercent}%; background: var(--neon-cyan); border-radius: 4px; transition: width 0.5s;"></div>
              </div>
            </div>
          {/if}

          {#if generationError}
            <div style="margin-top: 1rem; padding: 1rem; background: rgba(255, 51, 102, 0.05); border: 1px solid rgba(255, 51, 102, 0.2); border-radius: 10px; color: var(--neon-pink); font-size: 0.85rem;">
              {generationError}
            </div>
          {/if}
        </div>
      {:else if step === 4}
        <div class="step-view" in:fade>
          <div class="step-header-compact">
            <span class="step-badge">STAP 4</span>
            <h3>Resultaat</h3>
          </div>

          {#if generationResult?.profile_data}
            <p class="step-instruction">Het profiel is succesvol gegenereerd. Bekijk het resultaat hieronder.</p>

            {#if generationResult.profile_data.dossier_compleetheid != null}
              <div style="margin-bottom: 1rem; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 0.85rem; color: var(--text-secondary);">Dossiercompleetheid:</span>
                <strong style="color: {generationResult.profile_data.dossier_compleetheid > 75 ? 'var(--neon-green)' : generationResult.profile_data.dossier_compleetheid > 40 ? '#FFAB00' : 'var(--neon-pink)'}; font-size: 1.2rem;">
                  {generationResult.profile_data.dossier_compleetheid}%
                </strong>
              </div>
            {/if}

            <div class="result-profile" style="max-height: 350px; overflow-y: auto; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 1rem;">
              <table class="profile-table" style="width: 100%;">
                <tbody>
                  {#each Object.entries(generationResult.profile_data) as [key, value]}
                    {#if key !== '_waarschuwingen' && key !== 'last_generated'}
                      <tr>
                        <th style="font-size: 0.8rem; padding: 6px 10px; color: var(--neon-cyan); white-space: nowrap; vertical-align: top;">{key.replace(/_/g, ' ')}</th>
                        <td style="font-size: 0.8rem; padding: 6px 10px; color: var(--text-primary);">
                          {#if Array.isArray(value)}
                            {value.length > 0 ? value.join(', ') : '—'}
                          {:else if typeof value === 'object' && value !== null}
                            <pre style="margin: 0; font-size: 0.75rem; white-space: pre-wrap;">{JSON.stringify(value, null, 2)}</pre>
                          {:else}
                            {value ?? '—'}
                          {/if}
                        </td>
                      </tr>
                    {/if}
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <p class="step-instruction">Het profiel is gegenereerd maar er zijn geen details beschikbaar om te tonen.</p>
          {/if}
        </div>
      {/if}
    </div>

    <div class="modal-footer">
      <div class="footer-left">
        {#if step > 1 && step < 4 && !isGenerating}
          <button class="btn-ghost" onclick={() => step--}>
            <span class="material-icons">arrow_back</span>
            Vorige
          </button>
        {/if}
      </div>
      <div class="footer-right">
        {#if step === 4}
          <button class="btn-secondary" onclick={retryGeneration}>
            <span class="material-icons" style="font-size: 1rem;">refresh</span>
            Opnieuw
          </button>
          <button class="btn-generate" onclick={acceptResult}>
            <span class="material-icons">check</span>
            Accepteren
          </button>
        {:else}
          <button class="btn-secondary" onclick={onClose}>Annuleren</button>

          {#if step === 1}
            <button class="btn-primary" onclick={startScrubbing} disabled={isScrubbing || (!rawText.trim() && selectedDocs.length === 0)}>
              {#if isScrubbing}
                <span class="material-icons spin">autorenew</span>
                Scrubben...
              {:else}
                Scrubben & Volgende
                <span class="material-icons">arrow_forward</span>
              {/if}
            </button>
          {:else if step === 2}
            <button class="btn-primary" onclick={() => step = 3} disabled={!scrubbedText.trim()}>
              Bevestigen
              <span class="material-icons">arrow_forward</span>
            </button>
          {:else if step === 3}
            <button class="btn-generate" onclick={generateProfile} disabled={isGenerating}>
              {#if isGenerating}
                <span class="material-icons spin">autorenew</span>
                Bezig...
              {:else}
                <span class="material-icons">auto_awesome</span>
                {generationMode === 'enrich' ? 'Profiel Verrijken' : 'Genereer Profiel'}
              {/if}
            </button>
          {/if}
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(4, 7, 12, 0.85);
    backdrop-filter: blur(12px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: linear-gradient(135deg, rgba(16, 21, 33, 0.95) 0%, rgba(10, 14, 24, 0.98) 100%);
    border: 1px solid rgba(0, 229, 255, 0.2);
    border-radius: 20px;
    width: 95%;
    max-width: 700px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 30px rgba(0, 229, 255, 0.1);
    position: relative;
    overflow: hidden;
  }

  .modal-header {
    padding: 1.5rem 2rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 15px;
  }

  .shield-icon {
    font-size: 2.2rem;
    color: var(--neon-cyan);
    filter: drop-shadow(0 0 10px rgba(0, 229, 255, 0.4));
  }

  .title-text h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: #fff;
  }

  .subtitle {
    margin: 2px 0 0 0;
    font-size: 0.8rem;
    color: var(--text-secondary);
  }

  .btn-close {
    background: rgba(255, 255, 255, 0.05);
    border: none;
    color: var(--text-secondary);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-close:hover {
    background: rgba(255, 51, 102, 0.1);
    color: var(--neon-pink);
  }

  .step-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem 2rem;
    background: rgba(0, 0, 0, 0.2);
  }

  .step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    position: relative;
    z-index: 1;
  }

  .step-dot {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.03);
    border: 2px solid rgba(255, 255, 255, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-secondary);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }

  .step-dot.active {
    border-color: var(--neon-cyan);
    color: var(--neon-cyan);
  }

  .step-dot.current {
    background: var(--neon-cyan);
    color: #0c111d;
    border-color: var(--neon-cyan);
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
    transform: scale(1.1);
  }

  .step-label {
    font-size: 0.7rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    transition: color 0.3s;
  }

  .step-label.active {
    color: var(--neon-cyan);
  }

  .step-line {
    width: 60px;
    height: 2px;
    background: rgba(255, 255, 255, 0.05);
    margin: -20px 10px 0 10px;
    transition: background 0.3s;
  }

  .step-line.active {
    background: var(--neon-cyan);
  }

  .step-container {
    padding: 0 2rem 1.5rem 2rem;
    flex: 1;
    overflow-y: auto;
  }

  .step-header-compact {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1rem;
    margin-top: 0.5rem;
  }

  .step-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    background: rgba(0, 229, 255, 0.1);
    color: var(--neon-cyan);
    border-radius: 4px;
    letter-spacing: 0.05em;
  }

  .step-header-compact h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #fff;
  }

  .step-instruction {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
  }

  .doc-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 1.5rem;
  }

  .doc-item {
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .doc-item:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .doc-item.selected {
    background: rgba(0, 229, 255, 0.05);
    border-color: var(--neon-cyan);
    color: #fff;
  }

  .doc-item.selected .material-icons {
    color: var(--neon-cyan);
  }

  .divider {
    display: flex;
    align-items: center;
    gap: 15px;
    margin: 1.5rem 0;
  }

  .divider::before, .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255, 255, 255, 0.05);
  }

  .divider span {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-style: italic;
  }

  .wizard-textarea {
    width: 100%;
    min-height: 250px;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 1rem;
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    line-height: 1.6;
    resize: vertical;
    outline: none;
    transition: border-color 0.2s;
  }

  .wizard-textarea:focus {
    border-color: var(--neon-cyan);
  }

  .wizard-textarea.small {
    min-height: 120px;
  }

  .editor-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
  }

  .pii-sidebar {
    background: rgba(0, 229, 255, 0.03);
    border: 1px solid rgba(0, 229, 255, 0.1);
    border-radius: 10px;
    padding: 12px;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--neon-cyan);
    margin-bottom: 10px;
  }

  .pii-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .pii-tag {
    font-size: 0.7rem;
    padding: 2px 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    color: var(--text-secondary);
  }

  .mode-selection {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 1.5rem;
  }

  .mode-btn {
    padding: 1rem;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    color: var(--text-secondary);
  }

  .mode-btn.active {
    background: rgba(0, 229, 255, 0.05);
    border-color: var(--neon-cyan);
    color: #fff;
  }

  .mode-btn.active .material-icons {
    color: var(--neon-cyan);
  }

  .mode-title {
    display: block;
    font-weight: 600;
    font-size: 0.9rem;
  }

  .mode-desc {
    margin: 0;
    font-size: 0.7rem;
    opacity: 0.7;
  }

  .provider-selection {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 1rem;
  }

  .provider-card {
    padding: 1.2rem;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .provider-card:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.1);
    transform: translateY(-2px);
  }

  .provider-card.active {
    background: rgba(0, 229, 255, 0.03);
    border-color: var(--neon-cyan);
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.1);
  }

  .provider-info {
    display: flex;
    align-items: center;
    gap: 15px;
  }

  .provider-info .material-icons {
    font-size: 1.8rem;
    color: var(--text-secondary);
    transition: color 0.2s;
  }

  .provider-card.active .material-icons {
    color: var(--neon-cyan);
    filter: drop-shadow(0 0 5px rgba(0, 229, 255, 0.3));
  }

  .provider-text {
    display: flex;
    flex-direction: column;
  }

  .provider-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: #fff;
  }

  .provider-desc {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .radio-circle {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.1);
    position: relative;
    transition: all 0.2s;
  }

  .provider-card.active .radio-circle {
    border-color: var(--neon-cyan);
  }

  .provider-card.active .radio-circle::after {
    content: '';
    position: absolute;
    top: 4px; left: 4px; right: 4px; bottom: 4px;
    background: var(--neon-cyan);
    border-radius: 50%;
    box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
  }

  .modal-footer {
    padding: 1.5rem 2rem;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(0, 0, 0, 0.1);
  }

  .footer-right {
    display: flex;
    gap: 10px;
  }

  .btn-ghost {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-size: 0.9rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 5px;
    cursor: pointer;
    transition: color 0.2s;
  }

  .btn-ghost:hover {
    color: var(--neon-cyan);
  }

  .btn-primary {
    padding: 0.6rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }

  .btn-generate {
    background: var(--neon-cyan);
    color: #0c111d;
    padding: 0.6rem 1.8rem;
    border-radius: 10px;
    border: none;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
  }

  .btn-generate:hover:not(:disabled) {
    box-shadow: 0 0 30px rgba(0, 229, 255, 0.4);
    transform: translateY(-1px);
  }

  .btn-generate:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .loading-state, .empty-state {
    padding: 2rem;
    text-align: center;
    color: var(--text-secondary);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    border: 1px dashed rgba(255, 255, 255, 0.1);
  }
</style>
