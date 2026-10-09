"""
Minimal stand-ins for aiogram Bot/Message/CallbackQuery and ChatMember.

These are *test-only* virtual actors. They intentionally implement only the
surface used by the Redis game engine so the real production logic can be
exercised without a live Telegram connection.
"""
from aiogram.enums import ChatMemberStatus


class FakeChatMember:
    def __init__(self, status=ChatMemberStatus.CREATOR):
        self.status = status


class FakeSentMessage:
    _counter = 0

    def __init__(self, text="", chat_id=0):
        FakeSentMessage._counter += 1
        self.message_id = FakeSentMessage._counter
        self.text = text
        self.chat_id = chat_id

    async def pin(self, *args, **kwargs):
        return True

    async def edit_text(self, *args, **kwargs):
        return self

    async def delete(self, *args, **kwargs):
        return True


class FakeBot:
    """
    Records calls.

    ``fail_send``  -> send_message / edit / delete raise (Telegram unavailable).
    ``fail_media`` -> send_photo / send_animation / send_video raise, while
                      send_message still works (media-specific outage).
    """

    def __init__(self, bot_id=999_000_000, admin_status=ChatMemberStatus.CREATOR,
                 fail_send=False, fail_media=False, fail_delete=False):
        self.id = bot_id
        self._admin_status = admin_status
        self.fail_send = fail_send
        self.fail_media = fail_media
        self.fail_delete = fail_delete
        self.sent = []
        self.sent_media = []
        self.outbox = []          # every FakeSentMessage created (bot + message.answer)
        self.edited = []
        self.deleted = []

    class _Me:
        def __init__(self, i):
            self.id = i
            self.is_bot = True

    async def get_me(self):
        return FakeBot._Me(self.id)

    async def get_chat_member(self, chat_id, user_id):
        return FakeChatMember(self._admin_status)

    async def send_message(self, chat_id, text, **kwargs):
        if self.fail_send:
            raise RuntimeError("simulated Telegram failure")
        m = FakeSentMessage(text, chat_id)
        self.sent.append((chat_id, text))
        self.outbox.append(m)
        return m

    async def _media(self, kind, chat_id, value, caption=None, **kwargs):
        if self.fail_media or self.fail_send:
            raise RuntimeError("simulated Telegram media failure")
        val_str = getattr(value, "path", value)
        self.sent_media.append({"kind": kind, "chat_id": chat_id,
                                "value": val_str, "caption": caption})
        return FakeSentMessage(caption or "", chat_id)

    async def send_photo(self, chat_id, photo=None, caption=None, **kwargs):
        return await self._media("photo", chat_id, photo, caption, **kwargs)

    async def send_animation(self, chat_id, animation=None, caption=None, **kwargs):
        return await self._media("animation", chat_id, animation, caption, **kwargs)

    async def send_video(self, chat_id, video=None, caption=None, **kwargs):
        return await self._media("video", chat_id, video, caption, **kwargs)

    async def edit_message_text(self, *args, **kwargs):
        if self.fail_send:
            raise RuntimeError("simulated Telegram failure")
        self.edited.append((args, kwargs))
        return True

    async def delete_message(self, chat_id, message_id):
        if self.fail_send or self.fail_delete:
            raise RuntimeError("simulated Telegram failure")
        self.deleted.append((chat_id, message_id))
        return True

    # ---- helpers for message-lifecycle assertions ----
    def deleted_ids(self):
        return {mid for _cid, mid in self.deleted}

    def live_messages(self, chat_id=None):
        """Messages that still exist in the (virtual) chat."""
        dead = self.deleted_ids()
        return [
            m for m in self.outbox
            if (chat_id is None or m.chat_id == chat_id) and m.message_id not in dead
        ]


class FakeUser:
    def __init__(self, user_id, full_name=None):
        self.id = user_id
        self.user_id = user_id
        self.full_name = full_name or f"Player {user_id}"
        self.username = f"p{user_id}"
        self.is_bot = False

    def mention_html(self, name=None):
        return f"<a href='tg://user?id={self.user_id}'>{name or self.full_name}</a>"


class FakeChat:
    def __init__(self, chat_id, title="Test Group", type_="supergroup"):
        self.id = chat_id
        self.chat_id = chat_id
        self.title = title
        self.type = type_
        self.invite_link = None


class FakeMessage:
    def __init__(self, text, user, chat, bot=None):
        self.text = text
        self.from_user = user
        self.chat = chat
        self.bot = bot

    async def answer(self, text, **kwargs):
        m = FakeSentMessage(text, self.chat.id)
        if self.bot is not None:
            self.bot.outbox.append(m)
        return m
