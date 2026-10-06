import re

with open("utils/game_logic.py", "r") as f:
    content = f.read()

# I will just write a regex to remove ALL my debug prints and loggings
# The original file didn't have these.
content = re.sub(r'^\s*import logging\n\s*logging\.info\([^)]+\)\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*logging\.info\([^)]+\)\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*print\([^)]+DEBUG[^)]+\)\n', '', content, flags=re.MULTILINE)

with open("utils/game_logic.py", "w") as f:
    f.write(content)
