<script lang="ts">
  import type { PageData } from "./$types";
  import { toasts } from "$lib/toast";
  let { data } = $props<{ data: PageData }>();

  let selectedCandidate = $state(data.candidates?.[0]?.naam || "");
  let selectedEmployer = $state(data.employers?.[0]?.naam || "");
  let selectedMode = $state("quick_scan");
  let matchType = $state("individual"); // 'individual' or 'batch'
  let selectedCandidates: Set<string> = $state(
    new Set(data.candidates.map((c: any) => c.naam)),
  );

  let isMatching = $state(false);
  let matchResult = $state("");
  let finalMatchData: any = $state(null);
  let batchResults: any[] = $state([]);
  let currentBatchItem: any = $state(null);
  let errorMsg = $state("");
  let currentStep = $state(0);
  let showRawOutput = $state(false);
  let batchCandidateSearch = $state("");

  let filteredBatchCandidates = $derived(
    data.candidates.filter((c: any) =>
      c.naam.toLowerCase().includes(batchCandidateSearch.toLowerCase()),
    ),
  );

  function toggleCandidate(name: string) {
    if (selectedCandidates.has(name)) {
      selectedCandidates.delete(name);
    } else {
      selectedCandidates.add(name);
    }
    selectedCandidates = new Set(selectedCandidates);
  }

  function selectAll() {
    selectedCandidates = new Set(data.candidates.map((c: any) => c.naam));
  }

  function selectNone() {
    selectedCandidates = new Set();
  }

  async function startMatch() {
    if (
      matchType === "individual" &&
      (!selectedCandidate || !selectedEmployer)
    ) {
      toasts.add("Selecteer kandidaat én vacature.", "warning");
      return;
    }
    if (matchType === "batch") {
      if (!selectedEmployer) {
        toasts.add("Selecteer een vacature voor de batch analyse.", "warning");
        return;
      }
      if (selectedCandidates.size === 0) {
        toasts.add("Selecteer minimaal één kandidaat.", "warning");
        return;
      }
    }

    isMatching = true;
    matchResult = "";
    finalMatchData = null;
    batchResults = [];
    currentBatchItem = null;
    errorMsg = "";
    currentStep = 1;
    showRawOutput = false;

    const endpoint =
      matchType === "individual"
        ? "/api/matching/stream"
        : "/api/matching/batch";
    const body: any = {
      modus: selectedMode,
      vacature_naam: selectedEmployer,
    };
    if (matchType === "individual") {
      body.kandidaat_naam = selectedCandidate;
    } else {
      body.kandidaat_namen = Array.from(selectedCandidates);
    }

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.body) throw new Error("No readable stream.");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (let line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.substring(6).trim());

              if (matchType === "individual") {
                handleIndividualEvent(payload);
              } else {
                handleBatchEvent(payload);
              }
            } catch (e) {
              /* ignore partial chunks */
            }
          }
        }
      }
    } catch (e: any) {
      errorMsg = e.message || "Fout tijdens matchen.";
      toasts.add(errorMsg, "error");
    } finally {
      isMatching = false;
      if (currentStep < 2) currentStep = 0;
    }
  }

  function handleIndividualEvent(payload: any) {
    if (payload.type === "token") {
      matchResult += payload.data;
    } else if (payload.type === "result") {
      finalMatchData = payload.data;
      currentStep = 2;
      toasts.add("Match analyse voltooid!", "success");
    } else if (payload.type === "error") {
      errorMsg = payload.data;
      toasts.add(payload.data, "error");
    }
  }

  function handleBatchEvent(payload: any) {
    if (payload.type === "match_start") {
      currentBatchItem = payload.data;
      matchResult = `Bezig met analyseren van: ${payload.data.naam} (${payload.data.index}/${payload.data.total})...\n\n`;
    } else if (payload.type === "token") {
      matchResult += payload.data;
    } else if (payload.type === "match_result") {
      // Just record it, final list comes at the end or we can push to living list
      // batchResults = [...batchResults, { ...payload.data.result, naam: payload.data.naam }];
    } else if (payload.type === "batch_complete") {
      batchResults = payload.data;
      finalMatchData = { isBatch: true }; // Trigger result view
      currentStep = 2;
      toasts.add("Batch analyse voltooid!", "success");
    } else if (payload.type === "error") {
      toasts.add(payload.data, "error");
    }
  }

  function getScoreColor(score: number): string {
    if (score >= 75) return "var(--neon-green)";
    if (score >= 50) return "var(--neon-cyan)";
    if (score >= 25) return "#FFAB00";
    return "var(--neon-pink)";
  }

  function resetMatch() {
    matchResult = "";
    finalMatchData = null;
    batchResults = [];
    currentBatchItem = null;
    errorMsg = "";
    currentStep = 0;
    showRawOutput = false;
  }

  function selectBatchDetail(item: any) {
    finalMatchData = item;
    selectedCandidate = item.naam;
  }

  function backToBatch() {
    finalMatchData = { isBatch: true };
  }
</script>

<div class="page-hero">
  <h1>
    <span class="material-icons" style="font-size: 2.2rem; margin-right: 15px;"
      >gps_fixed</span
    >
    Nieuwe Match
  </h1>
  <p>Selecteer configuratie om de AI screening te starten.</p>
</div>

<!-- Step Indicator -->
<div class="step-indicator">
  <div class="step-bar">
    {#each ["Configuratie", "Analyseren", "Resultaat"] as label, idx}
      <div
        class="step-item"
        class:step-active={currentStep >= idx}
        class:step-current={currentStep === idx}
      >
        <div class="step-circle">{idx + 1}</div>
        <span class="step-label">{label}</span>
      </div>
      {#if idx < 2}
        <div class="step-line" class:step-line-active={currentStep > idx}></div>
      {/if}
    {/each}
  </div>
</div>

{#if !finalMatchData}
  <!-- ===== CONFIGURATIE + STREAMING PANEEL ===== -->
  <div class="grid-2">
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-cyan);">tune</span
        >
        Configuratie
      </h3>

      <div class="input-group" style="margin-bottom: 1.5rem;">
        <label class="input-label">Type Match</label>
        <div
          style="display: flex; gap: 0.5rem; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 8px; border: 1px solid var(--glass-border);"
        >
          <button
            class="btn-toggle {matchType === 'individual' ? 'active' : ''}"
            onclick={() => (matchType = "individual")}
            disabled={isMatching}>Individueel</button
          >
          <button
            class="btn-toggle {matchType === 'batch' ? 'active' : ''}"
            onclick={() => (matchType = "batch")}
            disabled={isMatching}>Batch (Allen)</button
          >
        </div>
      </div>

      <div class="input-group">
        <label class="input-label" for="emp">Vacature / Vraag</label>
        <select
          id="emp"
          class="input-field"
          bind:value={selectedEmployer}
          disabled={isMatching}
        >
          <option value="">Selecteer vacature...</option>
          {#each data.employers as e}
            <option value={e.naam}>{e.naam} (Score: {e.profile_score}%)</option>
          {/each}
        </select>
      </div>

      {#if matchType === "individual"}
        <div class="input-group" style="animation: slideDown 0.3s ease;">
          <label class="input-label" for="cand">Kandidaat</label>
          <select
            id="cand"
            class="input-field"
            bind:value={selectedCandidate}
            disabled={isMatching}
          >
            <option value="">Selecteer kandidaat...</option>
            {#each data.candidates as c}
              <option value={c.naam}
                >{c.naam} (Score: {c.profile_score}%)</option
              >
            {/each}
          </select>
        </div>
      {:else}
        <div class="input-group" style="animation: slideDown 0.3s ease;">
          <div
            style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;"
          >
            <label class="input-label" style="margin: 0;"
              >Selecteer Kandidaten</label
            >
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn-text" onclick={selectAll} disabled={isMatching}
                >Alles</button
              >
              <button
                class="btn-text"
                onclick={selectNone}
                disabled={isMatching}>Niets</button
              >
            </div>
          </div>

          <div class="candidate-search-wrapper" style="margin-bottom: 0.5rem;">
            <div style="position: relative;">
              <span
                class="material-icons"
                style="position: absolute; left: 10px; top: 10px; font-size: 1.1rem; color: var(--text-secondary);"
                >search</span
              >
              <input
                type="text"
                class="input-field"
                style="padding-left: 35px; height: 38px; font-size: 0.85rem;"
                placeholder="Zoek kandidaat..."
                bind:value={batchCandidateSearch}
              />
            </div>
          </div>

          <div class="candidate-select-list">
            {#each filteredBatchCandidates as c}
              <label
                class="candidate-select-item"
                class:selected={selectedCandidates.has(c.naam)}
              >
                <input
                  type="checkbox"
                  checked={selectedCandidates.has(c.naam)}
                  onchange={() => toggleCandidate(c.naam)}
                  disabled={isMatching}
                />
                <span class="cand-details">
                  <span class="cand-name">{c.naam}</span>
                  <span class="cand-score">{c.profile_score}%</span>
                </span>
              </label>
            {/each}
          </div>
        </div>
      {/if}

      <div class="input-group" style="margin-bottom: 2rem;">
        <label class="input-label" for="mode">Matching Modus</label>
        <select
          id="mode"
          class="input-field"
          bind:value={selectedMode}
          disabled={isMatching}
        >
          <option value="quick_scan">Quick Scan</option>
          <option value="standaard">Standaard</option>
          <option value="diepte_analyse">Diepgaand & Kritisch</option>
        </select>
      </div>

      <button
        class="btn-primary"
        style="width: 100%;"
        onclick={startMatch}
        disabled={isMatching}
      >
        {#if isMatching}
          <span
            class="material-icons spin"
            style="vertical-align: middle; font-size: 1.1rem;">sync</span
          >
          {matchType === "individual" ? "Analyseren..." : "Batch Analyseren..."}
        {:else}
          <span class="material-icons" style="vertical-align: middle;"
            >play_arrow</span
          >
          {matchType === "individual" ? "Start Match" : "Start Batch Match"}
        {/if}
      </button>
    </div>

    <div class="card" style="display: flex; flex-direction: column;">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-purple);"
          >analytics</span
        >
        Live Analyse
      </h3>
      <div class="stream-box">
        {#if matchResult}
          <span style="color: var(--text-primary);">{matchResult}</span>
        {:else if isMatching}
          <div class="stream-placeholder">
            <span
              class="material-icons spin"
              style="font-size: 2.5rem; color: var(--neon-cyan); opacity: 0.6;"
              >settings</span
            >
            <span>Verbinden met AI model...</span>
          </div>
        {:else}
          <div class="stream-placeholder">
            <span
              class="material-icons"
              style="font-size: 3rem; color: rgba(255,255,255,0.06);"
              >psychology</span
            >
            <span>Wacht op analyse</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
{:else if finalMatchData.isBatch}
  <!-- ===== BATCH RESULTATEN LIJST ===== -->
  <div class="card">
    <div
      style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;"
    >
      <h3 class="section-title" style="margin: 0;">
        <span class="material-icons" style="color: var(--neon-cyan);">list</span
        >
        Batch Resultaten: {selectedEmployer}
      </h3>
      <button class="btn-secondary" onclick={resetMatch}>Nieuwe Match</button>
    </div>

    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
      {#each batchResults as res, i}
        <div
          class="batch-item card stagger-item"
          style="animation-delay: {i *
            50}ms; cursor: pointer; padding: 1rem; border: 1px solid rgba(255,255,255,0.05);"
          onclick={() => selectBatchDetail(res)}
        >
          <div
            style="display: flex; justify-content: space-between; align-items: center;"
          >
            <div style="display: flex; align-items: center; gap: 15px;">
              <div
                class="score-mini"
                style="background: {getScoreColor(res.match_percentage)};"
              >
                {res.match_percentage}%
              </div>
              <div>
                <div
                  style="font-weight: 600; font-size: 1.1rem; color: var(--text-primary);"
                >
                  {res.naam}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">
                  {res.kernrol || "Kandidaat"}
                </div>
              </div>
            </div>
            <span class="material-icons" style="color: var(--text-secondary);"
              >chevron_right</span
            >
          </div>
        </div>
      {/each}
    </div>
  </div>
{:else}
  <!-- ===== INDIVIDUEEL RESULTAAT ===== -->
  <div class="result-header card">
    <div class="result-header-inner">
      <div class="result-meta">
        <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
          {#if batchResults.length > 0}
            <button
              class="btn-icon-secondary"
              onclick={backToBatch}
              title="Terug naar batch lijst"
            >
              <span class="material-icons">arrow_back</span>
            </button>
          {/if}
        </div>
        <div class="result-names">
          <span class="badge badge-success" style="font-size: 0.7rem;"
            >{selectedCandidate}</span
          >
          <span
            class="material-icons"
            style="font-size: 1rem; color: var(--text-secondary);"
            >compare_arrows</span
          >
          <span
            class="badge"
            style="font-size: 0.7rem; color: var(--neon-cyan); background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.25);"
            >{selectedEmployer}</span
          >
        </div>
        {#if finalMatchData.dossier_compleetheid}
          <span
            class="badge {finalMatchData.dossier_compleetheid.toLowerCase() ===
            'hoog'
              ? 'badge-success'
              : finalMatchData.dossier_compleetheid.toLowerCase() === 'laag'
                ? 'badge-danger'
                : 'badge-warning'}"
          >
            {finalMatchData.dossier_compleetheid} Dossiercompleetheid
          </span>
        {/if}
      </div>
      <div class="score-ring">
        <svg viewBox="0 0 36 36" width="90" height="90">
          <circle class="score-ring-bg" cx="18" cy="18" r="15.91549431" />
          <circle
            class="score-ring-fill"
            cx="18"
            cy="18"
            r="15.91549431"
            stroke={getScoreColor(finalMatchData.match_percentage)}
            stroke-dasharray="{finalMatchData.match_percentage} {100 -
              finalMatchData.match_percentage}"
          />
        </svg>
        <span class="score-ring-text">{finalMatchData.match_percentage}%</span>
      </div>
    </div>
  </div>

  <!-- Score Breakdown (standaard modus) -->
  {#if finalMatchData.score_breakdown}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-blue);"
          >leaderboard</span
        >
        Score Breakdown
      </h3>
      <div class="breakdown-grid">
        {#each Object.entries(finalMatchData.score_breakdown) as [key, value]}
          <div class="breakdown-item">
            <div class="breakdown-label">{key.replace(/_/g, " ")}</div>
            <div class="breakdown-bar-track">
              <div
                class="breakdown-bar-fill"
                style="width: {value}%; background: {getScoreColor(
                  Number(value),
                )};"
              ></div>
            </div>
            <div
              class="breakdown-value"
              style="color: {getScoreColor(Number(value))};"
            >
              {value}%
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Personality Axes -->
  {#if finalMatchData.personality_axes}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-purple);"
          >fingerprint</span
        >
        Persoonlijkheidsprofiel
      </h3>
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        {#each Object.entries(finalMatchData.personality_axes) as [key, value]}
          <div
            style="border-left: 2px solid var(--neon-purple); padding-left: 1rem;"
          >
            <div
              style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 0.25rem;"
            >
              {key}
            </div>
            <div
              style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;"
            >
              {value}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Match Narratief -->
  {#if finalMatchData.match_narratief}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-gold);"
          >auto_stories</span
        >
        Match Verhaal
      </h3>
      <p
        style="color: var(--text-primary); font-size: 1rem; line-height: 1.7; margin: 0;"
      >
        {finalMatchData.match_narratief}
      </p>
    </div>
  {/if}

  <!-- Matchende + Ontbrekende punten -->
  <div class="grid-2">
    {#if finalMatchData.matchende_punten?.length}
      <div class="card">
        <h3 class="section-title">
          <span class="material-icons" style="color: var(--neon-green);"
            >check_circle</span
          >
          Matchende Punten
        </h3>
        <ul class="result-list result-list-positive">
          {#each finalMatchData.matchende_punten as punt}
            <li>{punt}</li>
          {/each}
        </ul>
      </div>
    {/if}
    {#if finalMatchData.ontbrekende_punten?.length}
      <div class="card">
        <h3 class="section-title">
          <span class="material-icons" style="color: var(--neon-pink);"
            >cancel</span
          >
          Ontbrekende Punten
        </h3>
        <ul class="result-list result-list-negative">
          {#each finalMatchData.ontbrekende_punten as punt}
            <li>{punt}</li>
          {/each}
        </ul>
      </div>
    {/if}
  </div>

  <!-- Verrassingselement + Onderbouwing -->
  {#if finalMatchData.verrassings_element}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-gold);"
          >lightbulb</span
        >
        Verrassings-element
      </h3>
      <p style="color: var(--text-primary); margin: 0; line-height: 1.6;">
        {finalMatchData.verrassings_element}
      </p>
    </div>
  {/if}

  <!-- Onderbouwing -->
  {#if finalMatchData.onderbouwing}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-blue);"
          >gavel</span
        >
        Onderbouwing
      </h3>
      <p style="color: var(--text-secondary); margin: 0; line-height: 1.6;">
        {finalMatchData.onderbouwing}
      </p>
    </div>
  {/if}

  <!-- Cultuur fit + Groeipotentieel (standaard modus) -->
  {#if finalMatchData.cultuur_fit || finalMatchData.groeipotentieel}
    <div class="grid-2">
      {#if finalMatchData.cultuur_fit}
        <div class="card">
          <h3 class="section-title">
            <span class="material-icons" style="color: var(--neon-cyan);"
              >diversity_3</span
            >
            Cultuur Fit
          </h3>
          <p style="color: var(--text-primary); margin: 0; line-height: 1.6;">
            {finalMatchData.cultuur_fit}
          </p>
        </div>
      {/if}
      {#if finalMatchData.groeipotentieel}
        <div class="card">
          <h3 class="section-title">
            <span class="material-icons" style="color: var(--neon-green);"
              >trending_up</span
            >
            Groeipotentieel
          </h3>
          <p style="color: var(--text-primary); margin: 0; line-height: 1.6;">
            {finalMatchData.groeipotentieel}
          </p>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Overbruggingsadvies -->
  {#if finalMatchData.overbruggings_advies?.length}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-cyan);"
          >engineering</span
        >
        Overbruggingsadvies
      </h3>
      <ul class="result-list result-list-neutral">
        {#each finalMatchData.overbruggings_advies as advies}
          <li>{advies}</li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- Vervolgvragen -->
  {#if finalMatchData.vervolgvragen?.length}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: #FFAB00;">help</span>
        Vervolgvragen
      </h3>
      <ul class="result-list result-list-neutral">
        {#each finalMatchData.vervolgvragen as vraag}
          <li>{vraag}</li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- Aandachtspunten -->
  {#if finalMatchData.aandachtspunten?.length}
    <div class="card">
      <h3 class="section-title">
        <span class="material-icons" style="color: var(--neon-pink);"
          >priority_high</span
        >
        Aandachtspunten
      </h3>
      <ul class="result-list result-list-neutral">
        {#each finalMatchData.aandachtspunten as punt}
          <li>{punt}</li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- Toggle raw output + actions -->
  <div
    style="display: flex; gap: 1rem; margin-top: 1rem; justify-content: space-between; align-items: center;"
  >
    <button
      class="btn-secondary"
      onclick={() => (showRawOutput = !showRawOutput)}
      style="font-size: 0.8rem;"
    >
      <span
        class="material-icons"
        style="font-size: 0.9rem; vertical-align: middle;">code</span
      >
      {showRawOutput ? "Verberg" : "Toon"} ruwe output
    </button>
    <div style="display: flex; gap: 0.5rem;">
      {#if batchResults.length > 0}
        <button class="btn-secondary" onclick={backToBatch}>
          <span
            class="material-icons"
            style="font-size: 1rem; vertical-align: middle;">arrow_back</span
          >
          Lijst
        </button>
      {/if}
      <button class="btn-primary" onclick={resetMatch}>
        <span
          class="material-icons"
          style="font-size: 1rem; vertical-align: middle;">refresh</span
        >
        Nieuwe Match
      </button>
    </div>
  </div>

  {#if showRawOutput}
    <div class="card" style="margin-top: 1rem;">
      <div class="stream-box" style="max-height: 300px;">
        <span style="color: var(--text-primary);">{matchResult}</span>
      </div>
    </div>
  {/if}
{/if}

<style>
  .step-indicator {
    padding: 0 1rem;
    margin-bottom: 2rem;
  }
  .step-bar {
    display: flex;
    align-items: center;
  }
  .step-item {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .step-circle {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--surface-2);
    border: 1px solid var(--glass-border);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-secondary);
    transition: all 0.4s ease;
  }
  .step-active .step-circle {
    background: linear-gradient(135deg, var(--neon-cyan), var(--neon-blue));
    border-color: transparent;
    color: #0a0e18;
    box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
  }
  .step-current .step-circle {
    animation: stepPulse 2s ease infinite;
  }
  .step-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-secondary);
    transition: color 0.3s;
  }
  .step-active .step-label {
    color: var(--text-primary);
  }
  .step-line {
    flex: 1;
    height: 2px;
    background: var(--glass-border);
    margin: 0 1rem;
    transition: background 0.5s;
  }
  .step-line-active {
    background: linear-gradient(90deg, var(--neon-cyan), var(--neon-blue));
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
  }
  @keyframes stepPulse {
    0%,
    100% {
      box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
    }
    50% {
      box-shadow: 0 0 25px rgba(0, 229, 255, 0.6);
    }
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.1rem;
    margin-bottom: 1rem;
  }
  .section-title .material-icons {
    font-size: 1.2rem;
  }

  .stream-box {
    flex: 1;
    background: var(--surface-0);
    border-radius: var(--radius-sm);
    padding: 1rem;
    min-height: 300px;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.85rem;
    overflow-y: auto;
    color: var(--text-secondary);
    white-space: pre-wrap;
    border: 1px solid var(--glass-border);
    word-break: break-word;
  }
  .stream-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 1rem;
    color: rgba(255, 255, 255, 0.25);
    font-family: "Space Grotesk", sans-serif;
    font-size: 0.9rem;
  }

  /* Result display */
  .result-header-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .result-meta {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .result-names {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .result-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }
  .result-list li {
    position: relative;
    padding-left: 1.5rem;
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--text-secondary);
  }
  .result-list li::before {
    position: absolute;
    left: 0;
    top: 2px;
    font-size: 0.85rem;
  }
  .result-list-positive li::before {
    content: "✓";
    color: var(--neon-green);
  }
  .result-list-negative li::before {
    content: "✕";
    color: var(--neon-pink);
  }
  .result-list-neutral li::before {
    content: "→";
    color: var(--neon-cyan);
  }

  .breakdown-grid {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .breakdown-item {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .breakdown-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: capitalize;
    min-width: 140px;
    flex-shrink: 0;
  }
  .breakdown-bar-track {
    flex: 1;
    height: 8px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    overflow: hidden;
  }
  .breakdown-bar-fill {
    height: 100%;
    border-radius: 10px;
    transition: width 0.8s var(--transition-smooth);
  }
  .breakdown-value {
    font-size: 0.85rem;
    font-weight: 700;
    min-width: 40px;
    text-align: right;
  }

  .btn-toggle {
    flex: 1;
    padding: 8px;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    border-radius: 6px;
    transition: all 0.2s;
  }
  .btn-toggle.active {
    background: var(--neon-cyan);
    color: #0a0e18;
    box-shadow: 0 0 10px rgba(0, 229, 255, 0.4);
  }

  .batch-item:hover {
    border-color: var(--neon-cyan) !important;
    background: rgba(0, 229, 255, 0.05) !important;
    transform: translateX(5px);
  }

  .score-mini {
    width: 45px;
    height: 45px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.8rem;
    color: #0a0e18;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
  }

  .btn-icon-secondary {
    background: var(--surface-2);
    border: 1px solid var(--glass-border);
    color: var(--text-primary);
    width: 40px;
    height: 40px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-icon-secondary:hover {
    background: var(--surface-3);
    border-color: var(--neon-cyan);
  }

  .candidate-select-list {
    max-height: 200px;
    overflow-y: auto;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid var(--glass-border);
    border-radius: 8px;
    padding: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 1.5rem;
  }

  .candidate-select-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid transparent;
  }

  .candidate-select-item:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .candidate-select-item.selected {
    background: rgba(0, 229, 255, 0.08);
    border-color: rgba(0, 229, 255, 0.2);
  }

  .cand-details {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .cand-name {
    font-size: 0.9rem;
    font-weight: 500;
  }

  .cand-score {
    font-size: 0.75rem;
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.05);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .btn-text {
    background: transparent;
    border: none;
    color: var(--neon-cyan);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    padding: 2px 4px;
    opacity: 0.8;
  }

  .btn-text:hover {
    opacity: 1;
    text-decoration: underline;
  }

  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
