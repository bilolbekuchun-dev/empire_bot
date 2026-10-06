"""
Day/Night Presentation Layer (Redis game).

Presentation ONLY -- this module NEVER changes game state. Callers must
follow the safe order:

    1. transition game state
    2. persist the new phase
    3. confirm the transition succeeded
    4. send the presentation (this module)
    5. send phase text

Delivery is idempotent: each ``(game, event, number)`` presentation is
delivered at most once (Redis ``SET NX`` guard + in-process fallback), so
repeated callbacks / retries / concurrent transitions cannot spam the group.

Any Telegram failure is logged and swallowed -- a media failure must never
raise into, or corrupt, the game loop.

Media is configured via ``presentation_media.json`` (file_id / path) with
environment variable overrides; bundled images live in ``Empire/gifs``.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.database import redis_client as r

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------
EVENT_START = "start"
EVENT_DAY = "day"
EVENT_NIGHT = "night"
EVENTS = (EVENT_START, EVENT_DAY, EVENT_NIGHT)

STATUS_SENT = "sent"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

# Idempotency window (matches typical game lifetime).
_PRESENT_TTL = 86400
DEFAULT_LANG = "uz"

# --------------------------------------------------------------------------
# Localized announcement texts (uz / ru / en / tr).
# These mirror the existing inline-dict localization used by night_engine.py.
# --------------------------------------------------------------------------
TEXTS = {
    "uz": {
        "start_title": "🎮 <b>O'yin boshlandi!</b>",
        "phase_night": "Boshlang'ich faza: 🌙 <b>TUN {n}</b>",
        "phase_day": "Boshlang'ich faza: ☀️ <b>KUN {n}</b>",
        "night_title": "🌚 🌃 <b>TUN {n}</b>",
        "night_body": "Ko'chaga faqat jasur va qo'rqmas odamlar chiqishdi. Ertalab tirik qolganlarni sanaymiz...",
        "day_title": "Xayrli tong 🌝\n🌄 <b>KUN {n}</b>",
        "day_body": "Shamollar tundagi mish-mishlarni butun shaharga yetkazmoqda..",
    },
    "ru": {
        "start_title": "🎮 <b>Игра началась!</b>",
        "phase_night": "Начальная фаза: 🌙 <b>НОЧЬ {n}</b>",
        "phase_day": "Начальная фаза: ☀️ <b>ДЕНЬ {n}</b>",
        "night_title": "🌚 🌃 <b>НОЧЬ {n}</b>",
        "night_body": "На улицу вышли только смелые и бесстрашные люди. Утром посчитаем выживших...",
        "day_title": "Доброе утро 🌝\n🌄 <b>ДЕНЬ {n}</b>",
        "day_body": "Ветер разносит ночные слухи по всему городу..",
    },
    "en": {
        "start_title": "🎮 <b>The game has started!</b>",
        "phase_night": "Starting phase: 🌙 <b>NIGHT {n}</b>",
        "phase_day": "Starting phase: ☀️ <b>DAY {n}</b>",
        "night_title": "🌚 🌃 <b>NIGHT {n}</b>",
        "night_body": "Only the brave and fearless went out into the streets. We will count the survivors in the morning...",
        "day_title": "Good morning 🌝\n🌄 <b>DAY {n}</b>",
        "day_body": "The wind carries the night's rumors across the whole city..",
    },
    "tr": {
        "start_title": "🎮 <b>Oyun başladı!</b>",
        "phase_night": "Başlangıç fazı: 🌙 <b>GECE {n}</b>",
        "phase_day": "Başlangıç fazı: ☀️ <b>GÜNDÜZ {n}</b>",
        "night_title": "🌚 🌃 <b>GECE {n}</b>",
        "night_body": "Sokaklara sadece cesur ve korkusuz insanlar çıktı. Sabah hayatta kalanları sayacağız...",
        "day_title": "Günaydın 🌝\n🌄 <b>GÜNDÜZ {n}</b>",
        "day_body": "Rüzgar gecenin dedikodularını tüm şehre yayıyor..",
    },
}


def _pick_lang(lang: Optional[str]) -> str:
    code = (lang or "").lower()
    return code if code in TEXTS else DEFAULT_LANG


def build_text(event: str, number: int, lang: str = DEFAULT_LANG, phase: str = "night") -> str:
    """Build the localized announcement text for an event."""
    t = TEXTS[_pick_lang(lang)]
    if event == EVENT_START:
        key = "phase_night" if phase == "night" else "phase_day"
        return t["start_title"] + "\n" + t[key].format(n=number)
    if event == EVENT_NIGHT:
        return t["night_title"].format(n=number) + "\n" + t["night_body"]
    if event == EVENT_DAY:
        return t["day_title"].format(n=number) + "\n" + t["day_body"]
    raise ValueError(f"unknown presentation event: {event!r}")


# --------------------------------------------------------------------------
# Media configuration
# --------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parents[2]          # Empire/
_MEDIA_JSON = Path(__file__).resolve().parent / "presentation_media.json"
_ANIMATION_EXT = (".gif", ".mp4", ".webm")


@dataclass
class Media:
    """A presentation media reference. ``kind`` is photo/animation/video/none."""
    kind: str = "none"
    value: Optional[str] = None

    def __bool__(self) -> bool:
        return self.kind != "none" and bool(self.value)


def _infer_kind(value: Optional[str], declared: Optional[str] = None) -> str:
    if declared in ("photo", "animation", "video"):
        return declared
    v = (value or "").lower()
    if v.endswith(_ANIMATION_EXT):
        return "animation"
    return "photo"


def _load_media_config() -> dict:
    """Load the optional operator-managed media config (never raises)."""
    try:
        return json.loads(_MEDIA_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_local_path(path: Optional[str]) -> Optional[Path]:
    if not path:
        return None
    cand = Path(path)
    if not cand.is_absolute():
        cand = _BASE_DIR / path
    try:
        return cand if cand.exists() else None
    except Exception:
        return None


def resolve_media(event: str, phase: str = "night") -> Media:
    """
    Resolve the media for an event.

    Priority (highest first):
      1. env override   MAFIA_<EVENT>_MEDIA (+ optional MAFIA_<EVENT>_MEDIA_TYPE)
      2. config file    presentation_media.json  ->  {"file_id": ..., "path": ...}
      3. bundled asset  Empire/gifs/{day,night}.jpg

    ``start`` falls back to the current phase's media when no dedicated start
    media is configured. Returns ``Media("none", None)`` when nothing is
    available (caller then sends text only).
    """
    lookup = event
    if event == EVENT_START and phase in (EVENT_DAY, EVENT_NIGHT):
        lookup = phase

    # 1) environment override
    env_val = os.getenv(f"MAFIA_{event.upper()}_MEDIA")
    if env_val:
        env_type = os.getenv(f"MAFIA_{event.upper()}_MEDIA_TYPE")
        return Media(_infer_kind(env_val, env_type), env_val)

    # 2) config file (start may have a dedicated entry, else falls back to phase)
    cfg_all = _load_media_config()
    keys = [event] if event != EVENT_START else [EVENT_START, lookup]
    for cfg_key in keys:
        cfg = cfg_all.get(cfg_key) or {}
        file_id = (cfg.get("file_id") or "").strip()
        if file_id:
            return Media(_infer_kind(file_id, cfg.get("type")), file_id)
        path = _resolve_local_path(cfg.get("path"))
        if path:
            return Media(_infer_kind(str(path), cfg.get("type")), str(path))

    # 3) bundled default assets
    default_name = "day.jpg" if lookup == EVENT_DAY else "night.jpg"
    bundled = _resolve_local_path(f"gifs/{default_name}")
    if bundled:
        return Media("photo", str(bundled))

    return Media("none", None)


from collections import OrderedDict

# --------------------------------------------------------------------------
# Idempotency (LRU cache to prevent memory leaks)
# --------------------------------------------------------------------------
_sent_memory: OrderedDict = OrderedDict()
_MAX_SENT_MEMORY = 2000


def _remember_sent_key(key: str) -> None:
    _sent_memory[key] = True
    _sent_memory.move_to_end(key)
    while len(_sent_memory) > _MAX_SENT_MEMORY:
        _sent_memory.popitem(last=False)


def reset_presentation_cache() -> None:
    """Clear the in-process duplicate guard (used by tests / restart)."""
    _sent_memory.clear()


def _idem_key(game_id, event: str, number: int) -> str:
    return f"game:{game_id}:presented:{event}:{number}"


async def _acquire_slot(key: str) -> bool:
    """
    Atomically claim the right to send one presentation.

    Uses Redis SET NX; if Redis is unavailable, falls back to an in-process
    guard so duplicates are still prevented within this process.
    """
    if key in _sent_memory:
        return False
    try:
        ok = await r.set(key, "1", nx=True, ex=_PRESENT_TTL)
        if ok:
            _remember_sent_key(key)
            return True
        return False
    except Exception as exc:  # Redis down -> best-effort in-memory guard
        logger.warning("presentation idempotency check failed (%s): %s", key, exc)
        _remember_sent_key(key)
        return True


# --------------------------------------------------------------------------
# Delivery
# --------------------------------------------------------------------------
async def _send_media(bot, chat_id, media: Media, text: str, reply_markup) -> None:
    """Send media+caption. Raises on failure (handled by caller)."""
    if media.kind == "animation":
        await bot.send_animation(chat_id, media.value, caption=text,
                                 parse_mode="HTML", reply_markup=reply_markup)
    elif media.kind == "video":
        await bot.send_video(chat_id, media.value, caption=text,
                             parse_mode="HTML", reply_markup=reply_markup)
    elif media.kind == "photo":
        await bot.send_photo(chat_id, media.value, caption=text,
                             parse_mode="HTML", reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)


async def send_presentation(
    bot,
    chat_id: int,
    event: str,
    number: int,
    game_id,
    lang: str = DEFAULT_LANG,
    phase: str = "night",
    reply_markup=None,
) -> dict:
    """
    Send one idempotent Day/Night/start presentation.

    Returns a dict: {"status": sent|skipped|failed, "text": str, "error": ...}.
    Never raises -- a Telegram failure is logged and the game continues.
    """
    text = build_text(event, number, lang, phase)
    key = _idem_key(game_id, event, number)

    if not await _acquire_slot(key):
        return {"status": STATUS_SKIPPED, "text": text, "error": None, "media": False}

    media = resolve_media(event, phase)
    try:
        await _send_media(bot, chat_id, media, text, reply_markup)
        if media.kind != "none":
            _remember_file_id(event, media)
        return {"status": STATUS_SENT, "text": text, "error": None,
                "media": media.kind != "none"}
    except Exception as exc:
        # Media (or the combined send) failed -> fall back to a text-only message.
        logger.warning(
            "presentation send failed (game=%s event=%s n=%s): %s",
            game_id, event, number, exc,
        )
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)
            return {"status": STATUS_SENT, "text": text, "error": str(exc), "media": False}
        except Exception as exc2:
            logger.error(
                "presentation text fallback failed (game=%s event=%s n=%s): %s",
                game_id, event, number, exc2,
            )
            return {"status": STATUS_FAILED, "text": text, "error": str(exc2), "media": False}


def _remember_file_id(event: str, media: Media) -> None:
    """
    Best-effort note of the media used, so operators can later promote a
    local asset to a Telegram file_id without code changes. Never raises.
    """
    logger.debug("presentation media used for %s: %s (%s)", event, media.value, media.kind)


# --------------------------------------------------------------------------
# Language resolution (uses the existing ``User.lang`` field)
# --------------------------------------------------------------------------
async def resolve_game_lang(game_id) -> str:
    """Resolve the announcement language from the game creator's ``User.lang``."""
    try:
        from utils.redis_game.repositories.game_repository import game_repository as game_repo
        from models.user import User

        gs = await game_repo.load_game(game_id)
        if gs:
            user = await User.get_or_none(user_id=gs.creator_id)
            if user and user.lang:
                return _pick_lang(user.lang)
    except Exception as exc:
        logger.debug("resolve_game_lang failed for %s: %s", game_id, exc)
    return DEFAULT_LANG


# --------------------------------------------------------------------------
# Convenience wrappers used by the game flow
# --------------------------------------------------------------------------
async def send_game_start_presentation(bot, chat_id, game_id, phase: str = "night",
                                       number: int = 1, reply_markup=None) -> dict:
    lang = await resolve_game_lang(game_id)
    return await send_presentation(bot, chat_id, EVENT_START, number, game_id,
                                   lang=lang, phase=phase, reply_markup=reply_markup)


async def send_night_presentation(bot, chat_id, game_id, number: int,
                                  reply_markup=None) -> dict:
    lang = await resolve_game_lang(game_id)
    return await send_presentation(bot, chat_id, EVENT_NIGHT, number, game_id,
                                   lang=lang, phase="night", reply_markup=reply_markup)


async def send_day_presentation(bot, chat_id, game_id, number: int,
                                reply_markup=None) -> dict:
    lang = await resolve_game_lang(game_id)
    return await send_presentation(bot, chat_id, EVENT_DAY, number, game_id,
                                   lang=lang, phase="day", reply_markup=reply_markup)