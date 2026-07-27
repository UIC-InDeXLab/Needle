import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  RefreshCw, CheckCircle2, XCircle,
  FolderOpen, Sparkles, Search as SearchIcon, Cpu, Loader2,
} from 'lucide-react';
import { getHealth, getDirectories, getGenerators, getSearchLogs, getSetupStatus, setSetupGpu } from '../services/api';

const StatCard = ({ icon: Icon, label, value, sub }) => (
  <div className="card !p-5">
    <div className="flex items-center gap-3">
      <div className="h-10 w-10 rounded-xl bg-needle-50 grid place-items-center">
        <Icon className="h-5 w-5 text-needle-600" />
      </div>
      <div>
        <div className="text-2xl font-semibold text-ink-900 tabular-nums leading-none">{value}</div>
        <div className="text-xs text-ink-500 mt-1">{label}</div>
      </div>
    </div>
    {sub && <div className="text-xs text-ink-400 mt-3">{sub}</div>}
  </div>
);

const StatusPage = () => {
  const [data, setData] = useState({ health: null, directories: [], generators: [], logs: [] });
  const [setup, setSetup] = useState(null);
  const [gpuBusy, setGpuBusy] = useState(false);
  const [gpuError, setGpuError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updated, setUpdated] = useState(null);
  const gpuPollRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [h, d, g, l, s] = await Promise.allSettled([
      getHealth(), getDirectories(), getGenerators(), getSearchLogs().catch(() => ({ data: { queries: [] } })),
      getSetupStatus(),
    ]);
    setData({
      health: h.status === 'fulfilled' ? h.value.data : null,
      directories: d.status === 'fulfilled' ? d.value.data.directories || [] : [],
      generators: g.status === 'fulfilled' ? g.value.data || [] : [],
      logs: l.status === 'fulfilled' ? l.value.data.queries || [] : [],
    });
    if (s.status === 'fulfilled') setSetup(s.value.data);
    setUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);
  useEffect(() => () => { if (gpuPollRef.current) clearInterval(gpuPollRef.current); }, []);

  // Switching device rebuilds the embedders in the background (weights are
  // already cached), so poll until the backend reports ready again.
  const toggleGpu = async (next) => {
    setGpuError(null);
    setGpuBusy(true);
    try {
      const { data: s } = await setSetupGpu(next);
      setSetup(s);
      if (gpuPollRef.current) clearInterval(gpuPollRef.current);
      gpuPollRef.current = setInterval(async () => {
        try {
          const { data: cur } = await getSetupStatus();
          setSetup(cur);
          if (cur.ready || cur.state === 'error') {
            clearInterval(gpuPollRef.current);
            gpuPollRef.current = null;
            setGpuBusy(false);
            if (cur.state === 'error') setGpuError(cur.message || 'Failed to switch device');
          }
        } catch { /* backend busy; keep polling */ }
      }, 1000);
    } catch (e) {
      setGpuBusy(false);
      setGpuError(e.response?.data?.detail || e.message || 'Failed to switch device');
    }
  };

  const online = data.health?.status === 'running';
  const indexed = data.directories.filter((d) => d.is_indexed).length;
  const activeGen = data.generators.filter((g) => g.available).length;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Status</h1>
          <p className="text-sm text-ink-500 mt-1">
            {updated ? `Updated ${updated.toLocaleTimeString()}` : 'Loading…'}
          </p>
        </div>
        <button onClick={load} className="btn btn-secondary btn-sm">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      <div className="card !p-5 mb-4 flex items-center gap-3">
        {online ? <CheckCircle2 className="h-6 w-6 text-emerald-500" /> : <XCircle className="h-6 w-6 text-red-500" />}
        <div className="flex-1">
          <div className="font-medium text-ink-900">Backend {online ? 'online' : 'offline'}</div>
          <div className="text-xs text-ink-500">Embedded engine · SQLite + LanceDB · 127.0.0.1:8000</div>
        </div>
        <span className={`badge ${online ? 'badge-ok' : 'badge-warn'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${online ? 'bg-emerald-500' : 'bg-red-500'}`} />
          {online ? 'Healthy' : 'Down'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard icon={FolderOpen} label="Folders in library" value={data.directories.length}
          sub={`${indexed} fully indexed`} />
        <StatCard icon={Sparkles} label="Generators ready" value={activeGen}
          sub={`${data.generators.length} available`} />
        <StatCard icon={SearchIcon} label="Searches run" value={data.logs.length} />
      </div>

      {setup?.configured && (
        <div className="card !p-5 mb-6">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-xl bg-needle-50 grid place-items-center shrink-0">
              <Cpu className="h-5 w-5 text-needle-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-ink-900">Hardware acceleration</div>
              <p className="text-xs text-ink-500 mt-1">
                {setup.gpu_available
                  ? 'Use the GPU for indexing and search. Switching reloads the models — no re-download.'
                  : 'No compatible GPU detected on this machine — Needle runs on the CPU.'}
              </p>
              {gpuBusy && (
                <p className="text-xs text-ink-500 mt-2 flex items-center gap-1.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-needle-600" />
                  {setup.message || 'Reloading models…'}
                </p>
              )}
              {gpuError && <p className="text-xs text-red-600 mt-2 break-words">{gpuError}</p>}
            </div>
            <label className={`flex items-center gap-2 shrink-0 ${setup.gpu_available && !gpuBusy ? 'cursor-pointer' : 'opacity-50'}`}>
              <input type="checkbox" checked={Boolean(setup.use_gpu)}
                disabled={!setup.gpu_available || gpuBusy}
                onChange={(e) => toggleGpu(e.target.checked)}
                className="rounded border-ink-300 text-needle-600 focus:ring-needle-500" />
              <span className="text-sm text-ink-700">Use GPU</span>
            </label>
          </div>
        </div>
      )}

      {data.logs.length > 0 && (
        <div className="card">
          <h2 className="font-medium text-ink-900 mb-3">Recent searches</h2>
          <div className="divide-y divide-ink-100">
            {data.logs.slice(0, 12).map((l) => (
              <div key={l.qid} className="py-2.5 flex items-center gap-3 text-sm">
                <SearchIcon className="h-3.5 w-3.5 text-ink-400 shrink-0" />
                <span className="text-ink-700 truncate flex-1">{l.query}</span>
                <span className="text-xs text-ink-400">#{l.qid}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StatusPage;
