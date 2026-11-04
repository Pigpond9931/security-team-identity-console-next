// External, synchronous script: honor reduced motion before the first paint.
(() => {
  let setting = 'system';
  try { setting = localStorage.getItem('st.motion') || 'system'; } catch {}
  if (!['system', 'reduced'].includes(setting)) setting = 'system';
  const reduced = setting === 'reduced' || matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.dataset.motion = reduced ? 'reduced' : 'full';
})();
