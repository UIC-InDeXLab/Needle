import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles, RefreshCw, Loader2, AlertCircle, Settings2, CheckCircle2,
  KeyRound, X, Save, Wand2, Cpu, Boxes, Download,
  FlaskConical, ToggleLeft, ToggleRight, XCircle, ChevronUp, ChevronDown,
} from 'lucide-react';
import {
  getGenerators, getGeneratorPreferences, saveGeneratorPreferences,
  setGeneratorCredentials, getGenerateModels,
  testGenerator, loadGenerateModel, getGenerateState,
} from '../services/api';

// The built-in on-device engine. Older builds shipped a separate "Needle
// Generator" companion service; that is now the same thing, in-process.
const BUILTIN = 'needle-local';
const CLOUD_ICON = { openai: Sparkles, stability: Sparkles };

const GeneratorPage = () => {
  const [engines, setEngines] = useState([]);
  const [cfg, setCfg] = useState([]);
  const [fallback, setFallback] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Built-in engine capabilities
  const [caps, setCaps] = useState(null);
  const [selModel, setSelModel] = useState(null);
  const [downloadingModel, setDownloadingModel] = useState(null);
  const [dlState, setDlState] = useState(null);
  const dlPoll = useRef(null);

  // Test results keyed by model id / engine name
  const [tests, setTests] = useState({});

  // Cloud provider config modal
  const [editing, setEditing] = useState(null);
  const [params, setParams] = useState({});
  const [saving, setSaving] = useState(false);

  const engineInfo = useCallback((name) => engines.find((e) => e.name === name) || {}, [engines]);
  const confOf = useCallback(
    (name) => cfg.find((c) => c.name === name) || { enabled: false, params: {} },
    [cfg]
  );

  const detect = useCallback(async (storedParams) => {
    try {
      const { data } = await getGenerateModels();
      setCaps(data);
      const chosen = storedParams?.model;
      const model = chosen && data.models?.some((m) => m.id === chosen)
        ? chosen : data.default_model;
      setSelModel(model);
    } catch {
      setCaps(null);
    }
  }, []);

  const load = useCallback(async () => {
    try {
      setLoading(true); setError(null);
      // Engine descriptions come from /generator; which ones are enabled, in
      // what order, and the fallback flag are stored by the backend so that
      // needlectl and the app always agree.
      const [r, p] = await Promise.all([getGenerators(), getGeneratorPreferences()]);
      setEngines(r.data || []);
      const prefs = p.data || { engines: [], fallback: true };
      setFallback(prefs.fallback !== false);
      setCfg(prefs.engines || []);
      detect((prefs.engines || []).find((e) => e.name === BUILTIN)?.params);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load generators');
    } finally {
      setLoading(false);
    }
  }, [detect]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { if (dlPoll.current) clearInterval(dlPoll.current); }, []);

  const connected = !!(caps && caps.available);
  const builtinConf = confOf(BUILTIN);
  const activeModel = selModel || builtinConf.params?.model || caps?.default_model;
  const dlPct = dlState?.total ? Math.round((dlState.current / dlState.total) * 100) : null;

  // Optimistic update: render immediately, then persist and adopt whatever the
  // backend reports back (it re-checks availability).
  const persist = useCallback(async (nextEngines, nextFallback) => {
    setCfg(nextEngines);
    setFallback(nextFallback);
    try {
      const { data } = await saveGeneratorPreferences(
        nextEngines.map(({ name, enabled, params }) => ({ name, enabled, params: params || {} })),
        nextFallback,
      );
      setCfg(data.engines || []);
      setFallback(data.fallback !== false);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not save generator settings');
      load();
    }
  }, [load]);

  const setUse = (name, on) => {
    let next = cfg.map((c) => ({ ...c }));
    if (on && !fallback) {
      // Radio behaviour: only one engine may be on when fallback is off.
      next = next.map((c) => ({ ...c, enabled: c.name === name }));
    } else {
      next = next.map((c) => (c.name === name ? { ...c, enabled: on } : c));
    }
    persist(next, fallback);
  };

  const toggleFallback = (on) => {
    if (!on) {
      // Collapse to a single active engine: keep the first enabled (or first).
      const keep = cfg.find((c) => c.enabled)?.name || cfg[0]?.name;
      persist(cfg.map((c) => ({ ...c, enabled: c.name === keep })), false);
    } else {
      persist(cfg, true);
    }
  };

  const chooseModel = (id) => {
    setSelModel(id);
    persist(
      cfg.map((c) => (c.name === BUILTIN
        ? { ...c, params: { ...(c.params || {}), model: id } }
        : c)),
      fallback,
    );
  };

  const runTest = async (key, name, testParams) => {
    setTests((t) => ({ ...t, [key]: { loading: true } }));
    try {
      const r = await testGenerator(name, testParams);
      setTests((t) => ({ ...t, [key]: { img: r.data.image, ms: r.data.elapsed_ms } }));
    } catch (err) {
      setTests((t) => ({ ...t, [key]: { error: err.response?.data?.detail || err.message || 'Test failed' } }));
    }
  };

  // Downloading is explicit so that pressing "Test" can never kick off a
  // multi-gigabyte transfer behind the user's back.
  const startDlPoll = useCallback(() => {
    if (dlPoll.current) clearInterval(dlPoll.current);
    dlPoll.current = setInterval(async () => {
      try {
        const { data } = await getGenerateState();
        setDlState(data);
        if (['ready', 'idle', 'error'].includes(data.state)) {
          clearInterval(dlPoll.current);
          dlPoll.current = null;
          setDownloadingModel(null);
          if (data.state === 'error') setError(data.message);
          detect();
          load();
        }
      } catch { /* keep polling */ }
    }, 1000);
  }, [detect, load]);

  const downloadModel = async (id) => {
    setError(null);
    setDownloadingModel(id);
    // The backend publishes "loading" before returning, so show the progress
    // panel straight away instead of waiting a poll interval for it to appear.
    try {
      const { data } = await loadGenerateModel(id);
      setDlState(data);
    } catch (err) {
      setDownloadingModel(null);
      setError(err.response?.data?.detail || err.message || 'Could not start the download');
      return;
    }
    startDlPoll();
  };

  // A download started here keeps running in the backend while the user is on
  // another tab, so reattach to it on mount instead of losing the progress bar.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await getGenerateState();
        if (cancelled) return;
        if (['downloading', 'loading', 'warming'].includes(data.state)) {
          setDlState(data);
          setDownloadingModel(data.model);
          startDlPoll();
        }
      } catch { /* nothing in flight */ }
    })();
    return () => { cancelled = true; };
  }, [startDlPoll]);

  const openConfig = (engine) => { setEditing(engine); setParams({ ...(confOf(engine.name).params || {}) }); };

  const saveConfig = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      if (editing.requires_credentials) {
        const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v));
        if (Object.keys(clean).length) await setGeneratorCredentials(editing.name, clean);
      }
      // Non-credential settings live with the rest of the preferences.
      await persist(
        cfg.map((c) => (c.name === editing.name ? { ...c, params: { ...params } } : c)),
        fallback,
      );
      await load();
      setEditing(null); setParams({});
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  // ---- reorder ----
  // HTML5 drag-and-drop is unreliable inside the Tauri webview (the shell
  // intercepts drag events for file drops), so priority is moved with explicit
  // buttons instead.
  const move = (idx, delta) => {
    const to = idx + delta;
    if (to < 0 || to >= cfg.length) return;
    const next = [...cfg];
    const [moved] = next.splice(idx, 1);
    next.splice(to, 0, moved);
    persist(next, fallback);
  };

  const TestResult = ({ state }) => {
    if (!state) return null;
    if (state.loading) return <span className="inline-flex items-center gap-1.5 text-xs text-ink-500"><Loader2 className="h-3.5 w-3.5 animate-spin" />Generating…</span>;
    if (state.error) return <span className="inline-flex items-center gap-1.5 text-xs text-red-600"><XCircle className="h-3.5 w-3.5" />{state.error}</span>;
    return (
      <span className="inline-flex items-center gap-2">
        <img src={state.img} alt="test" className="h-10 w-10 rounded-md object-cover border border-ink-200" />
        <span className="inline-flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 className="h-3.5 w-3.5" />Works · {(state.ms / 1000).toFixed(1)}s</span>
      </span>
    );
  };

  const EnableToggle = ({ name, on, disabled }) => (
    <button onClick={() => setUse(name, !on)} disabled={disabled}
      className={`btn btn-sm shrink-0 ${on ? 'btn-primary' : 'btn-ghost'}`}
      title={on ? 'On for search' : 'Off for search'}>
      {on ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
      {on ? 'On' : 'Off'}
    </button>
  );

  const PriorityBadge = ({ idx, on }) => {
    if (!on) return null;
    if (!fallback) return <span className="badge badge-ok">Primary</span>;
    const rank = cfg.slice(0, idx + 1).filter((c) => c.enabled).length;
    return <span className="badge badge-muted">#{rank}</span>;
  };

  const DragHandle = ({ idx, dark }) => (
    <span className={`shrink-0 flex flex-col -my-1 ${dark ? 'text-white/70' : 'text-ink-300'}`}>
      <button type="button" onClick={() => move(idx, -1)} disabled={idx === 0}
        title="Higher priority"
        className={`p-0.5 rounded disabled:opacity-25 ${dark ? 'hover:bg-white/20' : 'hover:text-ink-600 hover:bg-ink-100'}`}>
        <ChevronUp className="h-4 w-4" />
      </button>
      <button type="button" onClick={() => move(idx, 1)} disabled={idx === cfg.length - 1}
        title="Lower priority"
        className={`p-0.5 rounded disabled:opacity-25 ${dark ? 'hover:bg-white/20' : 'hover:text-ink-600 hover:bg-ink-100'}`}>
        <ChevronDown className="h-4 w-4" />
      </button>
    </span>
  );

  // ---- Built-in engine card ----
  const NeedleCard = (idx) => {
    const on = !!builtinConf.enabled;
    return (
      <div className="card overflow-hidden !p-0">
        <div className="p-4 bg-gradient-to-br from-needle-600 to-needle-500 text-white flex items-start gap-3">
          <DragHandle idx={idx} dark />
          <div className="h-10 w-10 rounded-xl bg-white/15 grid place-items-center shrink-0 backdrop-blur">
            <Wand2 className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold">Built-in generator</h3>
              <PriorityBadge idx={idx} on={on} />
              {connected
                ? <span className="badge bg-white/20 text-white border-white/20"><CheckCircle2 className="h-3 w-3" />Ready</span>
                : <span className="badge bg-white/10 text-white/90 border-white/20">Unavailable</span>}
            </div>
            <p className="text-sm text-white/80 mt-0.5">
              Runs on this machine. No server, no API key.
            </p>
            {connected && (
              <div className="flex items-center gap-3 mt-2 text-xs text-white/80">
                <span className="inline-flex items-center gap-1"><Cpu className="h-3.5 w-3.5" />{caps.device?.toUpperCase()}</span>
                <span className="inline-flex items-center gap-1"><Boxes className="h-3.5 w-3.5" />{caps.models.length} models</span>
              </div>
            )}
          </div>
          <button onClick={() => setUse(BUILTIN, !on)}
            className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-white/15 hover:bg-white/25 px-3 py-1.5 text-sm font-medium transition">
            {on ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5 opacity-80" />}
            {on ? 'On' : 'Off'}
          </button>
        </div>

        <div className="p-4 space-y-4">
          {connected ? (
            <>
              <div className="grid gap-2">
                {caps.models.map((m) => {
                  const active = activeModel === m.id;
                  const ts = tests[m.id];
                  const busy = downloadingModel === m.id;
                  return (
                    <div key={m.id} className={`rounded-xl border p-3 ${active ? 'border-needle-400 bg-needle-50 ring-1 ring-needle-200' : 'border-ink-200 bg-white'}`}>
                      <div className="flex items-center gap-2">
                        <button onClick={() => chooseModel(m.id)} className="flex items-center gap-2 min-w-0 flex-1 text-left">
                          <div className={`h-4 w-4 rounded-full border-2 grid place-items-center shrink-0 ${active ? 'border-needle-500' : 'border-ink-300'}`}>
                            {active && <div className="h-1.5 w-1.5 rounded-full bg-needle-500" />}
                          </div>
                          <span className="font-medium text-ink-900">{m.label}</span>
                          {m.downloaded
                            ? <span className="badge badge-muted">Downloaded</span>
                            : <span className="badge badge-warn">{(m.download_mb / 1000).toFixed(1)} GB not downloaded</span>}
                          {active && on && m.downloaded && <span className="badge badge-ok">Used for search</span>}
                        </button>
                        {m.downloaded ? (
                          <button onClick={() => runTest(m.id, BUILTIN, { model: m.id })} disabled={ts?.loading}
                            className="btn btn-secondary btn-sm shrink-0"><FlaskConical className="h-3.5 w-3.5" />Test</button>
                        ) : (
                          <button onClick={() => downloadModel(m.id)} disabled={!!downloadingModel}
                            className="btn btn-secondary btn-sm shrink-0">
                            {busy
                              ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Downloading…</>
                              : <><Download className="h-3.5 w-3.5" />Download</>}
                          </button>
                        )}
                      </div>
                      <p className="text-xs text-ink-500 mt-1 ml-6">{m.description}</p>
                      {busy && (
                        <div className="mt-2 ml-6">
                          <div className="h-1.5 w-full bg-ink-100 rounded-full overflow-hidden">
                            <div className="h-full bg-needle-500 rounded-full transition-all duration-500"
                              style={{ width: dlPct !== null ? `${dlPct}%` : '35%' }} />
                          </div>
                          <p className="text-xs text-ink-500 mt-1">{dlState?.message || 'Starting…'}</p>
                        </div>
                      )}
                      {ts && <div className="mt-2 ml-6"><TestResult state={ts} /></div>}
                    </div>
                  );
                })}
              </div>
              <p className="text-xs text-ink-500">
                Want to create images yourself? Use the{' '}
                <Link to="/generate" className="text-needle-600 font-medium hover:underline">Generate</Link> page.
              </p>
            </>
          ) : (
            <div className="rounded-xl border border-dashed border-ink-200 p-3 bg-ink-50/50 text-sm text-ink-600">
              {caps?.error
                ? <>On-device generation failed to load: <span className="text-red-600 break-words">{caps.error}</span></>
                : 'On-device generation is not available in this build.'}
            </div>
          )}
        </div>
      </div>
    );
  };

  // ---- Cloud engine row ----
  const CloudRow = (name, idx) => {
    const e = engineInfo(name);
    const Icon = CLOUD_ICON[name] || Sparkles;
    const c = confOf(name);
    const on = !!c.enabled;
    const ts = tests[name];
    return (
      <div className="card !p-4">
        <div className="flex items-start gap-3">
          <DragHandle idx={idx} />
          <div className="h-10 w-10 rounded-xl bg-ink-100 grid place-items-center shrink-0">
            <Icon className="h-5 w-5 text-ink-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-medium text-ink-900 capitalize">{name}</h3>
              <PriorityBadge idx={idx} on={on} />
              {e.available
                ? <span className="badge badge-ok"><CheckCircle2 className="h-3 w-3" />Ready</span>
                : <span className="badge badge-warn"><KeyRound className="h-3 w-3" />Needs API key</span>}
            </div>
            <p className="text-sm text-ink-500 mt-1">{e.description}</p>
            {ts && <div className="mt-2"><TestResult state={ts} /></div>}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {e.requires_credentials && (
              <button onClick={() => openConfig(e)} className="btn btn-secondary btn-sm"><Settings2 className="h-4 w-4" />Configure</button>
            )}
            <button onClick={() => runTest(name, name, confOf(name).params || {})} disabled={ts?.loading || (!e.available && !on)}
              className="btn btn-secondary btn-sm"><FlaskConical className="h-4 w-4" />Test</button>
            <EnableToggle name={name} on={on} disabled={!e.available && !on} />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Generators</h1>
          <p className="text-sm text-ink-500 mt-1">
            Needle turns your query into images, then finds the closest matches in your library.
          </p>
        </div>
        <button onClick={load} className="btn btn-secondary btn-sm"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </header>

      {error && (
        <div className="card !p-4 mb-4 border-red-200 bg-red-50 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600" /><span className="text-sm text-red-800">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="grid place-items-center py-24"><Loader2 className="h-7 w-7 animate-spin text-needle-600" /></div>
      ) : (
        <>
          {/* Fallback control */}
          <div className="card !p-4 mb-4 flex items-start gap-3">
            <div className="h-9 w-9 rounded-lg bg-needle-50 grid place-items-center shrink-0">
              <RefreshCw className="h-4 w-4 text-needle-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-ink-900">Fallback chain</span>
                <button onClick={() => toggleFallback(!fallback)}
                  className={`btn btn-sm ${fallback ? 'btn-primary' : 'btn-ghost'}`}>
                  {fallback ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                  {fallback ? 'On' : 'Off'}
                </button>
              </div>
              <p className="text-sm text-ink-500 mt-0.5">
                {fallback
                  ? 'Generators are tried top-to-bottom; if one fails, the next enabled one is used. Use the arrows to reorder priority.'
                  : 'Only the first enabled generator is used. Turning others on will switch the active one.'}
              </p>
            </div>
          </div>

          {/* Unified ordered list */}
          <div className="space-y-3">
            {cfg.map((c, idx) => (
              <React.Fragment key={c.name}>
                {c.name === BUILTIN ? NeedleCard(idx) : CloudRow(c.name, idx)}
              </React.Fragment>
            ))}
          </div>
        </>
      )}

      {/* Cloud config modal */}
      {editing && (
        <div className="fixed inset-0 z-50 bg-ink-950/60 backdrop-blur-sm grid place-items-center p-4 animate-fade-in" onClick={() => setEditing(null)}>
          <div className="card w-full max-w-md animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-ink-900 capitalize">Configure {editing.name}</h3>
              <button onClick={() => setEditing(null)} className="btn btn-ghost !px-2"><X className="h-4 w-4" /></button>
            </div>
            <div className="space-y-4">
              {(editing.required_params || []).map((p) => {
                const secret = /key|token|secret/i.test(p.name);
                return (
                  <label key={p.name} className="block">
                    <span className="text-sm font-medium text-ink-700 capitalize">{p.name.replace(/_/g, ' ')}</span>
                    <input type={secret ? 'password' : 'text'} value={params[p.name] || ''}
                      onChange={(e) => setParams((x) => ({ ...x, [p.name]: e.target.value }))}
                      placeholder={p.description} className="input mt-1" />
                    <span className="text-xs text-ink-400 mt-1 block">{p.description}</span>
                  </label>
                );
              })}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setEditing(null)} className="btn btn-secondary">Cancel</button>
              <button onClick={saveConfig} disabled={saving} className="btn btn-primary">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GeneratorPage;
