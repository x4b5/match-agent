<script lang="ts">
  import type { PageData } from "./$types";

  let { data } = $props<{ data: PageData }>();

  let matches: any[] = $state(data.matches || []);
  let searchQuery = $state("");
  let sortOption = $state("date-desc");
  let expandedId: number | null = $state(null);

  let filteredMatches = $derived(
    (() => {
      let result = matches.filter(
        (m: any) =>
          m.kandidaat_naam?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          m.vacature_titel?.toLowerCase().includes(searchQuery.toLowerCase()),
      );

      return result.sort((a: any, b: any) => {
        if (sortOption === "date-desc")
          return (
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
          );
        if (sortOption === "date-asc")
          return (
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          );
        if (sortOption === "score-desc")
          return (b.match_percentage || 0) - (a.match_percentage || 0);
        if (sortOption === "score-asc")
          return (a.match_percentage || 0) - (b.match_percentage || 0);
        return 0;
      });
    })(),
  );

  function toggleExpand(id: number) {
    expandedId = expandedId === id ? null : id;
  }

  function scoreKleur(pct: number): string {
    if (pct >= 75) return "var(--neon-green)";
    if (pct >= 40) return "#FFAB00";
    return "var(--neon-pink)";
  }

  function formatDatum(ts: string): string {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString("nl-NL", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return ts;
    }
  }
</script>

<div class="page-hero">
  <h1 style="color: var(--neon-pink);">
    <span class="material-icons" style="font-size: 2.2rem; margin-right: 15px; color: var(--neon-pink);"
      >history</span
    > Match Historie
  </h1>
  <p>Overzicht van alle eerdere match-resultaten.</p>
</div>

{#if matches.length > 0}
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
        placeholder="Zoek op kandidaat of vacature..."
        bind:value={searchQuery}
      />
    </div>

    <select
      class="input-field"
      bind:value={sortOption}
      style="min-width: 180px; padding: 0.6rem 1rem;"
    >
      <option value="date-desc">Nieuwste eerst</option>
      <option value="date-asc">Oudste eerst</option>
      <option value="score-desc">Score (Hoog-Laag)</option>
      <option value="score-asc">Score (Laag-Hoog)</option>
    </select>
  </div>
{/if}

{#if matches.length === 0}
  <div
    class="card"
    style="text-align: center; color: var(--text-secondary); padding: 2rem;"
  >
    Geen match-historie gevonden. Start een match om resultaten te zien.
  </div>
{:else if filteredMatches.length === 0}
  <div
    class="card"
    style="text-align: center; color: var(--text-secondary); padding: 2rem;"
  >
    Geen resultaten voor "{searchQuery}".
  </div>
{:else}
  {#each filteredMatches as match}
    <div
      class="card"
      style="cursor: pointer;"
      onclick={() => toggleExpand(match.id)}
    >
      <div
        style="display: flex; justify-content: space-between; align-items: center;"
      >
        <div style="flex: 1;">
          <div
            style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.3rem;"
          >
            <strong style="font-size: 1.1rem;">{match.kandidaat_naam}</strong>
            <span style="color: var(--text-secondary);">↔</span>
            <strong style="font-size: 1.1rem;">{match.vacature_titel}</strong>
          </div>
          <div
            style="font-size: 0.8rem; color: var(--text-secondary); display: flex; gap: 1rem; flex-wrap: wrap;"
          >
            <span>{formatDatum(match.timestamp)}</span>
            <span
              class="status-dot-container"
              style="font-size: 0.65rem; border-radius: 4px; border: 1px solid var(--glass-border); background: rgba(255,255,255,0.05);"
            >
              {match.modus}
            </span>
            {#if match.resultaat?.dossier_compleetheid}
              <span
                >Dossiercompleetheid: {match.resultaat
                  .dossier_compleetheid}</span
              >
            {/if}
          </div>
        </div>
        <div style="text-align: right; min-width: 80px;">
          <div
            class="metric-value"
            style="font-size: 1.8rem; color: {scoreKleur(
              match.match_percentage,
            )};"
          >
            {match.match_percentage}%
          </div>
        </div>
      </div>

      {#if expandedId === match.id && match.resultaat}
        <div
          style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--glass-border);"
        >
          {#if match.resultaat.kernrol}
            <div style="margin-bottom: 0.5rem;">
              <strong>Kernrol:</strong>
              {match.resultaat.kernrol}
            </div>
          {/if}
          {#if match.resultaat.onderbouwing}
            <div style="margin-bottom: 0.5rem;">
              <strong>Onderbouwing:</strong>
              {match.resultaat.onderbouwing}
            </div>
          {/if}
          {#if match.resultaat.verrassende_match}
            <div style="margin-bottom: 0.5rem;">
              <strong>Verrassende match:</strong>
              {match.resultaat.verrassende_match}
            </div>
          {/if}
          {#if match.resultaat.risicos?.length}
            <div>
              <strong>Risico's:</strong>
              <ul style="margin: 0.3rem 0; padding-left: 1.2rem;">
                {#each match.resultaat.risicos as risico}
                  <li>{risico}</li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/each}
{/if}
