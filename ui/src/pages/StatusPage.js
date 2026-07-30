import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  RefreshCw, CheckCircle2, XCircle, FolderOpen, Sparkles,
  Search as SearchIcon, Cpu, Loader2, HardDrive, Image as ImageIcon, Download,
  ArrowUpCircle, Info, Clock, Layers,
} from 'lucide-react';
import {
  getHealth, getDirectories, getGenerators, getSearchLogs, getSetupStatus,
  setSetupGpu, getSystemInfo, checkForUpdate,
} from '../services/api';
import { openExternal } from '../services/tauri';

const formatBytes = (bytes) => {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** i;
  return `${value >= 100 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
};

const formatUptime = (seconds) => {
  if (seconds == null) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
};

const StatCard = ({ icon: Icon, label, value, sub }) => (
  <div className="card !p-5">
    <div className="flex items-center gap-3">
      <div className="h-10 w-10 rounded-xl bg-needle-50 grid place-items-center">
        <Icon className="h-5 w-5 text-needle-600" />
      </div>
      <div className="min-w-0">
        <div className="text-2xl font-semibold text-ink-900 tabular-nums leading-none">{value}</div>
        <div className="text-xs text-ink-500 mt-1">{label}</div>
      </div>
    </div>
    {sub && <div className="text-xs text-ink-400 mt-3">{sub}</div>}
  </div>
);

const Row = ({ label, value, mono }) => (
  <div className="flex items-baseline justify-between gap-4 py-2 text-sm">
    <span className="text-ink-500 shrink-0">{label}</span>
    <span className={`text-ink-800 truncate text-right ${mono ? 'font-mono text-xs' : ''}`}>
      {value ?? '—'}
    </span>
  </div>
);

// Storage segments, largest first so the bar reads left to right.
const SEGMENTS = [
  { key: 'models_bytes', label: 'Model weights', color: 'bg-needle-500' },
  { key: 'vectors_bytes', label: 'Search index', color: 'bg-emerald-500' },
  { key: 'metadata_bytes', label: 'Metadata', color: 'bg-amber-500' },
  { key: 'logs_bytes', label: 'Logs', color: 'bg-sky-500' },
  { key: 'other_bytes', label: 'Other', color: 'bg-ink-300' },
];

const StatusPage = () => {
  const [data, setData] = useState({ health: null, directories: [], generators: [], logs: [] });
  const [setup, setSetup] = useState(null);
  const [sys, setSys] = useState(null);
  const [gpuBusy, setGpuBusy] = useState(false);
  const [gpuError, setGpuError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updated, setUpdated] = useState(null);
  const [update, setUpdate] = useState(null);
  const [updateBusy, setUpdateBusy] = useState(false);
  const [updateError, setUpdateError] = useState(null);
  const gpuPollRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [h, d, g, l, s, i] = await Promise.allSettled([
      getHealth(), getDirectories(), getGenerators(),
      getSearchLogs().catch(() => ({ data: { queries: [] } })),
      getSetupStatus(), getSystemInfo(),
    ]);
    setData({
      health: h.status === 'fulfilled' ? h.value.data : null,
      directories: d.status === 'fulfilled' ? d.value.data.directories || [] : [],
      generators: g.status === 'fulfilled' ? g.value.data || [] : [],
      logs: l.status === 'fulfilled' ? l.value.data.queries || [] : [],
    });
    if (s.status === 'fulfilled') setSetup(s.value.data);
    if (i.status === 'fulfilled') setSys(i.value.data);
    setUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);
  useEffect(() => () => { if (gpuPollRef.current) clearInterval(gpuPollRef.current); }, []);

  // Only ever checked on request: Needle does not phone home on its own.
  const runUpdateCheck = async () => {
    setUpdateBusy(true); setUpdateError(null);
    try {
      const { data: u } = await checkForUpdate();
      setUpdate(u);
    } catch (e) {
      setUpdateError(e.response?.data?.detail || e.message || 'Update check failed');
    } finally {
      setUpdateBusy(false);
    }
  };

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
  const storage = sys?.storage;
  const total = storage?.total_bytes || 0;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Status</h1>
          <p className="text-sm text-ink-500 mt-1">
            {updated ? `Updated ${updated.toLocaleTimeString()}` : 'Loading…'}
            {sys?.version && <> · Needle {sys.version}</>}
          </p>
        </div>
        <button onClick={load} className="btn btn-secondary btn-sm">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      <div className="card !p-5 mb-4 flex items-center gap-3">
        {online ? <CheckCircle2 className="h-6 w-6 text-emerald-500" /> : <XCircle className="h-6 w-6 text-red-500" />}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-ink-900">Backend {online ? 'online' : 'offline'}</div>
          <div className="text-xs text-ink-500">
            Embedded engine · SQLite + LanceDB · 127.0.0.1:8000
            {sys && <> · up {formatUptime(sys.uptime_seconds)}</>}
          </div>
        </div>
        <span className={`badge ${online ? 'badge-ok' : 'badge-warn'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${online ? 'bg-emerald-500' : 'bg-red-500'}`} />
          {online ? 'Healthy' : 'Down'}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard icon={FolderOpen} label="Folders" value={data.directories.length}
          sub={`${indexed} fully indexed`} />
        <StatCard icon={ImageIcon} label="Images indexed"
          value={(sys?.library?.indexed_images ?? 0).toLocaleString()}
          sub={sys ? `${sys.library.images.toLocaleString()} tracked` : undefined} />
        <StatCard icon={Sparkles} label="Generators ready" value={activeGen}
          sub={`${data.generators.length} configured`} />
        <StatCard icon={SearchIcon} label="Searches run" value={data.logs.length} />
      </div>

      {/* ---- Version & updates ---- */}
      <div className="card !p-5 mb-4">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-xl bg-needle-50 grid place-items-center shrink-0">
            <ArrowUpCircle className="h-5 w-5 text-needle-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-ink-900">
              Version {sys?.version || '—'}
            </div>
            {!update && !updateError && (
              <p className="text-xs text-ink-500 mt-1">
                Needle never checks for updates on its own. Check when you want to.
              </p>
            )}
            {updateError && <p className="text-xs text-red-600 mt-1">{updateError}</p>}
            {update && !update.update_available && (
              <p className="text-xs text-emerald-600 mt-1 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" />
                {update.message || 'You are on the latest version.'}
              </p>
            )}
            {update?.update_available && (
              <div className="mt-2">
                <p className="text-sm text-ink-800">
                  Version <span className="font-medium">{update.latest}</span> is available.
                </p>
                {update.published_at && (
                  <p className="text-xs text-ink-400 mt-0.5">
                    Published {new Date(update.published_at).toLocaleDateString()}
                  </p>
                )}
                {update.notes && (
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-ink-600 bg-ink-50 rounded-lg p-3 border border-ink-100">
                    {update.notes}
                  </pre>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {update?.update_available && update.url && (
              <button onClick={() => openExternal(update.url)} className="btn btn-primary btn-sm">
                <Download className="h-4 w-4" /> Get update
              </button>
            )}
            <button onClick={runUpdateCheck} disabled={updateBusy} className="btn btn-secondary btn-sm">
              {updateBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Check
            </button>
          </div>
        </div>
      </div>

      {/* ---- Storage ---- */}
      {storage && (
        <div className="card !p-5 mb-4">
          <div className="flex items-start gap-3 mb-4">
            <div className="h-10 w-10 rounded-xl bg-needle-50 grid place-items-center shrink-0">
              <HardDrive className="h-5 w-5 text-needle-600" />
            </div>
            <div className="flex-1">
              <div className="font-medium text-ink-900">Storage used</div>
              <p className="text-xs text-ink-500 mt-1">
                {formatBytes(total)} in total — model weights are shared with other
                Hugging Face tools on this machine.
              </p>
            </div>
          </div>

          <div className="flex h-2.5 w-full rounded-full overflow-hidden bg-ink-100">
            {SEGMENTS.map(({ key, color }) => {
              const value = storage[key] || 0;
              if (!value || !total) return null;
              return <div key={key} className={color} style={{ width: `${(value / total) * 100}%` }} />;
            })}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-1 mt-4">
            {SEGMENTS.map(({ key, label, color }) => (
              <div key={key} className="flex items-center gap-2 text-sm py-1">
                <span className={`h-2 w-2 rounded-full ${color} shrink-0`} />
                <span className="text-ink-600 flex-1 truncate">{label}</span>
                <span className="text-ink-800 tabular-nums text-xs">{formatBytes(storage[key])}</span>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-3 border-t border-ink-100">
            <Row label="Data folder" value={storage.data_dir} mono />
          </div>
        </div>
      )}

      {/* ---- Hardware acceleration ---- */}
      {setup?.configured && (
        <div className="card !p-5 mb-4">
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

      {/* ---- System details ---- */}
      {sys && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div className="card !p-5">
            <div className="flex items-center gap-2 mb-2">
              <Info className="h-4 w-4 text-ink-400" />
              <h2 className="font-medium text-ink-900">System</h2>
            </div>
            <div className="divide-y divide-ink-100">
              <Row label="Platform" value={`${sys.platform.system} ${sys.platform.release}`} />
              <Row label="Architecture" value={sys.platform.machine} />
              <Row label="Running on" value={String(sys.platform.device).toUpperCase()} />
              <Row label="Python" value={sys.platform.python} />
              <Row label="PyTorch" value={sys.platform.torch} />
            </div>
          </div>

          <div className="card !p-5">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="h-4 w-4 text-ink-400" />
              <h2 className="font-medium text-ink-900">Search profile</h2>
            </div>
            <div className="divide-y divide-ink-100">
              <Row label="Profile" value={setup?.profile ? setup.profile[0].toUpperCase() + setup.profile.slice(1) : '—'} />
              <Row label="Embedding models" value={sys.library.embedders.length || '—'} />
              <Row label="Models in use" value={sys.library.embedders.join(', ') || '—'} />
              <Row label="Uptime" value={formatUptime(sys.uptime_seconds)} />
            </div>
          </div>
        </div>
      )}

      {data.logs.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="h-4 w-4 text-ink-400" />
            <h2 className="font-medium text-ink-900">Recent searches</h2>
          </div>
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
