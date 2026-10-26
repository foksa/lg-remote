<script>
  import { onMount } from 'svelte';
  import Remote from './lib/Remote.svelte';
  import Numbers from './lib/Numbers.svelte';
  import Guide from './lib/Guide.svelte';
  import Pair from './lib/Pair.svelte';
  import { ui } from './lib/state.svelte.js';
  import { checkState } from './lib/api.js';

  const pages = ['Remote', 'Numbers', 'Guide'];
  let pager;
  let current = 0;          // settled page, kept in sync with history
  let progress = $state(0); // live scroll position in pages, drives the tab indicator
  let settleTimer;

  const width = () => pager.clientWidth || 1;
  const scrollToPage = (i, smooth = true) => pager.scrollTo({ left: i * width(), behavior: smooth ? 'smooth' : 'instant' });

  /* History: the Remote page is the base entry; any other page sits one entry above it,
     so the phone's back gesture returns to Remote, and back on Remote leaves the app. */
  function settle() {
    const i = Math.round(pager.scrollLeft / width());
    if (i === current) return;
    if (current === 0) history.pushState({ page: i }, '');
    else if (i === 0) history.back();
    else history.replaceState({ page: i }, '');
    current = i;
  }

  function onScroll() {
    progress = pager.scrollLeft / width();
    clearTimeout(settleTimer);
    settleTimer = setTimeout(settle, 120);
  }

  function onPopState(e) {
    const s = e.state || {};
    if (!s.pair && ui.pairing) ui.pairing = false;
    const p = s.page ?? 0;
    if (p !== current) { current = p; scrollToPage(p); }
  }

  // Back gesture closes the pairing screen too.
  $effect(() => {
    if (ui.pairing && !history.state?.pair) history.pushState({ page: current, pair: true }, '');
    else if (!ui.pairing && history.state?.pair) history.back();
  });

  onMount(() => {
    history.replaceState({ page: 0 }, '');
    const onResize = () => scrollToPage(current, false);
    window.addEventListener('resize', onResize);
    checkState();
    return () => window.removeEventListener('resize', onResize);
  });
</script>

<svelte:window onpopstate={onPopState} />

<div class="app">
  <header>
    <span class="dot {ui.dot}" title="Connection"></span>
    <nav class="tabs" style="--n: {pages.length}">
      {#each pages as name, i}
        <button class="tab" class:active={Math.round(progress) === i} onclick={() => scrollToPage(i)}>{name}</button>
      {/each}
      <span class="indicator" style="transform: translateX({progress * 100}%)"></span>
    </nav>
    <span class="spacer"></span>
  </header>

  <main class="pager" bind:this={pager} onscroll={onScroll}>
    <section class="page"><Remote /></section>
    <section class="page"><Numbers /></section>
    <section class="page"><Guide /></section>
  </main>
</div>

{#if ui.pairing}<Pair />{/if}

<div class="toast" class:show={ui.toast}>{ui.toast}</div>

<style>
  .app { height: 100%; display: flex; flex-direction: column; max-width: 440px; margin: 0 auto;
         padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom); }

  header { display: flex; align-items: center; gap: 12px; padding: 10px 18px 4px; }
  .dot, .spacer { width: 8px; flex: none; }
  .dot { height: 8px; border-radius: 50%; background: var(--muted); transition: background .2s; }
  .dot.ok { background: var(--ok); }
  .dot.err { background: var(--accent); }

  .tabs { position: relative; flex: 1; display: grid; grid-template-columns: repeat(var(--n), 1fr);
          background: var(--surface); border-radius: 12px; padding: 3px; }
  .tab { position: relative; z-index: 1; height: 34px; background: none; box-shadow: none; border-radius: 9px;
         color: var(--muted); font-size: 14px; font-weight: 500; transition: color .15s; }
  .tab.active { color: var(--fg); }
  .indicator { position: absolute; top: 3px; bottom: 3px; left: 3px; width: calc((100% - 6px) / var(--n));
               background: var(--btn-hi); border-radius: 9px; }

  .pager { flex: 1; min-height: 0; display: flex; overflow-x: auto; overflow-y: hidden;
           scroll-snap-type: x mandatory; overscroll-behavior: contain; scrollbar-width: none; }
  .pager::-webkit-scrollbar { display: none; }
  .page { flex: 0 0 100%; min-width: 0; scroll-snap-align: start; scroll-snap-stop: always;
          touch-action: pan-x; padding: 12px 18px 14px; }

  .toast { position: fixed; left: 50%; bottom: calc(env(safe-area-inset-bottom) + 24px); z-index: 20;
           transform: translate(-50%, 20px); background: #2a2a2f; color: var(--fg); padding: 10px 16px; border-radius: 12px;
           font-size: 14px; opacity: 0; transition: opacity .2s, transform .2s; pointer-events: none; white-space: nowrap; }
  .toast.show { opacity: 1; transform: translate(-50%, 0); }
</style>
