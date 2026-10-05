// Dark mode toggle (persisted in localStorage)
document.addEventListener('click', (e) => {
  if (e.target.closest('#dark-toggle')) {
    const dark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }
});

// Surface Django messages that arrive with HTMX partial responses:
// views call `trigger_toast(response, ...)` which sets HX-Trigger headers.
document.body.addEventListener('htmx:afterRequest', (event) => {
  const header = event.detail.xhr.getResponseHeader('HX-Trigger');
  if (!header) return;
  try {
    const triggers = JSON.parse(header);
    const toast = triggers.toast;
    if (toast) {
      window.dispatchEvent(new CustomEvent('toast', { detail: toast }));
    }
  } catch (_) { /* ignore malformed headers */ }
});
