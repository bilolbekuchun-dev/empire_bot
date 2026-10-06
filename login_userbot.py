import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import qrcode
from config import TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH, TELEGRAM_USERBOT_SESSION

async def qr_login_flow(client: TelegramClient):
    print("\n" + "=" * 55)
    print("📷 TELEGRAM QR-KOD ORQALI KIRISH")
    print("=" * 55)
    print("⏳ QR-kod yaratilmoqda, kuting...")

    await client.connect()
    qr = await client.qr_login()

    print("\n" + "-" * 55)
    print("👉 TELEFONINGIZDA Telegram -> Sozlamalar -> Qurilmalar -> 'Qurilmani ulash'ni bosing va quyidagi QR-kodni skanerlang:\n")

    qr_obj = qrcode.QRCode(border=1)
    qr_obj.add_data(qr.url)
    qr_obj.print_ascii(invert=True)

    print("-" * 55)
    print("⏳ Skanerlashingiz kutilmoqda...")

    try:
        user = await qr.wait(timeout=120)
        return user
    except SessionPasswordNeededError:
        print("\n🔐 Hisobingizda Ikki bosqichli parol (2FA) yoqilgan!")
        pwd = input("🔑 2FA parolingizni kiriting: ").strip()
        user = await client.sign_in(password=pwd)
        return user
    except Exception as e:
        if "Two-steps verification" in str(e) or "password is required" in str(e):
            print("\n🔐 Hisobingizda Ikki bosqichli parol (2FA) yoqilgan!")
            pwd = input("🔑 2FA parolingizni kiriting: ").strip()
            user = await client.sign_in(password=pwd)
            return user
        print(f"❌ QR login xatosi: {e}")
        return None

async def phone_login_flow(client: TelegramClient):
    print("\n" + "=" * 55)
    print("📱 TELEFON RAQAM ORQALI KIRISH")
    print("=" * 55)
    await client.start()
    return await client.get_me()

async def main():
    print("=" * 55)
    print("🤖 TELEGRAM USERBOT KABINETI (NFT MARKET LOGIN)")
    print("=" * 55)

    session_path = TELEGRAM_USERBOT_SESSION + ".session" if not TELEGRAM_USERBOT_SESSION.endswith(".session") else TELEGRAM_USERBOT_SESSION
    session_dir = os.path.dirname(session_path)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)

    print("Qaysi usulda ulamoqchisiz?")
    print("1️⃣ - 📷 QR-kod orqali (TAVSIYA ETILADI)")
    print("2️⃣ - 📱 Telefon raqam orqali")

    tanlov = input("\nTanlovingizni kiriting (1 yoki 2, standart 1): ").strip()

    # Reset corrupted session file if present before new login
    for f in [session_path, session_path + "-journal"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    client = TelegramClient(
        TELEGRAM_USERBOT_SESSION,
        TELEGRAM_USERBOT_API_ID,
        TELEGRAM_USERBOT_API_HASH,
        device_model="Desktop",
        system_version="Windows 11",
        app_version="5.8.0 x64",
        lang_code="uz",
        system_lang_code="uz"
    )

    user = None
    if tanlov == "2":
        user = await phone_login_flow(client)
    else:
        user = await qr_login_flow(client)

    if await client.is_user_authorized():
        me = await client.get_me()
        print("\n" + "=" * 55)
        print("🎉 AKKAUNT MUVAFFAQIYATLI ULANDI!")
        print(f"👤 Ism: {me.first_name}")
        print(f"🏷 Username: @{me.username if me.username else 'Username yo`q'}")
        print(f"📱 Telefon: {me.phone}")
        print(f"🆔 User ID: {me.id}")
        print("=" * 55)
        print("\nEndi sessiyani serverga yuklash uchun quyidagi buyruqni bering:")
        print("python sync_session_to_server.py\n")
    else:
        print("\n❌ Akkauntga kirish amalga oshmadi.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
