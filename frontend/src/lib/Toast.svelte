<script lang="ts">
  import { toasts } from "./toast";
  import { fly, fade } from "svelte/transition";

  const iconMap: Record<string, string> = {
    success: "check_circle",
    error: "error",
    warning: "warning",
    info: "info",
  };
</script>

<div class="toast-container">
  {#each $toasts as toast (toast.id)}
    <div
      class="toast toast-{toast.type}"
      in:fly={{ x: 320, duration: 400, easing: (t) => 1 - Math.pow(1 - t, 3) }}
      out:fade={{ duration: 250 }}
    >
      <span class="material-icons toast-icon">{iconMap[toast.type]}</span>
      <span class="toast-msg">{toast.message}</span>
      <button class="toast-close" onclick={() => toasts.remove(toast.id)}>
        <span class="material-icons" style="font-size: 1rem;">close</span>
      </button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 1.5rem;
    right: 1.5rem;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    pointer-events: none;
    max-width: 420px;
  }

  .toast {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1.2rem;
    border-radius: 12px;
    backdrop-filter: blur(24px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.03);
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-primary);
    font-family: "Space Grotesk", sans-serif;
  }

  .toast-success {
    background: rgba(0, 230, 118, 0.12);
    border-color: rgba(0, 230, 118, 0.3);
  }
  .toast-success .toast-icon {
    color: #00e676;
  }

  .toast-error {
    background: rgba(255, 82, 82, 0.12);
    border-color: rgba(255, 82, 82, 0.3);
  }
  .toast-error .toast-icon {
    color: #ff5252;
  }

  .toast-warning {
    background: rgba(255, 171, 0, 0.12);
    border-color: rgba(255, 171, 0, 0.3);
  }
  .toast-warning .toast-icon {
    color: #ffab00;
  }

  .toast-info {
    background: rgba(0, 229, 255, 0.1);
    border-color: rgba(0, 229, 255, 0.25);
  }
  .toast-info .toast-icon {
    color: #00e5ff;
  }

  .toast-icon {
    font-size: 1.3rem;
    flex-shrink: 0;
  }
  .toast-msg {
    flex: 1;
    line-height: 1.4;
  }

  .toast-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.35);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
    transition: color 0.2s;
    flex-shrink: 0;
  }
  .toast-close:hover {
    color: var(--text-primary);
  }
</style>
