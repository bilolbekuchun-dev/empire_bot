with open("utils/game_logic.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "import logging" in line:
        continue
    if "logging.info" in line:
        continue
    if "print(" in line and "DEBUG:" in line:
        continue
    new_lines.append(line)

with open("utils/game_logic.py", "w") as f:
    f.writelines(new_lines)
