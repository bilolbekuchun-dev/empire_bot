# 🎭 Empire Mafia — WebApp (Netlify Deploy)

Bu papka Empire Mafia botining Telegram WebApp frontend'ini o'z ichiga oladi.

## 📁 Fayllar

| Fayl | Tavsif |
|------|--------|
| `index.html` | Asosiy HTML sahifa |
| `index.css` | Barcha stillar (88KB) |
| `index.js` | Barcha JavaScript logika (275KB) |
| `netlify.toml` | Netlify konfiguratsiyasi |
| `_redirects` | SPA routing (fallback) |

## 🚀 Netlify'ga Deploy Qilish

### 1-usul: Netlify Dashboard (Eng oson)
1. [netlify.com](https://app.netlify.com) ga kiring
2. "Add new site" → "Deploy manually" ni tanlang
3. `webapp_deploy` papkasini drag & drop qiling
4. Deploy tugagach, sizga URL beriladi (masalan: `https://empire-mafia-webapp.netlify.app`)

### 2-usul: Netlify CLI
```bash
# Login
npx netlify-cli login

# Yangi sayt yaratish va deploy
npx netlify-cli deploy --create-site --dir=.

# Ishonch hosil qilgach, production'ga
npx netlify-cli deploy --prod --dir=.
```

## ⚙️ Sozlash

### API Server URL
Deploy qilgandan keyin, `index.html` faylida `__EMPIRE_API_BASE` ni bot server URL'iga o'zgartiring:

```html
<script>
    window.__EMPIRE_API_BASE = "https://your-bot-server.com";
</script>
```

> **Muhim**: Bot serverida CORS yoqilgan bo'lishi kerak (webapp_api.py da `Access-Control-Allow-Origin: *` mavjud).

### Bot Keyboard URL
Bot'dagi `WEBAPP_URL` ni Netlify URL'iga o'zgartiring:

```env
# .env faylida:
WEBAPP_URL=https://your-site.netlify.app
```

## 🔒 Xavfsizlik

- **initData tekshiruvi**: Oddiy brauzerdan kirilganda WebApp bloklanadi
- Faqat Telegram WebApp orqali ochilganda ishlaydi
- Brauzer foydalanuvchilari "Botga o'tish" tugmasini ko'radi

## 📝 Qayta Build Qilish

Agar `index.js` yoki `index.html` da o'zgarish qilsangiz, qayta transform qiling:

```bash
cd Empire/
python transform_webapp.py
```

Bu script asl `index.js` ni olib, `API_BASE` va `initData` gate qo'shib `webapp_deploy/` ga saqlaydi.
