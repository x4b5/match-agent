<script lang="ts">
  interface MatchMode {
    label: string;
    beschrijving: string;
    prompt: string;
    model_override?: string;
    temperature: number;
    think: boolean;
  }

  interface PromptsData {
    SYSTEM_PROMPT: string;
    MATCH_PROMPT: string;
    PROFIEL_KANDIDAAT_PROMPT: string;
    PROFIEL_WERKGEVERSVRAAG_PROMPT: string;
    MATCH_MODI: Record<string, MatchMode>;
  }

  let { data }: { data: { prompts: PromptsData | null } } = $props();

  function formatPrompt(text: string) {
    if (!text) return "";
    return text.trim();
  }
</script>

<div class="page-container">
  <header class="page-header">
    <div class="header-content">
      <h1 class="page-title">Prompts & Openheid</h1>
      <p class="page-subtitle">
        Transparantie over hoe onze AI-agents denken en matchen.
      </p>
    </div>
    <div class="header-badge">
      <span class="material-icons">visibility</span>
      Open Source Ethos
    </div>
  </header>

  {#if data.prompts}
    <div class="prompts-grid">
      <!-- System Prompt -->
      <section class="prompt-card wide">
        <div class="card-header">
          <span class="material-icons">psychology</span>
          <h2>System Prompt</h2>
        </div>
        <div class="card-body">
          <p class="instruction">
            Dit is de basisinstructie die de 'identiteit' en waarden van de AI
            bepaalt.
          </p>
          <pre><code>{formatPrompt(data.prompts.SYSTEM_PROMPT)}</code></pre>
        </div>
      </section>

      <!-- Profiling Prompts -->
      <section class="prompt-card">
        <div class="card-header">
          <span class="material-icons">person_search</span>
          <h2>Kandidaat Profilering</h2>
        </div>
        <div class="card-body">
          <p class="instruction">
            Hoe we ruwe CV's omzetten naar gestructureerde talent-profielen.
          </p>
          <pre><code>{formatPrompt(data.prompts.PROFIEL_KANDIDAAT_PROMPT)}</code
            ></pre>
        </div>
      </section>

      <section class="prompt-card">
        <div class="card-header">
          <span class="material-icons">business_center</span>
          <h2>Vacature Profilering</h2>
        </div>
        <div class="card-body">
          <p class="instruction">
            Hoe we werkgeversvragen analyseren op persona en cultuur.
          </p>
          <pre><code
              >{formatPrompt(data.prompts.PROFIEL_WERKGEVERSVRAAG_PROMPT)}</code
            ></pre>
        </div>
      </section>

      <!-- Matching Modi -->
      {#each Object.entries(data.prompts.MATCH_MODI) as [key, mode]}
        <section class="prompt-card wide">
          <div class="card-header">
            <span class="material-icons">compare_arrows</span>
            <h2>Match Modus: {mode.label}</h2>
          </div>
          <div class="card-body">
            <p class="instruction">{mode.beschrijving}</p>
            <div class="meta-tags">
              <span class="tag"
                >Model: {mode.model_override || "Standaard"}</span
              >
              <span class="tag">Temp: {mode.temperature}</span>
              <span class="tag">Reasoning: {mode.think ? "Aan" : "Uit"}</span>
            </div>
            <pre><code>{formatPrompt(mode.prompt)}</code></pre>
          </div>
        </section>
      {/each}
    </div>
  {:else}
    <div class="empty-state">
      <span class="material-icons">error_outline</span>
      <p>Kon de prompts niet laden. Controleer of de backend actief is.</p>
    </div>
  {/if}
</div>

<style>
  .page-container {
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 3rem;
    border-bottom: 1px solid var(--glass-border);
    padding-bottom: 2rem;
  }

  .page-title {
    font-size: 2.5rem;
    margin: 0;
    background: linear-gradient(135deg, #fff 0%, var(--text-secondary) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .page-subtitle {
    color: var(--text-secondary);
    margin-top: 0.5rem;
  }

  .header-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--glass-bg);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    border: 1px solid var(--neon-cyan);
    color: var(--neon-cyan);
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .prompts-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 2rem;
  }

  .prompt-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    transition:
      transform 0.3s ease,
      border-color 0.3s ease;
  }

  .prompt-card:hover {
    transform: translateY(-4px);
    border-color: var(--neon-cyan);
  }

  .prompt-card.wide {
    grid-column: span 2;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    color: var(--neon-cyan);
  }

  .card-header h2 {
    margin: 0;
    font-size: 1.25rem;
    color: var(--text-primary);
  }

  .instruction {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
    font-style: italic;
  }

  .meta-tags {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .tag {
    font-size: 0.7rem;
    background: rgba(255, 255, 255, 0.05);
    padding: 2px 8px;
    border-radius: 4px;
    color: var(--text-secondary);
  }

  pre {
    background: rgba(0, 0, 0, 0.3);
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    font-family: "Fira Code", "Courier New", Courier, monospace;
    font-size: 0.85rem;
    line-height: 1.5;
    color: var(--text-primary);
    border: 1px solid rgba(255, 255, 255, 0.05);
    max-height: 400px;
  }

  code {
    white-space: pre-wrap;
  }

  .empty-state {
    text-align: center;
    padding: 4rem;
    color: var(--text-secondary);
  }

  .empty-state .material-icons {
    font-size: 4rem;
    margin-bottom: 1rem;
    opacity: 0.5;
  }

  @media (max-width: 900px) {
    .prompts-grid {
      grid-template-columns: 1fr;
    }
    .prompt-card.wide {
      grid-column: span 1;
    }
  }
</style>
