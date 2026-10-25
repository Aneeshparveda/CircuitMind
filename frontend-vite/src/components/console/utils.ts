import { Streamlit } from 'streamlit-component-lib';

export const fmt = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined || Number.isNaN(value) ? '—' : value.toFixed(digits);

export const normalButton = 'console-button console-button--quiet';

// Streamlit wraps the component in an iframe that grows to its content, so
// the page actually scrolls inside a parent container (Streamlit's `.main`).
// Save that container's offset before a round-trip and restore it after the
// iframe remounts, otherwise every button click snaps the view back to top.
export function findScrollContainer(win: Window): Element | null {
  const frame = win.frameElement ?? win.document.querySelector('iframe');
  if (!frame) return null;
  let container: Element | null = frame;
  while (container && container !== win.document.body) {
    if (container.scrollHeight > container.clientHeight + 1) return container;
    container = container.parentElement;
  }
  return null;
}

export function saveScroll() {
  try {
    const container = findScrollContainer(window.parent ?? window);
    sessionStorage.setItem('cm-scroll', String(container?.scrollTop || 0));
  } catch { /* noop */ }
}

// The round-trip actions (analyze/load_demo/scan_all) show a decode screen
// while the server reruns. The main component registers its setter here so
// emit() can flip it on synchronously at click time — the decode screen then
// covers the whole round-trip gap instead of dead air. The marker also
// survives the iframe reload via sessionStorage so the fresh document knows
// it was mid-flight.
let pendingSetter: ((flag: string) => void) | null = null;

export function registerPendingSetter(setter: (flag: string) => void) {
  pendingSetter = setter;
}

export function emit(event: Record<string, unknown>) {
  const eventId = typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  if (event.action === 'analyze' || event.action === 'load_demo' || event.action === 'scan_all') {
    const flag = `${String(event.action)}|${String(event.board_id ?? '')}`;
    try { sessionStorage.setItem('cm-pending', flag); } catch { /* noop */ }
    pendingSetter?.(flag);
  }
  saveScroll();
  Streamlit.setComponentValue({ ...event, event_id: eventId });
}
