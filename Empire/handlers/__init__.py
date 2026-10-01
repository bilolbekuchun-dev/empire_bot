from aiogram import Router
from . import game, other_handlers, admin, settings, geroy_handlers, paralar, role_config
from utils.redis_game.night_callbacks import router as night_cb_router

router = Router()

router.include_router(night_cb_router)
router.include_router(paralar.router)
router.include_router(other_handlers.router)
router.include_router(game.router)
router.include_router(admin.router)
router.include_router(settings.router)
router.include_router(geroy_handlers.router)
router.include_router(role_config.router)