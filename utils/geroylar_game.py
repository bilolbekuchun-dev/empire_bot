from aiogram import Router, F, Bot
from models.game_data import GamePhase, GeroyAction, Chat, GamePlayer
from aiogram.types import Message, CallbackQuery
from models.game_data import Geroys
from models.user import User, Profile
from aiogram.fsm.context import FSMContext
from keyboards.game_keyboard import geroy_action_btn, geroy_action_type_btn
import asyncio
from .role_names import RoleNames
from random import randint

async def assign_new_role(target: GamePlayer, phase: GamePhase, bot: Bot, chat: Chat, game=None):
    if phase:
        await phase.fetch_related("game")
    if target.role == RoleNames.DON:
        yangi_don = await GamePlayer.filter(
            game=phase.game if phase else game,
            is_alive=True,
            role=RoleNames.MAFIA
        ).first()
        if yangi_don:
            yangi_don.role = RoleNames.DON
            await yangi_don.save()
            await yangi_don.fetch_related("user")
            await bot.send_message(
                yangi_don.user.user_id,
                f"Siz endi <b>{RoleNames.DON}</b> bo‘ldingiz!",
                parse_mode="HTML"
            )
        else:
            pass

    elif target.role == RoleNames.KOMISSAR:
        yangi_komissar = await GamePlayer.filter(
            game=phase.game if phase else game,
            is_alive=True,
            role=RoleNames.SERJANT
        ).first()
        if yangi_komissar:
            yangi_komissar.role = RoleNames.KOMISSAR
            await yangi_komissar.save()
            await yangi_komissar.fetch_related("user")
            await bot.send_message(
                yangi_komissar.user.user_id,
               f"Siz endi <b>{RoleNames.KOMISSAR}</b> bo‘ldingiz!",
                parse_mode="HTML"
            )


async def send_geroys_action_message(players, bot: Bot, phase: GamePhase):
    for player in players:
            
        geroy = await Geroys.get_or_none(user=player.user)
        if not geroy:
            continue
        if player.role not in [RoleNames.DON, RoleNames.KOMISSAR, RoleNames.OVCHI, RoleNames.QAROQCHI, RoleNames.QOTIL]:
            await bot.send_message(player.user.user_id, "Harakat turini tanlang.", reply_markup=geroy_action_type_btn(phase_id=phase.id))
        else:
            await bot.send_message(player.user.user_id, "Harakat turini tanlang.", reply_markup=geroy_action_type_btn(phase_id=phase.id, attack=True))

async def geroy_attack_type_handler(call: CallbackQuery, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    geroy = await Geroys.get_or_none(user=user)
    if not geroy:
        await call.answer("Sizdagi geroyni topolmayabman!", show_alert=True)
        return
    if geroy.patron < 1:
        await call.answer("Geroyingizda o'qlar tugagan!")
        return
    phase = await GamePhase.filter(id=int(call.data.split("_")[2]), is_end=False).prefetch_related("game__players").first()
    if not phase:
        await call.message.edit_text("Siz kechikdingiz.")
        return
    await phase.fetch_related("game")
    nik = phase.game.mode.split(">")[1] if len(phase.game.mode.split(">")) > 1 else None
    players = await GamePlayer.filter(game=phase.game, is_alive=True).prefetch_related("user").all()
    markup = geroy_action_btn(players=players, phase_id=phase.id, action=call.data.split("_")[1], nik=nik)
    await call.message.edit_text(
        text="Kimni geroy bilan otasiz?",
        reply_markup=markup
    )
        
async def geroy_attack_handler(call: CallbackQuery, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    geroy = await Geroys.get_or_none(user=user)
    if not geroy:
        await call.answer("Sizdagi geroyni topolmayabman!", show_alert=True)
        await asyncio.sleep(1)
        return
    
    points = call.data.split("_")
    phase = await GamePhase.filter(id=int(points[2]), is_end=False).first()
    if not phase:
        await call.message.edit_text("Siz kechikdingiz.")
        await asyncio.sleep(1)
        return
    
    target_user = await User.get_or_none(user_id=int(points[1]))
    if not target_user:
        await call.answer("Ma'lumoti topilmadi!", show_alert=True)
        await asyncio.sleep(1)
        return
    
    await GeroyAction.create(   
        geroy=geroy,
        action_type="attack",
        target_user=target_user,
        phase=phase
    )
    await call.message.edit_text(
        text=f"Kimni geroy bilan otasiz?\n\nSSizning tanlov: {target_user.full_name}"
    )
    await asyncio.sleep(1)

async def geroy_shield_handler(call: CallbackQuery, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    geroy = await Geroys.get_or_none(user=user)
    if not geroy:
        await call.answer("Sizdagi geroyni topolmayabman!", show_alert=True)
        return
    points = call.data.split("_")
    phase = await GamePhase.filter(id=int(points[2]), is_end=False).first()
    if not phase:
        await call.message.edit_text("Siz kechikdingiz.")
        return
    
    await GeroyAction.create(
        geroy=geroy,
        action_type="shield",
        phase=phase
    )

    await call.message.edit_text(
        "Harakat turini tanlang:\n\nSizning tanlov: ⚜️ Himoyalanish"
    )

async def geroy_skip_handler(call: CallbackQuery, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return
    geroy = await Geroys.get_or_none(user=user)
    if not geroy:
        await call.answer("Sizdagi geroyni topolmayabman!", show_alert=True)
        return
    points = call.data.split("_")
    phase = await GamePhase.filter(id=int(points[2]), is_end=False).first()
    if not phase:
        await call.message.edit_text("Siz kechikdingiz.")
        return

    await call.message.edit_text(
        "Harakat turini tanlang:\n\nSizning tanlov: ⏭️ O'tkazib yuborish"
    )

async def geroys_action_result(players, phase: GamePhase, bot: Bot, chat: Chat):
    if phase:
        await phase.fetch_related("game")
    actions = await GeroyAction.filter(phase=phase).prefetch_related("geroy", "target_user").all()
    for action in actions:
        if action.action_type == "attack":
            geroy = action.geroy
            await geroy.fetch_related("user")
            geroy_user = geroy.user
            geroy_player = await GamePlayer.filter(user=geroy_user, game=phase.game, is_alive=True).first()
            if not geroy_player:
                continue
            target_user = action.target_user
            if not target_user:
                continue
            target_profile = await Profile.get_or_none(user=target_user)
            if target_profile and getattr(target_profile, "geroy_himoya", 0) > 0 and getattr(target_profile, "on_geroy_himoya", True):
                target_profile.geroy_himoya -= 1
                await target_profile.save()
                await bot.send_message(
                    chat.chat_id,
                    f"🔰 {target_user.mention}ning geroydan himoyasi <b>{geroy_player.role}</b> geroyi hujumidan uni saqlab qoldi!",
                    parse_mode="HTML"
                )
                continue
            target_player = await GamePlayer.get_or_none(user=target_user, game=phase.game, is_alive=True)
            if target_player:
                zarba = 40 + (geroy.level * 7)
                if zarba < 100:
                    zarba = randint(zarba - 7, zarba)
                else:
                    zarba = 100
                asl_zarba = zarba
                target_geroy = await Geroys.get_or_none(user=target_user)
                if target_geroy:
                    target_shield = await GeroyAction.filter(
                        geroy=target_geroy,
                        action_type="shield",
                        phase=phase
                    ).first()
                    if target_shield:
                        zarba = (zarba - target_geroy.himoya)
                        if zarba == 0:
                            target_geroy.himoya = 0
                            await target_geroy.save()
                            await bot.send_message(
                                chat.chat_id,
                                f"<b>{geroy_player.role}</b> geroyi bilan {target_geroy.name}ni jangda mag'lub qildi.",
                                parse_mode="HTML"
                            )
                            continue
                        elif zarba < 0:
                            target_geroy.himoya = abs(zarba)
                            await target_geroy.save()
                            await bot.send_message(
                                chat.chat_id,
                                f"<b>{geroy_player.role}</b> geroyi bilan {target_geroy.name}ga qarshi hujum qildi va jangda {target_geroy.name} himoyasi uni saqlab qoldi.",
                                parse_mode="HTML"
                            )
                            continue
                        else:
                            target_geroy.himoya = 0
                            await target_geroy.save()
                
                target_player.life  -= zarba
                await target_player.save()
                geroy.patron -= 1
                await geroy.save()
                if target_player.life > 0:
                    await bot.send_message(
                        chat.chat_id,
                        f"{target_user.mention}ga <b>{geroy_player.role}</b> geroyi bilan hujum qildi va {asl_zarba}% jonini oldi. Hozirda uni {target_player.life}% joni bor.",
                        parse_mode="HTML"
                    )
                    geroy.ball += geroy.level
                    await geroy.save()
                else:
                    await bot.send_message(
                        chat.chat_id,
                        f"⚰️ {target_player.role} {target_user.mention}ni <b>{geroy_player.role}</b> o'zining jasur geroyi bilan yer tishlatdi!",
                        parse_mode="HTML"
                    )
                    target_player.is_alive = False
                    geroy.ball += geroy.level + 1
                    await geroy.save()
                    await target_player.save()
                    if target_player.role in [RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR]:
                        await assign_new_role(target_player, phase, bot, chat)