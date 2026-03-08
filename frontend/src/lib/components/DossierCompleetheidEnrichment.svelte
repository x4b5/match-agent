<script lang="ts">
  import { toasts } from "$lib/toast";

  let {
    questions = [],
    name,
    docType,
    onSuccess,
  } = $props<{
    questions: string[];
    name: string;
    docType: "candidates" | "employers";
    onSuccess?: (newData: any) => void;
  }>();

  let answers: Record<string, string> = $state({});
  let isEnriching = $state(false);

  // Initialize answers for all questions
  $effect(() => {
    questions.forEach((q: string) => {
      if (!(q in answers)) {
        answers[q] = "";
      }
    });
  });

  async function submitAnswers() {
    const formattedAnswers = Object.fromEntries(
      Object.entries(answers).filter(([_, val]) => val.trim() !== ""),
    );

    if (Object.keys(formattedAnswers).length === 0) {
      toasts.add("Beantwoord ten minste één vraag", "warning");
      return;
    }

    isEnriching = true;
    try {
      const res = await fetch(
        `/api/${docType}/${encodeURIComponent(name)}/enrich`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ antwoorden: formattedAnswers }),
        },
      );

      if (res.ok) {
        const result = await res.json();
        toasts.add("Profiel succesvol verrijkt!", "success");
        // Clear answers
        answers = {};
        if (onSuccess) onSuccess(result);
      } else {
        const err = await res.json();
        toasts.add(err.detail || "Fout bij verrijken profiel", "error");
      }
    } catch (e) {
      toasts.add("Netwerkfout bij verrijken profiel", "error");
    } finally {
      isEnriching = false;
    }
  }

  const hasAnswers = $derived(
    Object.values(answers).some((a) => a.trim() !== ""),
  );
</script>

<div class="enrichment-container">
  <div class="detail-section-title">
    <span class="material-icons">psychology</span> Verbeter Dossiercompleetheid
  </div>
  <p class="enrichment-intro">
    De AI heeft extra informatie nodig om een betere match te kunnen maken.
    Beantwoord één of meer van de onderstaande vragen:
  </p>

  <div class="questions-list">
    {#each questions as question, i}
      <div class="question-item">
        <label for="q-{i}" class="input-label">{question}</label>
        <textarea
          id="q-{i}"
          class="input-field enrichment-textarea"
          placeholder="Typ hier je antwoord..."
          bind:value={answers[question]}
          disabled={isEnriching}
        ></textarea>
      </div>
    {/each}
  </div>

  <div class="enrichment-actions">
    <button
      class="btn-primary"
      onclick={submitAnswers}
      disabled={isEnriching || !hasAnswers}
    >
      {#if isEnriching}
        <span class="material-icons spin">autorenew</span> Bezig met verwerken...
      {:else}
        <span class="material-icons">send</span> Verstuur antwoorden
      {/if}
    </button>
  </div>
</div>

<style>
  .enrichment-container {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px dashed var(--glass-border);
  }

  .enrichment-intro {
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
    color: var(--text-secondary);
  }

  .questions-list {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .question-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .enrichment-textarea {
    min-height: 80px;
    resize: vertical;
    font-size: 0.9rem;
    background: rgba(0, 0, 0, 0.2);
  }

  .enrichment-actions {
    display: flex;
    justify-content: flex-end;
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    filter: grayscale(1);
    transform: none !important;
    box-shadow: none !important;
  }
</style>
