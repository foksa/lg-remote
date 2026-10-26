import { registerPlugin } from '@capacitor/core';
import { ui, toast, native, save } from './state.svelte.js';

/* Two backends with the same shape:
   - native: the Android app sends UDAP requests to the TV through the Tv plugin.
   - server: the browser asks the Pi's server.py to do it. */

const Tv = native ? registerPlugin('Tv') : null;
const KEY = 'pairingKey';

const envelope = (api) => `<?xml version="1.0" encoding="utf-8"?><envelope>${api}</envelope>`;

const nativeBackend = {
  async udap(path, api) {
    if (!ui.tvIp) return 0;
    const { status } = await Tv.send({ ip: ui.tvIp, path, body: envelope(api) });
    return status;
  },
  hello(key) {
    return this.udap('pairing', `<api type="pairing"><name>hello</name><value>${key}</value><port>8080</port></api>`);
  },
  command(code) {
    return this.udap('command', `<api type="command"><name>HandleKeyInput</name><value>${code}</value></api>`);
  },
  async key(code) {
    let status = await this.command(code);
    // 401: the TV forgot us (it does after a restart); say hello again with the saved key and retry.
    const saved = localStorage.getItem(KEY);
    if (status === 401 && saved && (await this.hello(saved)) === 200) status = await this.command(code);
    return status;
  },
  showKey() { return this.udap('pairing', '<api type="pairing"><name>showKey</name></api>'); },
  async pair(key) {
    const status = await this.hello(key);
    if (status === 200) save(KEY, key);
    return status;
  },
  async power() {
    if (!ui.tvIp) return 'error';
    const { on } = await Tv.isOn({ ip: ui.tvIp });
    if (!on) return 'is-off';
    return (await this.key(1)) === 200 ? 'off' : 'error';
  },
  async state() { return { paired: !!(ui.tvIp && localStorage.getItem(KEY)) }; },
  async current() {
    if (!ui.tvIp) return {};
    let { body } = await Tv.data({ ip: ui.tvIp, target: 'cur_channel' });
    const saved = localStorage.getItem(KEY);
    if (!body?.includes('<chname>') && saved && (await this.hello(saved)) === 200) {
      ({ body } = await Tv.data({ ip: ui.tvIp, target: 'cur_channel' }));
    }
    return parseCurrent(body);
  },
  async guide() {
    // The guide is built by epg.py on the Pi; the app only needs the Pi for this.
    for (const url of GUIDE_URLS) {
      const { status, body } = await Tv.fetch({ url });
      if (status === 200 && body) return JSON.parse(body);
    }
    return null;
  },
};

const GUIDE_URLS = ['http://pi.lan:8765/epg.json', 'http://192.168.1.61:8765/epg.json'];

function parseCurrent(xml) {
  if (!xml) return {};
  const doc = new DOMParser().parseFromString(xml, 'text/xml');
  const text = (tag) => doc.querySelector(tag)?.textContent ?? '';
  const num = parseInt(text('displayMajor'), 10);
  return Number.isNaN(num) ? {} : { num, name: text('chname'), prog: text('progName') };
}

async function post(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  return r.json();
}

const serverBackend = {
  async key(code) { return (await post('/api/key', { code })).status; },
  async showKey() { return (await post('/api/showkey')).status; },
  async pair(key) { return (await post('/api/pair', { key })).status; },
  async power() { return (await post('/api/power')).result; },
  state() { return post('/api/state'); },
  current() { return post('/api/current'); },
  async guide() {
    const r = await fetch('/epg.json');
    return r.ok ? r.json() : null;
  },
};

const backend = native ? nativeBackend : serverBackend;
const offline = (err) => {
  ui.dot = 'err';
  if (err?.code === 'PERMISSION_DENIED') toast('Allow “Local network” for this app in Settings');
  else toast(native ? 'Something went wrong talking to the TV' : 'Remote server is offline');
};

// Keys go out one at a time so they reach the TV in order; held keys don't pile up.
let queue = Promise.resolve();
let pending = 0;

export function sendKey(code) {
  if (pending > 2) return;
  sendKeys([code]);
}

/** Several keys as one queued job, e.g. channel digits; resolves true if all reached the TV. */
export function sendKeys(codes) {
  pending++;
  const job = queue.then(async () => {
    try {
      for (const code of codes) {
        const status = await backend.key(code);
        if (status === 200) { ui.dot = 'ok'; continue; }
        if (status === 401) { ui.dot = 'err'; ui.pairing = true; }
        else { ui.dot = 'err'; toast(status === 0 ? 'TV is off or not on this Wi-Fi' : `TV error ${status}`); }
        return false;
      }
      return true;
    } catch (e) { offline(e); return false; }
    finally { pending--; }
  });
  queue = job;
  return job;
}

/** Switch the TV to a channel number by typing its digits, then OK to skip the TV's wait. */
export function tuneTo(num) {
  const digits = String(num).split('').map((d) => Number(d) + 2);   // UDAP digit n is key n + 2
  return sendKeys([...digits, 20]);
}

export async function currentChannel() {
  try { return await backend.current(); } catch { return {}; }
}

export async function loadGuide() {
  try { return await backend.guide(); } catch { return null; }
}

export async function power() {
  try {
    const result = await backend.power();
    if (result === 'off') { ui.dot = ''; toast('Turning off'); }
    else if (result === 'waking') { ui.dot = 'ok'; toast('Turning on… ready in ~15 s'); }
    else if (result === 'is-off' || result === 'wake-failed') { ui.dot = 'err'; toast('TV is off. Turn it on with its button'); }
    else { ui.dot = 'err'; toast('TV didn’t respond'); }
  } catch (e) { offline(e); }
}

export async function showKey() {
  try {
    const status = await backend.showKey();
    toast(status === 200 ? 'Check the TV screen for the code' : 'TV is off or unreachable');
    return status === 200;
  } catch (e) { offline(e); return false; }
}

export async function pair(key) {
  try {
    if ((await backend.pair(key)) === 200) { ui.pairing = false; ui.dot = 'ok'; toast('Paired'); return true; }
    toast('That code didn’t work');
  } catch (e) { offline(e); }
  return false;
}

export async function checkState() {
  try {
    const { paired } = await backend.state();
    if (!paired) ui.pairing = true;
  } catch (e) { offline(e); }
}

/** Native only: find LG TVs on the Wi-Fi. Resolves [{ip, model}]. */
export async function discover() {
  if (!native) return [];
  try { return (await Tv.discover()).tvs; } catch (e) { offline(e); return []; }
}

export function chooseTv(ip, model = '') {
  if (ip !== ui.tvIp) save(KEY, '');   // a different TV needs its own pairing
  ui.tvIp = ip; ui.tvModel = model;
  save('tvIp', ip); save('tvModel', model);
}
