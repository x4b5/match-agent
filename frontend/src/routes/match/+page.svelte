<script lang="ts">
  import type { PageData } from "./$types";
  let { data } = $props<{ data: PageData }>();

  // Modus toggle
  let matchType = $state<"single" | "batch">("single");

  // Enkele match state
  let selectedCandidate = $state(data.candidates?.[0]?.naam || "");
  let selectedEmployer = $state(data.employers?.[0]?.naam || "");
  let selectedMode = $state("quick_scan");

  let isMatching = $state(false);
  let matchResult = $state("");
  let finalMatchData: any = $state(null);
  let errorMsg = $state("");

  // Batch match state
  let batchLimit = $state(10);
  let usePrefilter = $state(true);
  let batchProgress = $state("");
  let batchCurrentIndex = $state(0);
  let batchTotal = $state(0);
  let batchResults: any[] = $state([]);
  let prefilterResults: any[] = $state([]);
  let batchCurrentKandidaat = $state("");
  let batchTokens = $state("");

  async function startMatch() {
    if (!selectedCandidate || !selectedEmployer) {
      errorMsg = "Selecteer kandidaat én vacature.";
      return;
    }

    isMatching = true;
    matchResult = "";
    finalMatchData = null;
    errorMsg = "";

    try {
      const res = await fetch("/api/matching/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kandidaat_naam: selectedCandidate,
          vacature_naam: selectedEmployer,
          modus: selectedMode,
        }),
      });

      if (!res.body) throw new Error("No readable stream.");
      await processSSEStream(res.body, (payload: any) => {
        if (payload.type === "token") {
          matchResult += payload.data;
        } else if (payload.type === "result") {
          finalMatchData = payload.data;
        } else if (payload.type === "error") {
          errorMsg = payload.data;
        }
      });
    } catch (e: any) {
      errorMsg = e.message || "Fout tijdens matchen.";
    } finally {
      isMatching = false;
    }
  }

  async function startBatchMatch() {
    if (!selectedEmployer) {
      errorMsg = "Selecteer een vacature.";
      return;
    }

    isMatching = true;
    errorMsg = "";
    batchResults = [];
    prefilterResults = [];
    batchProgress = "Bezig met pre-filtering...";
    batchCurrentIndex = 0;
    batchTotal = 0;
    batchCurrentKandidaat = "";
    batchTokens = "";

    try {
      const res = await fetch("/api/matching/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vacature_naam: selectedEmployer,
          modus: selectedMode,
          limit: batchLimit,
          use_prefilter: usePrefilter,
        }),
      });

      if (!res.body) throw new Error("No readable stream.");
      await processSSEStream(res.body, (payload: any) => {
        if (payload.type === "prefilter") {
          prefilterResults = payload.data;
          batchProgress = `Pre-filter: ${payload.data.length} kandidaten geselecteerd`;
        } else if (payload.type === "match_start") {
          batchCurrentIndex = payload.data.index;
          batchTotal = payload.data.total;
          batchCurrentKandidaat = payload.data.naam;
          batchTokens = "";
          batchProgress = `Matching ${payload.data.naam} (${payload.data.index}/${payload.data.total})...`;
        } else if (payload.type === "token" && payload.kandidaat) {
          batchTokens += payload.data;
        } else if (payload.type === "match_result") {
          const r = payload.data;
          batchResults = [...batchResults, r];
        } else if (payload.type === "batch_complete") {
          batchResults = payload.data;
          batchProgress = `Klaar! ${payload.data.length} kandidaten gematcht.`;
        } else if (payload.type === "error") {
          errorMsg = payload.data;
        }
      });
    } catch (e: any) {
      errorMsg = e.message || "Fout tijdens batch matchen.";
    } finally {
      isMatching = false;
    }
  }

  async function processSSEStream(
    body: ReadableStream<Uint8Array>,
    handler: (payload: any) => void,
  ) {
    const reader = body.getReader();
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
            handler(payload);
          } catch {
            // negeer parse errors op incomplete chunks
          }
        }
      }
    }
  }

  function scoreKleur(pct: number): string {
    if (pct >= 75) return "var(--neon-green)";
    if (pct >= 40) return "#FFAB00";
    return "var(--neon-pink)";
  }
</script>

<div class="page-hero">
  <h1>
    <span class="material-icons" style="font-size: 2.2rem; margin-right: 15px;"
      >gps_fixed</span
    > Nieuwe Match
  </h1>
  <p>Selecteer kandidaat en vacature om de AI screening te starten.</p>
</div>

<!-- Match type toggle -->
<div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem;">
  <button
    class={matchType === "single" ? "btn-primary" : "btn-secondary"}
    onclick={() => (matchType = "single")}
  >
    <span class="material-icons" style="font-size: 1rem; vertical-align: middle;">person</span>
    Enkele match
  </button>
  <button
    class={matchType === "batch" ? "btn-primary" : "btn-secondary"}
    onclick={() => (matchType = "batch")}
  >
    <span class="material-icons" style="font-size: 1rem; vertical-align: middle;">groups</span>
    Batch match
  </button>
</div>

{#if matchType === "single"}
  <!-- Enkele match modus -->
  <div class="grid-2">
    <div class="card element-container">
      <h3>1. Configuratie</h3>
      <div class="input-group">
        <label class="input-label" for="cand">Kandidaat</label>
        <select id="cand" class="input-field" bind:value={selectedCandidate}>
          <option value="">Selecteer kandidaat...</option>
          {#each data.candidates as c}
            <option value={c.naam}>{c.naam} (Score: {c.profile_score}%)</option>
          {/each}
        </select>
      </div>

      <div class="input-group">
        <label class="input-label" for="emp">Vacature / Vraag</label>
        <select id="emp" class="input-field" bind:value={selectedEmployer}>
          <option value="">Selecteer vacature...</option>
          {#each data.employers as e}
            <option value={e.naam}>{e.naam} (Score: {e.profile_score}%)</option>
          {/each}
        </select>
      </div>

      <div class="input-group" style="margin-bottom: 2rem;">
        <label class="input-label" for="mode">Matching Modus</label>
        <select id="mode" class="input-field" bind:value={selectedMode}>
          <option value="quick_scan">Quick Scan</option>
          <option value="normal">Normaal</option>
          <option value="diepgaand">Diepgaand & Kritisch</option>
        </select>
      </div>

      <button
        class="btn-primary"
        style="width: 100%;"
        onclick={startMatch}
        disabled={isMatching}
      >
        {#if isMatching}
          <span class="material-icons" style="vertical-align: middle; animation: spin 2s linear infinite;">sync</span> Analyseren...
        {:else}
          <span class="material-icons" style="vertical-align: middle;">play_arrow</span> Start Match
        {/if}
      </button>
      {#if errorMsg}
        <div style="margin-top: 1rem; color: var(--neon-pink); font-size: 0.9rem;">
          {errorMsg}
        </div>
      {/if}
    </div>

    <div class="card element-container" style="display: flex; flex-direction: column;">
      <h3>2. Analyseresultaat</h3>
      <div
        style="flex: 1; background: var(--surface-0); border-radius: var(--radius-sm); padding: 1rem; min-height: 300px; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; overflow-y: auto; color: var(--text-secondary); white-space: pre-wrap; border: 1px solid var(--glass-border);"
      >
        {#if matchResult}
          <span style="color: var(--text-primary);">{matchResult}</span>
        {:else if isMatching}
          <span style="color: var(--neon-cyan); opacity: 0.7;">Verbinden met AI model...</span>
        {:else}
          Nog geen match gestart. Selecteer entiteiten en druk op start.
        {/if}
      </div>

      {#if finalMatchData}
        <div
          style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center;"
        >
          <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary);">
            Match Percentage
          </div>
          <div class="metric-value" style="font-size: 2rem;">
            {finalMatchData.match_percentage}%
          </div>
        </div>
        {#if finalMatchData.match_betrouwbaarheid}
          <div style="margin-top: 0.5rem; display: flex; align-items: center; gap: 8px;">
            <span
              class="status-dot-container {finalMatchData.match_betrouwbaarheid.toLowerCase() === 'hoog' ? 'online' : ''}"
              style="border-radius: 4px; border: 1px solid var(--glass-border); background: rgba(255,255,255,0.05);"
            >
              Betrouwbaarheid: {finalMatchData.match_betrouwbaarheid}
            </span>
          </div>
        {/if}
      {/if}
    </div>
  </div>
{:else}
  <!-- Batch match modus -->
  <div class="grid-2">
    <div class="card element-container">
      <h3>1. Batch Configuratie</h3>

      <div class="input-group">
        <label class="input-label" for="batch-emp">Vacature / Vraag</label>
        <select id="batch-emp" class="input-field" bind:value={selectedEmployer}>
          <option value="">Selecteer vacature...</option>
          {#each data.employers as e}
            <option value={e.naam}>{e.naam} (Score: {e.profile_score}%)</option>
          {/each}
        </select>
      </div>

      <div class="input-group">
        <label class="input-label" for="batch-mode">Matching Modus</label>
        <select id="batch-mode" class="input-field" bind:value={selectedMode}>
          <option value="quick_scan">Quick Scan</option>
          <option value="normal">Normaal</option>
          <option value="diepgaand">Diepgaand & Kritisch</option>
        </select>
      </div>

      <div class="input-group">
        <label class="input-label" for="batch-limit">Max kandidaten</label>
        <input
          id="batch-limit"
          type="number"
          class="input-field"
          min="1"
          max="50"
          bind:value={batchLimit}
        />
      </div>

      <div style="margin-bottom: 2rem;">
        <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; cursor: pointer;">
          <input type="checkbox" bind:checked={usePrefilter} />
          Embedding pre-filter gebruiken
        </label>
        <span style="font-size: 0.75rem; color: var(--text-secondary);">
          Selecteert de meest relevante kandidaten op basis van vectorafstand
        </span>
      </div>

      <button
        class="btn-primary"
        style="width: 100%;"
        onclick={startBatchMatch}
        disabled={isMatching}
      >
        {#if isMatching}
          <span class="material-icons" style="vertical-align: middle; animation: spin 2s linear infinite;">sync</span> Batch matching...
        {:else}
          <span class="material-icons" style="vertical-align: middle;">play_arrow</span> Start Batch Match
        {/if}
      </button>

      {#if errorMsg}
        <div style="margin-top: 1rem; color: var(--neon-pink); font-size: 0.9rem;">
          {errorMsg}
        </div>
      {/if}

      {#if batchProgress}
        <div style="margin-top: 1rem; font-size: 0.9rem; color: var(--neon-cyan);">
          {batchProgress}
        </div>
        {#if batchTotal > 0}
          <div style="margin-top: 0.5rem; background: var(--surface-0); border-radius: 4px; height: 6px; overflow: hidden; border: 1px solid var(--glass-border);">
            <div
              style="height: 100%; background: var(--neon-cyan); transition: width 0.3s; width: {(batchCurrentIndex / batchTotal) * 100}%;"
            ></div>
          </div>
        {/if}
      {/if}
    </div>

    <div class="card element-container" style="display: flex; flex-direction: column;">
      <h3>2. Resultaten</h3>

      {#if batchResults.length === 0 && !isMatching}
        <div
          style="flex: 1; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); min-height: 300px;"
        >
          Start een batch match om resultaten te zien.
        </div>
      {:else if isMatching && batchResults.length === 0}
        <div
          style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-secondary); min-height: 300px; gap: 1rem;"
        >
          <span class="material-icons" style="font-size: 2rem; animation: spin 2s linear infinite; color: var(--neon-cyan);">sync</span>
          <span>Kandidaten worden gematcht...</span>
          {#if batchTokens}
            <div
              style="max-height: 150px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; padding: 0.5rem; background: var(--surface-0); border-radius: var(--radius-sm); width: 100%; white-space: pre-wrap; border: 1px solid var(--glass-border);"
            >
              {batchTokens}
            </div>
          {/if}
        </div>
      {:else}
        <div style="display: flex; flex-direction: column; gap: 0.5rem; overflow-y: auto; max-height: 500px;">
          {#each batchResults as result, i}
            <div
              class="card"
              style="padding: 0.8rem; margin: 0; display: flex; justify-content: space-between; align-items: center;"
            >
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                  <span style="font-size: 0.8rem; color: var(--text-secondary);">#{i + 1}</span>
                  <strong>{result.naam}</strong>
                  {#if result.cached}
                    <span style="font-size: 0.65rem; color: var(--text-secondary); border: 1px solid var(--glass-border); padding: 1px 6px; border-radius: 4px;">cache</span>
                  {/if}
                </div>
                {#if result.result?.kernrol || result.kernrol}
                  <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">
                    {result.result?.kernrol || result.kernrol}
                  </div>
                {/if}
              </div>
              <div
                class="metric-value"
                style="font-size: 1.5rem; color: {scoreKleur(result.match_percentage || result.result?.match_percentage || 0)};"
              >
                {result.match_percentage || result.result?.match_percentage || 0}%
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}
