import React, {useEffect, useState} from 'react';
import {Accessibility} from 'lucide-react';

export function MotionControl() {
  const [setting, setSetting] = useState(() => {
    try { return localStorage.getItem('st.motion') === 'reduced' ? 'reduced' : 'system'; }
    catch { return 'system'; }
  });
  const [deviceReduced, setDeviceReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const query = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setDeviceReduced(query.matches);
    query.addEventListener('change', update);
    const storage = event => {
      if (event.key === 'st.motion') setSetting(event.newValue === 'reduced' ? 'reduced' : 'system');
    };
    addEventListener('storage', storage);
    return () => { query.removeEventListener('change', update); removeEventListener('storage', storage); };
  }, []);
  useEffect(() => {
    document.documentElement.dataset.motion = setting === 'reduced' || deviceReduced ? 'reduced' : 'full';
    try { localStorage.setItem('st.motion', setting); } catch {}
  }, [setting, deviceReduced]);
  return <label className="motion-control"><Accessibility size={15} aria-hidden="true"/>
    <span className="sr-only">Preferencia de movimiento</span>
    <select aria-label="Preferencia de movimiento" value={setting} onChange={event => setSetting(event.target.value)}>
      <option value="system">Movimiento: dispositivo</option>
      <option value="reduced">Movimiento: reducido</option>
    </select>
    {deviceReduced && <span className="sr-only">El dispositivo solicita movimiento reducido.</span>}
  </label>;
}
