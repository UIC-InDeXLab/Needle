import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderPlus, Folder, Trash2, RefreshCw, Loader2, AlertCircle,
  CheckCircle2, ToggleLeft, ToggleRight,
} from 'lucide-react';
import { getDirectories, addDirectory, updateDirectory, removeDirectory } from '../services/api';
import { pickDirectory, isTauri } from '../services/tauri';

const DirectoryPage = () => {
  const [dirs, setDirs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [manualPath, setManualPath] = useState('');
  const [showManual, setShowManual] = useState(false);

  const load = useCallback(async (spinner = true) => {
    try {
      if (spinner) setLoading(true);
      const r = await getDirectories();
      setDirs(r.data.directories || []);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load folders');
    } finally {
      if (spinner) setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Poll while anything is still indexing.
  useEffect(() => {
    const indexing = dirs.some((d) => !d.is_indexed);
    if (!indexing) return;
    const t = setInterval(() => load(false), 1000);
    return () => clearInterval(t);
  }, [dirs, load]);

  const addPath = async (path) => {
    if (!path) return;
    try {
      setAdding(true); setError(null);
      await addDirectory(path);
      setManualPath(''); setShowManual(false);
      await load(false);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to add folder');
    } finally {
      setAdding(false);
    }
  };

  const handleAdd = async () => {
    if (isTauri()) {
      const p = await pickDirectory();
      if (p) addPath(p);
    } else {
      setShowManual((v) => !v);
    }
  };

  const toggle = async (d) => {
    try { await updateDirectory(d.id, { is_enabled: !d.is_enabled }); load(false); }
    catch (err) { setError(err.response?.data?.detail || err.message); }
  };

  const remove = async (d) => {
    if (!window.confirm(`Remove "${d.path}" from the library?`)) return;
    try { await removeDirectory(d.path); load(false); }
    catch (err) { setError(err.response?.data?.detail || err.message); }
  };

  const pct = (d) => Math.round((d.indexing_ratio ?? (d.is_indexed ? 1 : 0)) * 100);

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Library</h1>
          <p className="text-sm text-ink-500 mt-1">Folders Needle indexes and watches for changes.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => load()} className="btn btn-secondary btn-sm">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button onClick={handleAdd} disabled={adding} className="btn btn-primary">
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderPlus className="h-4 w-4" />}
            Add folder
          </button>
        </div>
      </header>

      {showManual && !isTauri() && (
        <div className="card !p-4 mb-4 animate-fade-up">
          <div className="flex gap-2">
            <input value={manualPath} onChange={(e) => setManualPath(e.target.value)}
              placeholder="/absolute/path/to/images" className="input" />
            <button onClick={() => addPath(manualPath)} disabled={!manualPath.trim() || adding} className="btn btn-primary">Add</button>
          </div>
        </div>
      )}

      {error && (
        <div className="card !p-4 mb-4 border-red-200 bg-red-50 flex items-center gap-2 animate-fade-up">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <span className="text-sm text-red-800">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="grid place-items-center py-24"><Loader2 className="h-7 w-7 animate-spin text-needle-600" /></div>
      ) : dirs.length === 0 ? (
        <div className="card text-center py-16">
          <div className="h-14 w-14 rounded-2xl bg-needle-50 grid place-items-center mx-auto mb-4">
            <Folder className="h-7 w-7 text-needle-500" />
          </div>
          <h3 className="font-medium text-ink-900">No folders yet</h3>
          <p className="text-sm text-ink-500 mt-1 mb-5">Add a folder of images to start searching.</p>
          <button onClick={handleAdd} className="btn btn-primary mx-auto"><FolderPlus className="h-4 w-4" />Add folder</button>
        </div>
      ) : (
        <div className="space-y-3">
          {dirs.map((d) => (
            <div key={d.id} className="card !p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-xl bg-ink-100 grid place-items-center shrink-0">
                <Folder className="h-5 w-5 text-ink-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-ink-900 truncate">{d.path}</p>
                  {d.is_indexed ? (
                    <span className="badge badge-ok"><CheckCircle2 className="h-3 w-3" />Indexed</span>
                  ) : (
                    <span className="badge badge-warn"><Loader2 className="h-3 w-3 animate-spin" />Indexing {pct(d)}%</span>
                  )}
                  {!d.is_enabled && <span className="badge badge-muted">Paused</span>}
                </div>
                {!d.is_indexed && (
                  <div className="mt-2 h-1.5 w-full bg-ink-100 rounded-full overflow-hidden">
                    <div className="h-full bg-needle-500 rounded-full transition-all duration-500" style={{ width: `${pct(d)}%` }} />
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => toggle(d)} className="btn btn-ghost !px-2" title={d.is_enabled ? 'Pause' : 'Enable'}>
                  {d.is_enabled ? <ToggleRight className="h-5 w-5 text-needle-600" /> : <ToggleLeft className="h-5 w-5 text-ink-400" />}
                </button>
                <button onClick={() => remove(d)} className="btn btn-ghost !px-2 hover:!text-red-600" title="Remove">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DirectoryPage;
