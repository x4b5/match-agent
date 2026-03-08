<script lang="ts">
  import type { PageData } from "./$types";
  let { data } = $props<{ data: PageData }>();

  let selectedCandidate = $state(data.candidates?.[0]?.naam || "");
  let selectedEmployer = $state(data.employers?.[0]?.naam || "");
  let selectedMode = $state("quick_scan");

  let isMatching = $state(false);
  let matchResult = $state("");
  let finalMatchData: any = $state(null);
  let errorMsg = $state("");

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

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (let line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.substring(6).trim());
              if (payload.type === "token") {
                matchResult += payload.data;
              } else if (payload.type === "result") {
                finalMatchData = payload.data;
              } else if (payload.type === "error") {
                errorMsg = payload.data;
              } else if (payload.type === "warning") {
                console.warn(payload.data);
              }
            } catch (e) {
              // ignore parsing errors on partial chunks
            }
          }
        }
      }
    } catch (e: any) {
      errorMsg = e.message || "Fout tijdens matchen.";
    } finally {
      isMatching = false;
    }
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
        <span
          class="material-icons"
          style="vertical-align: middle; animation: spin 2s linear infinite;"
          >sync</span
        > Analyseren...
      {:else}
        <span class="material-icons" style="vertical-align: middle;"
          >play_arrow</span
        > Start Match
      {/if}
    </button>
    {#if errorMsg}
      <div
        style="margin-top: 1rem; color: var(--neon-pink); font-size: 0.9rem;"
      >
        {errorMsg}
      </div>
    {/if}
  </div>

  <div
    class="card element-container"
    style="display: flex; flex-direction: column;"
  >
    <h3>2. Analyseresultaat</h3>

    <div
      style="flex: 1; background: var(--surface-0); border-radius: var(--radius-sm); padding: 1rem; min-height: 300px; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; overflow-y: auto; color: var(--text-secondary); white-space: pre-wrap; border: 1px solid var(--glass-border);"
    >
      {#if matchResult}
        <span style="color: var(--text-primary);">{matchResult}</span>
      {:else if isMatching}
        <span style="color: var(--neon-cyan); opacity: 0.7;"
          >Verbinden met AI model...</span
        >
      {:else}
        Nog geen match gestart. Selecteer entiteiten en druk op start.
      {/if}
    </div>

    {#if finalMatchData}
      <div
        style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center;"
      >
        <div
          style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary);"
        >
          Match Percentage
        </div>
        <div class="metric-value" style="font-size: 2rem;">
          {finalMatchData.match_percentage}%
        </div>
      </div>
      {#if finalMatchData.match_betrouwbaarheid}
        <div
          style="margin-top: 0.5rem; display: flex; align-items: center; gap: 8px;"
        >
          <span
            class="status-dot-container {finalMatchData.match_betrouwbaarheid.toLowerCase() ===
            'hoog'
              ? 'online'
              : ''}"
            style="border-radius: 4px; border: 1px solid var(--glass-border); background: rgba(255,255,255,0.05);"
          >
            Betrouwbaarheid: {finalMatchData.match_betrouwbaarheid}
          </span>
        </div>
      {/if}
    {/if}
  </div>
</div>
