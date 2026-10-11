from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from keyboards.game_keyboard import join_game_button, action_buttons, vote_buttons, go_group_button
from models.game_data import Chat, Game, GamePlayer, GamePhase, Action, Vote
from models.game_set import GameSetTime
from models.user import User, Profile
from typing import List
import random
from utils.roles_text import Roles
from datetime import datetime, timedelta, timezone
from tortoise.transactions import in_transaction
from random import randint
from utils.game_logic import assign_new_role, safe_send_message
from utils.premium_emojis import role_display
from aiogram.fsm.context import FSMContext
from utils.role_names import RoleNames  # agar kerak bo‘lsa
from utils.vsgame import TeamCOlors
import asyncio

async def vote_target_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    colors_dict = TeamCOlors.all_colors_dict()
    if call.data.endswith("skype"):
        try:
            points = call.data.split("_")
            phase_id = int(points[-2])
        except (IndexError, ValueError):
            await call.answer("❌ Noto‘g‘ri format!", show_alert=True)
            
             
            return
        user = await User.filter(user_id=call.from_user.id).first()
        player = await GamePlayer.filter(user=user, is_alive=True).first()
        phase = await GamePhase.filter(id=phase_id).first().prefetch_related("game")
        if not player:
            await call.message.delete()
            
             
            return
        if phase is None:
            await call.message.delete()
            
             
            return
        if phase.is_end:
            await call.message.delete()
            
             
            return
        nik = phase.game.mode.split(">")[1] if len(phase.game.mode.split(">")) > 1 else None
        await phase.fetch_related("game")
        night_phase = await GamePhase.filter(
            game=phase.game, phase_type="night", number=phase.number
        ).first()
        afer_action = await Action.filter(
            phase=night_phase, actor=player, action_type="afer"
        ).prefetch_related("target").first()

        await player.fetch_related("game")
        await player.game.fetch_related("chat")
        chat = player.game.chat

        await call.message.edit_text(
            f"<b>Bu kunda kimga ovoz berasiz?\n\nSizning tanlov:</b> 🚷 O'tkazib yuborish",
            parse_mode="HTML",
            reply_markup=go_group_button(
                chat.invite_link
                )
        )

        if afer_action:
            await afer_action.target.fetch_related("user")
            await safe_send_message(bot, 
                afer_action.target.user.user_id,
                "Aferist aldab sizning ovoz berish huquqingizni olib qo'ydi!",
                parse_mode="HTML",
                reply_markup=go_group_button(
                    chat.invite_link
                )   
            )
            await safe_send_message(bot, 
                chat.chat_id,
                f"🚷 {colors_dict[afer_action.target.team] if afer_action.target.team else ''}{afer_action.target.user.mention if not nik else nik} hech kimni tanlamaslikka qaror qildi!",
                parse_mode="HTML"
            )
             
            return
        
        if player.role == RoleNames.JANOB:
            await safe_send_message(bot, 
                chat.chat_id,
                f"🚷 {RoleNames.JANOB} hech kimni tanlamaslikka qaror qildi!",
                parse_mode="HTML"
            )
        else:
            await safe_send_message(bot, 
                chat.chat_id,
                f"🚷 {colors_dict[player.team] if player.team else ''}{user.mention if not nik else nik} hech kimni tanlamaslikka qaror qildi!",
                parse_mode="HTML"
            )
         
         
        return

    try:
        points = call.data.split("_")
        phase_id = int(points[-2])
        target_id = int(points[-1])
    except (IndexError, ValueError):
        await call.answer("❌ Noto‘g‘ri format!", show_alert=True)

         
         
        return
    user = await User.filter(user_id=call.from_user.id).first()
    target_user = await User.filter(user_id=target_id).first()
    player = await GamePlayer.filter(user=user, is_alive=True).first()
    target_player = await GamePlayer.filter(user=target_user, is_alive=True).first()
    phase = await GamePhase.filter(id=phase_id).first()
    if phase is None:
        await call.message.delete()
        
         
         
        return
    if phase.is_end:
        await call.message.delete()
        
         
         
        return

    if not all([user, target_user, player, target_player, phase]):
        await call.answer("❌ Xatolik: foydalanuvchi yoki o‘yinchi topilmadi.", show_alert=True)

         
         
        return
    existing_vote = await Vote.filter(voter=player, phase=phase).exists()
    if existing_vote:
        await call.answer("❗ Siz allaqachon ovoz bergansiz!", show_alert=True)
    
         
         
        return
    await phase.fetch_related("game")
    night_phase = await GamePhase.filter(
        game=phase.game, phase_type="night", number=phase.number
    ).first()
    afer_action = await Action.filter(
        phase=night_phase, actor=player, action_type="afer"
    ).prefetch_related("target").first()

    await player.fetch_related("game")
    await player.game.fetch_related("chat")
    chat = player.game.chat
    nik = phase.game.mode.split(">")[1] if len(phase.game.mode.split(">")) > 1 else None

    await call.message.edit_text(
        f"<b>Bu kunda kimga ovoz berasiz?\n\nSizning tanlov:</b> {colors_dict[target_player.team] if target_player.team else ''}{target_user.full_name if not nik else nik}\n",
                        parse_mode="HTML",
        reply_markup=go_group_button(
            chat.invite_link
        )
    )

    if afer_action:
        await Vote.create(voter=afer_action.target, target=target_player, phase=phase)

        await afer_action.target.fetch_related("user")
        await safe_send_message(bot, 
            afer_action.target.user.user_id,
            "Aferist aldab sizning ovoz berish huquqingizni olib qo'ydi!",
            parse_mode="HTML",
            reply_markup=go_group_button(
                chat.invite_link
            )
        )
        await safe_send_message(bot, 
            chat.chat_id,
            f"{colors_dict[afer_action.target.team] if afer_action.target.team else ''}{afer_action.target.user.mention if not nik else nik} - {colors_dict[target_player.team] if target_player.team else ''}{target_user.mention if not nik else nik}ga ovoz berdi",
            parse_mode="HTML"
        )
         
         
        return
    else:
        await Vote.create(voter=player, target=target_player, phase=phase)
    
    if player.role == RoleNames.JANOB:
        await safe_send_message(bot, 
            chat.chat_id,
            f"{RoleNames.JANOB} - {colors_dict[target_player.team] if target_player.team else ''}{target_user.mention if not nik else nik}ga ovoz berdi",
            parse_mode="HTML"
        )
    else:
        await safe_send_message(bot, 
            chat.chat_id,
            f"{colors_dict[player.team] if player.team else ''}{user.mention if not nik else nik} - {colors_dict[target_player.team] if target_player.team else ''}{target_user.mention if not nik else nik}ga ovoz berdi",
            parse_mode="HTML")
     
     

async def say_last_word_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    sender_mention = message.from_user.mention_html()

    # 1. Avval Redis game tekshiramiz:
    try:
        from utils.redis_game.services.player_service import player_service
        from utils.redis_game.game_models_crud import game_repo
        from utils.redis_game.repositories.player_repository import player_repository as player_repo
        from utils.game_logic import safe_send_message
        from datetime import datetime, timezone

        redis_res = await player_service.find_player_dead_last_word_game(user_id)
        if redis_res:
            game_id, player_state = redis_res
            game_state = await game_repo.load_game(game_id)
            if game_state:
                player_state.is_sayed_last_word = True
                await player_repo.save_player(player_state)

                is_expired = False
                if player_state.deaded_at:
                    now = datetime.now(timezone.utc)
                    dt = player_state.deaded_at
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if (now - dt).total_seconds() > 120:
                        is_expired = True

                if is_expired:
                    await message.answer("Siz oxirgi so'zingizni aytishga ulgurmadingz🥲")
                    return

                msg_text = (
                    f"<b>O'limidan oldin kimdir, {sender_mention} ning qichqirganini eshitdi:</b>\n\n"
                    f"💬 <i>\"{message.html_text}\"</i>"
                )
                await safe_send_message(message.bot, game_state.chat_id, msg_text, parse_mode="HTML")
                await message.answer("Oxirgi habaringiz guruhga yetkazildi!")
                return
    except Exception as e:
        print(f"⚠️ say_last_word_handler redis error: {e}")

    # 2. Eski DB o'yini:
    from datetime import datetime, timezone
    user = await User.filter(user_id=user_id).first()
    if not user:
        return
    player = await GamePlayer.filter(user=user, is_alive=False).last()
    if not player or player.is_sayed_last_word:
        return
    await player.fetch_related("game")
    game = player.game
    if not game.is_active:
        return

    player.is_sayed_last_word = True
    await player.save()

    if player.deaded_at:
        now = datetime.now(timezone.utc)
        dt = player.deaded_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if (now - dt).total_seconds() > 120:
            await message.answer("Siz oxirgi so'zingizni aytishga ulgurmadingz🥲")
            return

    await game.fetch_related("chat")

    await safe_send_message(message.bot, 
        game.chat.chat_id,
        f"<b>O'limidan oldin kimdir, {user.mention} ning qichqirganini eshitdi:</b>\n\n💬 <i>\"{message.html_text}\"</i>",
        parse_mode="HTML"
    )
    await message.answer("Oxirgi habaringiz guruhga yetkazildi!")

async def select_card_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    colors_dict = TeamCOlors.all_colors_dict()
    try:
        points = call.data.split("_")
        phase_id = int(points[-3])
        card_id = int(points[-2])
        death_card_id = int(points[-1])
    except (IndexError, ValueError):
        await call.answer("❌ Noto‘g‘ri format!", show_alert=True)
        return
    user = await User.filter(user_id=call.from_user.id).first()
    player = await GamePlayer.filter(user=user, is_alive=True).first()
    if not player:
        await call.message.delete()
        player = await GamePlayer.filter(user=user, is_alive=False).last()
        player.should_choose_card = False
        await player.save()
        
         
         
        return
    phase = await GamePhase.filter(id=phase_id).first().prefetch_related("game")
    if not phase:
        try: await call.message.delete()
        except: pass
        
         
         
        return
    phase = await GamePhase.filter(game=phase.game, number=phase.number).last().prefetch_related("game")
    if not phase or phase.is_end:
        try: await call.message.delete()
        except: pass         
        return
    joker = await GamePlayer.filter(
        game=phase.game, role=RoleNames.JOKER
    ).first().prefetch_related("user")
    await phase.fetch_related("game")
    await phase.game.fetch_related("chat")
    chat = phase.game.chat
    if card_id == death_card_id:
        player.is_alive = False
        player.deaded_at = datetime.now(timezone.utc)
        await player.save()
        
        # Zanjir tekshirish
        night_phase = await GamePhase.filter(game=phase.game, phase_type="night", number=phase.number).first()
        if night_phase:
            zanjir_action = await Action.filter(phase=night_phase, action_type="zanjir").first()
            if zanjir_action:
                t1_id = zanjir_action.target_id
                t2_id = int(zanjir_action.result)
                if player.id == t1_id or player.id == t2_id:
                    other_id = t2_id if player.id == t1_id else t1_id
                    other_player = await GamePlayer.filter(id=other_id, is_alive=True).prefetch_related("user").first()
                    if other_player:
                        other_player.is_alive = False
                        other_player.deaded_at = datetime.now(timezone.utc)
                        await other_player.save()
                        await safe_send_message(bot, 
                            chat.chat_id,
                            f"⛓ {colors_dict[other_player.team] if other_player.team else ''}{other_player.user.mention} <b>{user.mention}</b> bilan zanjirlangan edi va u bilan birga halok bo'ldi!\nU edi <b>{role_display(other_player.role)}</b>.",
                            parse_mode="HTML"
                        )
                        await assign_new_role(other_player, phase, bot, chat)
        
        await call.message.edit_text(
            f"🤡 <b>Siz o'lim kartasini tanladingiz va o'ldingiz!</b>",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
         

        await safe_send_message(bot, 
            joker.user.user_id,
            f"🤡 {colors_dict[player.team] if player.team else ''}{user.mention} o'lim kartasini tanladi va siz uni o'yindan chiqarib yubordingiz!",
            parse_mode="HTML"
        )
        await safe_send_message(bot, 
            chat.chat_id,
            f"🤡 Joker hursand chunki {colors_dict[player.team] if player.team else ''}{user.mention} o'lim kartasini tanladi va o'ldi!\n\nU edi - {role_display(player.role)}",
            parse_mode="HTML"
        )
        joker.is_really_winner = True
        await joker.save()
        await assign_new_role(player, phase, bot, chat)
    else:
        await call.message.edit_text(
            f"🤡 <b>Tabriklayman, siz to'g'ri kartani tanladingiz va tirik qoldingiz!</b>",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )

        await safe_send_message(bot, 
            joker.user.user_id,
            f"🤡 Afsuski, {colors_dict[player.team] if player.team else ''}{user.mention} o'lim kartasini tanlamadi va tirik qoldi!",
            parse_mode="HTML"
        )
        await safe_send_message(bot, 
            chat.chat_id,
            f"🤡 Jokerni xafa qilishdi!",
            parse_mode="HTML"
        )
    player.should_choose_card = False
    await player.save()

     
     