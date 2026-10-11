import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("✅ Connected to TuronMafia VPS!")

sftp = ssh.open_sftp()

EXCLUDE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'userbot_session', '.system_generated', '.tempmediaStorage', '.user_uploaded', 'emojis', 'emoji_frames_diamond', 'emoji_frames_dollar', 'scratch', 'tmp', 'uploads', 'rollar', '.agents'}
EXCLUDE_FILES = {'.env', '.env.save', 'db.sqlite3', 'update_token.py', 'deploy_to_turon.py', 'generate_emojis.py', 'roles.zip', 'dump.rdb', 'cleanup.log', 'local_test.sqlite3', 'test_isolated_imports.py', 'fast_test_all.py'}

uploaded_count = 0

for root, dirs, files in os.walk('.'):
    # filter directories
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
    
    rel_dir = os.path.relpath(root, '.')
    remote_dir = '/root/Empire' if rel_dir == '.' else f'/root/Empire/{rel_dir.replace(os.sep, "/")}'
    
    # Ensure remote directory exists
    try:
        sftp.stat(remote_dir)
    except Exception:
        try:
            sftp.mkdir(remote_dir)
        except Exception:
            pass

    for file in files:
        if file in EXCLUDE_FILES or file.endswith('.pyc') or file.endswith('.log') or file.endswith('.webm') or file.endswith('.gif'):
            continue
        
        local_path = os.path.join(root, file)
        remote_path = f"{remote_dir}/{file}"
        try:
            sftp.put(local_path, remote_path)
            uploaded_count += 1
        except Exception as e:
            print(f"Error uploading {local_path}: {e}")

print(f"✅ Successfully synced {uploaded_count} files to /root/Empire/ on server!")
sftp.close()

# Restart empirebot service and verify status
stdin, stdout, stderr = ssh.exec_command('systemctl restart empirebot && sleep 3 && systemctl is-active empirebot')
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"🚀 TuronMafia (empirebot.service) holati: {status}")

# Check recent logs
stdin, stdout, stderr = ssh.exec_command('journalctl -u empirebot -n 15 --no-pager')
print("📋 Oxirgi loglar:\n", stdout.read().decode('utf-8', errors='replace'))

ssh.close()
