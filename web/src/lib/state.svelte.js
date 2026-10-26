import { Capacitor } from '@capacitor/core';

// In the Android app the phone talks to the TV itself; in a browser it goes through the Pi server.
export const native = Capacitor.isNativePlatform();

function load(key, fallback = '') {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
export function save(key, value) {
  try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch {}
}

export const ui = $state({
  dot: '',          // '' | 'ok' | 'err'
  toast: '',
  pairing: false,   // setup / pairing screen open
  tvIp: load('tvIp'),
  tvModel: load('tvModel'),
});

let toastTimer;
export function toast(msg) {
  ui.toast = msg;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (ui.toast = ''), 1800);
}
