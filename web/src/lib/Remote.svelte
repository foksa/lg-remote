<script>
  import Key from './Key.svelte';
  import { power } from './api.js';
</script>

<div class="remote">
  <div class="grid g3">
    <Key icon="power" label="Power" class="power" hold holdHint="Hold to turn off" onpress={power} />
    <Key icon="input" label="Input" code={47}>Input</Key>
    <Key icon="settings" label="Settings" code={22} />
  </div>

  <div class="dpad">
    <Key icon="up" label="Up" class="up" code={12} repeat />
    <Key icon="left" label="Left" class="left" code={14} repeat />
    <Key label="OK" class="ok" code={20}>OK</Key>
    <Key icon="right" label="Right" class="right" code={15} repeat />
    <Key icon="down" label="Down" class="down" code={13} repeat />
  </div>

  <div class="grid g3">
    <Key icon="back" label="Back" code={23} />
    <Key icon="home" label="Home" code={21} />
    <Key label="Exit" code={412}>Exit</Key>
  </div>

  <div class="rockers">
    <div class="rocker">
      <Key icon="plus" label="Volume up" code={24} repeat />
      <span>VOL</span>
      <Key icon="minus" label="Volume down" code={25} repeat />
    </div>
    <div class="mid">
      <Key icon="mute" label="Mute" code={26} />
      <Key label="Info" code={45}>Info</Key>
    </div>
    <div class="rocker">
      <Key icon="up" label="Channel up" code={27} repeat />
      <span>CH</span>
      <Key icon="down" label="Channel down" code={28} repeat />
    </div>
  </div>

  <div class="grid g5 playback">
    <Key icon="rew" label="Rewind" code={37} />
    <Key icon="play" label="Play" code={33} />
    <Key icon="pause" label="Pause" code={34} />
    <Key icon="stop" label="Stop" code={35} />
    <Key icon="ff" label="Fast forward" code={36} />
  </div>
</div>

<style>
  .remote { height: 100%; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; }
  .g3 { grid-template-columns: repeat(3, 1fr); }
  .g5 { grid-template-columns: repeat(5, 1fr); gap: 8px; }

  /* Power: fill bar shows hold progress. */
  .remote :global(.power) { position: relative; overflow: hidden; color: #ffb4b6; }
  .remote :global(.power)::after { content: ''; position: absolute; inset: 0; background: var(--accent); opacity: .35;
                                   transform: scaleX(0); transform-origin: left; }
  .remote :global(.power.holding)::after { transform: scaleX(1); transition: transform .6s linear; }

  .dpad { position: relative; width: min(76vw, 300px, 36dvh); aspect-ratio: 1; margin: 0 auto; border-radius: 50%;
          background: var(--surface); box-shadow: inset 0 0 0 1px var(--line); }
  .dpad :global(button) { position: absolute; height: auto; background: transparent; box-shadow: none;
                          color: var(--muted); border-radius: 22px; }
  .dpad :global(button.hit) { background: rgba(255, 255, 255, .07); color: var(--fg); transform: none; }
  .dpad :global(.up)    { top: 4%; left: 30%; width: 40%; height: 26%; }
  .dpad :global(.down)  { bottom: 4%; left: 30%; width: 40%; height: 26%; }
  .dpad :global(.left)  { left: 4%; top: 30%; width: 26%; height: 40%; }
  .dpad :global(.right) { right: 4%; top: 30%; width: 26%; height: 40%; }
  .dpad :global(.ok) { top: 31%; left: 31%; width: 38%; height: 38%; border-radius: 50%; background: var(--btn-hi);
                       color: var(--fg); font-weight: 600; font-size: 17px;
                       box-shadow: 0 4px 14px rgba(0, 0, 0, .4), inset 0 1px 0 rgba(255, 255, 255, .07); }
  .dpad :global(.ok.hit) { background: var(--press); transform: scale(.96); }

  .rockers { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  .rocker { display: flex; flex-direction: column; background: var(--btn); border-radius: 20px; overflow: hidden;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05); }
  .rocker :global(button) { background: transparent; box-shadow: none; border-radius: 0; height: 54px; }
  .rocker :global(button.hit) { background: var(--press); transform: none; }
  .rocker span { text-align: center; font-size: 11px; letter-spacing: .08em; color: var(--muted); padding: 2px 0; }
  .mid { display: flex; flex-direction: column; gap: 10px; justify-content: center; }
  .mid :global(button) { height: 54px; }

  .playback :global(button) { height: 46px; border-radius: 14px; }
</style>
