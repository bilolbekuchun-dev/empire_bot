from aiogram.types import Message
from models.game_set import GameModeSet, GameSetTime, GameSetListRoles, GameSetPermissions, GroupBalance, GroupGiveSet, GroupMoreSet, CommandPermissionsChat, WriteGroupPermis, GameSetWeapons, GamingOnChat
from models.user import User, Profile
from utils.role_names import RoleNames
from keyboards.main_keyboard import bot_link_markup
from keyboards.settings_buttons import nickpack_menu_btn, wolf_or_fox_btn, back_set_menu, can_gaming_btn, open_settings_button, set_time_types_button, set_time_values_button, set_roles_types_button, set_roles_values_button, set_leave_button, set_give_types_button, set_give_values_button, set_adv_view_button, set_mafs_vote_button, set_max_players_values_button, set_more_types_button, set_command_permission_values_button, set_command_permissions_button, set_write_group_perm_types_button, set_write_group_perm_values_button, set_rollarni_guruhlash_button, game_mode_select_btn, game_mode_info_btn, game_mode_menu_btn, set_weapons_types_button, set_weapons_values_button, set_weapons_combined_button
from aiogram.filters import Command
from models.game_set import NickList, NickListItem, NickModeSet, WolfOrFoxSet
from models.game_data import Chat, Game
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

async def group_info_handler(message: Message, bot: Bot):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]: return
    chat = await Chat.get_or_none(chat_id=message.chat.id)
    if not chat: return
    group_balance, _ = await GroupBalance.get_or_create(
        chat_id=chat.chat_id,
        defaults={"balance": 0}
    )
    games_count = await Game.filter(chat=chat).count()
    await message.answer(f"""
<b>Guruh nomi:</b> {chat.title}

🎮 <b>Jami o'yinlar soni:</b> {games_count}
<tg-emoji emoji-id='5210941235912552228'>💎</tg-emoji> <b>Guruh hisobi:</b> {group_balance.balance} ta

Guruh hisobini to'ldirish uchun /gsend buyrug'idan foydalaning
""", parse_mode="HTML")

async def can_gaming_handler(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    match len(points):
        case 3:
            me = await call.bot.get_me()
            gaming_set, _ = await GamingOnChat.get_or_create(chat_id=chat_id, defaults={"bot_id": me.id})
            await call.message.edit_text(
                "Guruhda o'yin o'ynashga ruxsat berilsinmi?",
                reply_markup=can_gaming_btn(chat_id=chat_id, default=gaming_set.can_gaming)
            )
            return
        case 4:
            value = points[3]
            me = await call.bot.get_me()
            gaming_set, _ = await GamingOnChat.get_or_create(chat_id=chat_id, defaults={"bot_id": me.id})
            new_value = True if value == "1" else False
            if gaming_set.can_gaming != new_value:
                gaming_set.can_gaming = new_value
                await gaming_set.save()
                await call.message.edit_reply_markup(
                    reply_markup=can_gaming_btn(chat_id=chat_id, default=new_value)
                )
            

async def open_set_game_mode(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    match len(points):
        case 2:
            await call.message.edit_text(
                "Nima qilamiz?",
                reply_markup=game_mode_menu_btn(chat_id=chat_id)
            )
            await call.answer()
            return
        case 3:
            if points[2] == "info":
                about_modes = {
                    "super": "Bunda yangicha rollar ertaroq chiqadi. O'yin shiddatli tus oladi.",
                    "super:vs": "Super modening jamoaviy (VS) talqini.",
                    "para x super": "Guruhda reply qilib .para buyrug'i bilan o'zingizga sherik toping. U qabul qilsa keyin sizlar sherik bo'lasizlar. O'yin davomida ikkingizdan kimdir o'lsa ikkingiz ham o'yindan chiqasizlar."
                }
                await call.message.edit_text(
                    "O'yin modlari haqida ma'lumot:\n\n" + "\n".join([f"<b>{mode}</b>: {desc}" for mode, desc in about_modes.items()]),
                    reply_markup=game_mode_menu_btn(chat_id=chat_id), parse_mode="HTML"
                )
            elif points[2] == "select":
                gmode = await GameModeSet.filter(chat_id=chat_id).first()
                default_mode = gmode.mode_name if gmode else "classic"
                await call.message.edit_text(
                    "Qaysi o'yin modini tanlaysiz?",
                    reply_markup=game_mode_select_btn(chat_id=chat_id, default=default_mode)
                )
            await call.answer()
            return
        case 4:
            selected_mode = points[3]
            if selected_mode not in ["super", "super:vs", "para x super"]:
                await call.answer("Noto'g'ri o'yin mode!", show_alert=True)
                return
            mode_set, _ = await GameModeSet.get_or_create(chat_id=chat_id)
            if mode_set.mode_name != selected_mode:
                mode_set.mode_name = selected_mode
                await mode_set.save()
                await call.message.edit_reply_markup(
                    reply_markup=game_mode_select_btn(chat_id=chat_id, default=selected_mode)
                )
            await call.answer()


async def open_set_command_permissions(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    if len(points) == 2:
        await call.message.edit_text(
            "Qaysi buyruqqa ruxsat bermoqchisiz?",
            reply_markup=set_command_permissions_button(chat_id)
        )
        return
    elif len(points) == 3:
        cmd = points[2]
        # Bu yerda modeldan default permissionni olish kerak
        perms, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin",
            "extend_cmd": "admin"
        }
    )
        default = getattr(perms, f"{cmd}_cmd", "admin")
        await call.message.edit_text(
            f"{cmd} buyrug'ini kimlar ishlata oladi?",
            reply_markup=set_command_permission_values_button(chat_id, cmd, default)
        )

        return
    elif len(points) == 4:
        cmd = points[2]
        value = points[3]
        perms, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin",
            "extend_cmd": "admin"
        }
    )
        current = getattr(perms, f"{cmd}_cmd", "admin")
        if current != value:
            setattr(perms, f"{cmd}_cmd", value)
            await perms.save()

        await call.message.edit_reply_markup(
            reply_markup=set_command_permission_values_button(chat_id, cmd, value)
        )

async def is_admin(message: Message) -> bool:
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except: return False

async def send_settings_to_admin(message: Message, bot: Bot):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]: return
    if not await is_admin(message):
        return
    try:
        await bot.send_message(
            chat_id=message.from_user.id,
            text=f"{hbold('Guruh o‘yin sozlamalariga xush kelibsiz!')}",
            parse_mode="HTML",
            reply_markup=open_settings_button(message.chat.id)
        )
    except: pass

async def show_settings_handler(call: CallbackQuery):
    points = call.data.split("_")
    await call.message.edit_text(
            text=f"{hbold('Guruh o‘yin sozlamalariga xush kelibsiz!')}",
            parse_mode="HTML",
            reply_markup=open_settings_button(points[1])
        )

async def open_set_time_answer(call:CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    match len(points):
        case 2:
            await call.message.edit_text("Qaysi vaqtni sozlamoqchisiz?", reply_markup=set_time_types_button(chat_id=chat_id))
            return
        case 3:
            time_type = points[2]
            time_set, _ = await GameSetTime.get_or_create(chat_id=chat_id)
            d = 45
            if time_type == "night": d = time_set.night_time
            if time_type == "day": d = time_set.day_time
            if time_type == "vote": d = time_set.vote_time
            if time_type == "like": d = time_set.like_time
            if time_type == "word": d = time_set.word_time
            if time_type == "reg": d = time_set.reg_time
            await call.message.edit_text("Necha soniya davom etsin?", reply_markup=set_time_values_button(chat_id=chat_id, time_type=time_type, default=d))
            return
        case 4:
            time_value = int(points[3])
            time_type = points[2]
            time_set, _ = await GameSetTime.get_or_create(chat_id=chat_id)
            if time_type == "night" and time_set.night_time != time_value: time_set.night_time = time_value
            elif time_type == "day" and time_set.day_time != time_value: time_set.day_time = time_value
            elif time_type == "vote" and time_set.vote_time != time_value: time_set.vote_time = time_value
            elif time_type == "like" and time_set.like_time != time_value: time_set.like_time = time_value
            elif time_type == "word" and time_set.word_time != time_value: time_set.word_time = time_value
            elif time_type == "reg" and time_set.reg_time != time_value: time_set.reg_time = time_value
            else: return
            await time_set.save()
            await call.message.edit_reply_markup(reply_markup=set_time_values_button(chat_id=chat_id, time_type=time_type, default=time_value))

async def open_set_give_answer(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    match len(points):
        case 2:
            await call.message.edit_text(
                "Qaysi giveaway turini sozlamoqchisiz?",
                reply_markup=set_give_types_button(chat_id=chat_id)
            )
            return
        case 3:
            give_type = points[2]
            give_set, _ = await GroupGiveSet.get_or_create(chat_id=chat_id)
            default = 0
            if give_type == "diamond":
                default = give_set.diamond
            elif give_type == "dollar":
                default = give_set.dollar
            await call.message.edit_text(
                "Nechta berilsin?",
                reply_markup=set_give_values_button(chat_id=chat_id, give_type=give_type, default=default)
            )
            return
        case 4:
            give_type = points[2]
            give_value = int(points[3])
            give_set, _ = await GroupGiveSet.get_or_create(chat_id=chat_id)
            if (give_type == "diamond" and give_set.diamond == give_value) or \
               (give_type == "dollar" and give_set.dollar == give_value):
                return
            if give_type == "diamond":
                give_set.diamond = give_value
            elif give_type == "dollar":
                give_set.dollar = give_value
            await give_set.save()
            await call.message.edit_reply_markup(
                reply_markup=set_give_values_button(chat_id=chat_id, give_type=give_type, default=give_value)
            )

async def open_set_role_answer(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    match len(points):
        case 2:
            await call.message.edit_text(
                "Qaysi rolni sozlamoqchisiz?",
                reply_markup=set_roles_types_button(chat_id=chat_id, page=0)
            )
            return
        case 3:
            # Bu rol tanlash
            role = points[2]
            # RoleNames da bu rol mavjudligini tekshirish
            if role not in RoleNames.all():
                await call.answer("Noto'g'ri rol!", show_alert=True)
                return
            
            role_set, _ = await GameSetListRoles.get_or_create(chat_id=chat_id)
            is_banned = role_set.is_banned(role)
            
            await call.message.edit_text(
                f"{role} roli taqiqlansinmi?",
                reply_markup=set_roles_values_button(chat_id=chat_id, role=role, default=is_banned)
            )
            return
        case 4:
            # Bu yerda sahifalash yoki rol qiymatini o'zgartirish bo'lishi mumkin
            if points[2] == "page":
                # Sahifalash
                page = int(points[3])
                await call.message.edit_text(
                    "Qaysi rolni sozlamoqchisiz?",
                    reply_markup=set_roles_types_button(chat_id=chat_id, page=page)
                )
            else:
                # Rol qiymatini o'zgartirish
                role = points[2]
                value = points[3]
                
                # RoleNames da bu rol mavjudligini tekshirish
                if role not in RoleNames.all():
                    await call.answer("Noto'g'ri rol!", show_alert=True)
                    return
                    
                role_set, _ = await GameSetListRoles.get_or_create(chat_id=chat_id)
                
                # value: "0" = taqiqlash, "1" = ruxsat berish
                if value == "0":
                    role_set.ban_role(role)
                    new_status = True  # taqiqlangan
                else:
                    role_set.unban_role(role)
                    new_status = False  # ruxsat berilgan
                    
                await role_set.save()
                
                await call.message.edit_reply_markup(
                    reply_markup=set_roles_values_button(chat_id=chat_id, role=role, default=new_status)
                )

async def set_leave_action_handler(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    match len(points):
        case 2:
            game_perm, _ = await GameSetPermissions.get_or_create(chat_id=chat_id)
            await call.message.edit_text(
                "/leave buyrug'iga ruxsat beramizmi?",
                reply_markup=set_leave_button(chat_id=chat_id, default=game_perm.leave_qilish)
            )
            return
        case 3:
            status = points[2]
            game_perm, _ = await GameSetPermissions.get_or_create(chat_id=chat_id)
            d = True
            if game_perm.leave_qilish == True and status == "0": 
                d = False
                game_perm.leave_qilish = False
            elif game_perm.leave_qilish == False and status == "1":
                game_perm.leave_qilish = True
            else:
                return
            await game_perm.save()
            await call.message.edit_reply_markup(
                            reply_markup=set_leave_button(chat_id=chat_id, default=d)
                        )            

async def add_diamond_group_balance(message: Message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]: return
    group_balance, _ = await GroupBalance.get_or_create(chat_id=message.chat.id)
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return
    
    count = int(message.text.split(" ")[1])
    sender_user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={"full_name": message.from_user.full_name, "mention": message.from_user.mention_html()}
    )
    sender_profile, _ = await Profile.get_or_create(user=sender_user, defaults={"dollar": 0, "diamond": 0})

    if sender_profile.diamond < count:
        return
    sender_profile.diamond -= count
    await sender_profile.save()
    group_balance.balance += count
    from datetime import datetime, timezone
    group_balance.last_reset_at = datetime.now(timezone.utc)
    await group_balance.save(update_fields=['balance', 'last_reset_at'])

    # Guruh ma'lumotlarini (nomi va havolasini) Chat jadvalida yangilash
    try:
        from utils.telegram_utils import get_chat_join_link
        chat_entry = await Chat.filter(chat_id=message.chat.id).first()
        link = await get_chat_join_link(message.bot, message.chat.id)
        if chat_entry:
            chat_entry.title = message.chat.title or chat_entry.title
            if link:
                chat_entry.invite_link = link
            await chat_entry.save()
        else:
            await Chat.create(chat_id=message.chat.id, title=message.chat.title or "Guruh", type=str(message.chat.type), invite_link=link)
    except Exception:
        pass

    await message.answer(f"<b>{sender_user.mention} guruh hisobiga {count} <tg-emoji emoji-id='5210941235912552228'>💎</tg-emoji> ta olmos hadya qildi!</b>", parse_mode="HTML")

async def open_set_more_answer(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    if "can-gaming" in call.data:
        return await can_gaming_handler(call)
    match len(points):
        case 2:
            await call.message.edit_text(
                "Qaysi boshqa sozlamani o'zgartirmoqchisiz?",
                reply_markup=set_more_types_button(chat_id=chat_id)
            )
            return
        case 3:
            more_type = points[2]
            more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat_id)
            if more_type == "mafs-vote":
                default = more_set.mafning_ovozi
                await call.message.edit_text(
                    "3 ta mafianing ovozi donnikidan ustun kelsinmi??",
                    reply_markup=set_mafs_vote_button(chat_id=chat_id, more_type=more_type, default=default)
                )
            elif more_type == "adv-view":
                default = more_set.adv_view
                await call.message.edit_text(
                    "Advokatni ko'rishga ruxsat berilsinmi?",
                    reply_markup=set_adv_view_button(chat_id=chat_id, more_type=more_type, default=default)
                )
            elif more_type == "max-players":
                default = more_set.max_players
                await call.message.edit_text(
                    "Maksimal o'yinchilar sonini tanlang:",
                    reply_markup=set_max_players_values_button(chat_id=chat_id, more_type=more_type, default=default)
                )
            elif more_type == "rollarni-guruhlash":
                default = more_set.rollarni_guruhlash
                await call.message.edit_text(
                    "Rollarni guruhlashga ruxsat berilsinmi?",
                    reply_markup=set_rollarni_guruhlash_button(chat_id=chat_id, more_type=more_type, default=default)
                )
            elif more_type == "wolf-or-fox":
                default, _ = await WolfOrFoxSet.get_or_create(chat_id=chat_id)
                await call.message.edit_text(
                    "Bo'ri yoki tulki qaysi biri?",
                    reply_markup=wolf_or_fox_btn(chat_id=chat_id, default=default.wolf_or_fox)
                )
            return
        case 4:
            more_type = points[2]
            value = points[3]
            more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat_id)
            if more_type == "mafs-vote":
                new_value = True if value == "0" else False
                if more_set.mafning_ovozi != new_value:
                    more_set.mafning_ovozi = new_value
                    await more_set.save()
                await call.message.edit_reply_markup(
                    reply_markup=set_mafs_vote_button(chat_id=chat_id, more_type=more_type, default=new_value)
                )
            elif more_type == "adv-view":
                new_value = True if value == "0" else False
                if more_set.adv_view != new_value:
                    more_set.adv_view = new_value
                    await more_set.save()
                await call.message.edit_reply_markup(
                    reply_markup=set_adv_view_button(chat_id=chat_id, more_type=more_type, default=new_value)
                )
            elif more_type == "max-players":
                try:
                    new_value = int(value)
                except ValueError:
                    return
                if more_set.max_players != new_value:
                    more_set.max_players = new_value
                    await more_set.save()
                await call.message.edit_reply_markup(
                    reply_markup=set_max_players_values_button(chat_id=chat_id, more_type=more_type, default=new_value)
                )
            elif more_type == "rollarni-guruhlash":
                new_value = True if value == "0" else False
                if more_set.rollarni_guruhlash != new_value:
                    more_set.rollarni_guruhlash = new_value
                    await more_set.save()
                await call.message.edit_reply_markup(
                    reply_markup=set_rollarni_guruhlash_button(chat_id=chat_id, more_type=more_type, default=new_value)
                )
            elif more_type == "wolf-or-fox":
                new_value = True if value == "1" else False
                wolf_fox_set, _ = await WolfOrFoxSet.get_or_create(chat_id=chat_id)
                if wolf_fox_set.wolf_or_fox != new_value:
                    wolf_fox_set.wolf_or_fox = new_value
                    await wolf_fox_set.save()
                try:    
                    await call.message.edit_reply_markup(
                        reply_markup=wolf_or_fox_btn(chat_id=chat_id, default=new_value)
                    )
                except: pass
                
async def open_set_write_group_perm_answer(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    match len(points):
        case 2:
            await call.message.edit_text(
                "Qaysi paytni sozlaymiz?",
                reply_markup=set_write_group_perm_types_button(chat_id=chat_id)
            )
            return
        case 3:
            perm_type = points[2]
            perm_set, _ = await WriteGroupPermis.get_or_create(chat_id=chat_id)
            if perm_type not in ["night", "day"]:
                await call.answer("Noto'g'ri tur!", show_alert=True)
                return
            default = getattr(perm_set, perm_type, "alive")
            await call.message.edit_text(
                "Kimlar yozishi mumkin?",
                reply_markup=set_write_group_perm_values_button(chat_id=chat_id, perm_type=perm_type, default=default)
            )
            return
        case 4:
            perm_type = points[2]
            value = points[3]
            perm_set, _ = await WriteGroupPermis.get_or_create(chat_id=chat_id)
            if perm_type not in ["night", "day"]:
                await call.answer("Noto'g'ri tur!", show_alert=True)
                return
            current = getattr(perm_set, perm_type, "alive")
            if current != value:
                setattr(perm_set, perm_type, value)
                await perm_set.save()
            await call.message.edit_reply_markup(
                reply_markup=set_write_group_perm_values_button(chat_id=chat_id, perm_type=perm_type, default=value)
            )

async def open_set_weapons_answer(call: CallbackQuery):
    points = call.data.split("_")
    chat_id = int(points[1])
    await call.answer()
    
    match len(points):
        case 2:
            weapon_set, _ = await GameSetWeapons.get_or_create(chat_id=chat_id)
            await call.message.edit_text(
                "Himoyalarni yoqish/o'chirish uchun bosing:",
                reply_markup=set_weapons_combined_button(chat_id=chat_id, weapon_set=weapon_set)
            )
            return
        case 4:
            weapon = points[2]
            value = points[3]

            # Qurol kalitini tekshirish
            valid_weapons = ["himoya", "hujjat", "qotildan-himoya", "ovozdan-himoya", "miltiq", "doridan-himoya", "slip-himoya", "maska", "geroy", "active-role"]
            if weapon not in valid_weapons:
                await call.answer("Noto'g'ri qurol!", show_alert=True)
                return

            weapon_db = weapon.replace("-", "_")
            weapon_set, _ = await GameSetWeapons.get_or_create(chat_id=chat_id)
            # value: "1" = yoqish, "0" = o'chirish
            new_value = True if value == "1" else False
            current_value = getattr(weapon_set, weapon_db, True)

            if current_value != new_value:
                setattr(weapon_set, weapon_db, new_value)
                await weapon_set.save()

            await call.message.edit_reply_markup(
                reply_markup=set_weapons_combined_button(chat_id=chat_id, weapon_set=weapon_set)
            )