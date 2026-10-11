import os

old_diamond_ids = ['5379995104347954750', '5211121920891723299']
old_dollar_ids = ['5215239948420003628', '5208946077574667388']

new_diamond_id = '5210941235912552228'
new_dollar_id = '5211062061932521090'

target_dirs = ['utils', 'handlers', 'keyboards', 'models', 'states']

modified_files = []

for root, _, files in os.walk('.'):
    norm_root = os.path.normpath(root)
    parts = norm_root.split(os.sep)
    if len(parts) > 1 and parts[0] in target_dirs:
        pass
    elif len(parts) == 1 and parts[0] in target_dirs:
        pass
    else:
        continue

    for file in files:
        if not file.endswith('.py'):
            continue
        path = os.path.join(root, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        orig = content
        for did in old_diamond_ids:
            content = content.replace(f"<tg-emoji emoji-id='{did}'>💎</tg-emoji>", f"<tg-emoji emoji-id='{new_diamond_id}'>💎</tg-emoji>")
            content = content.replace(f"<tg-emoji emoji-id='{did}'>💍</tg-emoji>", f"<tg-emoji emoji-id='{new_diamond_id}'>💎</tg-emoji>")
            content = content.replace(f'<tg-emoji emoji-id="{did}">💎</tg-emoji>', f'<tg-emoji emoji-id="{new_diamond_id}">💎</tg-emoji>')
            content = content.replace(f'<tg-emoji emoji-id="{did}">💍</tg-emoji>', f'<tg-emoji emoji-id="{new_diamond_id}">💎</tg-emoji>')
            content = content.replace(f'icon_custom_emoji_id="{did}"', f'icon_custom_emoji_id="{new_diamond_id}"')
            content = content.replace(f'icon_custom_emoji_id={did}', f'icon_custom_emoji_id="{new_diamond_id}"')
            content = content.replace(f"emoji-id='{did}'", f"emoji-id='{new_diamond_id}'")
            content = content.replace(f'emoji-id="{did}"', f'emoji-id="{new_diamond_id}"')

        for did in old_dollar_ids:
            content = content.replace(f"<tg-emoji emoji-id='{did}'>💵</tg-emoji>", f"<tg-emoji emoji-id='{new_dollar_id}'>💵</tg-emoji>")
            content = content.replace(f'<tg-emoji emoji-id="{did}">💵</tg-emoji>', f'<tg-emoji emoji-id="{new_dollar_id}">💵</tg-emoji>')
            content = content.replace(f'icon_custom_emoji_id="{did}"', f'icon_custom_emoji_id="{new_dollar_id}"')
            content = content.replace(f'icon_custom_emoji_id={did}', f'icon_custom_emoji_id="{new_dollar_id}"')
            content = content.replace(f"emoji-id='{did}'", f"emoji-id='{new_dollar_id}'")
            content = content.replace(f'emoji-id="{did}"', f'emoji-id="{new_dollar_id}"')

        if content != orig:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            modified_files.append(path)

print(f"Modifikatsiya qilingan fayllar soni: {len(modified_files)}")
for mf in modified_files:
    print(" ", mf)
