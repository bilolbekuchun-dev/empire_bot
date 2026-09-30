import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

files_to_check = []
for root, dirs, files in os.walk('.'):
    if 'venv' in root or '.git' in root or '__pycache__' in root or 'scratch' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            files_to_check.append(os.path.join(root, f))

found = []
for file_path in files_to_check:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for idx, line in enumerate(lines):
        if ('<tg-emoji' in line or '<b>' in line or '<code>' in line) and ('message.answer(' in line or 'call.message.edit_text(' in line or 'bot.send_message(' in line):
            if 'parse_mode' not in line:
                # check surrounding lines (multi-line call)
                block = "".join(lines[max(0, idx-2):min(len(lines), idx+8)])
                if 'parse_mode' not in block:
                    found.append((file_path, idx+1, line.strip()))

print(f"Total potential missing parse_mode found: {len(found)}")
for fp, ln, text in found:
    print(f"{fp}:{ln} -> {text[:100]}")
