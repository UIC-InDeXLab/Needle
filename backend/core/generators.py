"""In-process image generation orchestrator.

Maintains a registry of generation engines and routes generation requests. The
local on-device engine is the default; API engines are used when the requested
engine is selected and credentials are available. On failure, falls back to the
first available engine (typically local) when ``use_fallback`` is set.
"""

from typing import Dict, List, Tuple

from PIL import Image

from core.generation.api_engines import OpenAIEngine, StabilityEngine
from core.generation.base import GenerationEngine
from core.generation.credentials import credentials_set, set_credentials
from core.generation.local_engine import LocalDiffusionEngine
from core.generation import preferences
from core.singleton import Singleton
from monitoring import logger
from settings import settings


@Singleton
class ImageGenerator:
    def __init__(self):
        # Registration order defines fallback preference. The built-in on-device
        # engine comes first: it needs no credentials and no network once its
        # weights are cached. The API engines are used when configured.
        engines: List[GenerationEngine] = [
            LocalDiffusionEngine(),
            OpenAIEngine(),
            StabilityEngine(),
        ]
        self._engines: Dict[str, GenerationEngine] = {e.name: e for e in engines}
        self._order = [e.name for e in engines]
        # Map legacy/alternate ids (e.g. "remote") to their engine instance so
        # older stored configs and search requests keep working after rebrands.
        for e in engines:
            for alias in getattr(e, "aliases", []):
                self._engines.setdefault(alias, e)

    # -- introspection ----------------------------------------------------
    def get_available_engines(self) -> List[Dict]:
        infos = []
        for name in self._order:
            engine = self._engines[name]
            required = [p["name"] for p in engine.required_params]
            infos.append(engine.info(credentials_set(name, required) if required else True))
        return infos

    def get_capabilities(self, engine_name: str, params: Dict = None) -> Dict:
        engine = self._engines.get(str(engine_name).lower())
        if engine is None:
            raise ValueError(f"Unknown engine '{engine_name}'")
        fn = getattr(engine, "capabilities", None)
        return fn(params or {}) if callable(fn) else {}

    def set_credentials(self, engine_name: str, params: Dict[str, str]) -> None:
        if engine_name not in self._engines:
            raise ValueError(f"Unknown engine '{engine_name}'")
        set_credentials(engine_name, params)

    # -- shared preferences ----------------------------------------------
    def get_preferences(self) -> Dict:
        """Enabled engines, their order and the fallback flag.

        Stored server-side so the desktop app and needlectl always agree; each
        entry is annotated with whether the engine can actually run right now.
        """
        prefs = preferences.load(self._order, settings.generators.default_engine)
        availability = {name: self._engines[name].is_available() for name in self._order}
        for entry in prefs["engines"]:
            entry["available"] = availability.get(entry["name"], False)
            # An engine that cannot run must not read as enabled: search uses
            # this to decide whether it is ready to run at all.
            entry["enabled"] = entry["enabled"] and entry["available"]
        return prefs

    def set_preferences(self, engines: List[Dict], fallback: bool) -> Dict:
        known = set(self._order)
        unknown = [e.get("name") for e in engines or [] if e.get("name") not in known
                   and e.get("name") not in self._engines]
        if unknown:
            raise ValueError(f"Unknown engine(s): {', '.join(str(u) for u in unknown)}")
        preferences.save(engines, fallback)
        return self.get_preferences()

    def update_preference(self, name: str, **kwargs) -> Dict:
        if name not in self._engines:
            raise ValueError(f"Unknown engine '{name}'")
        preferences.update_engine(name, **kwargs)
        return self.get_preferences()

    def local_engine(self) -> LocalDiffusionEngine:
        return self._engines[LocalDiffusionEngine.name]

    # -- generation -------------------------------------------------------
    def _first_available(self) -> GenerationEngine:
        default = settings.generators.default_engine
        candidates = [default] + [n for n in self._order if n != default]
        for name in candidates:
            engine = self._engines.get(name)
            if engine and engine.is_available():
                return engine
        raise RuntimeError("No image generation engine is available")

    def generate(self, generation_config: Dict) -> List[Tuple[Image.Image, str]]:
        engines_cfg = generation_config.get("engines") or []
        num_images = generation_config.get("num_images", 1)
        image_size = generation_config.get("image_size", "MEDIUM")
        fallback_prompt = generation_config.get("prompt", "")

        # When the caller does not name engines, fall back to the stored
        # preferences rather than to whatever happens to be first. This is what
        # lets a client simply say "search" and get the user's configured chain.
        requested_fallback = generation_config.get("use_fallback")
        if not engines_cfg:
            stored = preferences.search_engines(self._order, settings.generators.default_engine)
            engines_cfg = stored["engines"]
            use_fallback = stored["fallback"] if requested_fallback is None else requested_fallback
        else:
            use_fallback = True if requested_fallback is None else requested_fallback

        # Build the ordered candidate chain from the config. Order defines
        # priority: the first engine is tried first.
        candidates: List[Tuple[GenerationEngine, Dict]] = []
        for ec in engines_cfg:
            engine = self._engines.get(str(ec.get("name", "")).lower())
            if engine:
                candidates.append((engine, ec))
        if not candidates:
            engine = self._first_available()
            candidates.append((engine, {"prompt": fallback_prompt, "params": {}}))

        # Without fallback, only the first (top-priority) engine is eligible.
        if not use_fallback:
            candidates = candidates[:1]

        last_error = None
        for engine, ec in candidates:
            prompt = ec.get("prompt") or fallback_prompt
            params = ec.get("params") or {}
            try:
                images = engine.generate(prompt, num_images, image_size, params)
                return [(img, engine.name) for img in images]
            except Exception as exc:
                last_error = exc
                logger.error(f"Engine '{engine.name}' failed to generate: {exc}", exc_info=True)
                continue

        raise RuntimeError(
            f"Image generation failed: {last_error}" if last_error
            else "Image generation produced no images"
        )
