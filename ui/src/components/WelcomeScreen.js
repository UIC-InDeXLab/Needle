import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Zap, Scale, Target, Cpu, Sparkles, Loader2, AlertCircle, Check } from 'lucide-react';
import { getSetupStatus, getSetupOptions, configureSetup } from '../services/api';
import logoImage from '../assets/images/logo.png';

const PROFILE_ICONS = { fast: Zap, balanced: Scale, accurate: Target };

const WelcomeScreen = ({ onReady }) => {
  const [phase, setPhase] = useState('connecting'); // connecting | choose | initializing | error
  const [options, setOptions] = useState(null);
  const [selectedProfile, setSelectedProfile] = useState('fast');
  // Opt in to the GPU by default; unchecked below if none is detected.
  const [useGpu, setUseGpu] = useState(true);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const stopPolling = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await getSetupStatus();
        setStatus(data);
        if (data.ready) { stopPolling(); onReady(); }
        else if (data.state === 'error') { stopPolling(); setError(data.message || 'Initialization failed'); setPhase('error'); }
      } catch { /* keep polling */ }
    }, 1000);
  }, [onReady]);

  useEffect(() => {
    let cancelled = false;
    const connect = async () => {
      try {
        const { data } = await getSetupStatus();
        if (cancelled) return;
        setStatus(data);
        if (data.ready) { onReady(); return; }
        const opts = await getSetupOptions();
        if (cancelled) return;
        setOptions(opts.data);
        setSelectedProfile(opts.data.default_profile || 'fast');
        setUseGpu(Boolean(opts.data.gpu_available));
        if (data.configured) { setPhase('initializing'); startPolling(); }
        else setPhase('choose');
      } catch {
        setTimeout(connect, 1200);
      }
    };
    connect();
    return () => { cancelled = true; stopPolling(); };
  }, [onReady, startPolling]);

  const start = async () => {
    setError(null); setPhase('initializing');
    try { const { data } = await configureSetup(selectedProfile, useGpu); setStatus(data); startPolling(); }
    catch (e) { setError(e.response?.data?.detail || e.message || 'Failed to start setup'); setPhase('error'); }
  };

  const gpuAvailable = options?.gpu_available;

  // ---- connecting ----
  if (phase === 'connecting') {
    return (
      <div className="min-h-screen grid place-items-center bg-ink-900 text-ink-300">
        <div className="text-center animate-fade-in">
          <img src={logoImage} alt="" className="h-12 w-12 mx-auto mb-4 object-contain opacity-90" />
          <Loader2 className="h-5 w-5 animate-spin text-needle-400 mx-auto" />
          <p className="mt-3 text-sm text-ink-500">Starting Needle…</p>
        </div>
      </div>
    );
  }

  // ---- initializing ----
  if (phase === 'initializing') {
    const total = status?.total || 0, current = status?.current || 0;
    const pct = total > 0 ? Math.round((current / total) * 100) : null;
    return (
      <div className="min-h-screen grid place-items-center bg-ink-900 px-6">
        <div className="w-full max-w-md text-center animate-fade-up">
          <div className="h-14 w-14 rounded-2xl bg-needle-500/10 grid place-items-center mx-auto mb-5">
            <Loader2 className="h-6 w-6 animate-spin text-needle-400" />
          </div>
          <h2 className="text-lg font-semibold text-white">Setting things up</h2>
          <p className="text-sm text-ink-400 mt-1 mb-5 min-h-[20px]">{status?.message || 'Preparing…'}</p>
          <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-needle-500 rounded-full transition-all duration-500"
              style={{ width: pct !== null ? `${pct}%` : '35%' }} />
          </div>
          <p className="mt-4 text-xs text-ink-600">One-time download — this can take a few minutes.</p>
        </div>
      </div>
    );
  }

  // ---- error ----
  if (phase === 'error') {
    return (
      <div className="min-h-screen grid place-items-center bg-ink-900 px-6">
        <div className="w-full max-w-md card animate-scale-in">
          <div className="flex items-center gap-2 text-red-600 mb-2">
            <AlertCircle className="h-5 w-5" /><span className="font-semibold">Setup failed</span>
          </div>
          <p className="text-sm text-ink-600 mb-5 break-words">{error}</p>
          <button onClick={() => setPhase('choose')} className="btn btn-primary w-full">Try again</button>
        </div>
      </div>
    );
  }

  // ---- choose ----
  return (
    <div className="min-h-screen bg-ink-900 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-14">
        <div className="text-center mb-10 animate-fade-up">
          <img src={logoImage} alt="" className="h-14 w-14 mx-auto mb-5 object-contain" />
          <h1 className="text-3xl font-semibold tracking-tight text-white">Welcome to Needle</h1>
          <p className="mt-2 text-ink-400">Choose how thoroughly Needle should understand your images.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {(options?.profiles || []).map((p) => {
            const Icon = PROFILE_ICONS[p.id] || Zap;
            const selected = selectedProfile === p.id;
            return (
              <button key={p.id} onClick={() => setSelectedProfile(p.id)}
                className={`text-left p-5 rounded-2xl border-2 transition-all ${
                  selected ? 'border-needle-500 bg-white shadow-pop' : 'border-white/10 bg-white/5 hover:bg-white/10'
                }`}>
                <div className="flex items-center justify-between mb-3">
                  <Icon className={`h-6 w-6 ${selected ? 'text-needle-600' : 'text-ink-400'}`} />
                  {selected && <span className="h-5 w-5 rounded-full bg-needle-600 grid place-items-center"><Check className="h-3 w-3 text-white" /></span>}
                </div>
                <div className={`font-semibold ${selected ? 'text-ink-900' : 'text-white'}`}>{p.label}</div>
                <div className={`text-xs mt-0.5 ${selected ? 'text-needle-600' : 'text-ink-500'}`}>{p.num_models} model{p.num_models > 1 ? 's' : ''}</div>
                <p className={`text-sm mt-2 ${selected ? 'text-ink-600' : 'text-ink-400'}`}>{p.description}</p>
              </button>
            );
          })}
        </div>

        {gpuAvailable ? (
          <label className="flex items-start gap-3 p-4 rounded-2xl border-2 border-white/10 bg-white/5 cursor-pointer mb-8 hover:bg-white/10 transition">
            <input type="checkbox" checked={useGpu} onChange={(e) => setUseGpu(e.target.checked)}
              className="mt-1 rounded border-ink-500 text-needle-600 focus:ring-needle-500 bg-transparent" />
            <span>
              <span className="font-medium text-white flex items-center gap-1.5"><Sparkles className="h-4 w-4 text-needle-400" />Use my GPU</span>
              <span className="block text-sm text-ink-400 mt-1">A compatible GPU was detected — enables much faster indexing and generation.</span>
            </span>
          </label>
        ) : (
          <div className="flex items-center gap-2 p-4 rounded-2xl border border-white/10 bg-white/5 mb-8 text-ink-400">
            <Cpu className="h-5 w-5" /><span className="text-sm">No compatible GPU detected — Needle will run in CPU mode.</span>
          </div>
        )}

        <button onClick={start} className="btn btn-primary w-full py-3.5 text-base">
          Download models &amp; continue
        </button>
        <p className="text-center text-xs text-ink-500 mt-3">You can change this later on the Status page.</p>
      </div>
    </div>
  );
};

export default WelcomeScreen;
