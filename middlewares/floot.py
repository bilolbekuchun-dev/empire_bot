from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any, Awaitable, Tuple
from time import monotonic
from utils.role_names import RoleNames
from collections import defaultdict, deque
import asyncio

CMD_LIST = {
    "start", "game", "stop", "send", "gsend", "change", "profile", "ginfo", "top1", "top7", "top30", "top",
    "gtop", "gtop1", "gtop7", "gtop30", "roles", "rolesnames"
}

class MyThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 2, window: float = 1.0, cooldown: float = 3.0):
        super().__init__()
        self.rate_limit = rate_limit
        self.window = window
        self.cooldown = cooldown

        self.cooldowns: Dict[Tuple[int, int], float] = {}
        self.group_activity: Dict[Tuple[int, int], deque] = defaultdict(deque)
        self._last_prune: float = monotonic()
        self._role_names_set = None

    def _get_role_names(self):
        if self._role_names_set is None:
            self._role_names_set = set(RoleNames.all())
        return self._role_names_set

    def _maybe_prune(self, now: float):
        """Prune inactive entries every 60 seconds to prevent memory leaks."""
        if now - self._last_prune < 60.0:
            return
        self._last_prune = now

        # Remove expired cooldowns
        expired_cooldowns = [k for k, until in self.cooldowns.items() if until < now]
        for k in expired_cooldowns:
            del self.cooldowns[k]

        # Remove empty or stale activity deques
        stale_activity = []
        for k, q in self.group_activity.items():
            while q and (now - q[0]) > self.window:
                q.popleft()
            if not q:
                stale_activity.append(k)
        for k in stale_activity:
            del self.group_activity[k]

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        now = monotonic()
        self._maybe_prune(now)

        if isinstance(event, Message):
            if not event.from_user:
                return await handler(event, data)
            try:
                text = (event.text or "").strip()
                if not text.startswith("/"):
                    return await handler(event, data)

                # Extract command without leading slash and optional bot mention
                cmd_part = text[1:].split()[0].split("@")[0].lower() if text[1:] else ""
                if cmd_part not in CMD_LIST:
                    return await handler(event, data)

                chat_id = event.chat.id
                user_id = event.from_user.id
                key = (chat_id, user_id)

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
                        await event.answer("🚫 Siz juda tez buyruq yubordingiz. Iltimos, biroz kuting.")
                    except Exception:
                        pass
                    return
            except Exception as e:
                print(f"Error in MyThrottlingMiddleware: {e}")

        elif isinstance(event, CallbackQuery):
            try:
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

                cb_data = event.data or ""
                limit = 2
                roles = self._get_role_names()
                for role in roles:
                    if cb_data.startswith(role):
                        limit = 1
                        break

                if len(q) > limit:
                    self.cooldowns[key] = now + self.cooldown
                    await event.answer("🚫 Siz juda tez buyruq yubordingiz. Iltimos, biroz kuting.", show_alert=True)
                    return
            except Exception as e:
                print(f"Error in MyThrottlingMiddleware: {e}")

        return await handler(event, data)