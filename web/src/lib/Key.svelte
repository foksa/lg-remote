<script>
  import { press } from './press.js';
  import { sendKey } from './api.js';
  import Icon from './Icon.svelte';

  // code: TV key code to send, or pass onpress for custom behaviour.
  let { code = null, icon = null, label = '', repeat = false, hold = false, holdHint = '', onpress = null, class: cls = '', children } = $props();

  const handle = () => (onpress ? onpress() : sendKey(code));
</script>

<button class={cls} aria-label={label} title={label} use:press={{ onpress: handle, repeat, hold, holdHint }}>
  {#if icon}<Icon name={icon} />{/if}
  {#if children}{@render children()}{/if}
</button>
