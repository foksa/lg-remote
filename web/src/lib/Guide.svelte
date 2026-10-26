<script>
  import { onMount } from 'svelte';
  import { press } from './press.js';
  import { loadGuide, currentChannel, tuneTo } from './api.js';
  import { toast } from './state.svelte.js';

  const GUIDE_REFRESH = 15 * 60 * 1000;
  const CURRENT_REFRESH = 20 * 1000;

  let channels = $state([]);
  let loading = $state(true);
  let failed = $state(false);
  let query = $state('');
  let open = $state(null);        // channel number whose details are expanded
  let current = $state({});       // what the TV is showing: {num, name, prog}
  let now = $state(Date.now() / 1000);

  const time = (s) => new Date(s * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  const progress = (p) => Math.min(100, Math.max(0, ((now - p.s) / (p.e - p.s)) * 100));

  function nowAndNext(ch) {
    const p = ch.p ?? [];
    const i = p.findIndex((x) => x.e > now);
    return i < 0 ? [null, null] : [p[i].s <= now ? p[i] : null, p[p[i].s <= now ? i + 1 : i] ?? null];
  }
  const upcoming = (ch) => (ch.p ?? []).filter((p) => p.e > now).slice(0, 8);

  // Every channel is listed; ones without guide data just show their name.
  const listed = $derived.by(() => {
    const q = query.trim().toLowerCase();
    return channels.filter((c) => !q || c.name.toLowerCase().includes(q) || String(c.num).startsWith(q));
  });

  async function refreshGuide() {
    const data = await loadGuide();
    if (data?.channels) { channels = data.channels; failed = false; }
    else if (!channels.length) failed = true;
    loading = false;
  }
  async function refreshCurrent() {
    if (document.visibilityState !== 'visible') return;
    const c = await currentChannel();
    if (c.num) current = c;
  }

  async function watch(ch) {
    if (await tuneTo(ch.num)) {
      toast(`Switching to ${ch.num} ${ch.name}`);
      current = { ...current, num: ch.num, name: ch.name };
      setTimeout(refreshCurrent, 3000);
    }
  }

  onMount(() => {
    refreshGuide();
    refreshCurrent();
    const timers = [
      setInterval(() => (now = Date.now() / 1000), 30 * 1000),
      setInterval(refreshGuide, GUIDE_REFRESH),
      setInterval(refreshCurrent, CURRENT_REFRESH),
    ];
    const onVisible = () => { if (document.visibilityState === 'visible') { now = Date.now() / 1000; refreshCurrent(); } };
    document.addEventListener('visibilitychange', onVisible);
    return () => { timers.forEach(clearInterval); document.removeEventListener('visibilitychange', onVisible); };
  });
</script>

<div class="guide">
  <input class="search" type="search" bind:value={query} placeholder="Search channels" autocomplete="off" spellcheck="false">

  {#if current.num}
    <div class="on-tv">
      <span class="label">On TV</span>
      <span class="num">{current.num}</span>
      <span class="what">{current.name}{current.prog ? ` · ${current.prog}` : ''}</span>
    </div>
  {/if}

  <div class="list">
    {#if loading}
      <p class="empty">Loading guide…</p>
    {:else if failed}
      <p class="empty">Couldn’t load the guide. It comes from the Pi (pi.lan), so check that it’s on.</p>
    {:else if !listed.length}
      <p class="empty">No channels match “{query}”.</p>
    {/if}

    {#each listed as ch (ch.num)}
      {@const [cur, next] = nowAndNext(ch)}
      {@const hasGuide = !!ch.p?.length}
      {@const playing = ch.num === current.num}
      <div class="row" class:playing class:open={open === ch.num}>
        <button class="summary" class:bare={!hasGuide} use:press={{ onpress: () => (open = open === ch.num ? null : ch.num) }}>
          <span class="num">{ch.num}</span>
          <span class="body">
            {#if hasGuide}
              <span class="name">{ch.name}</span>
              <span class="title">{cur ? cur.t : 'No show now'}</span>
              {#if cur}<span class="bar"><span style="width: {progress(cur)}%"></span></span>{/if}
              {#if next}<span class="next">{time(next.s)} {next.t}</span>{/if}
            {:else}
              <span class="title">{ch.name}</span>
              <!-- No guide, but the TV itself knows the current show's title. -->
              <span class="next">{playing && current.prog ? current.prog : 'No guide'}</span>
            {/if}
          </span>
          {#if cur?.i}<img src={cur.i} alt="" loading="lazy" onerror={(e) => (e.currentTarget.style.visibility = 'hidden')}>{/if}
        </button>

        {#if open === ch.num}
          <div class="details">
            {#if cur?.d}<p class="desc">{cur.d}</p>{/if}
            {#if hasGuide}
              <ul>
                {#each upcoming(ch) as p}
                  <li class:now={p.s <= now}>
                    <span class="t">{time(p.s)}</span>
                    <span class="pt">{p.t}{#if p.c}<small>{p.c}</small>{/if}</span>
                  </li>
                {/each}
              </ul>
            {/if}
            <button class="watch" use:press={{ onpress: () => watch(ch) }}>
              {ch.num === current.num ? 'Watching' : `Watch ${ch.name}`}
            </button>
          </div>
        {/if}
      </div>
    {/each}
  </div>
</div>

<style>
  .guide { height: 100%; display: flex; flex-direction: column; gap: 10px; }
  .search { width: 100%; height: 44px; flex: none; border-radius: 12px; border: 1px solid var(--line); background: var(--surface);
            color: var(--fg); font-size: 16px; padding: 0 14px; outline: none; user-select: text; -webkit-user-select: text; }
  .search:focus { border-color: #555; }

  .on-tv { display: flex; align-items: center; gap: 8px; flex: none; font-size: 14px; padding: 0 2px; min-width: 0; }
  .on-tv .label { flex: none; white-space: nowrap; color: var(--ok); font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
  .on-tv .num { flex: none; color: var(--muted); }
  .on-tv .what { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* The list scrolls vertically; sideways swipes must still reach the pager, so contain only the y axis. */
  .list { flex: 1; min-height: 0; overflow-y: auto; touch-action: pan-x pan-y; overscroll-behavior-y: contain;
          display: flex; flex-direction: column; gap: 8px; padding-bottom: 8px; }

  .row { background: var(--surface); border-radius: 14px; box-shadow: inset 0 0 0 1px var(--line); flex: none; }
  .row.playing { box-shadow: inset 0 0 0 2px var(--ok); }

  .summary { width: 100%; height: auto; min-height: 72px; padding: 10px 12px; background: none; box-shadow: none;
             justify-content: flex-start; align-items: flex-start; gap: 12px; text-align: left; border-radius: 14px; }
  .summary:global(.hit) { background: rgba(255, 255, 255, .04); transform: none; }
  .summary.bare { min-height: 56px; align-items: center; }
  .summary.bare .num { padding-top: 0; }
  .num { flex: none; min-width: 34px; color: var(--muted); font-size: 14px; font-variant-numeric: tabular-nums; padding-top: 1px; }
  .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
  .name { font-size: 12px; color: var(--muted); }
  .title { font-size: 15px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bar { height: 3px; border-radius: 2px; background: var(--line); overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--fg); opacity: .7; }
  .next { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  img { flex: none; width: 72px; height: 41px; object-fit: cover; border-radius: 6px; background: var(--btn); align-self: center; }

  .details { padding: 0 12px 12px 58px; display: flex; flex-direction: column; gap: 10px; }
  .desc { margin: 0; font-size: 13px; line-height: 1.45; color: #c9c9cf; }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  li { display: flex; gap: 10px; font-size: 13px; color: var(--muted); }
  li.now { color: var(--fg); }
  .t { flex: none; width: 42px; font-variant-numeric: tabular-nums; }
  .pt { min-width: 0; }
  .pt small { margin-left: 6px; color: var(--muted); font-size: 11px; }
  .watch { height: 44px; background: var(--fg); color: var(--bg); font-weight: 600; margin-top: 2px; }

  .empty { margin: 24px 8px; text-align: center; color: var(--muted); line-height: 1.45; }
</style>
