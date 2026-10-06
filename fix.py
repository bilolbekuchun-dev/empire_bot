with open("utils/game_logic.py", "r") as f:
    content = f.read()

content = content.replace(
    '    import logging\n    logging.info("DEBUG: Sending \'Ro\'yxatdan o\'tish boshlandi!\' message")\n        msg = await message.answer(\n        f"<b>Ro\'yxatdan o\'tish boshlandi!</b>\\",\n        reply_markup=join_markup,\n        parse_mode="HTML"\n    )',
    '    import logging\n    logging.info("DEBUG: Sending \'Ro\'yxatdan o\'tish boshlandi!\' message")\n    msg = await message.answer(\n        f"<b>Ro\'yxatdan o\'tish boshlandi!</b>",\n        reply_markup=join_markup,\n        parse_mode="HTML"\n    )'
)
with open("utils/game_logic.py", "w") as f:
    f.write(content)
