<script>
  import Key from './Key.svelte';
  import { ui, native } from './state.svelte.js';

  const digits = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  // UDAP key codes: digit n is n + 2.
  const codeFor = (n) => n + 2;
</script>

<div class="numbers">
  <div class="grid g3 keypad">
    {#each digits as n}
      <Key label={String(n)} code={codeFor(n)}>{n}</Key>
    {/each}
    <Key label="Previous channel" code={403} class="small">Prev</Key>
    <Key label="0" code={codeFor(0)}>0</Key>
    <Key label="OK" code={20} class="ok">OK</Key>
  </div>

  <div>
    <h3>More</h3>
    <div class="grid g3 extras">
      <Key label="Quick menu" code={405}>Q.Menu</Key>
      <Key label="Aspect ratio" code={46}>Ratio</Key>
      <Key label="AV mode" code={410}>AV mode</Key>
      <Key label="Apps" code={408}>Apps</Key>
      <Key label="TV's own guide" code={44}>TV EPG</Key>
      <Key label="TV setup" onpress={() => (ui.pairing = true)}>{native ? 'TV setup' : 'Pair'}</Key>
    </div>
  </div>
</div>

<style>
  .numbers { height: 100%; display: flex; flex-direction: column; gap: 28px; }
  .g3 { grid-template-columns: repeat(3, 1fr); }
  .keypad :global(button) { height: clamp(52px, 9dvh, 76px); font-size: 24px; font-weight: 500; }
  .keypad :global(button.small) { font-size: 15px; color: var(--muted); }
  .keypad :global(button.ok) { font-size: 17px; font-weight: 600; background: var(--fg); color: var(--bg); }
  .keypad :global(button.ok.hit) { background: #d4d4d8; }
  .extras :global(button) { height: 48px; font-size: 14px; }
  h3 { margin: 0 2px 10px; font-size: 12px; font-weight: 600; letter-spacing: .08em; color: var(--muted); text-transform: uppercase; }
</style>
