import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connected to server!")

new_token = "8755769302:AAEd5RyEyQmuebAazulk15whVBsyOKrNb4Y"

# 1. Update TOKEN in /root/Empire/.env
cmd_update = f"sed -i 's|^TOKEN=.*|TOKEN={new_token}|' /root/Empire/.env"
stdin, stdout, stderr = ssh.exec_command(cmd_update)
print("Updated .env line:")
stdin, stdout, stderr = ssh.exec_command("grep TOKEN= /root/Empire/.env")
print(stdout.read().decode("utf-8", errors="replace").strip())

# 2. Restart empirebot service
stdin, stdout, stderr = ssh.exec_command("systemctl restart empirebot && sleep 3 && systemctl is-active empirebot")
status = stdout.read().decode("utf-8", errors="replace").strip()
print(f"TuronMafia (empirebot.service) holati: {status}")

# 3. Check logs
stdin, stdout, stderr = ssh.exec_command("journalctl -u empirebot -n 25 --no-pager")
print("Logs:\n", stdout.read().decode("utf-8", errors="replace"))

ssh.close()
