import re

with open("bot.py", "r") as f:
    content = f.read()

middleware_code = """
import logging

@dp.message.outer_middleware()
async def log_all_messages(handler, event, data):
    logging.info(f"RECEIVED MESSAGE: {event.text} from {event.from_user.id} in chat {event.chat.id}")
    return await handler(event, data)
"""

if "log_all_messages" not in content:
    content = content.replace("async def main():", middleware_code + "\nasync def main():")
    with open("bot.py", "w") as f:
        f.write(content)
    print("Middleware added")
else:
    print("Middleware already exists")
