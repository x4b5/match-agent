<script lang="ts">
  import favicon from "$lib/assets/favicon.svg";
  import Toast from "$lib/Toast.svelte";
  import "../app.css";
  import { page } from "$app/state";

  let { children } = $props();

  const hour = new Date().getHours();
  const greeting =
    hour < 12
      ? "☀️ Goedemorgen"
      : hour < 18
        ? "👋 Goedemiddag"
        : "🌙 Goedenavond";
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <link
    href="https://fonts.googleapis.com/icon?family=Material+Icons"
    rel="stylesheet"
  />
</svelte:head>

<div class="app-container">
  <aside class="sidebar">
    <div class="sidebar-brand">
      <h1 class="brand-logo">
        <span style="color: var(--neon-cyan);">MATCH</span>FLIX
      </h1>
      <p class="brand-tagline">De mismatch die raak is!</p>
      <p class="brand-greeting">{greeting}</p>
    </div>

    <nav style="display: flex; flex-direction: column; gap: 0.5rem;">
      <a href="/" class="nav-link nav-cyan {page.url.pathname === '/' ? 'active' : ''}">
        <span class="material-icons">bar_chart</span> Dashboard
      </a>
      <a
        href="/generator"
        id="nav-profiel-generator"
        class="nav-link nav-green {page.url.pathname.startsWith('/generator') ? 'active' : ''}"
      >
        <span class="material-icons">shield</span> Profiel Generator
      </a>
      <a
        href="/candidates"
        class="nav-link nav-blue {page.url.pathname.startsWith('/candidates')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">group</span> Kandidaten
      </a>
      <a
        href="/employers"
        class="nav-link nav-purple {page.url.pathname.startsWith('/employers')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">business</span> Werkgeversvragen
      </a>
      <a
        href="/match"
        class="nav-link nav-gold {page.url.pathname === '/match' ? 'active' : ''}"
      >
        <span class="material-icons">gps_fixed</span> Matchen
      </a>
      <a
        href="/history"
        class="nav-link nav-pink {page.url.pathname.startsWith('/history')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">history</span> Historie
      </a>
      <hr
        style="border: 0; height: 1px; background: var(--glass-border); margin: 0.5rem 0;"
      />
      <a
        href="/over"
        class="nav-link nav-cyan {page.url.pathname.startsWith('/over') ? 'active' : ''}"
      >
        <span class="material-icons">info</span> Over MATCHFLIX
      </a>
      <a
        href="/prompts"
        class="nav-link nav-gold {page.url.pathname.startsWith('/prompts')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">code</span> Prompts & Openheid
      </a>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-footer-badge">
        <span
          class="material-icons"
          style="font-size: 0.9rem; color: var(--neon-green);"
          >verified_user</span
        >
        Privacy-First & AVG-Proof
      </div>
      <div
        style="font-size: 0.6rem; color: rgba(255,255,255,0.2); margin-top: 6px;"
      >
        v0.1.0 — powered by Ollama
      </div>
    </div>
  </aside>

  <main class="main-content">
    {@render children()}
  </main>
</div>

<Toast />

<style>
  .sidebar-brand {
    margin-bottom: 2rem;
    padding: 0.5rem 10px;
  }
  .brand-logo {
    margin: 0;
    font-size: 1.5rem;
    letter-spacing: 2px;
    transition: text-shadow 0.4s ease;
  }
  .brand-logo:hover {
    text-shadow:
      0 0 20px rgba(0, 229, 255, 0.4),
      0 0 40px rgba(0, 229, 255, 0.15);
  }
  .brand-tagline {
    margin: 5px 0 0 0;
    font-size: 0.65rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .brand-greeting {
    margin: 10px 0 0 0;
    font-size: 0.85rem;
    color: var(--text-primary);
    font-weight: 500;
    opacity: 0.8;
  }
  .sidebar-footer {
    margin-top: auto;
    padding: 1rem;
    text-align: center;
    border-top: 1px solid var(--glass-border);
  }
  .sidebar-footer-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.65rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
  }
</style>
