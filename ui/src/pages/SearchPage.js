import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Search, Loader2, AlertCircle, SlidersHorizontal, X, Download,
  ChevronLeft, ChevronRight, ImageOff, Clock, Sparkles,
  FolderOpen, Wand2,
} from 'lucide-react';
import {
  createQuery, search, getSearchLogs, getFile,
  getDirectories, getGenerators, getGeneratorConfig,
} from '../services/api';
import logoImage from '../assets/images/logo.png';

const EXAMPLES = ['a red sports car at sunset', 'golden retriever on a beach', 'city skyline at night', 'plate of sushi'];
const SIZES = ['SMALL', 'MEDIUM', 'LARGE'];

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [imageUrls, setImageUrls] = useState({});
  const [loadingImages, setLoadingImages] = useState(false);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const [showOptions, setShowOptions] = useState(false);
  const [lightbox, setLightbox] = useState(null); // index into results.results
  const [startTime, setStartTime] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [ready, setReady] = useState({ library: true, generator: true, checked: false });
  const urlsRef = useRef({});

  const [config, setConfig] = useState({
    num_images_to_retrieve: 24,
    num_images_to_generate: 1,
    generated_image_size: 'SMALL',
    include_base_images_in_preview: true,
    verbose: false,
  });

  const canSearch = ready.library && ready.generator;

  const checkReadiness = useCallback(async () => {
    let library = false, generator = false;
    try {
      const d = await getDirectories();
      library = (d.data.directories || []).some((x) => x.is_indexed);
    } catch { /* ignore */ }
    try {
      const g = await getGenerators();
      const enabled = getGeneratorConfig().filter((c) => c.enabled).map((c) => c.name);
      generator = (g.data || []).some((e) => enabled.includes(e.name) && e.available);
    } catch { /* ignore */ }
    setReady({ library, generator, checked: true });
  }, []);

  useEffect(() => { loadLogs(); checkReadiness(); }, [checkReadiness]);
  useEffect(() => {
    const onFocus = () => checkReadiness();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [checkReadiness]);
  useEffect(() => { urlsRef.current = imageUrls; }, [imageUrls]);
  useEffect(() => () => {
    Object.values(urlsRef.current).forEach((u) => u?.startsWith?.('blob:') && URL.revokeObjectURL(u));
  }, []);

  useEffect(() => {
    let t;
    if (isSearching && startTime) t = setInterval(() => setElapsed(Date.now() - startTime), 100);
    else setElapsed(0);
    return () => clearInterval(t);
  }, [isSearching, startTime]);

  // Lightbox keyboard nav
  const move = useCallback((dir) => {
    setLightbox((i) => {
      if (i === null || !results?.results?.length) return i;
      const n = results.results.length;
      return (i + dir + n) % n;
    });
  }, [results]);

  useEffect(() => {
    if (lightbox === null) return;
    const onKey = (e) => {
      if (e.key === 'Escape') setLightbox(null);
      else if (e.key === 'ArrowRight') move(1);
      else if (e.key === 'ArrowLeft') move(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightbox, move]);

  const loadLogs = async () => {
    try { const r = await getSearchLogs(); setLogs(r.data.queries || []); } catch { setLogs([]); }
  };

  const fetchImage = async (path) => {
    try {
      const r = await getFile(path);
      return URL.createObjectURL(new Blob([r.data]));
    } catch { return null; }
  };

  const loadImages = async (paths) => {
    setLoadingImages(true);
    // Load in parallel, updating as they arrive.
    await Promise.all(paths.map(async (p) => {
      const url = await fetchImage(p);
      if (url) setImageUrls((prev) => ({ ...prev, [p]: url }));
    }));
    setLoadingImages(false);
  };

  const runSearch = async (q) => {
    const term = (q ?? query).trim();
    if (!term) return;
    if (!canSearch) return;
    setQuery(term);
    setSubmitted(true);
    setIsSearching(true);
    setError(null);
    setResults(null);
    Object.values(urlsRef.current).forEach((u) => u?.startsWith?.('blob:') && URL.revokeObjectURL(u));
    setImageUrls({});

    try {
      const st = Date.now();
      setStartTime(st);
      const { data: q1 } = await createQuery(term);
      const { data } = await search(q1.qid, config);
      setResults({
        results: data.results || [],
        baseImages: data.base_images || [],
        timings: { ...data.timings, frontend_total_time: (Date.now() - st) / 1000 },
      });
      if (data.results?.length) loadImages(data.results);
      loadLogs();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const onSubmit = (e) => { e.preventDefault(); runSearch(); };
  const fileName = (p) => (typeof p === 'string' ? p : p?.id || '').split('/').pop();
  const totalMs = results?.timings?.frontend_total_time
    ? Math.round(results.timings.frontend_total_time * 1000)
    : results?.timings?.total_request_time
    ? Math.round(results.timings.total_request_time * 1000)
    : null;

  // ---- Search bar (shared) ----
  const SearchBar = ({ hero }) => (
    <form onSubmit={onSubmit} className={`relative ${hero ? '' : 'flex-1'}`}>
      <Search className={`absolute left-4 top-1/2 -translate-y-1/2 text-ink-400 ${hero ? 'h-5 w-5' : 'h-[18px] w-[18px]'}`} />
      <input
        autoFocus
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={!canSearch}
        placeholder={canSearch ? "Describe what you're looking for…" : 'Search unavailable — finish setup below'}
        className={`w-full bg-white border border-ink-200 rounded-2xl text-ink-900 placeholder-ink-400
          shadow-card focus:outline-none focus:border-needle-400 focus:ring-4 focus:ring-needle-500/10 transition
          disabled:bg-ink-50 disabled:cursor-not-allowed
          ${hero ? 'pl-12 pr-32 py-4 text-lg' : 'pl-11 pr-28 py-3 text-sm'}`}
      />
      <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
        {isSearching && elapsed > 0 && (
          <span className="text-xs text-ink-400 tabular-nums pr-1">{(elapsed / 1000).toFixed(1)}s</span>
        )}
        <button type="button" onClick={() => setShowOptions((v) => !v)}
          className={`btn btn-ghost ${hero ? '' : 'btn-sm'} !px-2`} title="Search options">
          <SlidersHorizontal className="h-[18px] w-[18px]" />
        </button>
        <button type="submit" disabled={isSearching || !query.trim() || !canSearch} className={`btn btn-primary ${hero ? '' : 'btn-sm'}`}>
          {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          <span className={hero ? '' : 'hidden sm:inline'}>Search</span>
        </button>
      </div>
    </form>
  );

  const SetupNotice = () => {
    if (!ready.checked || canSearch) return null;
    return (
      <div className="mt-6 card !p-4 border-amber-200 bg-amber-50 text-left animate-fade-up">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="h-4 w-4 text-amber-600" />
          <span className="text-sm font-medium text-amber-800">Finish setup to start searching</span>
        </div>
        <div className="space-y-2">
          {!ready.library && (
            <Link to="/directories" className="flex items-center gap-2 text-sm text-amber-800 hover:underline">
              <FolderOpen className="h-4 w-4" /> Add and index an image folder in <span className="font-medium">Library</span>
            </Link>
          )}
          {!ready.generator && (
            <Link to="/generators" className="flex items-center gap-2 text-sm text-amber-800 hover:underline">
              <Wand2 className="h-4 w-4" /> Connect or enable a generator in <span className="font-medium">Generators</span>
            </Link>
          )}
        </div>
      </div>
    );
  };

  const OptionsPanel = () => (
    <div className="mt-3 card !p-4 animate-fade-up">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <label className="block">
          <span className="text-xs font-medium text-ink-500">Results</span>
          <input type="number" min="1" max="100" value={config.num_images_to_retrieve}
            onChange={(e) => setConfig((c) => ({ ...c, num_images_to_retrieve: parseInt(e.target.value) || 24 }))}
            className="input mt-1 !py-2" />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-ink-500">Images to generate</span>
          <input type="number" min="1" max="8" value={config.num_images_to_generate}
            onChange={(e) => setConfig((c) => ({ ...c, num_images_to_generate: parseInt(e.target.value) || 1 }))}
            className="input mt-1 !py-2" />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-ink-500">Generated size</span>
          <select value={config.generated_image_size}
            onChange={(e) => setConfig((c) => ({ ...c, generated_image_size: e.target.value }))}
            className="input mt-1 !py-2">
            {SIZES.map((s) => <option key={s} value={s}>{s[0] + s.slice(1).toLowerCase()}</option>)}
          </select>
        </label>
      </div>
    </div>
  );

  // ---- HERO (empty) state ----
  if (!submitted) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center px-6 py-16">
        <div className="w-full max-w-2xl text-center animate-fade-up">
          <img src={logoImage} alt="" className="h-16 w-16 mx-auto mb-6 object-contain drop-shadow" />
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900">
            Search your images <span className="text-gradient">in plain language</span>
          </h1>
          <p className="mt-2 text-ink-500">Describe a scene, object, or mood — Needle finds the closest matches.</p>

          <div className="mt-8">{SearchBar({ hero: true })}</div>
          {showOptions && OptionsPanel()}
          {SetupNotice()}

          <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => runSearch(ex)} disabled={!canSearch}
                className="chip disabled:opacity-40 disabled:cursor-not-allowed">{ex}</button>
            ))}
          </div>

          {logs.length > 0 && (
            <div className="mt-10 text-left">
              <div className="flex items-center gap-2 text-xs font-medium text-ink-400 mb-2">
                <Clock className="h-3.5 w-3.5" /> RECENT
              </div>
              <div className="flex flex-wrap gap-2">
                {logs.slice(0, 8).map((l) => (
                  <button key={l.qid} onClick={() => runSearch(l.query)} disabled={!canSearch}
                    className="chip disabled:opacity-40 disabled:cursor-not-allowed">{l.query}</button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ---- RESULTS state ----
  const list = results?.results || [];
  return (
    <div className="min-h-full flex flex-col">
      {/* Sticky search header */}
      <div className="sticky top-0 z-20 glass border-b border-ink-200/70">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-3">
          <button onClick={() => { setSubmitted(false); setResults(null); setError(null); }}
            className="shrink-0 flex items-center gap-2 group" title="Home">
            <img src={logoImage} alt="Needle" className="h-8 w-8 object-contain" />
          </button>
          {SearchBar({})}
        </div>
        {showOptions && <div className="max-w-6xl mx-auto px-6 pb-3">{OptionsPanel()}</div>}
      </div>

      <div className="max-w-6xl w-full mx-auto px-6 py-6 flex-1">
        {/* Result meta */}
        {(list.length > 0 || (!isSearching && results)) && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-ink-500">
              {list.length > 0
                ? <><span className="font-medium text-ink-800">{list.length}</span> results for <span className="font-medium text-ink-800">“{query}”</span></>
                : <>No results for <span className="font-medium text-ink-800">“{query}”</span></>}
            </p>
            {totalMs !== null && (
              <span className="text-xs text-ink-400 tabular-nums">{totalMs} ms</span>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card !p-4 border-red-200 bg-red-50 flex items-start gap-3 animate-fade-up">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-800">{error}</p>
              {String(error).includes('generator') || String(error).includes('engine') ? (
                <p className="text-xs text-red-600/80 mt-1">
                  Configure a generator in <span className="font-medium">Generators</span>, or run the generator service and set its URL.
                </p>
              ) : null}
            </div>
          </div>
        )}

        {/* Loading skeleton */}
        {isSearching && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="aspect-square rounded-xl bg-ink-100 animate-pulse" />
            ))}
          </div>
        )}

        {/* Generated (base) images */}
        {!isSearching && results?.baseImages?.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 text-xs font-medium text-ink-400 mb-2">
              <Sparkles className="h-3.5 w-3.5" /> GENERATED PREVIEW
            </div>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {results.baseImages.map((b, i) => (
                <img key={i} src={typeof b === 'string' ? (b.startsWith('data:') ? b : `data:image/png;base64,${b}`) : ''}
                  alt="" className="h-24 w-24 rounded-lg object-cover border border-ink-200 shrink-0" />
              ))}
            </div>
          </div>
        )}

        {/* Results grid */}
        {!isSearching && list.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {list.map((r, i) => {
              const path = typeof r === 'string' ? r : r.id || r;
              const url = imageUrls[path];
              return (
                <button key={i} onClick={() => url && setLightbox(i)}
                  className="group relative aspect-square rounded-xl overflow-hidden bg-ink-100 border border-ink-200
                    focus:outline-none focus-visible:ring-4 focus-visible:ring-needle-500/20 animate-fade-up"
                  style={{ animationDelay: `${Math.min(i * 20, 300)}ms` }}>
                  {url ? (
                    <img src={url} alt={fileName(path)} loading="lazy"
                      className="w-full h-full object-cover transition duration-300 group-hover:scale-[1.04]" />
                  ) : (
                    <div className="w-full h-full grid place-items-center">
                      {loadingImages ? <Loader2 className="h-5 w-5 text-ink-300 animate-spin" /> : <ImageOff className="h-6 w-6 text-ink-300" />}
                    </div>
                  )}
                  <div className="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/60 to-transparent
                    opacity-0 group-hover:opacity-100 transition">
                    <p className="text-[11px] text-white/90 truncate text-left">{fileName(path)}</p>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Empty (no results, not searching) */}
        {!isSearching && results && list.length === 0 && !error && (
          <div className="text-center py-20 text-ink-400">
            <ImageOff className="h-10 w-10 mx-auto mb-3" />
            <p className="text-sm">Try a different description, or add more folders in <span className="font-medium text-ink-600">Library</span>.</p>
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightbox !== null && list[lightbox] && (
        <div className="fixed inset-0 z-50 bg-ink-950/90 backdrop-blur-sm flex flex-col animate-fade-in"
          onClick={() => setLightbox(null)}>
          <div className="flex items-center justify-between px-5 h-14 text-white/80 shrink-0">
            <span className="text-sm truncate">{fileName(list[lightbox])} · {lightbox + 1}/{list.length}</span>
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <a href={imageUrls[list[lightbox]]} download={fileName(list[lightbox])}
                className="btn btn-ghost !text-white/80 hover:!bg-white/10 btn-sm" title="Download">
                <Download className="h-4 w-4" />
              </a>
              <button onClick={() => setLightbox(null)} className="btn btn-ghost !text-white/80 hover:!bg-white/10 btn-sm">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="flex-1 flex items-center justify-center px-4 pb-6 min-h-0" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => move(-1)} className="p-2 text-white/60 hover:text-white shrink-0">
              <ChevronLeft className="h-8 w-8" />
            </button>
            <img src={imageUrls[list[lightbox]]} alt=""
              className="max-h-full max-w-full object-contain rounded-lg shadow-pop animate-scale-in" />
            <button onClick={() => move(1)} className="p-2 text-white/60 hover:text-white shrink-0">
              <ChevronRight className="h-8 w-8" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
