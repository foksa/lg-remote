import { toast } from './state.svelte.js';

const MOVE_TOLERANCE = 10;   // px a finger may drift before the touch counts as a swipe
const REPEAT_DELAY = 400;
const REPEAT_EVERY = 160;
const HOLD_MS = 600;

/**
 * Svelte action for remote buttons.
 * A tap fires on release, and only if the finger didn't move, so swiping between pages never presses anything.
 * `repeat`: holding fires repeatedly. `hold`: fires only after a long press (power).
 */
export function press(node, opts) {
  let o = opts;
  let start = null, timer = null, interval = null, cancelled = false, done = false;

  const fire = () => o.onpress?.();
  const clear = () => {
    clearTimeout(timer); clearInterval(interval);
    timer = interval = null;
    node.classList.remove('hit', 'holding');
  };

  function down(e) {
    if (e.button > 0) return;
    start = { x: e.clientX, y: e.clientY };
    cancelled = done = false;
    node.classList.add('hit');
    if (o.hold) {
      node.classList.add('holding');
      timer = setTimeout(() => { done = true; clear(); fire(); }, HOLD_MS);
    } else if (o.repeat) {
      timer = setTimeout(() => { done = true; fire(); interval = setInterval(fire, REPEAT_EVERY); }, REPEAT_DELAY);
    }
  }
  function move(e) {
    if (!start || cancelled) return;
    if (Math.hypot(e.clientX - start.x, e.clientY - start.y) > MOVE_TOLERANCE) { cancelled = true; clear(); }
  }
  function up() {
    if (!start) return;
    clear();
    if (!cancelled && !done) {
      if (o.hold) toast(o.holdHint || 'Hold to confirm');
      else fire();
    }
    start = null;
  }
  function cancel() { cancelled = true; clear(); start = null; }   // browser took the gesture for swiping
  const noMenu = (e) => e.preventDefault();

  node.addEventListener('pointerdown', down);
  node.addEventListener('pointermove', move);
  node.addEventListener('pointerup', up);
  node.addEventListener('pointercancel', cancel);
  node.addEventListener('contextmenu', noMenu);

  return {
    update(next) { o = next; },
    destroy() {
      clear();
      node.removeEventListener('pointerdown', down);
      node.removeEventListener('pointermove', move);
      node.removeEventListener('pointerup', up);
      node.removeEventListener('pointercancel', cancel);
      node.removeEventListener('contextmenu', noMenu);
    },
  };
}
