let injected = false;

export function ensureStatusAnimations() {
  if (injected || typeof document === 'undefined') {
    return;
  }
  const style = document.createElement('style');
  style.setAttribute('data-mosaic-animations', 'status');
  style.textContent = `
@keyframes mosaic-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes mosaic-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
`;
  document.head.appendChild(style);
  injected = true;
}
