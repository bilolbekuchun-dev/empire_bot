# from aiogram import Bot
# from aiogram.exceptions import TelegramMigrateToChat, TelegramAPIError
# from aiogram.types import ErrorEvent
# from aiogram.dispatcher.middlewares.error import ErrorMiddleware

# class MyErrorHandler(ErrorMiddleware):
#     async def __call__(self, handler, event: ErrorEvent, data: dict):
#         exception = event.exception
#         bot: Bot = data.get("bot")

#         if isinstance(exception, TelegramMigrateToChat):
#             try:
#                 chat_id = None
#                 if hasattr(event.update, 'message') and event.update.message:
#                     chat_id = event.update.message.chat.id
#                     await bot.send_message(chat_id, "❗ Bu guruh superguruhga aylantirilgan. Iltimos, botni guruhga qaytadan qo‘shing.")
#                 elif hasattr(event.update, 'callback_query') and event.update.callback_query:
#                     chat_id = event.update.callback_query.message.chat.id
#                     await bot.send_message(chat_id, "❗ Bu guruh superguruhga aylantirilgan. Iltimos, botni guruhga qaytadan qo‘shing.")

#                 if chat_id:
#                     await bot.leave_chat(chat_id)
#             except TelegramAPIError:
#                 pass 

#             return  
#         return await handler(event, data)
