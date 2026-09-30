from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable, Tuple
from time import monotonic
from utils.role_names import RoleNames
from collections import defaultdict, deque
import asyncio

CMD_LIST = [
    "start", "game", "stop", "send", "gsend", "change", "profile", "ginfo", "top1", "top7", "top30", "top",
    "gtop", "gtop1", "gtop7", "gtop30", "roles", "rolesnames"
]

class MyThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 2, window: float = 1.0, cooldown: float = 3.0):
        super().__init__()
        self.rate_limit = rate_limit
        self.window = window
        self.cooldown = cooldown

        self.cooldowns: Dict[Tuple[int, int], float] = {}
        self.group_activity: Dict[Tuple[int, int], deque] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            if not event.from_user:
                return await handler(event, data)
            try:
                now = monotonic()
                chat_id = event.chat.id
                user_id = event.from_user.id
                key = (chat_id, user_id)

                for cmd in CMD_LIST:
                    if cmd in (event.text or ""): break
                else:
                    return await handler(event, data)

                until = self.cooldowns.get(key, 0)
                if until > now:
                    return
                q = self.group_activity[key]
                while q and (now - q[0]) > self.window:
                    q.popleft()
                q.append(now)
                if len(q) > self.rate_limit:
                    self.cooldowns[key] = now + self.cooldown
                    try:
                        msg = await event.answer("🚫 Siz juda tez buyruq yubordingiz. Iltimos, biroz kuting.")
                        async def _del_after(m, delay):
                            await asyncio.sleep(delay)
                            try: await m.delete()
                            except Exception: pass
                        asyncio.create_task(_del_after(msg, self.cooldown))
                    except Exception:
                        pass
                    return
            except Exception as e:
                print(f"Error in MyThrottlingMiddleware: {e}")
        if isinstance(event, CallbackQuery):
            try:
                now = monotonic()
                chat_id = event.from_user.id
                user_id = event.from_user.id
                key = (chat_id, user_id)

                until = self.cooldowns.get(key, 0)
                if until > now:
                    await event.answer()
                    return
                q = self.group_activity[key]
                while q and (now - q[0]) > self.window:
                    q.popleft()
                q.append(now)
                limit = 1
                for role in RoleNames.all():
                    if event.data.startswith(role):
                        limit = 1
                        break
                else:
                    limit = 2
                if len(q) > limit:
                    self.cooldowns[key] = now + self.cooldown
                    await event.answer("🚫 Siz juda tez buyruq yubordingiz. Iltimos, biroz kuting.", show_alert=True)
                    return
            except Exception as e:
                print(f"Error in MyThrottlingMiddleware: {e}")
        return await handler(event, data)