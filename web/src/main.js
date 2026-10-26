import { mount } from 'svelte';
import { App as CapApp } from '@capacitor/app';
import App from './App.svelte';
import './app.css';
import { native } from './lib/state.svelte.js';

mount(App, { target: document.getElementById('app') });

// Android back: step back through the app's own history (Numbers → Remote, close setup),
// and only send the app to the background when there's nothing left to go back to.
if (native) {
  CapApp.addListener('backButton', ({ canGoBack }) => (canGoBack ? history.back() : CapApp.minimizeApp()));
}

if ('serviceWorker' in navigator && !native) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
