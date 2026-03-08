<script lang="ts">
  import favicon from "$lib/assets/favicon.svg";
  import "../app.css";
  import { page } from "$app/state";

  let { children } = $props();
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
    <div style="margin-bottom: 2rem; padding-left: 10px;">
      <h1 style="margin: 0; font-size: 1.5rem; letter-spacing: 2px;">
        <span style="color: var(--neon-cyan);">MATCH</span>FLIX
      </h1>
      <p
        style="margin: 5px 0 0 0; font-size: 0.65rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;"
      >
        Agent Kompas
      </p>
    </div>

    <nav style="display: flex; flex-direction: column; gap: 0.5rem;">
      <a href="/" class="nav-link {page.url.pathname === '/' ? 'active' : ''}">
        <span class="material-icons">bar_chart</span> Dashboard
      </a>
      <a
        href="/candidates"
        class="nav-link {page.url.pathname.startsWith('/candidates')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">group</span> Kandidaten
      </a>
      <a
        href="/employers"
        class="nav-link {page.url.pathname.startsWith('/employers')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">business</span> Werkgeversvragen
      </a>
      <a
        href="/match"
        class="nav-link {page.url.pathname.startsWith('/match')
          ? 'active'
          : ''}"
      >
        <span class="material-icons">gps_fixed</span> Match Starten
      </a>
      <a
        href="/history"
        class="nav-link {page.url.pathname.startsWith('/history')
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
        class="nav-link {page.url.pathname.startsWith('/over') ? 'active' : ''}"
      >
        <span class="material-icons">info</span> Over MATCHFLIX
      </a>
    </nav>

    <div
      style="margin-top: auto; padding: 1rem; text-align: center; border-top: 1px solid var(--glass-border);"
    >
      <div
        style="font-size: 0.65rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;"
      >
        100% Lokaal & AVG-Proof
      </div>
    </div>
  </aside>

  <main class="main-content">
    {@render children()}
  </main>
</div>
