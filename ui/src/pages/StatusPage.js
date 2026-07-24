import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw, CheckCircle2, XCircle,
  FolderOpen, Sparkles, Search as SearchIcon,
} from 'lucide-react';
import { getHealth, getDirectories, getGenerators, getSearchLogs } from '../services/api';

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
  const [loading, setLoading] = useState(true);
  const [updated, setUpdated] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [h, d, g, l] = await Promise.allSettled([
      getHealth(), getDirectories(), getGenerators(), getSearchLogs().catch(() => ({ data: { queries: [] } })),
    ]);
    setData({
      health: h.status === 'fulfilled' ? h.value.data : null,
      directories: d.status === 'fulfilled' ? d.value.data.directories || [] : [],
      generators: g.status === 'fulfilled' ? g.value.data || [] : [],
      logs: l.status === 'fulfilled' ? l.value.data.queries || [] : [],
    });
    setUpdated(new Date());
    setLoading(false);
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

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
