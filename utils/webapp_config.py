import config

# Defalt: WebApp vaqtincha ta'mir va takomillashtirish sababli o'chirilgan (False)
_webapp_active = getattr(config, "IS_WEBAPP_ACTIVE", False)

async def is_webapp_active() -> bool:
    global _webapp_active
    try:
        from utils.database import get_redis_client
        r = await get_redis_client()
        val = await r.get("settings:webapp_active")
        if val is not None:
            _webapp_active = (val == "1" or str(val).lower() == "true")
            return _webapp_active
    except Exception:
        pass
    return getattr(config, "IS_WEBAPP_ACTIVE", _webapp_active)

async def set_webapp_active(status: bool) -> bool:
    global _webapp_active
    _webapp_active = status
    config.IS_WEBAPP_ACTIVE = status
    try:
        from utils.database import get_redis_client
        r = await get_redis_client()
        await r.set("settings:webapp_active", "1" if status else "0")
    except Exception:
        pass
    return status

async def get_webapp_button_text() -> str:
    active = await is_webapp_active()
    return "🌐 WebApp: 🟢 Yoqilgan" if active else "🌐 WebApp: 🔴 O'chirilgan"
