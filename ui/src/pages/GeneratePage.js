import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Sparkles, Loader2, Download, Check, Save, Shuffle, AlertCircle, Cpu, Wand2,
} from 'lucide-react';
import {
  getGenerateModels, getGenerateState, loadGenerateModel, generateImages, saveGeneratedImage,
} from '../services/api';
import { isTauri, pickDirectory } from '../services/tauri';

const TIER_LABEL = { fast: 'Fastest', balanced: 'Balanced', quality: 'Best quality' };

// Engine states that mean work is still running in the backend.
const IN_FLIGHT = ['downloading', 'loading', 'warming', 'generating'];

const formatSize = (mb) => (mb >= 1000 ? `${(mb / 1000).toFixed(1)} GB` : `${mb} MB`);

const GeneratePage = () => {
  const [catalog, setCatalog] = useState(null);
  const [model, setModel] = useState(null);
  const [engineState, setEngineState] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [size, setSize] = useState(512);
  const [steps, setSteps] = useState(1);
  const [seed, setSeed] = useState('');
  const [count, setCount] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [saved, setSaved] = useState({});
  const pollRef = useRef(null);

  const spec = catalog?.models?.find((m) => m.id === model) || null;

  const loadCatalog = useCallback(async () => {
    try {
      const { data } = await getGenerateModels();
      setCatalog(data);
      setModel((cur) => cur || data.loaded_model || data.default_model);
    } catch (e) {
      setError('Could not reach the generation engine.');
    }
  }, []);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  // Apply each model's own defaults when the selection changes.
  useEffect(() => {
    if (!spec) return;
    setSize(spec.default_size);
    setSteps(spec.default_steps);
  }, [spec?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const pollState = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await getGenerateState();
        setEngineState(data);
        if (['ready', 'idle', 'error'].includes(data.state)) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          if (data.state === 'error') setError(data.message);
          loadCatalog();
        }
      } catch { /* keep polling */ }
    }, 1000);
  }, [loadCatalog]);

  // A download/load started on this page keeps running in the backend even
  // while another tab is open, so pick it back up on mount instead of showing
  // no progress at all until the user clicks again.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await getGenerateState();
        if (cancelled) return;
        setEngineState(data);
        if (IN_FLIGHT.includes(data.state)) pollState();
      } catch { /* engine unreachable; the catalog call reports it */ }
    })();
    return () => { cancelled = true; };
  }, [pollState]);

  const download = async (id) => {
    setError(null);
    setModel(id);
    // The backend flips to "loading" before returning, so render the progress
    // panel immediately rather than waiting for the first poll tick.
    try {
      const { data } = await loadGenerateModel(id);
      setEngineState(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      return;
    }
    pollState();
  };

  const run = async () => {
    if (!prompt.trim() || busy) return;
    setBusy(true); setError(null); setResult(null); setSaved({});
    pollState();
    try {
      const { data } = await generateImages({
        prompt,
        model,
        num_images: count,
        width: size,
        height: size,
        steps,
        seed: seed === '' ? null : Number(seed),
      });
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Generation failed');
    } finally {
      setBusy(false);
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    }
  };

  const save = async (dataUrl, index) => {
    const dir = await pickDirectory('Choose where to save the image');
    if (!dir) return;
    try {
      const stem = prompt.trim().slice(0, 40).replace(/\s+/g, '-').toLowerCase() || 'needle';
      const { data } = await saveGeneratedImage(dataUrl, dir, `${stem}-${index + 1}`);
      setSaved((s) => ({ ...s, [index]: data.path }));
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not save the image');
    }
  };

  const downloading = ['downloading', 'loading', 'warming'].includes(engineState?.state);
  const pct = engineState?.total ? Math.round((engineState.current / engineState.total) * 100) : null;

  if (catalog && !catalog.available) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="card flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <div className="font-medium text-ink-900">On-device generation unavailable</div>
            <p className="text-sm text-ink-500 mt-1">
              This build does not include the diffusion libraries. You can still connect an
              external generator from the Generators page.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Generate</h1>
        <p className="text-sm text-ink-500 mt-1 flex items-center gap-1.5">
          <Cpu className="h-3.5 w-3.5" />
          Runs on this machine · {catalog?.device ? catalog.device.toUpperCase() : '…'}
          {catalog?.loaded_model && <span>· {catalog.loaded_model} loaded</span>}
        </p>
      </header>

      {/* Model picker */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
        {(catalog?.models || []).map((m) => {
          const selected = model === m.id;
          return (
            <button key={m.id} onClick={() => setModel(m.id)}
              className={`text-left p-4 rounded-2xl border-2 transition-all ${
                selected ? 'border-needle-500 bg-needle-50' : 'border-ink-100 hover:border-ink-200'
              }`}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-ink-900">{m.label}</span>
                {m.downloaded
                  ? <Check className="h-4 w-4 text-emerald-500" />
                  : <Download className="h-4 w-4 text-ink-400" />}
              </div>
              <div className="text-xs text-needle-600 mb-1">{TIER_LABEL[m.tier] || m.tier}</div>
              <p className="text-xs text-ink-500 leading-snug">{m.description}</p>
              <div className="text-xs text-ink-400 mt-2">
                {m.downloaded ? 'Downloaded' : `${formatSize(m.download_mb)} download`}
              </div>
            </button>
          );
        })}
      </div>

      {spec && !spec.downloaded && !downloading && (
        <button onClick={() => download(spec.id)} className="btn btn-secondary w-full mb-5">
          <Download className="h-4 w-4" /> Download {spec.label} ({formatSize(spec.download_mb)})
        </button>
      )}

      {downloading && (
        <div className="card !p-4 mb-5">
          <div className="flex items-center gap-2 text-sm text-ink-700 mb-2">
            <Loader2 className="h-4 w-4 animate-spin text-needle-600" />
            {engineState?.message || 'Preparing…'}
          </div>
          <div className="h-2 w-full bg-ink-100 rounded-full overflow-hidden">
            <div className="h-full bg-needle-500 rounded-full transition-all duration-500"
              style={{ width: pct !== null ? `${pct}%` : '35%' }} />
          </div>
        </div>
      )}

      {/* Prompt + controls */}
      <div className="card mb-5">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) run(); }}
          rows={3}
          placeholder="Describe the image you want…"
          className="w-full resize-none bg-transparent text-ink-900 placeholder-ink-400 focus:outline-none"
        />

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-ink-100">
          <label className="text-xs text-ink-500">
            Size
            <select value={size} onChange={(e) => setSize(Number(e.target.value))}
              className="mt-1 w-full input">
              {(spec?.sizes || [512]).map((s) => <option key={s} value={s}>{s}×{s}</option>)}
            </select>
          </label>
          <label className="text-xs text-ink-500">
            Steps
            <input type="number" min={1} max={spec?.max_steps || 8} value={steps}
              onChange={(e) => setSteps(Number(e.target.value))} className="mt-1 w-full input" />
          </label>
          <label className="text-xs text-ink-500">
            Images
            <input type="number" min={1} max={8} value={count}
              onChange={(e) => setCount(Number(e.target.value))} className="mt-1 w-full input" />
          </label>
          <label className="text-xs text-ink-500">
            Seed
            <div className="mt-1 flex gap-1">
              <input type="number" value={seed} placeholder="random"
                onChange={(e) => setSeed(e.target.value)} className="w-full input" />
              <button type="button" title="Random seed"
                onClick={() => setSeed(String(Math.floor(Math.random() * 2 ** 31)))}
                className="btn btn-secondary btn-sm shrink-0"><Shuffle className="h-3.5 w-3.5" /></button>
            </div>
          </label>
        </div>

        <button onClick={run} disabled={busy || !prompt.trim()}
          className="btn btn-primary w-full mt-4 py-3 disabled:opacity-50">
          {busy
            ? <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</>
            : <><Wand2 className="h-4 w-4" /> Generate</>}
        </button>
        <p className="text-center text-xs text-ink-400 mt-2">
          {spec && !spec.downloaded
            ? `First run downloads ${formatSize(spec.download_mb)} of weights.`
            : 'Tip: press ⌘↵ to generate.'}
        </p>
      </div>

      {error && (
        <div className="card !p-4 mb-5 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
          <span className="text-sm text-red-600 break-words">{error}</span>
        </div>
      )}

      {result && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-medium text-ink-900 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-needle-500" /> Results
            </h2>
            <span className="text-xs text-ink-400 tabular-nums">
              {result.ms_per_image} ms/image · {result.steps} step{result.steps > 1 ? 's' : ''} ·
              {' '}{result.width}×{result.height} · {String(result.device).toUpperCase()}
              {result.seed != null && ` · seed ${result.seed}`}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {result.images.map((img, i) => (
              <div key={i} className="card !p-3">
                <img src={img} alt={`${result.prompt} (${i + 1})`}
                  className="w-full rounded-xl bg-ink-50" />
                {isTauri() && (
                  <button onClick={() => save(img, i)}
                    className="btn btn-secondary btn-sm w-full mt-3">
                    {saved[i]
                      ? <><Check className="h-3.5 w-3.5 text-emerald-500" /> Saved</>
                      : <><Save className="h-3.5 w-3.5" /> Save image</>}
                  </button>
                )}
                {saved[i] && <p className="text-[11px] text-ink-400 mt-1.5 truncate">{saved[i]}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GeneratePage;
