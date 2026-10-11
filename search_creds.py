import glob
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

files = glob.glob('C:/Users/user/.gemini/antigravity-ide/brain/*/.system_generated/logs/transcript.jsonl')
passwords = set()
ips = set()
for f in files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        content = fp.read()
        for m in re.findall(r'password[\'":\s=]+([^\s,;\'"}\]\\]+)', content, re.I):
            if len(m) >= 4:
                passwords.add(m)
        for ip in re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', content):
            if not ip.startswith('127.') and not ip.startswith('0.0.'):
                ips.add(ip)

print("IPs:", ips)
print("Passwords:", passwords)
