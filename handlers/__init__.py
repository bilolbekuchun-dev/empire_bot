from aiogram import Router
from . import game, other_handlers, admin, settings, geroy_handlers, paralar, role_config, airdrop_handlers

router = Router()

router.include_router(paralar.router)
router.include_router(other_handlers.router)
router.include_router(game.router)
router.include_router(admin.router)
router.include_router(settings.router)
router.include_router(geroy_handlers.router)
router.include_router(role_config.router)
router.include_router(airdrop_handlers.router)