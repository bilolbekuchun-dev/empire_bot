"""
Transform index.js for standalone Netlify/Vercel deployment.
- Adds API_BASE configuration variable
- Replaces all /webapp/ relative paths with API_BASE prefix
- Adds initData validation gate (Telegram vs browser check)

Strategy: Use a single-pass approach to avoid double-replacement issues.
"""
import re
import os

SRC = os.path.join(os.path.dirname(__file__), 'index.js')
DST = os.path.join(os.path.dirname(__file__), 'webapp_deploy', 'index.js')

with open(SRC, 'r', encoding='utf-8') as f:
    js = f.read()

# ──────────────────────────────────────────────────────────────
# 1) Insert API_BASE config right after "use strict";
# ──────────────────────────────────────────────────────────────
api_base_block = '''
    // ═══════ API SERVER CONFIGURATION ═══════
    // Bu URL bot serveri ishga tushganda o'zgaradi.
    // Hozircha bo'sh — relative path sifatida ishlaydi (same-origin).
    // Production'da bot server URL'ini qo'ying, masalan: "https://your-server.com"
    const API_BASE = window.__EMPIRE_API_BASE || "";

'''

js = js.replace(
    '"use strict";\n',
    '"use strict";\n' + api_base_block,
    1
)

# ──────────────────────────────────────────────────────────────
# 2) Replace all /webapp/ paths with API_BASE prefix
#    Strategy: single-pass regex to catch ALL patterns at once
# ──────────────────────────────────────────────────────────────

def replace_webapp_paths(text):
    """
    Replace /webapp/ paths in different contexts:
    - In template literals: `/webapp/... -> `${API_BASE}/webapp/...
    - In api("/webapp/...) -> api(API_BASE + "/webapp/...
    - In fetch("/webapp/...) -> fetch(API_BASE + "/webapp/...
    - In string: "/webapp/... -> " + API_BASE + "/webapp/...
    - In string: '/webapp/... -> ' + API_BASE + '/webapp/...
    """
    result = []
    i = 0
    while i < len(text):
        # Check for `/webapp/  (template literal context)
        if i < len(text) - 8 and text[i] == '`' and text[i+1:i+9] == '/webapp/':
            result.append('`${API_BASE}/webapp/')
            i += 9
            continue
        
        # Check for api("/webapp/ -> api(API_BASE + "/webapp/
        if (i < len(text) - 13 and text[i:i+5] == 'api("' and 
            text[i+5:i+13] == '/webapp/'):
            result.append('api(API_BASE + "/webapp/')
            i += 13
            continue
        
        # Check for fetch("/webapp/ -> fetch(API_BASE + "/webapp/
        if (i < len(text) - 15 and text[i:i+7] == 'fetch("' and 
            text[i+7:i+15] == '/webapp/'):
            result.append('fetch(API_BASE + "/webapp/')
            i += 15
            continue

        # Check for "/webapp/ in src= or href= attribute context
        # Like: src="/webapp/ or href="/webapp/
        if (i < len(text) - 9 and text[i] == '"' and 
            text[i+1:i+9] == '/webapp/' and
            i > 0 and text[i-1] == '='):
            result.append('"${API_BASE}/webapp/')
            # Actually this is inside a template literal most likely
            # Let's check if we're in a template literal context
            # For safety, use concatenation
            # But since these are mostly inside template literals already,
            # and the ` prefix is handled above, this handles 
            # HTML-in-JS like innerHTML
            # Since these are within template literals, ${API_BASE} works
            i += 9
            continue
        
        # Check for src="/webapp/ in regular strings (not template)
        # Like: src=\"/webapp/  -> src=\"" + API_BASE + "/webapp/
        if (i < len(text) - 9 and text[i:i+2] == '="' and 
            text[i+2:i+10] == '/webapp/'):
            result.append('="${API_BASE}/webapp/')
            i += 10
            continue
        
        # Regular character
        result.append(text[i])
        i += 1
    
    return ''.join(result)

js = replace_webapp_paths(js)

# Now handle remaining patterns more carefully:
# Any "/webapp/ that hasn't been converted yet (standalone strings)
# These are things like: const url = "/webapp/api/profile";
# Pattern: match "/webapp/ that isn't preceded by API_BASE
lines = js.split('\n')
new_lines = []
for line in lines:
    # Skip lines already containing API_BASE
    if 'API_BASE' in line:
        new_lines.append(line)
        continue
    
    # Replace "/webapp/ -> API_BASE + "/webapp/ in this line
    if '"/webapp/' in line:
        line = line.replace('"/webapp/', 'API_BASE + "/webapp/')
    if "'/webapp/" in line:
        line = line.replace("'/webapp/", "API_BASE + '/webapp/")
    
    new_lines.append(line)

js = '\n'.join(new_lines)

# ──────────────────────────────────────────────────────────────
# 3) Add initData validation gate (Telegram vs browser)
# ──────────────────────────────────────────────────────────────
initdata_gate = '''
    // ═══════ INITDATA TEKSHIRUVI (Telegram vs Brauzer) ═══════
    const isTelegramWebApp = !!(tg && initData && initData.length > 0);
    
    if (!isTelegramWebApp) {
        // Oddiy brauzerdan kirilgan — cheklangan rejim
        const gateOverlay = document.createElement("div");
        gateOverlay.id = "browser-gate-overlay";
        gateOverlay.style.cssText = "position:fixed; inset:0; z-index:99999; background:linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #0a0a1a 100%); display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:32px; font-family:'Outfit',sans-serif;";
        
        gateOverlay.innerHTML = `
            <div style="max-width:400px;">
                <div style="font-size:64px; margin-bottom:20px;">🎭</div>
                <h1 style="color:#fff; font-size:28px; font-weight:800; margin:0 0 12px;">Empire Mafia</h1>
                <p style="color:rgba(255,255,255,0.6); font-size:15px; line-height:1.6; margin:0 0 28px;">
                    Bu WebApp faqat <strong style="color:#38bdf8;">Telegram</strong> ilovasi orqali ochiladi.
                    <br>Iltimos, botga o\\'ting va <strong style="color:#f0c419;">🌐 Shaxsiy kabinet</strong> tugmasini bosing.
                </p>
                <a href="https://t.me/UnvMafiaBot" 
                   style="display:inline-flex; align-items:center; gap:8px; padding:14px 28px; background:linear-gradient(135deg, #2AABEE, #229ED9); color:#fff; text-decoration:none; border-radius:12px; font-size:16px; font-weight:700; box-shadow:0 4px 20px rgba(42,171,238,0.3); transition:transform 0.2s;"
                   onmouseover="this.style.transform='scale(1.05)'"
                   onmouseout="this.style.transform='scale(1)'">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.03-1.99 1.27-5.62 3.72-.53.36-1.01.54-1.44.53-.47-.01-1.38-.27-2.06-.49-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.75 3.99-1.73 6.65-2.87 7.97-3.44 3.8-1.58 4.59-1.86 5.1-1.87.11 0 .37.03.54.17.14.12.18.28.2.47-.01.06.01.24 0 .38z"/>
                    </svg>
                    Botga o\\'tish
                </a>
                <p style="color:rgba(255,255,255,0.25); font-size:11px; margin-top:24px;">
                    Telegram WebApp initData topilmadi
                </p>
            </div>
        `;
        document.body.appendChild(gateOverlay);
        
        // Asosiy kontentni yashiramiz
        const shell = document.querySelector(".shell");
        if (shell) shell.style.display = "none";
        
        console.warn("[Empire WebApp] Telegram initData topilmadi — brauzer rejimi.");
        return; // IIFE dan chiqamiz, hech narsa yuklanmaydi
    }

'''

# Insert after the initData/tgUser declarations
marker = 'const tgUser = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;\n'
if marker in js:
    js = js.replace(marker, marker + initdata_gate, 1)
    print("✅ initData gate qo'shildi")
else:
    # Try with \r\n
    marker_rn = marker.replace('\n', '\r\n')
    if marker_rn in js:
        js = js.replace(marker_rn, marker_rn + initdata_gate, 1)
        print("✅ initData gate qo'shildi (CRLF)")
    else:
        print("⚠️ tgUser marker topilmadi!")

# ──────────────────────────────────────────────────────────────
# 4) Write output
# ──────────────────────────────────────────────────────────────
with open(DST, 'w', encoding='utf-8') as f:
    f.write(js)

# Verify no broken double-API_BASE patterns
broken_count = js.count('API_BASE + " + API_BASE')
broken_count += js.count("API_BASE + ' + API_BASE")
broken_count += js.count('API_BASE + "" + API_BASE')
if broken_count > 0:
    print(f"⚠️ {broken_count} ta double-API_BASE topildi — tuzatish kerak!")
else:
    print("✅ Double-replacement yo'q")

print(f"✅ Transformatsiya tugadi!")
print(f"   Fayl saqlandi: {DST}")
print(f"   Fayl hajmi: {os.path.getsize(DST):,} bytes")
