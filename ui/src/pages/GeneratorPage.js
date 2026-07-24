import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles, RefreshCw, Loader2, AlertCircle, Settings2, CheckCircle2,
  KeyRound, X, Save, Wand2, Cpu, Plug, PlugZap, Download, Boxes,
  FlaskConical, ToggleLeft, ToggleRight, XCircle, GripVertical,
} from 'lucide-react';
import {
  getGenerators, getGeneratorConfig, saveGeneratorConfig,
  updateGeneratorConfig, setGeneratorCredentials, getGeneratorCapabilities,
  testGenerator, getGeneratorFallback, setGeneratorFallback,
} from '../services/api';

const NEEDLE = 'needle-generator';
const DEFAULT_LOCAL_URL = 'http://127.0.0.1:8001';
const CLOUD_ICON = { openai: Sparkles, stability: Sparkles };

const GeneratorPage = () => {
  const [engines, setEngines] = useState([]);
  const [cfg, setCfg] = useState([]);
  const [fallback, setFallback] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Needle Generator connection state
  const [url, setUrl] = useState(DEFAULT_LOCAL_URL);
  const [caps, setCaps] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [probeMsg, setProbeMsg] = useState(null);
  const [selModel, setSelModel] = useState(null);

  // Test results keyed by model id / engine name
  const [tests, setTests] = useState({});

  // Cloud provider config modal
  const [editing, setEditing] = useState(null);
  const [params, setParams] = useState({});
  const [saving, setSaving] = useState(false);

  // Drag-to-reorder
  const [dragIndex, setDragIndex] = useState(null);

  const engineInfo = useCallback((name) => engines.find((e) => e.name === name) || {}, [engines]);
  const confOf = useCallback(
    (name) => cfg.find((c) => c.name === name) || { enabled: false, params: {} },
    [cfg]
  );

  const detect = useCallback(async (tryUrl, { persist = false } = {}) => {
    setConnecting(true); setProbeMsg(null);
    try {
      const r = await getGeneratorCapabilities(NEEDLE, tryUrl);
      const data = r.data || {};
      if (data.models && data.models.length) {
        setCaps(data);
        const c = getGeneratorConfig().find((x) => x.name === NEEDLE) || { params: {} };
        const model = c.params?.model && data.models.some((m) => m.id === c.params.model)
          ? c.params.model : data.default_model || data.models[0].id;
        setSelModel(model);
        if (persist) {
          await setGeneratorCredentials(NEEDLE, { base_url: tryUrl });
          const updated = updateGeneratorConfig(NEEDLE, { params: { ...(c.params || {}), base_url: tryUrl, model } });
          setCfg([...updated]);
        }
        return true;
      }
      setCaps(null);
      if (persist) setProbeMsg('No Needle Generator responded at that URL.');
      return false;
    } catch {
      setCaps(null);
      if (persist) setProbeMsg('Could not reach a Needle Generator at that URL.');
      return false;
    } finally {
      setConnecting(false);
    }
  }, []);

  const load = useCallback(async () => {
    try {
      setLoading(true); setError(null);
      const r = await getGenerators();
      const list = r.data || [];
      setEngines(list);
      setFallback(getGeneratorFallback());
      let stored = getGeneratorConfig();
      // Seed/repair config: keep order, ensure every engine present, drop stale.
      const names = list.map((e) => e.name);
      if (!stored || stored.length === 0) {
        stored = list.map((e) => ({ name: e.name, enabled: e.name === NEEDLE, params: {} }));
      } else {
        stored = stored.filter((c) => names.includes(c.name));
        for (const n of names) if (!stored.some((c) => c.name === n)) stored.push({ name: n, enabled: false, params: {} });
      }
      saveGeneratorConfig(stored);
      setCfg(stored);
      const savedUrl = stored.find((c) => c.name === NEEDLE)?.params?.base_url || DEFAULT_LOCAL_URL;
      setUrl(savedUrl);
      detect(savedUrl);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load generators');
    } finally {
      setLoading(false);
    }
  }, [detect]);

  useEffect(() => { load(); }, [load]);

  const connected = !!(caps && caps.models && caps.models.length);
  const needleConf = confOf(NEEDLE);
  const activeModel = selModel || needleConf.params?.model || caps?.default_model;

  const persist = (next) => { saveGeneratorConfig(next); setCfg([...next]); };

  const setUse = (name, on) => {
    let next = cfg.map((c) => ({ ...c }));
    if (on && !fallback) {
      // Radio behaviour: only one engine may be on when fallback is off.
      next = next.map((c) => ({ ...c, enabled: c.name === name }));
    } else {
      next = next.map((c) => (c.name === name ? { ...c, enabled: on } : c));
    }
    persist(next);
  };

  const toggleFallback = (on) => {
    setGeneratorFallback(on);
    setFallback(on);
    if (!on) {
      // Collapse to a single active engine: keep the first enabled (or first).
      const keep = cfg.find((c) => c.enabled)?.name || cfg[0]?.name;
      persist(cfg.map((c) => ({ ...c, enabled: c.name === keep })));
    }
  };

  const chooseModel = (id) => {
    setSelModel(id);
    const updated = updateGeneratorConfig(NEEDLE, { params: { ...(needleConf.params || {}), base_url: url, model: id } });
    setCfg([...updated]);
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

  const openConfig = (engine) => { setEditing(engine); setParams({ ...(confOf(engine.name).params || {}) }); };

  const saveConfig = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const updated = updateGeneratorConfig(editing.name, { params });
      setCfg([...updated]);
      if (editing.requires_credentials) {
        const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v));
        if (Object.keys(clean).length) await setGeneratorCredentials(editing.name, clean);
      }
      await load();
      setEditing(null); setParams({});
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  // ---- reorder ----
  const onDrop = (toIdx, e) => {
    if (e) e.preventDefault();
    let from = dragIndex;
    if (from === null && e) {
      const raw = e.dataTransfer?.getData('text/plain');
      if (raw !== undefined && raw !== '') from = parseInt(raw, 10);
    }
    if (from === null || Number.isNaN(from) || from === toIdx) { setDragIndex(null); return; }
    const next = [...cfg];
    const [moved] = next.splice(from, 1);
    next.splice(toIdx, 0, moved);
    setDragIndex(null);
    persist(next);
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

  const DragHandle = ({ idx }) => (
    <span draggable
      onDragStart={(e) => {
        setDragIndex(idx);
        // WebKit (Tauri) only initiates a drag when dataTransfer is set;
        // without this it just selects text instead of dragging.
        e.dataTransfer.effectAllowed = 'move';
        try { e.dataTransfer.setData('text/plain', String(idx)); } catch { /* ignore */ }
      }}
      onDragEnd={() => setDragIndex(null)}
      className="shrink-0 cursor-grab active:cursor-grabbing select-none text-ink-300 hover:text-ink-500" title="Drag to reorder">
      <GripVertical className="h-5 w-5 pointer-events-none" />
    </span>
  );

  // ---- Needle Generator card ----
  const NeedleCard = (idx) => {
    const on = !!needleConf.enabled;
    return (
      <div onDragOver={(e) => e.preventDefault()} onDrop={(e) => onDrop(idx, e)}
        className={`card overflow-hidden !p-0 ${dragIndex === idx ? 'ring-2 ring-needle-300' : ''}`}>
        <div className="p-4 bg-gradient-to-br from-needle-600 to-needle-500 text-white flex items-start gap-3">
          <DragHandle idx={idx} />
          <div className="h-10 w-10 rounded-xl bg-white/15 grid place-items-center shrink-0 backdrop-blur">
            <Wand2 className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold">Needle Generator</h3>
              <PriorityBadge idx={idx} on={on} />
              {connected
                ? <span className="badge bg-white/20 text-white border-white/20"><CheckCircle2 className="h-3 w-3" />Connected</span>
                : <span className="badge bg-white/10 text-white/90 border-white/20">Not connected</span>}
            </div>
            <p className="text-sm text-white/80 mt-0.5">Companion app · switch models per search.</p>
            {connected && (
              <div className="flex items-center gap-3 mt-2 text-xs text-white/80">
                <span className="inline-flex items-center gap-1"><Cpu className="h-3.5 w-3.5" />{caps.device?.toUpperCase()}</span>
                <span className="inline-flex items-center gap-1"><Boxes className="h-3.5 w-3.5" />{caps.models.length} models</span>
              </div>
            )}
          </div>
          <button onClick={() => setUse(NEEDLE, !on)}
            className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-white/15 hover:bg-white/25 px-3 py-1.5 text-sm font-medium transition">
            {on ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5 opacity-80" />}
            {on ? 'On' : 'Off'}
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="flex gap-2">
            <input value={url} onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && detect(url, { persist: true })}
              placeholder={DEFAULT_LOCAL_URL} className="input flex-1" />
            <button onClick={() => detect(url, { persist: true })} disabled={connecting} className="btn btn-primary shrink-0">
              {connecting ? <Loader2 className="h-4 w-4 animate-spin" /> : connected ? <PlugZap className="h-4 w-4" /> : <Plug className="h-4 w-4" />}
              {connected ? 'Reconnect' : 'Connect'}
            </button>
          </div>
          {probeMsg && <p className="text-xs text-amber-600">{probeMsg}</p>}

          {connected ? (
            <div className="grid gap-2">
              {caps.models.map((m) => {
                const active = activeModel === m.id;
                const ts = tests[m.id];
                return (
                  <div key={m.id} className={`rounded-xl border p-3 ${active ? 'border-needle-400 bg-needle-50 ring-1 ring-needle-200' : 'border-ink-200 bg-white'}`}>
                    <div className="flex items-center gap-2">
                      <button onClick={() => chooseModel(m.id)} className="flex items-center gap-2 min-w-0 flex-1 text-left">
                        <div className={`h-4 w-4 rounded-full border-2 grid place-items-center shrink-0 ${active ? 'border-needle-500' : 'border-ink-300'}`}>
                          {active && <div className="h-1.5 w-1.5 rounded-full bg-needle-500" />}
                        </div>
                        <span className="font-medium text-ink-900">{m.label}</span>
                        {active && on && <span className="badge badge-ok">Used for search</span>}
                        {active && !on && <span className="badge badge-muted">Selected</span>}
                      </button>
                      <button onClick={() => runTest(m.id, NEEDLE, { base_url: url, model: m.id })} disabled={ts?.loading}
                        className="btn btn-secondary btn-sm shrink-0"><FlaskConical className="h-3.5 w-3.5" />Test</button>
                    </div>
                    <p className="text-xs text-ink-500 mt-1 ml-6">{m.description}</p>
                    {ts && <div className="mt-2 ml-6"><TestResult state={ts} /></div>}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-ink-200 p-3 bg-ink-50/50 text-sm text-ink-600">
              <p className="font-medium text-ink-800 flex items-center gap-2"><Download className="h-4 w-4" />Not installed?</p>
              <code className="block mt-2 text-xs bg-white px-2.5 py-1.5 rounded-lg border border-ink-200 text-ink-700">cd generator-service &amp;&amp; ./run.sh</code>
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
      <div onDragOver={(ev) => ev.preventDefault()} onDrop={(ev) => onDrop(idx, ev)}
        className={`card !p-4 ${dragIndex === idx ? 'ring-2 ring-needle-300' : ''}`}>
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
                  ? 'Generators are tried top-to-bottom; if one fails, the next enabled one is used. Drag to reorder priority.'
                  : 'Only the first enabled generator is used. Turning others on will switch the active one.'}
              </p>
            </div>
          </div>

          {/* Unified ordered list */}
          <div className="space-y-3">
            {cfg.map((c, idx) => (
              <React.Fragment key={c.name}>
                {c.name === NEEDLE ? NeedleCard(idx) : CloudRow(c.name, idx)}
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
