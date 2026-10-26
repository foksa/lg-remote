<script>
  import { onMount } from 'svelte';
  import { ui, native } from './state.svelte.js';
  import { showKey, pair, discover, chooseTv } from './api.js';

  let code = $state('');
  let manualIp = $state(ui.tvIp);
  let searching = $state(false);
  let searched = $state(false);
  let found = $state([]);
  let input;

  async function search() {
    searching = true;
    found = await discover();
    searching = false;
    searched = true;
    if (found.length === 1 && !ui.tvIp) pick(found[0]);
  }

  function pick(tv) {
    chooseTv(tv.ip, tv.model);
    manualIp = tv.ip;
  }

  function useManual(e) {
    e.preventDefault();
    const ip = manualIp.trim();
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(ip)) pick({ ip, model: '' });
  }

  async function show() { if (await showKey()) input?.focus(); }
  async function submit(e) {
    e.preventDefault();
    if (code.trim() && (await pair(code.trim()))) { code = ''; input?.blur(); }
  }

  onMount(() => { if (native && !ui.tvIp) search(); });
</script>

<div class="setup">
  <div class="card">
    {#if native}
      <section>
        <h2>Your TV</h2>
        {#if ui.tvIp}
          <p class="current">{ui.tvModel || 'LG TV'} <span>{ui.tvIp}</span></p>
        {:else}
          <p>Turn the TV on and make sure the phone is on the same Wi-Fi.</p>
        {/if}

        <button type="button" class="wide" onclick={search} disabled={searching}>
          {#if searching}<span class="spinner"></span> Searching…{:else}Search for TVs{/if}
        </button>

        {#if found.length}
          <ul>
            {#each found as tv}
              <li>
                <button type="button" class="row" class:selected={tv.ip === ui.tvIp} onclick={() => pick(tv)}>
                  <span>{tv.model}</span><span class="ip">{tv.ip}</span>
                </button>
              </li>
            {/each}
          </ul>
        {:else if searched && !searching}
          <p class="hint">No LG TV found. Is it on? You can also type its address below.</p>
        {/if}

        <form class="manual" onsubmit={useManual}>
          <input bind:value={manualIp} inputmode="decimal" placeholder="192.168.1.x" autocomplete="off" spellcheck="false">
          <button type="submit">Use</button>
        </form>
      </section>
    {/if}

    <section class:disabled={native && !ui.tvIp}>
      <h2>Pair</h2>
      <p>Tap <b>Show code</b>, then type the code that appears on the TV screen.</p>
      <form onsubmit={submit}>
        <input class="code" bind:this={input} bind:value={code} autocomplete="off" autocapitalize="characters"
               spellcheck="false" maxlength="8" placeholder="······">
        <div class="actions">
          <button type="button" onclick={show}>Show code</button>
          <button type="submit" class="primary">Pair</button>
        </div>
      </form>
    </section>

    <button type="button" class="link" onclick={() => (ui.pairing = false)}>Close</button>
  </div>
</div>

<style>
  .setup { position: fixed; inset: 0; z-index: 10; background: var(--bg); overflow-y: auto; scrollbar-width: none;
           display: flex; justify-content: center; padding: calc(env(safe-area-inset-top) + 24px) 20px calc(env(safe-area-inset-bottom) + 24px); }
  .card { width: 100%; max-width: 380px; display: flex; flex-direction: column; gap: 28px; margin: auto 0; }
  section { display: flex; flex-direction: column; gap: 12px; transition: opacity .2s; }
  section.disabled { opacity: .35; pointer-events: none; }
  h2 { margin: 0; font-size: 20px; }
  p { margin: 0; color: var(--muted); line-height: 1.45; }
  .current { color: var(--fg); font-weight: 500; }
  .current span, .ip { color: var(--muted); font-weight: 400; margin-left: 6px; }
  .hint { font-size: 14px; }

  input { width: 100%; height: 52px; border-radius: 14px; border: 1px solid var(--line); background: var(--surface);
          color: var(--fg); font-size: 18px; padding: 0 14px; user-select: text; -webkit-user-select: text; outline: none; }
  input:focus { border-color: #555; }
  .code { height: 60px; font-size: 28px; text-align: center; letter-spacing: .3em; text-transform: uppercase; margin-bottom: 10px; }

  .wide { width: 100%; }
  button:disabled { opacity: .7; }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
  .row { width: 100%; justify-content: space-between; padding: 0 16px; background: var(--surface);
         box-shadow: inset 0 0 0 1px var(--line); }
  .row.selected { box-shadow: inset 0 0 0 2px var(--ok); }
  .manual { display: grid; grid-template-columns: 1fr auto; gap: 10px; }
  .manual button { padding: 0 20px; }
  .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .primary { background: var(--fg); color: var(--bg); font-weight: 600; }
  .link { align-self: center; background: none; box-shadow: none; color: var(--muted); height: 40px; padding: 0 16px; }

  .spinner { width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--muted); border-top-color: var(--fg);
             animation: spin .8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
