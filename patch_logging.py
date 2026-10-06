import re

with open("utils/game_logic.py", "r") as f:
    content = f.read()

content = content.replace('print("DEBUG', 'import logging\n    logging.info("DEBUG')
content = content.replace('print(f"DEBUG', 'import logging\n    logging.info(f"DEBUG')

with open("utils/game_logic.py", "w") as f:
    f.write(content)

print("Logging patch applied")
