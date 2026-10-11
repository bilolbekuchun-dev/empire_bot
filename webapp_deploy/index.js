(function () {
    "use strict";

    // ═══════ API SERVER CONFIGURATION ═══════
    // Bu URL bot serveri ishga tushganda o'zgaradi.
    // Hozircha bo'sh — relative path sifatida ishlaydi (same-origin).
    // Production'da bot server URL'ini qo'ying, masalan: "https://your-server.com"
    const API_BASE = window.__EMPIRE_API_BASE || "";


    function showFatalError(msg) {
        try {
            console.error(msg);
            if (typeof isAdminUser !== "undefined" && !isAdminUser) {
                if (document.querySelector('[data-fatal-box="1"]')) return;
                const box = document.createElement("div");
                box.setAttribute("data-fatal-box", "1");
                box.style.cssText = "position:fixed; inset:0; z-index:99999; background:#0a0a0f; color:#f2f2f2; font-family:inherit; font-size:14px; padding:24px; display:flex; align-items:center; justify-content:center; text-align:center;";
                box.textContent = "⚠️ Nimadir xato ketdi. Iltimos, ilovani qayta oching.";
                document.body.appendChild(box);
                return;
            }
            const box = document.createElement("div");
            box.setAttribute("data-fatal-box", "1");
            box.style.cssText = "position:fixed; inset:0; z-index:99999; background:#0a0a0f; color:#ffb4b4; font-family:monospace; font-size:13px; padding:16px; overflow:auto; white-space:pre-wrap; word-break:break-word;";
            box.textContent = "⚠️ XATOLIK YUZ BERDI:\n\n" + msg;
            document.body.appendChild(box);
        } catch (e) {}
    }
    window.addEventListener("error", (e) => {
        showFatalError((e.message || "noma'lum xato") + "\n" + (e.filename || "") + ":" + (e.lineno || "") + ":" + (e.colno || "") + "\n\n" + ((e.error && e.error.stack) || ""));
    });
    window.addEventListener("unhandledrejection", (e) => {
        const reason = e.reason;
        showFatalError("Promise rejection: " + (reason && reason.message ? reason.message : String(reason)) + "\n\n" + ((reason && reason.stack) || ""));
    });

    try {
        const fontLink = document.createElement("link");
        fontLink.rel = "stylesheet";
        fontLink.href = "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap";
        document.head.appendChild(fontLink);
        const iconLink = document.createElement("link");
        iconLink.rel = "stylesheet";
        iconLink.href = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css";
        document.head.appendChild(iconLink);
    } catch (e) {}

    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) {
        try { tg.ready(); } catch (e) {}
        try { tg.expand(); } catch (e) {}
        try { tg.disableVerticalSwipes(); } catch (e) {}
        try { tg.setHeaderColor("#05080a"); } catch (e) {}
        try { tg.setBackgroundColor("#05080a"); } catch (e) {}
    }

    const initData = tg ? tg.initData : "";
    const tgUser = tg && tg.initDataUnsafe ? tg.initDataUnsafe.user : null;

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
                    <br>Iltimos, botga o\'ting va <strong style="color:#f0c419;">🌐 Shaxsiy kabinet</strong> tugmasini bosing.
                </p>
                <a href="https://t.me/UnvMafiaBot" 
                   style="display:inline-flex; align-items:center; gap:8px; padding:14px 28px; background:linear-gradient(135deg, #2AABEE, #229ED9); color:#fff; text-decoration:none; border-radius:12px; font-size:16px; font-weight:700; box-shadow:0 4px 20px rgba(42,171,238,0.3); transition:transform 0.2s;"
                   onmouseover="this.style.transform='scale(1.05)'"
                   onmouseout="this.style.transform='scale(1)'">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.03-1.99 1.27-5.62 3.72-.53.36-1.01.54-1.44.53-.47-.01-1.38-.27-2.06-.49-.83-.27-1.49-.42-1.43-.88.03-.24.37-.49 1.02-.75 3.99-1.73 6.65-2.87 7.97-3.44 3.8-1.58 4.59-1.86 5.1-1.87.11 0 .37.03.54.17.14.12.18.28.2.47-.01.06.01.24 0 .38z"/>
                    </svg>
                    Botga o\'tish
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


    setTimeout(() => {
        try {
            const el = document.getElementById("sidebar-user-name");
            const stillLoading = el && (el.textContent === "" || el.textContent.indexOf("Yuklanmoqda") !== -1 || el.textContent === "webapp_loading");
            const hasFatalBox = document.querySelector('[data-fatal-box]');
            if (stillLoading && !hasFatalBox) {
                const diag = [
                    "window.Telegram mavjud: " + (!!window.Telegram),
                    "Telegram.WebApp mavjud: " + !!(window.Telegram && window.Telegram.WebApp),
                    "initData uzunligi: " + (initData ? initData.length : 0),
                    "User Agent: " + navigator.userAgent,
                ].join("\n");
                const box = document.createElement("div");
                box.setAttribute("data-fatal-box", "1");
                box.style.cssText = "position:fixed; inset:0; z-index:99999; background:#0a0a0f; color:#ffd27a; font-family:monospace; font-size:13px; padding:16px; overflow:auto; white-space:pre-wrap; word-break:break-word;";
                box.textContent = "⏳ Ilova 4 soniyadan ko'p yuklanmoqda.\n\nDiagnostika:\n" + diag + "\n\nQuyidagi tugmani bosing:";
                const btn = document.createElement("button");
                btn.textContent = "🔄 Qayta yuklash";
                btn.style.cssText = "margin-top:16px; padding:12px 20px; font-size:15px; background:#f0c419; color:#000; border:none; border-radius:8px; display:block;";
                btn.onclick = () => location.reload();
                box.appendChild(btn);
                document.body.appendChild(box);
            }
        } catch (e) {}
    }, 4000);

    let profileCache = null;
    let currentGroupChatId = null;
    let geroyLoaded = false;
    let geroyMarketLoaded = false;
    let nftMarketLoaded = false;
    let geroyMarketPage = 1;
    let geroyMarketHasMore = false;
    let isAdminUser = false;
    let UI = {};

    function t(key, fallback) {
        return (UI && UI[key]) || fallback || key;
    }

    function isVideoUrl(url) {
        return !!url && /\.(mp4|webm|mov)(\?|$)/i.test(url);
    }

    function deriveVideoPoster(url) {
        return url.replace(/\.(mp4|webm|mov)(\?|$)/i, ".jpg$2");
    }

    function smoothScrollTo(el, targetLeft, duration) {
        const startLeft = el.scrollLeft;
        const delta = targetLeft - startLeft;
        if (!delta) return;
        const startTime = performance.now();
        const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
        function step(now) {
            const elapsed = now - startTime;
            const progress = Math.min(1, elapsed / duration);
            el.scrollLeft = startLeft + delta * ease(progress);
            if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }

    function runSlideshow(imgEl, gallery, timersArr) {
        if (!imgEl || !gallery.length) { if (imgEl) imgEl.style.display = "none"; return; }
        imgEl.src = gallery[0];
        imgEl.style.display = "";
        imgEl.style.opacity = "1";
        if (gallery.length < 2) return;

        const layerB = imgEl.cloneNode(false);
        layerB.removeAttribute("id");
        layerB.style.opacity = "0";
        imgEl.parentElement.insertBefore(layerB, imgEl.nextSibling);

        let idx = 0;
        let showingA = true;
        const timer = setInterval(() => {
            idx = (idx + 1) % gallery.length;
            const next = showingA ? layerB : imgEl;
            const cur = showingA ? imgEl : layerB;
            const doTransition = () => {
                next.style.opacity = "1";
                cur.style.opacity = "0";
            };
            next.onload = doTransition;
            next.src = gallery[idx];
            if (next.complete) doTransition();
            showingA = !showingA;
        }, 4500);
        timersArr.push(timer);
    }

    function playWhenBuffered(video) {
        if (!video || video.dataset.playArmed) return;
        video.dataset.playArmed = "1";
        let started = false;
        const tryStart = () => {
            if (started) return;
            started = true;
            video.play().catch(() => {});
        };
        if (video.readyState >= 3) { tryStart(); return; }
        video.addEventListener("canplaythrough", tryStart, { once: true });
        video.addEventListener("canplay", () => { setTimeout(tryStart, 400); }, { once: true });
        setTimeout(tryStart, 3000);
    }

    function setMediaBanner(idPrefix, url) {
        const img = document.getElementById(idPrefix + "-img");
        const video = document.getElementById(idPrefix + "-video");
        const muteBtn = document.getElementById(idPrefix + "-mute");
        if (!video) {
            if (url) { img.src = url; img.style.display = ""; } else { img.style.display = "none"; }
            return;
        }
        if (url && isVideoUrl(url)) {
            video.poster = deriveVideoPoster(url);
            video.preload = "auto";
            video.src = url;
            video.muted = true;
            video.style.display = "";
            img.style.display = "none";
            if (muteBtn) {
                muteBtn.style.display = "flex";
                muteBtn.innerHTML = `<i class="fa-solid fa-volume-xmark"></i>`;
                muteBtn.onclick = (ev) => {
                    ev.stopPropagation();
                    ev.preventDefault();
                    video.muted = !video.muted;
                    muteBtn.innerHTML = video.muted ? `<i class="fa-solid fa-volume-xmark"></i>` : `<i class="fa-solid fa-volume-high"></i>`;
                };
            }
        } else if (url) {
            img.src = url; img.style.display = ""; video.style.display = "none";
            if (muteBtn) muteBtn.style.display = "none";
        } else {
            img.style.display = "none"; video.style.display = "none";
            if (muteBtn) muteBtn.style.display = "none";
        }
    }

    function showBannerPreview(url) {
        const img = document.getElementById("adm-t-banner-preview");
        if (!url) { img.style.display = "none"; return; }
        img.src = url; img.style.display = "";
    }

    function tf(key, params, fallback) {
        let str = t(key, fallback);
        if (params) {
            Object.keys(params).forEach((k) => {
                str = str.split("{" + k + "}").join(params[k]);
            });
        }
        return str;
    }

    function toast(msg, kind) {
        let el = document.querySelector(".wa-toast");
        if (!el) {
            el = document.createElement("div");
            el.className = "wa-toast";
            document.body.appendChild(el);
        }
        el.textContent = msg;
        el.className = "wa-toast show" + (kind ? " " + kind : "");
        clearTimeout(el._t);
        el._t = setTimeout(() => el.classList.remove("show"), 2200);
    }

    async function api(path, payload) {
        const res = await fetch(path, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.assign({ initData: initData }, payload || {})),
        });
        const data = await res.json().catch(() => ({ ok: false, error: "bad_response" }));
        if (!res.ok || !data.ok) {
            throw new Error(data.error || "request_failed");
        }
        return data;
    }

    function fmt(n) {
        return (n || 0).toLocaleString("en-US");
    }

    const FALLBACK_CHAT_BG = "radial-gradient(circle at 50% 30%, rgba(34,197,94,.14), transparent 60%), linear-gradient(180deg, #14120f, #0d0a08)";

    function setChatWallpaper(box, userId) {
        if (!userId) { box.style.backgroundImage = FALLBACK_CHAT_BG; return; }
        const avatarUrl = `${API_BASE}/webapp/avatar/${userId}`;
        const probe = new Image();
        probe.onload = () => { box.style.backgroundImage = `linear-gradient(rgba(13,10,8,.88), rgba(13,10,8,.88)), url(${avatarUrl})`; };
        probe.onerror = () => { box.style.backgroundImage = FALLBACK_CHAT_BG; };
        box.style.backgroundImage = FALLBACK_CHAT_BG;
        probe.src = avatarUrl;
    }

    function tgConfirm(message) {
        return new Promise((resolve) => {
            if (tg && typeof tg.showConfirm === "function") {
                tg.showConfirm(message, (ok) => resolve(!!ok));
            } else {
                resolve(confirm(message));
            }
        });
    }

    function escapeHtml(s) {
        const d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    }

    const BANNER_COLORS = {
        qizil: "#f87171", pushti: "#f472b6", binafsha: "#c084fc", siyoh: "#818cf8",
        moviy: "#60a5fa", osmon: "#38bdf8", zumrad: "#2dd4bf", yashil: "#4ade80",
        limon: "#a3e635", sariq: "#facc15", oltin: "#fbbf24", apelsin: "#fb923c",
        jigar: "#d4a373", kulrang: "#cbd5e1",
    };
    const BANNER_SIZES = { kichik: "11px", normal: "14px", katta: "17px", jkatta: "21px" };

    /* [rang]matn[/rang] yoki [olcham]matn[/olcham] — ichma-ich ham bo'lishi mumkin.
       Yopilish tegi bo'lmasa (eski uslub), qatorning qolgan qismiga qo'llanadi. */
    function parseInlineMarkers(text) {
        let result = "";
        let i = 0;
        let plainStart = 0;
        const flushPlain = (end) => {
            if (end > plainStart) result += escapeHtml(text.slice(plainStart, end));
        };
        while (i < text.length) {
            const rest = text.slice(i);
            const openMatch = rest.match(/^\[(\w+)\]\s?/);
            if (openMatch && (BANNER_COLORS[openMatch[1]] || BANNER_SIZES[openMatch[1]])) {
                const name = openMatch[1];
                const afterOpen = i + openMatch[0].length;
                const closeTag = `[/${name}]`;
                const closeIdx = text.indexOf(closeTag, afterOpen);
                flushPlain(i);
                const styleAttr = BANNER_COLORS[name] ? `color:${BANNER_COLORS[name]};` : `font-size:${BANNER_SIZES[name]};`;
                if (closeIdx !== -1) {
                    const inner = text.slice(afterOpen, closeIdx);
                    result += `<span style="${styleAttr}">${parseInlineMarkers(inner)}</span>`;
                    i = closeIdx + closeTag.length;
                } else {
                    const inner = text.slice(afterOpen);
                    result += `<span style="${styleAttr}">${parseInlineMarkers(inner)}</span>`;
                    i = text.length;
                }
                plainStart = i;
                continue;
            }
            i++;
        }
        flushPlain(text.length);
        return result;
    }

    function formatBannerText(s) {
        const lines = String(s || "").split("\n");
        return lines.map((line) => {
            const trimmed = line.trim();
            if (!trimmed) return `<div class="ban-gap"></div>`;
            return `<div class="ban-line">${parseInlineMarkers(trimmed)}</div>`;
        }).join("");
    }
    /* ---------------- navigation ---------------- */
    function goTo(target) {
        document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
        const view = document.getElementById("view-" + target);
        if (view) view.classList.add("active");

        document.querySelectorAll(".nav-item, .tab-item").forEach((el) => el.classList.remove("active"));
        document.querySelectorAll('[data-target="' + target + '"]').forEach((el) => el.classList.add("active"));

        closeSidebarDrawer();

        if (target === "leaderboard" && !leaderboardLoaded) loadLeaderboard("wins");
        if (target === "history" && !historyLoaded) loadHistory();
        if (target === "groups" && !groupsLoaded) loadGroups();
        if (target === "admin" && !adminLoaded) { adminLoaded = true; loadAdminStats(); }
        if (target === "admin") refreshAdminSupportBadge();
        if (target === "admin-support") showAdminSupportList(); else stopAdminSupportThreadPolling();
        if (target === "tournament" && !tournamentLoaded) { tournamentLoaded = true; loadTournament(); }
        if (target === "holiday" && !holidayLoaded) { holidayLoaded = true; loadHoliday(); }
        if (target === "tm-tournament" && !tmTournamentLoaded) { tmTournamentLoaded = true; setupTmTournamentView(); loadTmTournamentList(); }
        if (target === "geroy" && !geroyLoaded) loadGeroy();
        if (target === "geroy-market" && !geroyMarketLoaded) { geroyMarketLoaded = true; initGeroyMarket(); }
        if (target === "nft-market" && !nftMarketLoaded) { nftMarketLoaded = true; initNftMarket(); }
        if (target === "support") startSupportChatPolling(); else stopSupportChatPolling();
        if (target === "overview") startOverviewPolling(); else stopOverviewPolling();

        const fab = document.getElementById("support-fab-btn");
        if (fab) fab.classList.toggle("hidden", target !== "overview");
    }

    let overviewPollTimer = null;
    function startOverviewPolling() {
        if (overviewPollTimer) return;
        overviewPollTimer = setInterval(() => {
            tournamentLoaded = true;
            safe(() => loadTournament(), "loadTournament");
        }, 15000);
    }
    function stopOverviewPolling() {
        if (overviewPollTimer) clearInterval(overviewPollTimer);
        overviewPollTimer = null;
    }

    function openSidebarDrawer() {
        document.getElementById("sidebar").classList.add("open");
        document.getElementById("sidebar-backdrop").classList.add("open");
    }
    function closeSidebarDrawer() {
        document.getElementById("sidebar").classList.remove("open");
        document.getElementById("sidebar-backdrop").classList.remove("open");
    }

    function setupNav() {
        document.querySelectorAll(".nav-item, .tab-item").forEach((btn) => {
            btn.addEventListener("click", () => {
                let target = btn.dataset.target;
                if (target === "support" && isAdminUser) target = "admin-support";
                if (target) goTo(target);
            });
        });
        document.getElementById("menu-toggle-btn").addEventListener("click", openSidebarDrawer);
        document.getElementById("sidebar-backdrop").addEventListener("click", closeSidebarDrawer);

        const fab = document.getElementById("support-fab-btn");
        if (fab) fab.addEventListener("click", () => {
            goTo(isAdminUser ? "admin-support" : "support");
        });
    }

    let supportFabTimer = null;
    async function refreshSupportFabBadge() {
        const fabBadge = document.getElementById("support-fab-badge");
        const navBadge = document.getElementById("nav-support-badge");
        try {
            let unread = 0;
            if (isAdminUser) {
                const res = await api(API_BASE + "/webapp/api/admin_support_list");
                unread = (res.conversations || []).filter((c) => c.unread).length;
            } else {
                const res = await api(API_BASE + "/webapp/api/support_unread");
                unread = res.unread || 0;
            }
            [fabBadge, navBadge].forEach((badge) => {
                if (!badge) return;
                if (unread > 0) {
                    badge.textContent = unread > 99 ? "99+" : String(unread);
                    badge.style.display = "";
                } else {
                    badge.style.display = "none";
                }
            });
        } catch (e) { /* jim */ }
        if (!supportFabTimer) supportFabTimer = setInterval(refreshSupportFabBadge, 6000);
    }

    /* ---------------- overview ---------------- */
    function renderUser(data) {
        const u = data.user || {};
        document.getElementById("user-name").textContent = u.full_name || t("label_gamer");
        document.getElementById("user-username").textContent = u.username ? "@" + u.username : "";

        document.getElementById("sidebar-user-name").textContent = u.full_name || t("label_gamer");
        document.getElementById("sidebar-user-username").textContent = u.username ? "@" + u.username : "";

        if (u.user_id) {
            const svgFallback = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100%" height="100%" fill="%231e1e2d"/><text x="50%" y="55%" font-size="42" fill="%23f0c419" text-anchor="middle" dominant-baseline="middle">👤</text></svg>`;
            const proxyUrl = `${API_BASE}/webapp/avatar/${u.user_id}`;
            const photoUrl = u.photo_url || (tgUser && tgUser.photo_url) || null;

            [document.getElementById("user-avatar"), document.getElementById("sidebar-user-avatar")].forEach((img) => {
                if (!img) return;
                img.onerror = () => {
                    if (photoUrl && img.src !== photoUrl) {
                        img.src = photoUrl;
                    } else if (img.src !== svgFallback) {
                        img.src = svgFallback;
                    }
                    img.onerror = null;
                };
                img.src = photoUrl || proxyUrl;
            });
        }

        const rank = data.rank || { title: t("label_gamer"), icon: "⭐️" };
        document.getElementById("rank-badge").innerHTML = `<i class="fa-solid fa-star"></i> ${escapeHtml(rank.title)}`;

        const games = data.profile.games_count || 0;
        const wins = data.profile.wins || 0;
        const pct = games > 0 ? Math.round((wins / games) * 100) : 0;
        document.getElementById("xp-pct-val").textContent = pct + "%";
        document.getElementById("xp-bar-fill").style.width = pct + "%";
        document.getElementById("stat-winrate").textContent = pct + "%";

        document.getElementById("bal-dollars").textContent = fmt(data.profile.dollar);
        document.getElementById("bal-diamonds").textContent = fmt(data.profile.diamond);

        const vipActive = !!(data.vip && data.vip.active);
        const vipText = vipActive ? `VIP — ${data.vip.days_left} ${t("label_days_short")}` : t("label_no_vip");
        document.getElementById("sidebar-vip-text").textContent = vipText;
        document.getElementById("avatar-ring").classList.toggle("vip", vipActive);
        document.body.classList.toggle("vip-active", vipActive);
        document.getElementById("vip-luxury-badge").style.display = vipActive ? "" : "none";

        if (data.can_manage_groups) {
            document.getElementById("nav-groups").style.display = "";
        }
        if (data.is_admin) {
            document.getElementById("nav-admin").style.display = "";
            document.getElementById("gm-tab-admin-btn").style.display = "";
            document.getElementById("nft-tab-admin-btn").style.display = "";
            document.getElementById("nft-tab-storeedit-btn").style.display = "";
            isAdminUser = true;
        }
        if (data.is_tournament_manager) {
            document.getElementById("nav-tm-tournament").style.display = "";
        }
        refreshSupportFabBadge();

        renderOwnedSummary(data);
        renderDailyClaim(data);
    }

    const DAILY_REWARD_TABLE = { 1: 100, 2: 150, 3: 200, 4: 250, 5: 300, 6: 400, 7: 500 };

    function renderDailyClaim(data) {
        const dc = data.daily_claim || data.daily || {};
        const streak = dc.streak || 0;
        const claimedToday = dc.claimed_today !== undefined ? dc.claimed_today : (dc.can_claim === false);
        const nextStreak = dc.next_streak || (claimedToday ? (streak || 1) : (streak >= 7 ? 1 : (streak === 0 ? 1 : streak + 1)));
        const nextReward = dc.next_reward || DAILY_REWARD_TABLE[nextStreak] || 100;

        const box = document.getElementById("daily-claim-days");
        if (box) {
            let html = "";
            for (let day = 1; day <= 7; day++) {
                const isDone = claimedToday ? day <= streak : day < nextStreak;
                const isCurrent = !claimedToday && day === nextStreak;
                html += `
                    <div class="dc-day${isDone ? " done" : ""}${isCurrent ? " current" : ""}">
                        <span class="dc-check">${isDone ? '<i class="fa-solid fa-check"></i>' : day}</span>
                        <span class="dc-amt">${DAILY_REWARD_TABLE[day]}$</span>
                    </div>
                `;
            }
            box.innerHTML = html;
        }

        const btn = document.getElementById("daily-claim-btn");
        if (btn) {
            if (claimedToday) {
                btn.textContent = t("daily_claim_done_btn") || "Bugun olingan ✅";
                btn.disabled = true;
                btn.classList.add("disabled");
                btn.style.opacity = "0.6";
                btn.style.pointerEvents = "none";
                btn.style.cursor = "not-allowed";
            } else {
                btn.textContent = `${t("daily_claim_btn") || "Kunlik bonus olish"} (+${nextReward}$)`;
                btn.disabled = false;
                btn.classList.remove("disabled");
                btn.style.opacity = "1";
                btn.style.pointerEvents = "auto";
                btn.style.cursor = "pointer";
            }
        }
    }

    async function claimDaily() {
        const btn = document.getElementById("daily-claim-btn");
        if (!btn || btn.disabled) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/claim_daily");
            if (!res.ok) {
                if (res.error === "already_claimed_today") {
                    if (profileCache) {
                        profileCache.daily_claim = profileCache.daily_claim || {};
                        profileCache.daily_claim.claimed_today = true;
                        renderUser(profileCache);
                    }
                    toast(t("daily_claim_done_btn") || "Bugun bonusni olib bo'lgansiz!", "info");
                    return;
                }
                throw new Error(res.error || "failed");
            }
            if (profileCache && profileCache.profile) {
                profileCache.profile.dollar = res.dollar;
                profileCache.daily_claim = {
                    streak: res.streak,
                    claimed_today: true,
                    next_streak: res.streak,
                    next_reward: DAILY_REWARD_TABLE[res.streak] || 100
                };
                profileCache.daily = profileCache.daily_claim;
                renderUser(profileCache);
            }
            toast(tf("daily_claim_success", { reward: res.reward, streak: res.streak }), "success");
            if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
        } catch (e) {
            toast(t("toast_generic_error"), "error");
            if (profileCache && profileCache.daily_claim && profileCache.daily_claim.claimed_today) {
                btn.disabled = true;
            } else {
                btn.disabled = false;
            }
        }
    }

    function renderOwnedSummary(data) {
        const box = document.getElementById("owned-summary-container");
        if (!box) return;
        const icons = {
            himoya: "🛡", hujjat: "📁", qotildan_himoya: "🔪",
            osishdan_himoya: "⚖️", miltiq: "😀", doridan_himoya: "➕",
            maska: "🎭", slip_himoya: "🪤", geroy_himoya: "🔰",
        };
        const labelKeys = {
            himoya: "item_himoya", hujjat: "item_hujjat", qotildan_himoya: "item_qotildan_himoya",
            osishdan_himoya: "item_osishdan_himoya", miltiq: "item_miltiq", doridan_himoya: "item_doridan_himoya",
            maska: "item_maska", slip_himoya: "item_slip_himoya", geroy_himoya: "item_geroy_himoya",
        };
        let html = "";
        Object.keys(icons).forEach((field) => {
            const count = data.profile[field] || 0;
            html += `<div class="owned-chip ${count > 0 ? "has" : ""}" title="${t(labelKeys[field])}"><span class="owned-icon">${icons[field]}</span><b>${count}</b></div>`;
        });
        html += `<div class="owned-chip ${data.has_geroy ? "has" : ""}" title="${t("item_geroy_field")}"><span class="owned-icon">🥷</span><b>${data.has_geroy ? "✓" : "0"}</b></div>`;
        const vipActive = !!(data.vip && data.vip.active);
        html += `<div class="owned-chip ${vipActive ? "has" : ""}" title="VIP"><span class="owned-icon">👑</span><b>${vipActive ? data.vip.days_left + " " + t("label_days_short") : t("label_no_vip")}</b></div>`;
        box.innerHTML = html;
    }

    function renderGlobalStats(data) {
        document.getElementById("global-active-games").textContent = fmt(data.global_stats.active_games);
        document.getElementById("global-total-users").textContent = fmt(data.global_stats.total_users);
    }

    /* ---------------- admin panel ---------------- */
    let adminLoaded = false;

    let adminGroupsLoaded = false;
    let homeCarouselTimers = [];
    let homeCarouselAutoTimer = null;
    let heroCarouselTimer = null;

    /* ---------------- tournament (public) ---------------- */
    let tournamentLoaded = false;
    let tmTournamentLoaded = false;

    function renderNextUpList(list, boxId, idPrefix, timerTag) {
        boxId = boxId || "tournament-nextup-list";
        idPrefix = idPrefix || "nextup-car-";
        timerTag = timerTag || "_nextup";

        homeCarouselTimers.filter((tm) => tm && typeof tm === "object" && tm.tag === timerTag).forEach((tm) => clearInterval(tm.id));
        homeCarouselTimers = homeCarouselTimers.filter((tm) => !(tm && typeof tm === "object" && tm.tag === timerTag));

        const box = document.getElementById(boxId);
        if (!box) return;
        if (!list.length) { box.innerHTML = ""; return; }

        box.innerHTML = list.map((u, i) => {
            const isFinished = u.cardStatus === "finished";
            const joinHtml = (!isFinished && u.contact_username) ? `
                <a href="https://t.me/${escapeHtml(u.contact_username.replace(/^@/, ""))}" target="_blank" rel="noopener" class="tournament-join-btn tournament-join-btn-inline">
                    ${u.contact_user_id ? `<span class="tournament-join-avatar"><img src="${API_BASE}/webapp/avatar_chat/${u.contact_user_id}" alt="" onerror="this.parentElement.style.display='none';"></span>` : ""}
                    <i class="fa-brands fa-telegram"></i> ${escapeHtml(u.contact_button_text || t("tournament_join_btn"))}
                </a>` : "";
            const winnerHtml = (isFinished && (u.winner_name || u.winner_team)) ? `
                <div class="tournament-promo-text">🏆 ${escapeHtml(t("tournament_winner_label"))}: ${escapeHtml(u.winner_name || u.winner_team)}${u.winner_team && u.winner_name ? " (" + escapeHtml(u.winner_team) + ")" : ""}</div>
            ` : "";
            const badgeCls = isFinished ? "tournament-promo-badge is-finished" : "tournament-promo-badge is-upcoming";
            const badgeText = isFinished ? t("tournament_status_finished") : t("tournament_nextup_badge");
            return `
                <div class="tournament-promo" data-nextup-idx="${i}" style="cursor:pointer;" onclick="if(event.target.closest('.tournament-join-btn'))return; const t=this.querySelector('.tournament-promo-text'); if(t) t.classList.toggle('expanded');">
                    <div class="tournament-promo-imgwrap">
                        <img id="${idPrefix}${i}-img" src="" alt="" style="display:none;">
                        <div class="tournament-promo-imgfade"></div>
                        <span class="${badgeCls}">${escapeHtml(badgeText)}</span>
                    </div>
                    <div class="tournament-promo-body">
                        <div class="tournament-promo-title">${escapeHtml(u.title || "")}</div>
                        <div class="tournament-promo-text">${formatBannerText(u.banner_text || "")}</div>
                        ${u.event_date ? `<div class="tournament-promo-date">🗓 ${escapeHtml(u.event_date)}</div>` : ""}
                        ${winnerHtml}
                        ${joinHtml}
                    </div>
                </div>
            `;
        }).join("");

        list.forEach((u, i) => {
            const img = document.getElementById(idPrefix + i + "-img");
            const gallery = [u.banner_image, ...(u.banner_images || [])].filter(Boolean);
            const before = homeCarouselTimers.length;
            runSlideshow(img, gallery, homeCarouselTimers);
            if (homeCarouselTimers.length > before) {
                const rawId = homeCarouselTimers[homeCarouselTimers.length - 1];
                homeCarouselTimers[homeCarouselTimers.length - 1] = { id: rawId, tag: timerTag };
            }
        });
    }

    let lastHomeCarouselKey = null;
    const PERSONAL_SLIDE_DWELL_MS = 18000;

    function renderHomeCarousel(info, nextUpList, holidays, personal) {
        const wrap = document.getElementById("home-tournament-carousel-wrap");
        const track = document.getElementById("home-tournament-carousel");
        const slides = [];
        if (personal) slides.push(Object.assign({}, personal, { isPersonal: true }));
        (holidays || []).forEach((h) => slides.push(Object.assign({}, h, { isHoliday: true })));
        if (info && info.active) slides.push(Object.assign({}, info, { isUpcoming: info.status === "upcoming" }));
        (nextUpList || []).forEach((u) => slides.push(Object.assign({}, u, { isUpcoming: true })));

        const carouselKey = slides.map((s) => `${s.id}:${s.isPersonal ? "p" : (s.isHoliday ? "h" : "")}`).join(",");
        if (carouselKey === lastHomeCarouselKey && wrap.style.display !== "none") {
            return;
        }
        lastHomeCarouselKey = carouselKey;

        if (!slides.length) {
            wrap.style.display = "none";
            return;
        }

        homeCarouselTimers.forEach((tm) => clearInterval(typeof tm === "object" ? tm.id : tm));
        homeCarouselTimers = [];
        if (homeCarouselAutoTimer) clearInterval(homeCarouselAutoTimer);

        track.innerHTML = slides.map((s, i) => {
            const badgeCls = s.isPersonal ? "tournament-promo-badge is-personal" : (s.isHoliday ? "tournament-promo-badge is-personal" : (s.isUpcoming ? "tournament-promo-badge is-upcoming" : "tournament-promo-badge"));
            const badgeText = s.isPersonal ? "🎁 Sizga tabrik" : (s.isHoliday ? "🎉 Bayram" : (s.isUpcoming ? t("tournament_nextup_badge") : t("tournament_status_live")));
            const joinHtml = s.contact_username ? `
                <a href="https://t.me/${escapeHtml(s.contact_username.replace(/^@/, ""))}" target="_blank" rel="noopener" class="tournament-join-btn tournament-join-btn-inline" onclick="event.stopPropagation();">
                    ${s.contact_user_id ? `<span class="tournament-join-avatar"><img src="${API_BASE}/webapp/avatar_chat/${s.contact_user_id}" alt="" onerror="this.parentElement.style.display='none';"></span>` : ""}
                    <i class="fa-brands fa-telegram"></i> ${escapeHtml(s.contact_button_text || t("tournament_join_btn"))}
                </a>` : "";
            return `
                <div class="tournament-promo ${(s.isHoliday || s.isPersonal) ? "is-holiday" : ""}" data-slide-idx="${i}">
                    <div class="tournament-promo-imgwrap">
                        <img id="home-car-${i}-img" src="" alt="" style="display:none;">
                        <div class="tournament-promo-imgfade"></div>
                        <span class="${badgeCls}">${escapeHtml(badgeText)}</span>
                        <i class="fa-solid fa-chevron-right tournament-promo-arrow"></i>
                    </div>
                    <div class="tournament-promo-body">
                        <div class="tournament-promo-title">${escapeHtml(s.title || "")}</div>
                        <div class="tournament-promo-text">${formatBannerText(s.banner_text || "")}</div>
                        ${s.event_date ? `<div class="tournament-promo-date">🗓 ${escapeHtml(s.event_date)}</div>` : ""}
                        ${joinHtml}
                    </div>
                </div>
            `;
        }).join("");

        const IMAGE_DWELL_MS = 8000;
        const slideDurations = slides.map((s) => {
            if (s.isPersonal) return PERSONAL_SLIDE_DWELL_MS;
            const gallery = [s.banner_image, ...(s.banner_images || [])].filter(Boolean);
            const base = Math.max(1, gallery.length) * IMAGE_DWELL_MS;
            return s.isHoliday ? Math.max(base, 8000) : base;
        });

        slides.forEach((s, i) => {
            const img = document.getElementById("home-car-" + i + "-img");
            const gallery = [s.banner_image, ...(s.banner_images || [])].filter(Boolean);
            runSlideshow(img, gallery, homeCarouselTimers);
        });

        track.querySelectorAll("[data-slide-idx]").forEach((el) => {
            el.addEventListener("click", (e) => {
                if (e.target.closest(".tournament-join-btn")) return;
                const textEl = el.querySelector(".tournament-promo-text");
                if (textEl) textEl.classList.toggle("expanded");
                syncTrackHeight(parseInt(el.dataset.slideIdx, 10));
            });
        });

        const syncTrackHeight = (idx) => {
            const el = track.querySelector(`[data-slide-idx="${idx}"]`);
            if (el && el.scrollHeight > 0) track.style.height = el.scrollHeight + "px";
        };
        requestAnimationFrame(() => {
            let maxHeight = 0;
            track.querySelectorAll("[data-slide-idx]").forEach((el) => {
                if (el.scrollHeight > maxHeight) maxHeight = el.scrollHeight;
            });
            if (maxHeight > 0) track.style.height = maxHeight + "px";
        });

        if (slides.length > 1) {
            let activeIdx = 0;
            let userScrolled = false;
            let userScrollTimeout = null;
            track.addEventListener("scroll", () => {
                userScrolled = true;
                clearTimeout(userScrollTimeout);
                userScrollTimeout = setTimeout(() => { userScrolled = false; }, 4000);
                activeIdx = Math.round(track.scrollLeft / (track.clientWidth || 1));
            });

            const scheduleNext = () => {
                homeCarouselAutoTimer = setTimeout(() => {
                    if (!userScrolled) {
                        activeIdx = (activeIdx + 1) % slides.length;
                        const left = track.clientWidth * activeIdx;
                        smoothScrollTo(track, left, 900);
                    }
                    scheduleNext();
                }, slideDurations[activeIdx]);
            };
            scheduleNext();
        }

        wrap.style.display = "";
    }

    async function loadTournament() {
        try {
            const res = await api(API_BASE + "/webapp/api/tournament");
            const hasHistory = (res.history || []).length > 0;

            let homeHolidays = [];
            try {
                const hRes = await api(API_BASE + "/webapp/api/holiday");
                homeHolidays = [...(hRes.active || []), ...(hRes.upcoming || [])];
            } catch (e) { /* bayram yuklanmasa ham reklama ko'rsatilaveradi */ }

            const personalHero = document.getElementById("tournament-personal-hero");
            if (res.personal) {
                const p = res.personal;
                document.getElementById("tournament-personal-title").textContent = p.title || "";
                document.getElementById("tournament-personal-text").innerHTML = formatBannerText(p.banner_text || "");
                const pImg = document.getElementById("tournament-personal-img");
                if (p.banner_image) { pImg.src = p.banner_image; pImg.style.display = ""; } else { pImg.style.display = "none"; }
                const pJoin = document.getElementById("tournament-personal-join-btn");
                if (p.contact_username) {
                    pJoin.href = "https://t.me/" + p.contact_username.replace(/^@/, "");
                    pJoin.querySelector("span").textContent = p.contact_button_text || "Qatnashish uchun yozing";
                    pJoin.style.display = "flex";
                    pJoin.onclick = () => { safe(() => api(API_BASE + "/webapp/api/tournament_track_click", { tournament_id: p.id }), "trackClick"); };
                } else {
                    pJoin.style.display = "none";
                }
                personalHero.style.display = "";
            } else {
                personalHero.style.display = "none";
            }

            renderHomeCarousel(res.info, res.next_up, homeHolidays, res.personal);
            document.getElementById("tournament-title").textContent = res.info.title || t("webapp_nav_tournament");

            const joinBtn = document.getElementById("tournament-join-btn");
            const joinAvatar = document.getElementById("tournament-join-avatar");
            if (res.info.active && res.info.contact_username) {
                joinBtn.href = "https://t.me/" + res.info.contact_username.replace(/^@/, "");
                if (res.info.contact_user_id) {
                    joinAvatar.innerHTML = `<img src="${API_BASE}/webapp/avatar_chat/${res.info.contact_user_id}" alt="" onerror="this.parentElement.style.display='none';">`;
                    joinAvatar.style.display = "";
                } else {
                    joinAvatar.style.display = "none";
                }
                joinBtn.style.display = "flex";
                joinBtn.onclick = () => { safe(() => api(API_BASE + "/webapp/api/tournament_track_click", { tournament_id: res.info.id }), "trackClick"); };
            } else {
                joinBtn.style.display = "none";
            }

            const upcoming = (res.next_up || []).map((u) => Object.assign({}, u, { cardStatus: "upcoming" }));
            const finished = (res.history || []).map((h) => Object.assign({}, h, { cardStatus: "finished" }));
            renderNextUpList(upcoming, "tournament-nextup-list", "nextup-car-", "_nextup");
            renderNextUpList(finished, "tournament-finished-list", "finished-car-", "_finished");
            document.getElementById("tournament-upcoming-title").style.display = upcoming.length ? "" : "none";
            document.getElementById("tournament-finished-title").style.display = finished.length ? "" : "none";

            const hero = document.getElementById("tournament-hero");
            const heroDate = document.getElementById("tournament-hero-date");
            if (res.info.event_date) {
                heroDate.textContent = "🗓 " + res.info.event_date;
                heroDate.style.display = "";
            } else {
                heroDate.style.display = "none";
            }
            if (heroCarouselTimer) clearInterval(heroCarouselTimer);
            const heroGallery = [res.info.banner_image, ...(res.info.banner_images || [])].filter(Boolean);
            if (heroGallery.length > 0) {
                setMediaBanner("tournament-hero", heroGallery[0]);
                document.getElementById("tournament-hero-title").textContent = res.info.title || "";
                document.getElementById("tournament-hero-text").innerHTML = formatBannerText(res.info.banner_text || "");
                hero.style.display = "";
                document.getElementById("tournament-banner").textContent = "";

                if (heroGallery.length > 1) {
                    const heroImg = document.getElementById("tournament-hero-img");
                    const heroTimers = [];
                    runSlideshow(heroImg, heroGallery, heroTimers);
                    heroCarouselTimer = heroTimers[0] || null;
                }
            } else {
                hero.style.display = "none";
                document.getElementById("tournament-banner").innerHTML = formatBannerText(res.info.banner_text || "");
            }

        } catch (e) {
            console.warn("[Empire WebApp] loadTournament failed:", e);
        }
    }

    async function loadAdminStats() {
        const box = document.getElementById("admin-stats-container");
        box.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/admin_stats");
            const s = res.stats;
            const cards = [
                [t("admin_stat_users"), fmt(s.total_users), "fa-users", "blue"],
                [t("admin_stat_new_today"), fmt(s.new_users_today), "fa-user-plus", "green"],
                [t("admin_stat_new_week"), fmt(s.new_users_week), "fa-calendar-week", "green"],
                [t("admin_stat_new_month"), fmt(s.new_users_month), "fa-calendar-days", "green"],
                [t("admin_stat_groups"), fmt(s.total_groups), "fa-people-group", "blue"],
                [t("admin_stat_active_games"), fmt(s.active_games), "fa-gamepad", "green"],
                [t("admin_stat_total_games"), fmt(s.total_games), "fa-trophy", "gold"],
                [t("admin_stat_vip"), fmt(s.vip_count), "fa-crown", "purple"],
                [t("admin_stat_total_dollar"), fmt(s.total_dollar), "fa-sack-dollar", "gold"],
                [t("admin_stat_total_diamond"), fmt(s.total_diamond), "fa-gem", "blue"],
            ];
            box.innerHTML = cards.map(([label, val, icon, color]) => `
                <div class="stat-card">
                    <div class="stat-icon ${color}"><i class="fa-solid ${icon}"></i></div>
                    <div><span class="stat-val">${val}</span><span class="stat-label">${escapeHtml(label)}</span></div>
                </div>
            `).join("");
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    const ADMIN_ITEM_DEFS = [
        { field: "himoya", icon: "🛡", label: "Himoya" },
        { field: "hujjat", icon: "📁", label: "Hujjat" },
        { field: "qotildan_himoya", icon: "🔪", label: "Qotildan himoya" },
        { field: "osishdan_himoya", icon: "⚖️", label: "Osishdan himoya" },
        { field: "miltiq", icon: "😀", label: "Miltiq" },
        { field: "doridan_himoya", icon: "➕", label: "Doridan himoya" },
        { field: "maska", icon: "🎭", label: "Maska" },
        { field: "slip_himoya", icon: "🪤", label: "Sirpanishdan himoya" },
        { field: "geroy_himoya", icon: "🔰", label: "Geroydan himoya" },
    ];

    function renderAdminItemsGrid(u) {
        const box = document.getElementById("admin-items-grid");
        if (!box) return;
        box.innerHTML = ADMIN_ITEM_DEFS.map((def) => `
            <div class="admin-item-row">
                <span class="admin-item-label">${def.icon} ${escapeHtml(def.label)}</span>
                <span class="admin-item-val">${fmt(u[def.field] || 0)}</span>
                <input type="text" class="admin-item-input" data-field="${def.field}" placeholder="0" inputmode="numeric">
                <button class="admin-item-btn add" data-field="${def.field}" data-sign="1">➕</button>
                <button class="admin-item-btn sub" data-field="${def.field}" data-sign="-1">➖</button>
            </div>
        `).join("");
        box.querySelectorAll(".admin-item-btn").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const field = btn.dataset.field;
                const sign = parseInt(btn.dataset.sign, 10);
                const input = box.querySelector(`.admin-item-input[data-field="${field}"]`);
                const amt = parseInt(input.value, 10);
                if (!amt) return;
                input.value = "";
                const userId = document.getElementById("admin-user-result").dataset.userId;
                if (!userId) return;
                try {
                    await api(API_BASE + "/webapp/api/admin_adjust_balance", { user_id: userId, item_deltas: { [field]: sign * amt } });
                    toast(t("admin_action_success"), "success");
                    const res = await api(API_BASE + "/webapp/api/admin_search_user", { query: userId });
                    renderAdminUserCard(res.user);
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                }
            });
        });
    }

    function renderAdminUserCard(u) {
        const card = document.getElementById("admin-user-card");
        const name = u.full_name || t("label_gamer");
        const initial = name.trim().charAt(0).toUpperCase() || "?";
        card.innerHTML = `
            <div class="auc-head">
                <div class="auc-avatar"><img src="${API_BASE}/webapp/avatar/${u.user_id}" alt="" onerror="var p=this.parentElement; this.remove(); if(p) p.textContent='${escapeHtml(initial)}';"></div>
                <div>
                    <div class="auc-name">${escapeHtml(name)}</div>
                    <div class="auc-meta">${u.username ? "@" + escapeHtml(u.username) + " · " : ""}ID: ${u.user_id}</div>
                </div>
            </div>
            <div class="auc-chips">
                <span class="auc-chip">💵 ${fmt(u.dollar)}</span>
                <span class="auc-chip">💎 ${fmt(u.diamond)}</span>
                <span class="auc-chip">🏆 ${fmt(u.wins)}</span>
                <span class="auc-chip">🎮 ${fmt(u.games_count)}</span>
                <span class="auc-chip ${u.vip_active ? "vip-on" : "vip-off"}">👑 ${u.vip_active ? t("admin_vip_active_label") : t("admin_vip_none_label")}</span>
                ${u.geroy_level != null ? `<span class="auc-chip">🥷 ${fmt(u.geroy_level)}-daraja</span>` : ""}
                ${ADMIN_ITEM_DEFS.map((def) => `<span class="auc-chip">${def.icon} ${fmt(u[def.field] || 0)}</span>`).join("")}
                <span class="auc-chip auc-chip-block ${u.is_blocked ? "is-blocked" : ""}" id="auc-block-chip" onclick="window.adminToggleBlock(${u.user_id}, ${u.is_blocked ? "true" : "false"})">${u.is_blocked ? "🔓 Blokdan chiqarish" : "🚫 Bloklash"}</span>
            </div>
        `;
        document.getElementById("admin-user-result").style.display = "";
        document.getElementById("admin-user-result").dataset.userId = u.user_id;
        renderAdminItemsGrid(u);
        document.getElementById("admin-geroy-level-val").textContent = u.geroy_level != null ? u.geroy_level : "—";
    }

    window.adminToggleBlock = async function(userId, currentlyBlocked) {
        try {
            await api(currentlyBlocked ? API_BASE + "/webapp/api/admin_unblock_user" : API_BASE + "/webapp/api/admin_block_user", { user_id: userId });
            toast(t("admin_action_success"), "success");
            const res = await api(API_BASE + "/webapp/api/admin_search_user", { query: String(userId) });
            renderAdminUserCard(res.user);
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        }
    };

    let adminGroupsCache = [];
    let adminTournamentLoaded = false;
    let adminSelectedTournamentId = null;
    let adminTournamentsCache = [];
    let adminExtraImagesCache = [];
    let adminSelectedBirthdayAdId = null;

    function renderAdminExtraImages() {
        const box = document.getElementById("adm-t-extra-preview-list");
        if (!adminExtraImagesCache.length) { box.innerHTML = ""; return; }
        box.innerHTML = adminExtraImagesCache.map((url, i) => `
            <div class="admin-tlist-row">
                <span class="atl-info"><img src="${url}" alt="" style="width:36px; height:36px; border-radius:6px; object-fit:cover; vertical-align:middle; margin-right:8px;">${i + 1}-rasm</span>
                <button data-remove-extra="${i}">${t("admin_action_delete")}</button>
            </div>
        `).join("");
        box.querySelectorAll("[data-remove-extra]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.dataset.removeExtra, 10);
                adminExtraImagesCache.splice(idx, 1);
                document.getElementById("adm-t-banner-images").value = JSON.stringify(adminExtraImagesCache);
                renderAdminExtraImages();
            });
        });
    }

    function autoGrowBannerTextarea() {
        autoGrowNamedTextarea("adm-t-banner");
    }

    function autoGrowNamedTextarea(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.height = "auto";
        el.style.height = Math.max(el.scrollHeight, 140) + "px";
    }

    function resetTournamentForm() {
        adminSelectedTournamentId = null;
        document.getElementById("adm-t-form-title").textContent = t("tournament_new_btn");
        document.getElementById("adm-t-title").value = "";
        document.getElementById("adm-t-banner").value = "";
        autoGrowBannerTextarea();
        document.getElementById("adm-t-event-date").value = "";
        document.getElementById("adm-t-contact-username").value = "";
        document.getElementById("adm-t-contact-btn-text").value = "";
        document.getElementById("adm-t-contact-preview").style.display = "none";
        document.getElementById("adm-t-banner-image").value = "";
        document.getElementById("adm-t-banner-preview").style.display = "none";
        document.getElementById("adm-t-banner-images").value = "";
        adminExtraImagesCache = [];
        renderAdminExtraImages();
        document.getElementById("adm-t-lang").value = "";
        document.getElementById("adm-t-status").value = "upcoming";
        document.getElementById("adm-t-winner-row").style.display = "none";
        document.getElementById("adm-t-winner-name").value = "";
        document.getElementById("adm-t-winner-team").value = "";
        document.getElementById("adm-t-winner-uid").value = "";
    }

    function renderTargetUserSelected(boxId, u) {
        const box = document.getElementById(boxId);
        if (!u) { box.style.display = "none"; return; }
        const name = u.full_name || t("label_gamer");
        const initial = name.trim().charAt(0).toUpperCase() || "?";
        const openLink = u.username
            ? `<a href="https://t.me/${escapeHtml(u.username)}" target="_blank" rel="noopener" class="auc-open-link" onclick="event.stopPropagation();"><i class="fa-brands fa-telegram"></i> Telegramga o'tish</a>`
            : `<span class="auc-open-link is-disabled">Username yo'q — Telegramdan to'g'ridan-to'g'ri ochib bo'lmaydi</span>`;
        box.innerHTML = `
            <div class="auc-head">
                <div class="auc-avatar"><img src="${API_BASE}/webapp/avatar/${u.user_id}" alt="" onerror="this.remove();"></div>
                <div>
                    <div class="auc-name">${escapeHtml(name)}</div>
                    <div class="auc-meta">${u.username ? "@" + escapeHtml(u.username) + " · " : ""}ID: ${u.user_id}</div>
                    ${openLink}
                </div>
            </div>
        `;
        box.style.display = "";
    }

    function setupTargetUserSearch(searchInputId, suggestBoxId, hiddenInputId, selectedBoxId, onSelect) {
        const input = document.getElementById(searchInputId);
        const suggestBox = document.getElementById(suggestBoxId);
        if (!input || !suggestBox) return;
        document.body.appendChild(suggestBox);
        let debounceTimer = null;
        const positionSuggest = () => {
            const rect = input.getBoundingClientRect();
            suggestBox.style.left = rect.left + "px";
            suggestBox.style.top = (rect.bottom + 4) + "px";
            suggestBox.style.width = rect.width + "px";
        };
        const doSearch = async () => {
            const query = input.value.trim();
            if (!query) { suggestBox.classList.remove("open"); return; }
            try {
                const res = await api(API_BASE + "/webapp/api/admin_support_search_users", { query });
                const users = res.users || [];
                if (!users.length) { suggestBox.innerHTML = `<div class="admin-support-search-empty">Hech kim topilmadi</div>`; positionSuggest(); suggestBox.classList.add("open"); return; }
                suggestBox.innerHTML = users.map((u) => `
                    <div class="admin-role-suggest-item" data-uid="${u.user_id}" data-uname="${escapeHtml(u.full_name || "")}" data-uusername="${escapeHtml(u.username || "")}">
                        ${escapeHtml(u.full_name || t("label_gamer"))} ${u.username ? "(@" + escapeHtml(u.username) + ")" : ""} · ID: ${u.user_id}
                    </div>
                `).join("");
                positionSuggest();
                suggestBox.classList.add("open");
                suggestBox.querySelectorAll("[data-uid]").forEach((el) => {
                    el.addEventListener("click", () => {
                        const uid = parseInt(el.dataset.uid, 10);
                        document.getElementById(hiddenInputId).value = uid;
                        input.value = "";
                        suggestBox.classList.remove("open");
                        if (selectedBoxId) renderTargetUserSelected(selectedBoxId, { user_id: uid, full_name: el.dataset.uname, username: el.dataset.uusername });
                        if (onSelect) onSelect(uid);
                    });
                });
            } catch (e) {
                suggestBox.classList.remove("open");
            }
        };
        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(doSearch, 400);
        });
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); doSearch(); }
        });
        document.addEventListener("click", (e) => {
            if (!suggestBox.contains(e.target) && e.target !== input) suggestBox.classList.remove("open");
        });
    }

    async function refreshTournamentContactPreview(query, boxId) {
        const box = document.getElementById(boxId || "adm-t-contact-preview");
        const q = (query || "").trim().replace(/^@/, "");
        if (!q) { box.style.display = "none"; return; }
        try {
            const res = await api(API_BASE + "/webapp/api/admin_resolve_contact", { username: q });
            if (!res.found) {
                box.innerHTML = `<span class="inv-empty">❌ @${escapeHtml(q)} topilmadi — Telegram bu username haqida ma'lumot bermayapti (guruh/kanal bo'lsa nomi noto'g'ri, shaxs bo'lsa botni hali ishga tushirmagan)</span>`;
                box.style.display = "";
                return;
            }
            const name = res.title || q;
            const initial = name.trim().charAt(0).toUpperCase() || "?";
            box.innerHTML = `
                <div class="auc-head">
                    <div class="auc-avatar"><img src="${API_BASE}/webapp/avatar_chat/${res.id}" alt="" onerror="var p=this.parentElement; this.remove(); if(p) p.textContent='${escapeHtml(initial)}';"></div>
                    <div>
                        <div class="auc-name">${escapeHtml(name)}</div>
                        <div class="auc-meta">@${escapeHtml(q)} · ID: ${res.id}</div>
                    </div>
                </div>
            `;
            box.style.display = "";
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">🔗 https://t.me/${escapeHtml(q)} (${t("admin_contact_group_hint")})</span>`;
            box.style.display = "";
        }
    }

    let contactPreviewTimer = null;
    function setupTournamentContactPreview() {
        document.getElementById("adm-t-contact-username").addEventListener("input", (e) => {
            clearTimeout(contactPreviewTimer);
            contactPreviewTimer = setTimeout(() => refreshTournamentContactPreview(e.target.value, "adm-t-contact-preview"), 400);
        });
        const trInput = document.getElementById("adm-tr-contact-username");
        if (trInput) {
            let trTimer = null;
            trInput.addEventListener("input", (e) => {
                clearTimeout(trTimer);
                trTimer = setTimeout(() => refreshTournamentContactPreview(e.target.value, "adm-tr-contact-preview"), 400);
            });
        }
    }

    function renderAdminTournamentsList() {
        const box = document.getElementById("adm-t-list");
        const items = adminTournamentsCache.filter((tr) => tr.kind !== "tournament" && !tr.target_user_id);
        if (!items.length) {
            box.innerHTML = `<span class="inv-empty">${t("tournament_empty")}</span>`;
            return;
        }
        box.innerHTML = items.map((tr) => `
            <div class="admin-tlist-row">
                <span class="atl-info">${escapeHtml(tr.title)}${tr.target_user_id ? ` <span class="atl-meta">🎯 ${escapeHtml(tr.target_full_name || String(tr.target_user_id))}</span>` : ""}<span class="atl-meta">${t("tournament_status_" + (tr.status === "active" ? "live" : tr.status))} · 👆 ${fmt(tr.contact_clicks || 0)}</span></span>
                <span style="display:flex; gap:6px;">
                    <button data-edit-tr="${tr.id}" style="background:rgba(255,209,102,.14); color:var(--dollar-gold);">${t("tournament_edit_btn")}</button>
                    <button data-del-tr="${tr.id}">${t("admin_action_delete")}</button>
                </span>
            </div>
        `).join("");

        box.querySelectorAll("[data-edit-tr]").forEach((btn) => {
            btn.addEventListener("click", () => selectTournamentForEdit(parseInt(btn.dataset.editTr, 10)));
        });
        box.querySelectorAll("[data-del-tr]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                try {
                    await api(API_BASE + "/webapp/api/admin_tournament_delete", { entity: "tournament", id: btn.dataset.delTr });
                    toast(t("admin_action_success"), "success");
                    if (adminSelectedTournamentId === parseInt(btn.dataset.delTr, 10)) resetTournamentForm();
                    loadAdminTournament();
                    tournamentLoaded = true;
                    safe(() => loadTournament(), "loadTournament");
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                }
            });
        });
    }

    async function selectTournamentForEdit(id) {
        const tr = adminTournamentsCache.find((x) => x.id === id);
        if (!tr) return;
        adminSelectedTournamentId = id;
        document.getElementById("adm-t-form-title").textContent = tr.title;
        document.getElementById("adm-t-title").value = tr.title || "";
        document.getElementById("adm-t-banner").value = tr.banner_text || "";
        autoGrowBannerTextarea();
        document.getElementById("adm-t-event-date").value = tr.event_date || "";
        document.getElementById("adm-t-contact-username").value = tr.contact_username || "";
        document.getElementById("adm-t-contact-btn-text").value = tr.contact_button_text || "";
        refreshTournamentContactPreview(tr.contact_username);
        document.getElementById("adm-t-banner-image").value = tr.banner_image || "";
        showBannerPreview(tr.banner_image);
        adminExtraImagesCache = Array.isArray(tr.banner_images) ? tr.banner_images.slice() : [];
        document.getElementById("adm-t-banner-images").value = JSON.stringify(adminExtraImagesCache);
        renderAdminExtraImages();
        document.getElementById("adm-t-lang").value = tr.lang || "";
        document.getElementById("adm-t-status").value = tr.status || "upcoming";
        document.getElementById("adm-t-winner-row").style.display = tr.status === "finished" ? "" : "none";
        document.getElementById("adm-t-winner-name").value = tr.winner_name || "";
        document.getElementById("adm-t-winner-team").value = tr.winner_team || "";
        document.getElementById("adm-t-winner-uid").value = tr.winner_user_id || "";
    }

    async function loadAdminTournament() {
        try {
            const res = await api(API_BASE + "/webapp/api/admin_tournaments_list");
            adminTournamentsCache = res.tournaments || [];
            renderAdminTournamentsList();
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        }
    }

    async function loadAdminTournamentManagers() {
        const box = document.getElementById("adm-tm-managers-list");
        if (!box) return;
        try {
            const res = await api(API_BASE + "/webapp/api/admin_tournament_managers_list");
            const managers = res.managers || [];
            if (!managers.length) { box.innerHTML = `<span class="inv-empty">Hozircha menejer yo'q</span>`; return; }
            box.innerHTML = managers.map((m) => `
                <div class="admin-tlist-row">
                    <span class="atl-info">${escapeHtml(m.full_name || "")}${m.username ? " @" + escapeHtml(m.username) : ""}<span class="atl-meta">ID: ${m.user_id}</span></span>
                    <button data-revoke-tm="${m.user_id}">❌ Bekor qilish</button>
                </div>
            `).join("");
            box.querySelectorAll("[data-revoke-tm]").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    try {
                        await api(API_BASE + "/webapp/api/admin_revoke_tournament_manager", { user_id: btn.dataset.revokeTm });
                        toast(t("admin_action_success"), "success");
                        loadAdminTournamentManagers();
                    } catch (e) {
                        toast(t("toast_generic_error"), "error");
                    }
                });
            });
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    /* ---------------- Turnir (kind="tournament") admin CRUD ---------------- */
    let adminSelectedTurnirId = null;
    let adminTurnirExtraImagesCache = [];

    function renderAdminTurnirExtraImages() {
        const box = document.getElementById("adm-tr-extra-preview-list");
        if (!adminTurnirExtraImagesCache.length) { box.innerHTML = ""; return; }
        box.innerHTML = adminTurnirExtraImagesCache.map((url, i) => `
            <div class="admin-tlist-row">
                <span class="atl-info"><img src="${url}" alt="" style="width:36px; height:36px; border-radius:6px; object-fit:cover; vertical-align:middle; margin-right:8px;">${i + 1}-rasm</span>
                <button data-remove-tr-extra="${i}">${t("admin_action_delete")}</button>
            </div>
        `).join("");
        box.querySelectorAll("[data-remove-tr-extra]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const idx = parseInt(btn.dataset.removeTrExtra, 10);
                adminTurnirExtraImagesCache.splice(idx, 1);
                document.getElementById("adm-tr-banner-images").value = JSON.stringify(adminTurnirExtraImagesCache);
                renderAdminTurnirExtraImages();
            });
        });
    }

    function resetTurnirForm() {
        adminSelectedTurnirId = null;
        document.getElementById("adm-tr-form-title").textContent = "➕ Yangi turnir";
        document.getElementById("adm-tr-title").value = "";
        document.getElementById("adm-tr-banner").value = "";
        autoGrowNamedTextarea("adm-tr-banner");
        document.getElementById("adm-tr-event-date").value = "";
        document.getElementById("adm-tr-contact-username").value = "";
        document.getElementById("adm-tr-contact-btn-text").value = "";
        document.getElementById("adm-tr-contact-preview").style.display = "none";
        document.getElementById("adm-tr-banner-image").value = "";
        document.getElementById("adm-tr-banner-preview").style.display = "none";
        document.getElementById("adm-tr-banner-images").value = "";
        adminTurnirExtraImagesCache = [];
        renderAdminTurnirExtraImages();
        document.getElementById("adm-tr-lang").value = "";
        document.getElementById("adm-tr-status").value = "upcoming";
        document.getElementById("adm-tr-winner-row").style.display = "none";
        document.getElementById("adm-tr-winner-name").value = "";
        document.getElementById("adm-tr-winner-team").value = "";
        document.getElementById("adm-tr-winner-uid").value = "";
    }

    function renderAdminTurnirList() {
        const box = document.getElementById("adm-tr-list");
        const items = adminTournamentsCache.filter((tr) => tr.kind === "tournament");
        if (!items.length) { box.innerHTML = `<span class="inv-empty">${t("tournament_empty")}</span>`; return; }
        box.innerHTML = items.map((tr) => `
            <div class="admin-tlist-row">
                <span class="atl-info">${escapeHtml(tr.title)}<span class="atl-meta">${t("tournament_status_" + (tr.status === "active" ? "live" : tr.status))}</span></span>
                <span style="display:flex; gap:6px;">
                    <button data-edit-turnir="${tr.id}" style="background:rgba(52,211,153,.14); color:#34d399;">${t("tournament_edit_btn")}</button>
                    <button data-del-turnir="${tr.id}">${t("admin_action_delete")}</button>
                </span>
            </div>
        `).join("");
        box.querySelectorAll("[data-edit-turnir]").forEach((btn) => {
            btn.addEventListener("click", () => selectTurnirForEdit(parseInt(btn.dataset.editTurnir, 10)));
        });
        box.querySelectorAll("[data-del-turnir]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                try {
                    await api(API_BASE + "/webapp/api/admin_tournament_delete", { entity: "tournament", id: btn.dataset.delTurnir });
                    toast(t("admin_action_success"), "success");
                    if (adminSelectedTurnirId === parseInt(btn.dataset.delTurnir, 10)) resetTurnirForm();
                    await loadAdminTournament();
                    renderAdminTurnirList();
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                }
            });
        });
    }

    function selectTurnirForEdit(id) {
        const tr = adminTournamentsCache.find((x) => x.id === id);
        if (!tr) return;
        adminSelectedTurnirId = id;
        document.getElementById("adm-tr-form-title").textContent = tr.title;
        document.getElementById("adm-tr-title").value = tr.title || "";
        document.getElementById("adm-tr-banner").value = tr.banner_text || "";
        autoGrowNamedTextarea("adm-tr-banner");
        document.getElementById("adm-tr-event-date").value = tr.event_date || "";
        document.getElementById("adm-tr-contact-username").value = tr.contact_username || "";
        document.getElementById("adm-tr-contact-btn-text").value = tr.contact_button_text || "";
        refreshTournamentContactPreview(tr.contact_username, "adm-tr-contact-preview");
        document.getElementById("adm-tr-banner-image").value = tr.banner_image || "";
        if (tr.banner_image) { document.getElementById("adm-tr-banner-preview").src = tr.banner_image; document.getElementById("adm-tr-banner-preview").style.display = ""; }
        else document.getElementById("adm-tr-banner-preview").style.display = "none";
        adminTurnirExtraImagesCache = Array.isArray(tr.banner_images) ? tr.banner_images.slice() : [];
        document.getElementById("adm-tr-banner-images").value = JSON.stringify(adminTurnirExtraImagesCache);
        renderAdminTurnirExtraImages();
        document.getElementById("adm-tr-lang").value = tr.lang || "";
        document.getElementById("adm-tr-status").value = tr.status || "upcoming";
        document.getElementById("adm-tr-winner-row").style.display = tr.status === "finished" ? "" : "none";
        document.getElementById("adm-tr-winner-name").value = tr.winner_name || "";
        document.getElementById("adm-tr-winner-team").value = tr.winner_team || "";
        document.getElementById("adm-tr-winner-uid").value = tr.winner_user_id || "";
    }

    function setupTurnirAdmin() {
        document.getElementById("adm-tr-banner").addEventListener("input", () => autoGrowNamedTextarea("adm-tr-banner"));
        document.getElementById("adm-tr-new-btn").addEventListener("click", resetTurnirForm);
        document.getElementById("adm-tr-status").addEventListener("change", (e) => {
            document.getElementById("adm-tr-winner-row").style.display = e.target.value === "finished" ? "" : "none";
        });
        document.getElementById("adm-tr-preview-btn").addEventListener("click", () => {
            goTo("tournament");
        });
        document.getElementById("adm-tr-save-btn").addEventListener("click", async () => {
            const payload = {
                entity: "tournament",
                kind: "tournament",
                title: document.getElementById("adm-tr-title").value.trim(),
                banner_text: document.getElementById("adm-tr-banner").value.trim(),
                event_date: document.getElementById("adm-tr-event-date").value.trim(),
                contact_username: document.getElementById("adm-tr-contact-username").value.trim().replace(/^@/, ""),
                contact_button_text: document.getElementById("adm-tr-contact-btn-text").value.trim(),
                banner_image: document.getElementById("adm-tr-banner-image").value.trim(),
                banner_images: JSON.stringify(adminTurnirExtraImagesCache),
                lang: document.getElementById("adm-tr-lang").value,
                status: document.getElementById("adm-tr-status").value,
                winner_name: document.getElementById("adm-tr-winner-name").value.trim(),
                winner_team: document.getElementById("adm-tr-winner-team").value.trim(),
                winner_user_id: document.getElementById("adm-tr-winner-uid").value.trim(),
            };
            if (!payload.title) return;
            if (adminSelectedTurnirId) payload.id = adminSelectedTurnirId;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_tournament_save", payload);
                adminSelectedTurnirId = res.id;
                toast(t("admin_action_success"), "success");
                await loadAdminTournament();
                renderAdminTurnirList();
                tournamentLoaded = true;
                safe(() => loadTournament(), "loadTournament");
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });
        document.getElementById("adm-tr-upload-btn").addEventListener("click", () => {
            document.getElementById("adm-tr-upload-input").click();
        });
        document.getElementById("adm-tr-upload-input").addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const fd = new FormData();
                fd.append("initData", initData);
                fd.append("file", file);
                const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || "upload_failed");
                document.getElementById("adm-tr-banner-image").value = data.url;
                document.getElementById("adm-tr-banner-preview").src = data.url;
                document.getElementById("adm-tr-banner-preview").style.display = "";
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                e.target.value = "";
            }
        });
        document.getElementById("adm-tr-upload-extra-btn").addEventListener("click", () => {
            document.getElementById("adm-tr-upload-extra-input").click();
        });
        document.getElementById("adm-tr-upload-extra-input").addEventListener("change", async (e) => {
            const files = Array.from(e.target.files || []);
            if (!files.length) return;
            try {
                const urls = adminTurnirExtraImagesCache.slice();
                for (const file of files) {
                    const fd = new FormData();
                    fd.append("initData", initData);
                    fd.append("file", file);
                    const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                    const data = await res.json();
                    if (data.ok) urls.push(data.url);
                }
                adminTurnirExtraImagesCache = urls;
                document.getElementById("adm-tr-banner-images").value = JSON.stringify(urls);
                renderAdminTurnirExtraImages();
                toast(t("admin_action_success"), "success");
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                e.target.value = "";
            }
        });
    }

    /* ---------------- Holiday admin CRUD ---------------- */
    let adminHolidaysCache = [];
    let adminSelectedHolidayId = null;

    function resetHolidayForm() {
        adminSelectedHolidayId = null;
        document.getElementById("adm-h-form-title").textContent = "➕ Yangi bayram";
        document.getElementById("adm-h-title").value = "";
        document.getElementById("adm-h-banner").value = "";
        autoGrowNamedTextarea("adm-h-banner");
        document.getElementById("adm-h-event-date").value = "";
        document.getElementById("adm-h-banner-image").value = "";
        document.getElementById("adm-h-banner-preview").style.display = "none";
        document.getElementById("adm-h-status").value = "upcoming";
    }

    function renderAdminHolidaysList() {
        const box = document.getElementById("adm-h-list");
        if (!adminHolidaysCache.length) { box.innerHTML = `<span class="inv-empty">Hozircha bayram yo'q</span>`; return; }
        box.innerHTML = adminHolidaysCache.map((h) => `
            <div class="admin-tlist-row">
                <span class="atl-info">${escapeHtml(h.title)}<span class="atl-meta">${t("tournament_status_" + (h.status === "active" ? "live" : h.status))}</span></span>
                <span style="display:flex; gap:6px;">
                    <button data-edit-h="${h.id}" style="background:rgba(192,132,252,.14); color:#c084fc;">${t("tournament_edit_btn")}</button>
                    <button data-del-h="${h.id}">${t("admin_action_delete")}</button>
                </span>
            </div>
        `).join("");
        box.querySelectorAll("[data-edit-h]").forEach((btn) => {
            btn.addEventListener("click", () => selectHolidayForEdit(parseInt(btn.dataset.editH, 10)));
        });
        box.querySelectorAll("[data-del-h]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                try {
                    await api(API_BASE + "/webapp/api/admin_holiday_delete", { id: btn.dataset.delH });
                    toast(t("admin_action_success"), "success");
                    if (adminSelectedHolidayId === parseInt(btn.dataset.delH, 10)) resetHolidayForm();
                    loadAdminHolidays();
                    safe(() => loadHoliday(), "loadHoliday");
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                }
            });
        });
    }

    function selectHolidayForEdit(id) {
        const h = adminHolidaysCache.find((x) => x.id === id);
        if (!h) return;
        adminSelectedHolidayId = id;
        document.getElementById("adm-h-form-title").textContent = h.title;
        document.getElementById("adm-h-title").value = h.title || "";
        document.getElementById("adm-h-banner").value = h.banner_text || "";
        autoGrowNamedTextarea("adm-h-banner");
        document.getElementById("adm-h-event-date").value = h.event_date || "";
        document.getElementById("adm-h-banner-image").value = h.banner_image || "";
        if (h.banner_image) { document.getElementById("adm-h-banner-preview").src = h.banner_image; document.getElementById("adm-h-banner-preview").style.display = ""; }
        else document.getElementById("adm-h-banner-preview").style.display = "none";
        document.getElementById("adm-h-status").value = h.status || "upcoming";
    }

    async function loadAdminHolidays() {
        try {
            const res = await api(API_BASE + "/webapp/api/admin_holidays_list");
            adminHolidaysCache = res.holidays || [];
            renderAdminHolidaysList();
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        }
    }

    function setupHolidayAdmin() {
        document.getElementById("adm-h-banner").addEventListener("input", () => autoGrowNamedTextarea("adm-h-banner"));
        document.getElementById("adm-h-new-btn").addEventListener("click", resetHolidayForm);
        document.getElementById("adm-h-save-btn").addEventListener("click", async () => {
            const payload = {
                title: document.getElementById("adm-h-title").value.trim(),
                banner_text: document.getElementById("adm-h-banner").value.trim(),
                event_date: document.getElementById("adm-h-event-date").value.trim(),
                banner_image: document.getElementById("adm-h-banner-image").value.trim(),
                status: document.getElementById("adm-h-status").value,
            };
            if (!payload.title) return;
            if (adminSelectedHolidayId) payload.id = adminSelectedHolidayId;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_holiday_save", payload);
                adminSelectedHolidayId = res.id;
                toast(t("admin_action_success"), "success");
                await loadAdminHolidays();
                safe(() => loadHoliday(), "loadHoliday");
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });
        document.getElementById("adm-h-upload-btn").addEventListener("click", () => {
            document.getElementById("adm-h-upload-input").click();
        });
        document.getElementById("adm-h-upload-input").addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const fd = new FormData();
                fd.append("initData", initData);
                fd.append("file", file);
                const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || "upload_failed");
                document.getElementById("adm-h-banner-image").value = data.url;
                document.getElementById("adm-h-banner-preview").src = data.url;
                document.getElementById("adm-h-banner-preview").style.display = "";
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                e.target.value = "";
            }
        });
    }

    let holidayLoaded = false;
    async function loadHoliday() {
        try {
            const res = await api(API_BASE + "/webapp/api/holiday");
            const active = res.active || [];
            const upcoming = res.upcoming || [];
            document.getElementById("nav-holiday").style.display = (active.length || upcoming.length) ? "" : "none";
            const activeBox = document.getElementById("holiday-active-list");
            activeBox.innerHTML = active.map((h) => `
                <div class="tournament-promo is-holiday">
                    <div class="tournament-promo-imgwrap">
                        ${h.banner_image ? `<img src="${h.banner_image}" alt="">` : ""}
                        <div class="tournament-promo-imgfade"></div>
                        <span class="tournament-promo-badge is-upcoming">🎉 Faol</span>
                    </div>
                    <div class="tournament-promo-body">
                        <div class="tournament-promo-title">${escapeHtml(h.title)}</div>
                        ${h.event_date ? `<div class="tournament-promo-date">🗓 ${escapeHtml(h.event_date)}</div>` : ""}
                        <div class="tournament-promo-text">${formatBannerText(h.banner_text || "")}</div>
                    </div>
                </div>
            `).join("");
            const upcomingBox = document.getElementById("holiday-upcoming-list");
            upcomingBox.innerHTML = upcoming.map((h) => `
                <div class="tournament-promo is-holiday">
                    <div class="tournament-promo-imgwrap">
                        ${h.banner_image ? `<img src="${h.banner_image}" alt="">` : ""}
                        <div class="tournament-promo-imgfade"></div>
                        <span class="tournament-promo-badge is-upcoming">📅 Kelasi</span>
                    </div>
                    <div class="tournament-promo-body">
                        <div class="tournament-promo-title">${escapeHtml(h.title)}</div>
                        ${h.event_date ? `<div class="tournament-promo-date">🗓 ${escapeHtml(h.event_date)}</div>` : ""}
                    </div>
                </div>
            `).join("");
            document.getElementById("holiday-upcoming-title").style.display = upcoming.length ? "" : "none";
        } catch (e) {
            console.warn("[Empire WebApp] loadHoliday failed:", e);
        }
    }

    /* ---------------- Birthday admin ---------------- */
    async function loadAdminBirthdays() {
        const box = document.getElementById("adm-bd-today-list");
        if (!box) return;
        try {
            const res = await api(API_BASE + "/webapp/api/admin_todays_birthdays");
            const list = res.birthdays || [];
            if (!list.length) { box.innerHTML = `<span class="inv-empty">Bugun tug'ilgan kuni bo'lganlar yo'q</span>`; return; }
            box.innerHTML = list.map((b) => `
                <div class="admin-tlist-row">
                    <span class="atl-info">${escapeHtml(b.full_name || "")}${b.username ? " @" + escapeHtml(b.username) : ""}<span class="atl-meta">ID: ${b.user_id}${b.already_greeted ? " · ✅ Tabriklangan" : ""}</span></span>
                    <span style="display:flex; gap:6px; align-items:center;">
                        <input type="text" class="admin-item-input" data-bd-gift="${b.user_id}" placeholder="💎 sovg'a" inputmode="numeric" style="width:80px;">
                        <button data-greet-bd="${b.user_id}" ${b.already_greeted ? "disabled" : ""}>🎉 Tabriklash</button>
                    </span>
                </div>
            `).join("");
            box.querySelectorAll("[data-greet-bd]").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    const uid = btn.dataset.greetBd;
                    const giftInput = box.querySelector(`[data-bd-gift="${uid}"]`);
                    const gift = parseInt(giftInput.value, 10) || 0;
                    try {
                        await api(API_BASE + "/webapp/api/admin_greet_birthday", { user_id: uid, diamond_gift: gift });
                        toast(t("admin_action_success"), "success");
                        loadAdminBirthdays();
                    } catch (e) {
                        toast(t("toast_generic_error"), "error");
                    }
                });
            });
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    function resetBirthdayAdForm() {
        adminSelectedBirthdayAdId = null;
        document.getElementById("adm-bd-form-title").textContent = "➕ Yangi shaxsiy tabrik";
        document.getElementById("adm-bd-target-user-id").value = "";
        document.getElementById("adm-bd-target-search").value = "";
        document.getElementById("adm-bd-target-selected").style.display = "none";
        document.getElementById("adm-bd-title").value = "";
        document.getElementById("adm-bd-banner").value = "";
        autoGrowNamedTextarea("adm-bd-banner");
        document.getElementById("adm-bd-banner-image").value = "";
        document.getElementById("adm-bd-banner-preview").style.display = "none";
        document.getElementById("adm-bd-status").value = "active";
        document.getElementById("adm-bd-date").value = "";
        document.getElementById("adm-bd-gift-diamond").value = "";
        document.getElementById("adm-bd-gift-dollar").value = "";
    }

    function showBdPreview({ title, banner_text, banner_image }) {
        const slot = document.getElementById("bd-preview-card-slot");
        slot.innerHTML = `
            <div class="tournament-promo is-holiday">
                <div class="tournament-promo-imgwrap">
                    ${banner_image ? `<img src="${banner_image}" alt="">` : ""}
                    <div class="tournament-promo-imgfade"></div>
                    <span class="tournament-promo-badge is-personal">🎁 Shaxsiy tabrik</span>
                </div>
                <div class="tournament-promo-body">
                    <div class="tournament-promo-title">${escapeHtml(title || "")}</div>
                    <div class="tournament-promo-text">${formatBannerText(banner_text || "")}</div>
                </div>
            </div>
        `;
        document.getElementById("bd-preview-overlay").style.display = "flex";
    }

    function renderAdminBirthdayAdsList() {
        const box = document.getElementById("adm-bd-list");
        if (!box) return;
        const items = adminTournamentsCache.filter((tr) => !!tr.target_user_id);
        if (!items.length) {
            box.innerHTML = `<span class="inv-empty">Hozircha shaxsiy tabriklar yo'q</span>`;
            return;
        }
        box.innerHTML = items.map((tr) => `
            <div class="admin-tlist-row">
                <span class="atl-info">🎯 ${escapeHtml(tr.title)}<span class="atl-meta">${t("tournament_status_" + (tr.status === "active" ? "live" : tr.status))} · ${escapeHtml(tr.target_full_name || String(tr.target_user_id))}${tr.birthday_date ? " · 📅 " + escapeHtml(tr.birthday_date) : ""}${(tr.gift_diamond || tr.gift_dollar) ? " · 🎁 " + [tr.gift_diamond ? tr.gift_diamond + "💎" : "", tr.gift_dollar ? tr.gift_dollar + "💵" : ""].filter(Boolean).join(" ") : ""}</span></span>
                <span style="display:flex; gap:6px;">
                    <button data-preview-bd="${tr.id}" style="background:rgba(255,255,255,.08);">👁</button>
                    <button data-edit-bd="${tr.id}" style="background:rgba(255,209,102,.14); color:var(--dollar-gold);">${t("tournament_edit_btn")}</button>
                    <button data-del-bd="${tr.id}">${t("admin_action_delete")}</button>
                </span>
            </div>
        `).join("");

        box.querySelectorAll("[data-preview-bd]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const tr = adminTournamentsCache.find((x) => x.id === parseInt(btn.dataset.previewBd, 10));
                if (tr) showBdPreview(tr);
            });
        });
        box.querySelectorAll("[data-edit-bd]").forEach((btn) => {
            btn.addEventListener("click", () => selectBirthdayAdForEdit(parseInt(btn.dataset.editBd, 10)));
        });
        box.querySelectorAll("[data-del-bd]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                try {
                    await api(API_BASE + "/webapp/api/admin_tournament_delete", { entity: "tournament", id: btn.dataset.delBd });
                    toast(t("admin_action_success"), "success");
                    if (adminSelectedBirthdayAdId === parseInt(btn.dataset.delBd, 10)) resetBirthdayAdForm();
                    await loadAdminTournament();
                    renderAdminBirthdayAdsList();
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                }
            });
        });
    }

    function selectBirthdayAdForEdit(id) {
        const tr = adminTournamentsCache.find((x) => x.id === id);
        if (!tr) return;
        adminSelectedBirthdayAdId = id;
        document.getElementById("adm-bd-form-title").textContent = tr.title;
        document.getElementById("adm-bd-target-user-id").value = tr.target_user_id || "";
        renderTargetUserSelected("adm-bd-target-selected", { user_id: tr.target_user_id, full_name: tr.target_full_name, username: tr.target_username });
        document.getElementById("adm-bd-title").value = tr.title || "";
        document.getElementById("adm-bd-banner").value = tr.banner_text || "";
        autoGrowNamedTextarea("adm-bd-banner");
        document.getElementById("adm-bd-banner-image").value = tr.banner_image || "";
        const bdImg = document.getElementById("adm-bd-banner-preview");
        if (tr.banner_image) { bdImg.src = tr.banner_image; bdImg.style.display = ""; } else { bdImg.style.display = "none"; }
        document.getElementById("adm-bd-status").value = tr.status === "finished" ? "finished" : "active";
        document.getElementById("adm-bd-date").value = tr.birthday_date || "";
        document.getElementById("adm-bd-gift-diamond").value = tr.gift_diamond || "";
        document.getElementById("adm-bd-gift-dollar").value = tr.gift_dollar || "";
    }

    function setupBirthdayAdmin() {
        document.getElementById("adm-bd-banner").addEventListener("input", () => autoGrowNamedTextarea("adm-bd-banner"));
        document.getElementById("adm-bd-new-btn").addEventListener("click", resetBirthdayAdForm);
        document.getElementById("adm-bd-preview-btn").addEventListener("click", () => {
            showBdPreview({
                title: document.getElementById("adm-bd-title").value.trim(),
                banner_text: document.getElementById("adm-bd-banner").value.trim(),
                banner_image: document.getElementById("adm-bd-banner-image").value.trim(),
            });
        });
        document.getElementById("bd-preview-close").addEventListener("click", () => {
            document.getElementById("bd-preview-overlay").style.display = "none";
        });
        document.getElementById("bd-preview-overlay").addEventListener("click", (e) => {
            if (e.target.id === "bd-preview-overlay") e.target.style.display = "none";
        });

        setupTargetUserSearch("adm-bd-target-search", "adm-bd-target-suggest", "adm-bd-target-user-id", "adm-bd-target-selected");
        document.getElementById("adm-bd-target-clear-btn").addEventListener("click", () => {
            document.getElementById("adm-bd-target-user-id").value = "";
            document.getElementById("adm-bd-target-search").value = "";
            document.getElementById("adm-bd-target-selected").style.display = "none";
        });

        document.getElementById("adm-bd-save-btn").addEventListener("click", async () => {
            const targetUserId = document.getElementById("adm-bd-target-user-id").value.trim();
            if (!targetUserId) { toast("Avval kimga tabrik yuborishni tanlang", "error"); return; }
            const payload = {
                entity: "tournament",
                kind: "ad",
                target_user_id: targetUserId,
                title: document.getElementById("adm-bd-title").value.trim(),
                banner_text: document.getElementById("adm-bd-banner").value.trim(),
                banner_image: document.getElementById("adm-bd-banner-image").value.trim(),
                lang: "",
                status: document.getElementById("adm-bd-status").value,
                birthday_date: document.getElementById("adm-bd-date").value.trim(),
                gift_diamond: parseInt(document.getElementById("adm-bd-gift-diamond").value, 10) || 0,
                gift_dollar: parseInt(document.getElementById("adm-bd-gift-dollar").value, 10) || 0,
            };
            if (!payload.title) return;
            if (adminSelectedBirthdayAdId) payload.id = adminSelectedBirthdayAdId;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_tournament_save", payload);
                adminSelectedBirthdayAdId = res.id;
                toast(t("admin_action_success"), "success");
                await loadAdminTournament();
                renderAdminBirthdayAdsList();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        document.getElementById("adm-bd-upload-btn").addEventListener("click", () => {
            document.getElementById("adm-bd-upload-input").click();
        });
        document.getElementById("adm-bd-upload-input").addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const fd = new FormData();
                fd.append("initData", initData);
                fd.append("file", file);
                const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || "upload_failed");
                document.getElementById("adm-bd-banner-image").value = data.url;
                const bdImg = document.getElementById("adm-bd-banner-preview");
                bdImg.src = data.url; bdImg.style.display = "";
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                e.target.value = "";
            }
        });
    }

    /* ---------------- Tournament Manager (cheklangan reklama) view ---------------- */
    let tmSelectedId = null;
    let tmListCache = [];

    function resetTmTournamentForm() {
        tmSelectedId = null;
        document.getElementById("tm-t-form-title").textContent = "➕ Yangi reklama";
        document.getElementById("tm-t-title").value = "";
        document.getElementById("tm-t-banner").value = "";
        autoGrowNamedTextarea("tm-t-banner");
        document.getElementById("tm-t-event-date").value = "";
        document.getElementById("tm-t-contact-username").value = "";
        document.getElementById("tm-t-contact-btn-text").value = "";
        document.getElementById("tm-t-banner-image").value = "";
        document.getElementById("tm-t-banner-preview").style.display = "none";
        document.getElementById("tm-t-status").value = "upcoming";
    }

    function renderTmTournamentList() {
        const box = document.getElementById("tm-t-list");
        if (!tmListCache.length) { box.innerHTML = `<span class="inv-empty">Hozircha reklamalaringiz yo'q</span>`; return; }
        box.innerHTML = tmListCache.map((tr) => `
            <div class="admin-tlist-row">
                <span class="atl-info">${escapeHtml(tr.title)}<span class="atl-meta">${t("tournament_status_" + (tr.status === "active" ? "live" : tr.status))} · 👆 ${fmt(tr.contact_clicks || 0)}</span></span>
                <span style="display:flex; gap:6px;">
                    <button data-edit-tm="${tr.id}" style="background:rgba(255,209,102,.14); color:var(--dollar-gold);">${t("tournament_edit_btn")}</button>
                    <button data-del-tm="${tr.id}">${t("admin_action_delete")}</button>
                </span>
            </div>
        `).join("");
        box.querySelectorAll("[data-edit-tm]").forEach((btn) => {
            btn.addEventListener("click", () => selectTmTournamentForEdit(parseInt(btn.dataset.editTm, 10)));
        });
        box.querySelectorAll("[data-del-tm]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                try {
                    await api(API_BASE + "/webapp/api/admin_tournament_delete", { entity: "tournament", id: btn.dataset.delTm });
                    toast(t("admin_action_success"), "success");
                    if (tmSelectedId === parseInt(btn.dataset.delTm, 10)) resetTmTournamentForm();
                    loadTmTournamentList();
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                }
            });
        });
    }

    function selectTmTournamentForEdit(id) {
        const tr = tmListCache.find((x) => x.id === id);
        if (!tr) return;
        tmSelectedId = id;
        document.getElementById("tm-t-form-title").textContent = tr.title;
        document.getElementById("tm-t-title").value = tr.title || "";
        document.getElementById("tm-t-banner").value = tr.banner_text || "";
        autoGrowNamedTextarea("tm-t-banner");
        document.getElementById("tm-t-event-date").value = tr.event_date || "";
        document.getElementById("tm-t-contact-username").value = tr.contact_username || "";
        document.getElementById("tm-t-contact-btn-text").value = tr.contact_button_text || "";
        document.getElementById("tm-t-banner-image").value = tr.banner_image || "";
        if (tr.banner_image) { document.getElementById("tm-t-banner-preview").src = tr.banner_image; document.getElementById("tm-t-banner-preview").style.display = ""; }
        else document.getElementById("tm-t-banner-preview").style.display = "none";
        document.getElementById("tm-t-status").value = tr.status || "upcoming";
    }

    async function loadTmTournamentList() {
        try {
            const res = await api(API_BASE + "/webapp/api/admin_tournaments_list");
            tmListCache = res.tournaments || [];
            renderTmTournamentList();
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        }
    }

    function setupTmTournamentView() {
        resetTmTournamentForm();
        document.getElementById("tm-t-banner").addEventListener("input", () => autoGrowNamedTextarea("tm-t-banner"));
        document.getElementById("tm-t-new-btn").addEventListener("click", resetTmTournamentForm);
        document.getElementById("tm-t-save-btn").addEventListener("click", async () => {
            const payload = {
                entity: "tournament",
                title: document.getElementById("tm-t-title").value.trim(),
                banner_text: document.getElementById("tm-t-banner").value.trim(),
                event_date: document.getElementById("tm-t-event-date").value.trim(),
                contact_username: document.getElementById("tm-t-contact-username").value.trim().replace(/^@/, ""),
                contact_button_text: document.getElementById("tm-t-contact-btn-text").value.trim(),
                banner_image: document.getElementById("tm-t-banner-image").value.trim(),
                status: document.getElementById("tm-t-status").value,
            };
            if (!payload.title) return;
            if (tmSelectedId) payload.id = tmSelectedId;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_tournament_save", payload);
                tmSelectedId = res.id;
                toast(t("admin_action_success"), "success");
                loadTmTournamentList();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });
        document.getElementById("tm-t-upload-btn").addEventListener("click", () => {
            document.getElementById("tm-t-upload-input").click();
        });
        document.getElementById("tm-t-upload-input").addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const fd = new FormData();
                fd.append("initData", initData);
                fd.append("file", file);
                const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || "upload_failed");
                document.getElementById("tm-t-banner-image").value = data.url;
                document.getElementById("tm-t-banner-preview").src = data.url;
                document.getElementById("tm-t-banner-preview").style.display = "";
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                e.target.value = "";
            }
        });
    }

    function renderAdminGroupsList(groups) {
        const box = document.getElementById("admin-groups-container");
        if (!groups.length) {
            box.innerHTML = `<span class="inv-empty">${t("admin_groups_empty")}</span>`;
            return;
        }
        box.innerHTML = groups.map((g) => `
            <div class="admin-group-card"${g.invite_link ? ` data-link="${escapeHtml(g.invite_link)}" style="cursor:pointer;"` : ""}>
                <div class="agc-avatar"><img src="${API_BASE}/webapp/avatar_chat/${g.chat_id}" alt="" onerror="this.remove();"></div>
                <div class="agc-info">
                    <div class="agc-title">${escapeHtml(g.title)}</div>
                    <div class="agc-meta">👥 ${fmt(g.member_count)} · ${g.games_count} ${t("admin_group_games")}</div>
                </div>
                ${g.invite_link ? `<i class="fa-solid fa-arrow-up-right-from-square" style="color:var(--text-2); font-size:12px;"></i>` : ""}
                <span class="agc-dot${g.active ? " active" : ""}"></span>
            </div>
        `).join("");
        box.querySelectorAll(".admin-group-card[data-link]").forEach((card) => {
            card.addEventListener("click", () => {
                const link = card.dataset.link;
                if (tg && tg.openTelegramLink) tg.openTelegramLink(link);
                else window.open(link, "_blank");
            });
        });
    }

    const ADMIN_GIVE_FIELD_LABELS = {
        dollar: ["💵", "dollar"], diamond: ["💎", "olmos"],
        vip_days: ["👑", "VIP kun"], vip_revoke: ["❌", "VIP olib tashlandi"],
        role: ["🎭", "Faol rol"], geroy_level: ["🥷", "Geroy darajasi"],
    };
    function adminGiveFieldLabel(field) {
        if (ADMIN_GIVE_FIELD_LABELS[field]) return ADMIN_GIVE_FIELD_LABELS[field];
        const def = ADMIN_ITEM_DEFS.find((d) => d.field === field);
        return def ? [def.icon, def.label] : ["📦", field];
    }

    async function loadAdminActivity() {
        const pBox = document.getElementById("admin-purchases-list");
        const cBox = document.getElementById("admin-daily-claims-list");
        const gBox = document.getElementById("admin-gives-list");
        pBox.innerHTML = '<div class="skeleton-list"></div>';
        cBox.innerHTML = '<div class="skeleton-list"></div>';
        gBox.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/admin_activity");
            const purchases = res.purchases || [];
            pBox.innerHTML = purchases.length ? purchases.map((p) => {
                const name = p.full_name || t("label_gamer");
                const initial = name.trim().charAt(0).toUpperCase() || "?";
                const isDollar = p.kind === "dollar";
                const icon = isDollar ? "💵" : "💎";
                return `
                    <div class="admin-activity-card kind-${p.kind}">
                        <div class="admin-activity-avatar"><img src="${API_BASE}/webapp/avatar/${p.user_id}" alt="" onerror="var e=this.parentElement; e.innerHTML=''; e.textContent='${escapeHtml(initial)}';"></div>
                        <div class="admin-activity-info">
                            <div class="admin-activity-name">${escapeHtml(name)}</div>
                            <div class="admin-activity-meta">${p.username ? "@" + escapeHtml(p.username) + " · " : ""}ID: ${p.user_id}<br>🕐 ${escapeHtml(p.date)} · ${p.source === "webapp" ? "📱 WebApp" : "🤖 Bot"}</div>
                        </div>
                        <div class="admin-activity-badges">
                            <span class="admin-activity-pill ${isDollar ? "dollar" : "diamond"}">${icon} ${fmt(p.amount)}</span>
                            <span class="admin-activity-pill stars">⭐ ${fmt(p.stars)}</span>
                        </div>
                    </div>
                `;
            }).join("") : `<span class="inv-empty">Hali xarid yo'q</span>`;

            const claims = res.daily_claims || [];
            cBox.innerHTML = claims.length ? claims.map((c) => {
                const name = c.full_name || t("label_gamer");
                const initial = name.trim().charAt(0).toUpperCase() || "?";
                return `
                    <div class="admin-activity-card">
                        <div class="admin-activity-avatar"><img src="${API_BASE}/webapp/avatar/${c.user_id}" alt="" onerror="var e=this.parentElement; e.innerHTML=''; e.textContent='${escapeHtml(initial)}';"></div>
                        <div class="admin-activity-info">
                            <div class="admin-activity-name">${escapeHtml(name)}</div>
                            <div class="admin-activity-meta">${c.username ? "@" + escapeHtml(c.username) + " · " : ""}ID: ${c.user_id}</div>
                        </div>
                        <div class="admin-activity-badges">
                            <span class="admin-activity-pill streak">🔥 ${fmt(c.streak)}-kun</span>
                        </div>
                    </div>
                `;
            }).join("") : `<span class="inv-empty">Bugun hali hech kim olmagan</span>`;

            const gives = res.admin_gives || [];
            gBox.innerHTML = gives.length ? gives.map((g) => {
                const [icon, label] = adminGiveFieldLabel(g.field);
                const amountText = g.amount ? `${g.amount > 0 ? "+" : ""}${fmt(g.amount)}` : "";
                return `
                    <div class="admin-activity-card">
                        <div class="admin-activity-avatar"><img src="${API_BASE}/webapp/avatar/${g.admin_user_id}" alt="" onerror="var e=this.parentElement; e.innerHTML=''; e.textContent='👮';"></div>
                        <div class="admin-activity-info">
                            <div class="admin-activity-name">${escapeHtml(g.admin_name)} → ${escapeHtml(g.target_name)}</div>
                            <div class="admin-activity-meta">🕐 ${escapeHtml(g.date)} · ${g.source === "webapp" ? "📱 WebApp" : "🤖 Bot"}${g.extra ? " · " + escapeHtml(g.extra) : ""}</div>
                        </div>
                        <div class="admin-activity-badges">
                            <span class="admin-activity-pill diamond">${icon} ${amountText || label}</span>
                        </div>
                    </div>
                `;
            }).join("") : `<span class="inv-empty">Hali admin harakati yo'q</span>`;
        } catch (e) {
            pBox.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
            cBox.innerHTML = "";
            gBox.innerHTML = "";
        }
    }

    /* ---------------- admin: support chat ---------------- */
    let adminSupportThreadTimer = null;
    let adminSupportOpenCustomerId = null;
    let adminSupportThreadLastId = 0;
    let adminSupportListTimer = null;

    function stopAdminSupportThreadPolling() {
        if (adminSupportThreadTimer) clearInterval(adminSupportThreadTimer);
        adminSupportThreadTimer = null;
        adminSupportOpenCustomerId = null;
        if (adminSupportListTimer) clearInterval(adminSupportListTimer);
        adminSupportListTimer = null;
    }

    async function uploadSupportImage(file) {
        const fd = new FormData();
        fd.append("initData", initData);
        fd.append("file", file);
        const res = await fetch(API_BASE + "/webapp/api/support_upload_image", { method: "POST", body: fd });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || "upload_failed");
        return data.url;
    }

    async function refreshAdminSupportBadge() {
        const badge = document.getElementById("admin-support-badge");
        if (!badge) return;
        try {
            const res = await api(API_BASE + "/webapp/api/admin_support_list");
            const unread = (res.conversations || []).filter((c) => c.unread).length;
            if (unread > 0) {
                badge.textContent = unread > 99 ? "99+" : String(unread);
                badge.style.display = "";
            } else {
                badge.style.display = "none";
            }
        } catch (e) { /* jim */ }
    }

    async function showAdminSupportList() {
        stopAdminSupportThreadPolling();
        document.getElementById("admin-support-thread-panel").style.display = "none";
        document.getElementById("admin-support-list-panel").style.display = "";
        const box = document.getElementById("admin-support-list");
        box.innerHTML = '<div class="skeleton-list"></div>';
        const load = async () => {
            try {
                const res = await api(API_BASE + "/webapp/api/admin_support_list");
                const convos = res.conversations || [];
                box.innerHTML = convos.length ? convos.map((c) => {
                    const name = c.full_name || t("label_gamer");
                    return `
                        <div class="admin-support-convo${c.unread ? " unread" : ""}" data-cid="${c.customer_user_id}">
                            <div class="auc-avatar" style="width:40px;height:40px;flex-shrink:0;">
                                <img src="${API_BASE}/webapp/avatar/${c.customer_user_id}" alt="" onerror="this.remove();">
                            </div>
                            <div class="admin-support-convo-info">
                                <div class="admin-support-convo-name">${escapeHtml(name)}${c.username ? " · @" + escapeHtml(c.username) : ""}${c.unread ? '<span class="admin-support-convo-new-tag">Yangi</span>' : ""}</div>
                                <div class="admin-support-convo-preview">${c.last_from_admin ? "Siz: " : ""}${escapeHtml(c.last_text)}</div>
                            </div>
                            <div class="admin-support-convo-time">${escapeHtml((c.date || "").split(" ").pop())}</div>
                        </div>
                    `;
                }).join("") : `<span class="inv-empty">Hali murojaat yo'q</span>`;
                box.querySelectorAll(".admin-support-convo").forEach((el) => {
                    el.addEventListener("click", () => openAdminSupportThread(parseInt(el.dataset.cid, 10)));
                });
                refreshAdminSupportBadge();
            } catch (e) {
                box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
            }
        };
        await load();
        if (adminSupportListTimer) clearInterval(adminSupportListTimer);
        adminSupportListTimer = setInterval(() => {
            if (adminSupportOpenCustomerId) return;
            load();
        }, 5000);
    }

    function renderAdminSupportThread(messages, append) {
        const box = document.getElementById("admin-support-thread-messages");
        if (!append) box.innerHTML = "";
        messages.forEach((m) => {
            if (m.id <= adminSupportThreadLastId) return;
            adminSupportThreadLastId = Math.max(adminSupportThreadLastId, m.id);
            const el = document.createElement("div");
            el.className = "support-msg " + (m.is_from_admin ? "mine" : "theirs");
            const img = m.image_url ? `<img class="support-msg-img" src="${escapeHtml(m.image_url)}" alt="" onclick="window.open(this.src,'_blank')">` : "";
            const ticks = m.is_from_admin ? `<i class="fa-solid ${m.is_read ? "fa-check-double read" : "fa-check"} support-msg-ticks${m.is_read ? " read" : ""}"></i>` : "";
            el.innerHTML = `${img}${m.text ? escapeHtml(m.text) : ""}<span class="support-msg-time">${escapeHtml((m.date || "").split(" ").pop())}${ticks}</span>`;
            box.appendChild(el);
        });
        box.scrollTop = box.scrollHeight;
    }

    function renderAdminSupportCustomerCard(customer) {
        const card = document.getElementById("admin-support-customer-card");
        const messagesBox = document.getElementById("admin-support-thread-messages");
        if (!customer) { card.innerHTML = ""; return; }
        const name = customer.full_name || t("label_gamer");
        card.innerHTML = `
            <img class="admin-support-customer-avatar" src="${API_BASE}/webapp/avatar/${customer.user_id}" alt="" onerror="this.style.display='none';">
            <div class="admin-support-customer-info">
                <div class="admin-support-customer-name">${escapeHtml(name)}</div>
                <div class="admin-support-customer-meta">${customer.username ? "@" + escapeHtml(customer.username) + " · " : ""}ID: ${customer.user_id}</div>
            </div>
        `;
        if (messagesBox) {
            messagesBox.style.backgroundSize = "cover";
            messagesBox.style.backgroundPosition = "center";
            messagesBox.style.backgroundRepeat = "no-repeat";
            setChatWallpaper(messagesBox, tgUser && tgUser.id);
        }
    }

    async function openAdminSupportThread(customerId) {
        adminSupportOpenCustomerId = customerId;
        adminSupportThreadLastId = 0;
        document.getElementById("admin-support-list-panel").style.display = "none";
        document.getElementById("admin-support-thread-panel").style.display = "";
        const box = document.getElementById("admin-support-thread-messages");
        box.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/admin_support_thread", { customer_user_id: customerId });
            adminSupportThreadLastId = 0;
            renderAdminSupportCustomerCard(res.customer);
            renderAdminSupportThread(res.messages || [], false);
            refreshSupportFabBadge();
            refreshAdminSupportBadge();
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
        if (adminSupportThreadTimer) clearInterval(adminSupportThreadTimer);
        adminSupportThreadTimer = setInterval(async () => {
            if (adminSupportOpenCustomerId !== customerId) return;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_support_thread", { customer_user_id: customerId });
                renderAdminSupportThread((res.messages || []).filter((m) => m.id > adminSupportThreadLastId), true);
                refreshSupportFabBadge();
            } catch (e) { /* jim */ }
        }, 4000);
    }

    function setupAdminSupportChat() {
        document.getElementById("admin-support-back-btn").addEventListener("click", showAdminSupportList);
        const searchInput = document.getElementById("admin-support-search-input");
        const searchBtn = document.getElementById("admin-support-search-btn");
        const resultsBox = document.getElementById("admin-support-search-results");
        let searchDebounce = null;

        const renderSearchResults = (users) => {
            if (!users.length) {
                resultsBox.innerHTML = `<div class="admin-support-search-empty">Hech kim topilmadi</div>`;
            } else {
                resultsBox.innerHTML = users.map((u) => `
                    <div class="admin-support-search-result" data-uid="${u.user_id}">
                        <img src="${API_BASE}/webapp/avatar/${u.user_id}" alt="" onerror="this.remove();">
                        <div>
                            <div class="admin-support-search-result-name">${escapeHtml(u.full_name || t("label_gamer"))}</div>
                            <div class="admin-support-search-result-sub">${u.username ? "@" + escapeHtml(u.username) + " · " : ""}ID: ${u.user_id}</div>
                        </div>
                    </div>
                `).join("");
                resultsBox.querySelectorAll(".admin-support-search-result").forEach((el) => {
                    el.addEventListener("click", () => {
                        resultsBox.style.display = "none";
                        searchInput.value = "";
                        openAdminSupportThread(parseInt(el.dataset.uid, 10));
                    });
                });
            }
            resultsBox.style.display = "";
        };

        const doSearch = async () => {
            const query = searchInput.value.trim();
            if (!query) { resultsBox.style.display = "none"; return; }
            try {
                const res = await api(API_BASE + "/webapp/api/admin_support_search_users", { query });
                renderSearchResults(res.users || []);
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        };
        searchBtn.addEventListener("click", doSearch);
        searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); doSearch(); }
        });
        searchInput.addEventListener("input", () => {
            if (searchDebounce) clearTimeout(searchDebounce);
            const query = searchInput.value.trim();
            if (!query) { resultsBox.style.display = "none"; return; }
            searchDebounce = setTimeout(doSearch, 350);
        });
        document.addEventListener("click", (e) => {
            if (!resultsBox.contains(e.target) && e.target !== searchInput) resultsBox.style.display = "none";
        });
        document.getElementById("admin-support-delete-btn").addEventListener("click", async () => {
            if (!adminSupportOpenCustomerId) return;
            if (!(await tgConfirm("Bu suhbat sizning ro'yxatingizdan yashiriladi (foydalanuvchida saqlanib qoladi). Davom etasizmi?"))) return;
            try {
                await api(API_BASE + "/webapp/api/admin_support_delete_conversation", { customer_user_id: adminSupportOpenCustomerId });
                toast(t("admin_action_success"), "success");
                showAdminSupportList();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });
        const input = document.getElementById("admin-support-reply-input");
        const replyBtn = document.getElementById("admin-support-reply-btn");
        const photoBtn = document.getElementById("admin-support-photo-btn");
        const photoInput = document.getElementById("admin-support-photo-input");
        const send = async (imageUrl) => {
            const text = input.value.trim();
            if ((!text && !imageUrl) || !adminSupportOpenCustomerId) return;
            input.value = "";
            try {
                const res = await api(API_BASE + "/webapp/api/admin_support_reply", { customer_user_id: adminSupportOpenCustomerId, text, image_url: imageUrl || "" });
                renderAdminSupportThread([res.message], true);
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        };
        replyBtn.addEventListener("click", () => send());
        photoBtn.addEventListener("click", () => photoInput.click());
        photoInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file || !adminSupportOpenCustomerId) return;
            photoBtn.classList.add("uploading");
            try {
                const url = await uploadSupportImage(file);
                await send(url);
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                photoBtn.classList.remove("uploading");
                e.target.value = "";
            }
        });
    }


    async function loadAdminGroups() {
        const box = document.getElementById("admin-groups-container");
        box.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/admin_groups");
            adminGroupsCache = res.groups || [];
            renderAdminGroupsList(adminGroupsCache);
            document.getElementById("admin-groups-search").addEventListener("input", (e) => {
                const q = e.target.value.trim().toLowerCase();
                renderAdminGroupsList(adminGroupsCache.filter((g) => g.title.toLowerCase().includes(q)));
            });
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    function setupAdminPanel() {
        setupTournamentContactPreview();
        setupAdminSupportChat();
        document.querySelectorAll(".admin-collapse-toggle").forEach((toggle) => {
            toggle.addEventListener("click", () => {
                toggle.closest(".admin-collapsible").classList.toggle("collapsed");
            });
        });
        document.querySelectorAll("#admin-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#admin-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                const tabKey = btn.dataset.adminTab;
                document.querySelectorAll(".admin-tab-panel").forEach((p) => p.style.display = "none");
                document.getElementById("admin-tab-" + tabKey).style.display = "";
                if (tabKey === "groups" && !adminGroupsLoaded) {
                    adminGroupsLoaded = true;
                    loadAdminGroups();
                }
                if (tabKey === "tournament" && !adminTournamentLoaded) {
                    adminTournamentLoaded = true;
                    resetTournamentForm();
                    loadAdminTournament();
                }
                if (tabKey === "tournament") {
                    loadAdminTournamentManagers();
                }
                if (tabKey === "turnir") {
                    resetTurnirForm();
                    loadAdminTournament().then(renderAdminTurnirList);
                }
                if (tabKey === "holiday") {
                    resetHolidayForm();
                    loadAdminHolidays();
                }
                if (tabKey === "birthday") {
                    loadAdminBirthdays();
                    resetBirthdayAdForm();
                    if (!adminTournamentLoaded) {
                        adminTournamentLoaded = true;
                        loadAdminTournament().then(renderAdminBirthdayAdsList);
                    } else {
                        renderAdminBirthdayAdsList();
                    }
                }
                if (tabKey === "activity") {
                    loadAdminActivity();
                }
            });
        });

        setupTargetUserSearch("adm-tm-grant-search", "adm-tm-grant-suggest", "adm-tm-grant-user-id");
        document.getElementById("adm-tm-grant-btn").addEventListener("click", async () => {
            const uid = document.getElementById("adm-tm-grant-user-id").value.trim();
            if (!uid) { toast("Avval foydalanuvchini tanlang", "error"); return; }
            try {
                await api(API_BASE + "/webapp/api/admin_grant_tournament_manager", { user_id: uid });
                toast(t("admin_action_success"), "success");
                document.getElementById("adm-tm-grant-search").value = "";
                document.getElementById("adm-tm-grant-user-id").value = "";
                loadAdminTournamentManagers();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        setupTurnirAdmin();
        setupHolidayAdmin();
        setupBirthdayAdmin();

        document.getElementById("adm-bd-goto-tournament-btn").addEventListener("click", () => {
            document.querySelectorAll("#admin-tabs .seg").forEach((b) => b.classList.remove("active"));
            document.querySelector('#admin-tabs .seg[data-admin-tab="tournament"]').classList.add("active");
            document.querySelectorAll(".admin-tab-panel").forEach((p) => p.style.display = "none");
            document.getElementById("admin-tab-tournament").style.display = "";
        });

        const adminSearchResultsBox = document.getElementById("admin-search-results");

        async function selectAdminSearchUser(userId) {
            adminSearchResultsBox.style.display = "none";
            try {
                const res = await api(API_BASE + "/webapp/api/admin_search_user", { query: String(userId) });
                renderAdminUserCard(res.user);
            } catch (e) {
                toast(t("admin_user_not_found"), "error");
                document.getElementById("admin-user-result").style.display = "none";
            }
        }

        async function doAdminSearch() {
            const query = document.getElementById("admin-search-input").value.trim();
            if (!query) return;
            adminSearchResultsBox.style.display = "none";
            try {
                const res = await api(API_BASE + "/webapp/api/admin_search_user", { query });
                await selectAdminSearchUser(res.user.user_id);
            } catch (e) {
                try {
                    const res2 = await api(API_BASE + "/webapp/api/admin_support_search_users", { query });
                    const users = res2.users || [];
                    if (users.length === 1) {
                        await selectAdminSearchUser(users[0].user_id);
                    } else if (users.length > 1) {
                        adminSearchResultsBox.innerHTML = users.map((u) => `
                            <div class="admin-support-search-result" data-uid="${u.user_id}">
                                <img src="${API_BASE}/webapp/avatar/${u.user_id}" alt="" onerror="this.remove();">
                                <div>
                                    <div class="admin-support-search-result-name">${escapeHtml(u.full_name || t("label_gamer"))}</div>
                                    <div class="admin-support-search-result-sub">${u.username ? "@" + escapeHtml(u.username) + " · " : ""}ID: ${u.user_id}</div>
                                </div>
                            </div>
                        `).join("");
                        adminSearchResultsBox.querySelectorAll(".admin-support-search-result").forEach((el) => {
                            el.addEventListener("click", () => selectAdminSearchUser(parseInt(el.dataset.uid, 10)));
                        });
                        adminSearchResultsBox.style.display = "";
                    } else {
                        toast(t("admin_user_not_found"), "error");
                        document.getElementById("admin-user-result").style.display = "none";
                    }
                } catch (e2) {
                    toast(t("admin_user_not_found"), "error");
                    document.getElementById("admin-user-result").style.display = "none";
                }
            }
        }
        document.getElementById("admin-search-btn").addEventListener("click", doAdminSearch);
        document.getElementById("admin-search-input").addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); doAdminSearch(); }
        });
        document.addEventListener("click", (e) => {
            if (!adminSearchResultsBox.contains(e.target) && e.target.id !== "admin-search-input") adminSearchResultsBox.style.display = "none";
        });

        async function refreshAdminUser() {
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            const res = await api(API_BASE + "/webapp/api/admin_search_user", { query: userId });
            renderAdminUserCard(res.user);
        }

        async function applyBalanceDelta(dollarDelta, diamondDelta) {
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            try {
                await api(API_BASE + "/webapp/api/admin_adjust_balance", { user_id: userId, dollar_delta: dollarDelta, diamond_delta: diamondDelta });
                toast(t("admin_action_success"), "success");
                await refreshAdminUser();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        }

        document.getElementById("admin-dollar-add-btn").addEventListener("click", () => {
            const amt = parseInt(document.getElementById("admin-dollar-amount").value, 10);
            if (!amt) return;
            document.getElementById("admin-dollar-amount").value = "";
            applyBalanceDelta(amt, 0);
        });
        document.getElementById("admin-dollar-sub-btn").addEventListener("click", () => {
            const amt = parseInt(document.getElementById("admin-dollar-amount").value, 10);
            if (!amt) return;
            document.getElementById("admin-dollar-amount").value = "";
            applyBalanceDelta(-amt, 0);
        });
        document.getElementById("admin-diamond-add-btn").addEventListener("click", () => {
            const amt = parseInt(document.getElementById("admin-diamond-amount").value, 10);
            if (!amt) return;
            document.getElementById("admin-diamond-amount").value = "";
            applyBalanceDelta(0, amt);
        });
        document.getElementById("admin-diamond-sub-btn").addEventListener("click", () => {
            const amt = parseInt(document.getElementById("admin-diamond-amount").value, 10);
            if (!amt) return;
            document.getElementById("admin-diamond-amount").value = "";
            applyBalanceDelta(0, -amt);
        });
        document.getElementById("admin-geroy-level-add-btn").addEventListener("click", async () => {
            const amt = parseInt(document.getElementById("admin-geroy-level-amount").value, 10);
            if (!amt) return;
            document.getElementById("admin-geroy-level-amount").value = "";
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            try {
                await api(API_BASE + "/webapp/api/admin_adjust_balance", { user_id: userId, geroy_level_delta: amt });
                toast(t("admin_action_success"), "success");
                await refreshAdminUser();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });
        document.getElementById("admin-geroy-level-sub-btn").addEventListener("click", async () => {
            const amt = parseInt(document.getElementById("admin-geroy-level-amount").value, 10);
            if (!amt) return;
            document.getElementById("admin-geroy-level-amount").value = "";
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            try {
                await api(API_BASE + "/webapp/api/admin_adjust_balance", { user_id: userId, geroy_level_delta: -amt });
                toast(t("admin_action_success"), "success");
                await refreshAdminUser();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        document.getElementById("admin-grant-vip-btn").addEventListener("click", async () => {
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            const days = parseInt(document.getElementById("admin-vip-days").value, 10);
            if (!days) return;
            try {
                await api(API_BASE + "/webapp/api/admin_grant_vip", { user_id: userId, days });
                toast(t("admin_action_success"), "success");
                document.getElementById("admin-vip-days").value = "";
                await refreshAdminUser();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        document.getElementById("admin-revoke-vip-btn").addEventListener("click", async () => {
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            try {
                await api(API_BASE + "/webapp/api/admin_revoke_vip", { user_id: userId });
                toast(t("admin_action_success"), "success");
                await refreshAdminUser();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        let selectedRoleKey = null;
        const roleKeyInput = document.getElementById("admin-role-key");
        const roleSuggest = document.getElementById("admin-role-suggest");
        document.body.appendChild(roleSuggest);

        function positionRoleSuggest() {
            const rect = roleKeyInput.getBoundingClientRect();
            roleSuggest.style.left = rect.left + "px";
            roleSuggest.style.top = (rect.bottom + 4) + "px";
            roleSuggest.style.width = rect.width + "px";
        }

        roleKeyInput.addEventListener("input", () => {
            selectedRoleKey = null;
            const q = roleKeyInput.value.trim().toLowerCase();
            const allRoles = (profileCache && profileCache.roles) ? profileCache.roles.filter((r) => r.team !== "anjom") : [];
            if (!q) { roleSuggest.classList.remove("open"); return; }
            const matches = allRoles.filter((r) => r.name.toLowerCase().includes(q)).slice(0, 25);
            if (!matches.length) { roleSuggest.classList.remove("open"); roleSuggest.innerHTML = ""; return; }
            roleSuggest.innerHTML = matches.map((r) => `<div class="admin-role-suggest-item" data-role-key="${escapeHtml(r.role_key)}">${escapeHtml(r.name)}</div>`).join("");
            positionRoleSuggest();
            roleSuggest.classList.add("open");
        });
        roleSuggest.addEventListener("click", (e) => {
            const item = e.target.closest(".admin-role-suggest-item");
            if (!item) return;
            selectedRoleKey = item.dataset.roleKey;
            roleKeyInput.value = item.textContent;
            roleSuggest.classList.remove("open");
        });
        document.addEventListener("click", (e) => {
            if (!roleSuggest.contains(e.target) && e.target !== roleKeyInput) roleSuggest.classList.remove("open");
        });

        document.getElementById("admin-grant-role-btn").addEventListener("click", async () => {
            const userId = document.getElementById("admin-user-result").dataset.userId;
            if (!userId) return;
            const role = selectedRoleKey || roleKeyInput.value.trim();
            if (!role) return;
            try {
                await api(API_BASE + "/webapp/api/admin_grant_role", { user_id: userId, role: role });
                toast(t("admin_action_success"), "success");
                roleKeyInput.value = "";
                selectedRoleKey = null;
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        document.getElementById("admin-broadcast-btn").addEventListener("click", async () => {
            const text = document.getElementById("admin-broadcast-text").value.trim();
            if (!text) return;
            if (!(await tgConfirm(t("admin_broadcast_confirm")))) return;
            const btn = document.getElementById("admin-broadcast-btn");
            btn.disabled = true;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_broadcast", { text: text });
                toast(tf("admin_broadcast_queued", { count: res.queued }), "success");
                document.getElementById("admin-broadcast-text").value = "";
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            } finally {
                btn.disabled = false;
            }
        });

        document.querySelectorAll(".adm-t-emoji-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const strip = btn.closest("[data-textarea]");
                const textarea = document.getElementById(strip ? strip.dataset.textarea : "adm-t-banner");
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const val = textarea.value;
                const emoji = btn.textContent;
                textarea.value = val.slice(0, start) + emoji + val.slice(end);
                textarea.focus();
                textarea.selectionStart = textarea.selectionEnd = start + emoji.length;
            });
        });

        document.getElementById("adm-t-banner").addEventListener("input", autoGrowBannerTextarea);

        function wrapSelectionWithMarker(textareaId, name) {
            const textarea = document.getElementById(textareaId);
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const val = textarea.value;
            const selected = val.slice(start, end);
            const openTag = `[${name}]`;
            const closeTag = `[/${name}]`;
            textarea.value = val.slice(0, start) + openTag + selected + closeTag + val.slice(end);
            textarea.focus();
            if (selected) {
                textarea.selectionStart = start + openTag.length;
                textarea.selectionEnd = start + openTag.length + selected.length;
            } else {
                const pos = start + openTag.length;
                textarea.selectionStart = textarea.selectionEnd = pos;
            }
            autoGrowNamedTextarea(textareaId);
        }

        function clearMarkersInSelection(textareaId) {
            const textarea = document.getElementById(textareaId);
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const val = textarea.value;
            const selected = val.slice(start, end);
            const cleaned = selected.replace(/\[\/?\w+\]\s?/g, "");
            textarea.value = val.slice(0, start) + cleaned + val.slice(end);
            textarea.focus();
            textarea.selectionStart = start;
            textarea.selectionEnd = start + cleaned.length;
            autoGrowNamedTextarea(textareaId);
        }

        document.querySelectorAll(".adm-t-color-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const strip = btn.closest("[data-textarea]");
                const textareaId = strip ? strip.dataset.textarea : "adm-t-banner";
                const name = btn.dataset.colorName;
                if (name === "oq") clearMarkersInSelection(textareaId);
                else wrapSelectionWithMarker(textareaId, name);
            });
        });

        document.querySelectorAll(".adm-t-size-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const strip = btn.closest("[data-textarea]");
                const textareaId = strip ? strip.dataset.textarea : "adm-t-banner";
                const name = btn.dataset.sizeName;
                if (name === "normal") clearMarkersInSelection(textareaId);
                else wrapSelectionWithMarker(textareaId, name);
            });
        });

        document.getElementById("adm-t-new-btn").addEventListener("click", resetTournamentForm);

        document.getElementById("adm-t-status").addEventListener("change", (e) => {
            document.getElementById("adm-t-winner-row").style.display = e.target.value === "finished" ? "" : "none";
        });

        document.getElementById("adm-t-info-save-btn").addEventListener("click", async () => {
            const payload = {
                entity: "tournament",
                title: document.getElementById("adm-t-title").value.trim(),
                banner_text: document.getElementById("adm-t-banner").value.trim(),
                event_date: document.getElementById("adm-t-event-date").value.trim(),
                contact_username: document.getElementById("adm-t-contact-username").value.trim().replace(/^@/, ""),
                contact_button_text: document.getElementById("adm-t-contact-btn-text").value.trim(),
                banner_image: document.getElementById("adm-t-banner-image").value.trim(),
                banner_images: JSON.stringify(adminExtraImagesCache),
                lang: document.getElementById("adm-t-lang").value,
                status: document.getElementById("adm-t-status").value,
                winner_name: document.getElementById("adm-t-winner-name").value.trim(),
                winner_team: document.getElementById("adm-t-winner-team").value.trim(),
                winner_user_id: document.getElementById("adm-t-winner-uid").value.trim(),
                kind: "ad",
            };
            if (!payload.title) return;
            if (adminSelectedTournamentId) payload.id = adminSelectedTournamentId;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_tournament_save", payload);
                adminSelectedTournamentId = res.id;
                toast(t("admin_action_success"), "success");
                await loadAdminTournament();
                tournamentLoaded = true;
                safe(() => loadTournament(), "loadTournament");
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });

        document.getElementById("adm-t-preview-btn").addEventListener("click", () => {
            goTo("tournament");
        });

        document.getElementById("adm-t-upload-btn").addEventListener("click", () => {
            document.getElementById("adm-t-upload-input").click();
        });

        document.getElementById("adm-t-upload-input").addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const btn = document.getElementById("adm-t-upload-btn");
            const oldText = btn.textContent;
            btn.textContent = "...";
            btn.disabled = true;
            try {
                const fd = new FormData();
                fd.append("initData", initData);
                fd.append("file", file);
                const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || "upload_failed");
                document.getElementById("adm-t-banner-image").value = data.url;
                showBannerPreview(data.url);
                toast(t("admin_action_success"), "success");
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                btn.textContent = oldText;
                btn.disabled = false;
                e.target.value = "";
            }
        });

        document.getElementById("adm-t-upload-extra-btn").addEventListener("click", () => {
            document.getElementById("adm-t-upload-extra-input").click();
        });

        document.getElementById("adm-t-upload-extra-input").addEventListener("change", async (e) => {
            const files = Array.from(e.target.files || []);
            if (!files.length) return;
            const btn = document.getElementById("adm-t-upload-extra-btn");
            const oldText = btn.textContent;
            btn.textContent = "...";
            btn.disabled = true;
            try {
                const urls = adminExtraImagesCache.slice();
                for (const file of files) {
                    const fd = new FormData();
                    fd.append("initData", initData);
                    fd.append("file", file);
                    const res = await fetch(API_BASE + "/webapp/api/admin_upload_banner", { method: "POST", body: fd });
                    const data = await res.json();
                    if (data.ok) urls.push(data.url);
                }
                adminExtraImagesCache = urls;
                document.getElementById("adm-t-banner-images").value = JSON.stringify(urls);
                renderAdminExtraImages();
                toast(t("admin_action_success"), "success");
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                btn.textContent = oldText;
                btn.disabled = false;
                e.target.value = "";
            }
        });

    }

    const VIP_PLANS = [
        { days: 7, diamond: 8, stars: 50 },
        { days: 14, diamond: 15, stars: 100 },
        { days: 30, diamond: 30, stars: 200 },
    ];

    function renderSubs(data) {
        const box = document.getElementById("subs-container");
        const vip = data.vip || { active: false, days_left: 0 };
        const diamond = data.profile.diamond || 0;
        box.innerHTML = "";
        if (vip.active) {
            const card = document.createElement("div");
            card.className = "sub-card active";
            card.innerHTML = `
                <div>
                    <div class="sub-title">💎 ${t("webapp_vip_title")}</div>
                    <div class="sub-desc">${tf("vip_active_status", { days: vip.days_left })}</div>
                </div>
                <button class="sub-cta" disabled>${t("btn_active")}</button>
            `;
            box.appendChild(card);
            return;
        }
        VIP_PLANS.forEach((plan) => {
            const canAfford = diamond >= plan.diamond;
            const card = document.createElement("div");
            card.className = "sub-card";
            card.innerHTML = `
                <div>
                    <div class="sub-title">💎 ${tf("vip_plan_days", { days: plan.days })}</div>
                    <div class="sub-desc">${t("vip_plan_desc")}</div>
                    <div class="sub-cta-row">
                        <button class="sub-cta" data-days="${plan.days}"${canAfford ? "" : " disabled"}>💎 ${plan.diamond} ${t("label_via")}</button>
                        <button class="sub-cta stars" data-days="${plan.days}">⭐️ ${plan.stars} ${t("label_via")}</button>
                    </div>
                </div>
            `;
            const [diaBtn, starBtn] = card.querySelectorAll(".sub-cta");
            diaBtn.addEventListener("click", () => buyVip(diaBtn, plan.days));
            starBtn.addEventListener("click", () => buyVipWithStars(starBtn, plan.days));
            box.appendChild(card);
        });
    }

    async function buyVip(btn, days) {
        if (btn.disabled) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/buy_vip", { days });
            profileCache.profile.diamond = res.profile.diamond;
            profileCache.vip = res.vip;
            renderUser(profileCache);
            renderSubs(profileCache);
            toast(t("toast_vip_activated"), "success");
            if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : e.message === "already_vip" ? t("toast_already_vip") : t("toast_generic_error");
            toast(msg, "error");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    async function buyVipWithStars(btn, days) {
        if (btn.disabled || !tg) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/vip_invoice", { days });
            tg.openInvoice(res.link, (status) => {
                btn.disabled = false;
                btn.textContent = oldText;
                if (status === "paid") {
                    profileCache.vip = { active: true, days_left: days };
                    renderSubs(profileCache);
                    toast(t("toast_vip_activated"), "success");
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
                }
            });
        } catch (e) {
            const msg = e.message === "already_vip" ? t("toast_already_vip") : t("toast_generic_error");
            toast(msg, "error");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    function renderStats(data) {
        document.getElementById("stat-games").textContent = fmt(data.profile.games_count);
        document.getElementById("stat-wins").textContent = fmt(data.profile.wins);
        document.getElementById("stat-losses").textContent = fmt(data.profile.losses);
    }

    /* ---------------- roles ---------------- */
    function formatRoleDesc(text) {
        const lines = String(text || "").split("\n");
        let html = "";
        lines.forEach((raw) => {
            const line = raw.trim();
            if (!line) { html += `<div class="role-gap"></div>`; return; }
            const headerMatch = line.match(/^━+\s*(.+?)\s*━+$/);
            if (headerMatch) {
                html += `<div class="role-section-head">${escapeHtml(headerMatch[1])}</div>`;
                return;
            }
            const abilityMatch = line.match(/^(\p{Emoji_Presentation}|\p{Extended_Pictographic}|[☀-➿️‍]+)\s*([^:]{1,60}):\s*(.+)$/u);
            if (abilityMatch) {
                html += `<div class="role-ability"><span class="ra-icon">${escapeHtml(abilityMatch[1])}</span><span class="ra-body"><b class="ra-name">${escapeHtml(abilityMatch[2].trim())}:</b> ${escapeHtml(abilityMatch[3].trim())}</span></div>`;
                return;
            }
            html += `<div class="role-line">${escapeHtml(line)}</div>`;
        });
        return html;
    }

    function renderRoles(data) {
        const box = document.getElementById("roles-container");
        box.innerHTML = "";
        const groups = [
            { key: "tinch", label: "Tinch aholi", badge: "TINCH AHOLI" },
            { key: "mafia", label: "Mafia", badge: "MAFIYA" },
            { key: "yakka", label: "Yakka", badge: "YAKKA" },
        ];

        groups.forEach((g) => {
            const roles = (data.roles || []).filter((r) => r.team === g.key);
            if (!roles.length) return;
            const head = document.createElement("div");
            head.className = "roles-group-head group-" + g.key;
            head.textContent = g.label;
            box.appendChild(head);
            const grid = document.createElement("div");
            grid.className = "roles-grid-modern";
            roles.forEach((r) => {
                const item = document.createElement("div");
                item.className = "role-card-modern team-" + g.key + (r.elite ? " shop-card-elite" : "");
                const { text } = splitIconLabel(r.name);
                const titleText = text || r.name;
                const imgHtml = r.image 
                    ? `<div class="role-card-avatar-wrap"><img class="role-card-avatar" src="${r.image}" alt="${escapeHtml(titleText)}" loading="lazy" onerror="this.parentElement.style.display='none'"></div>` 
                    : "";
                item.innerHTML = `
                    ${r.elite ? `<div class="shop-elite-badge">${t("label_elite")}</div>` : ""}
                    ${imgHtml}
                    <div class="role-card-info">
                        <div class="role-card-title">${escapeHtml(titleText)}</div>
                        <div class="role-card-description">${formatRoleDesc(r.description)}</div>
                        <div class="role-card-badge-wrap">
                            <span class="role-team-badge badge-${g.key}">${g.badge}</span>
                        </div>
                    </div>
                `;
                grid.appendChild(item);
            });
            box.appendChild(grid);
        });

        document.getElementById("roles-search").addEventListener("input", (e) => {
            const q = e.target.value.trim().toLowerCase();
            box.querySelectorAll(".role-card-modern").forEach((el) => {
                const name = (el.querySelector(".role-card-title")?.textContent || "").toLowerCase();
                const desc = (el.querySelector(".role-card-description")?.textContent || "").toLowerCase();
                el.style.display = (name.includes(q) || desc.includes(q)) ? "" : "none";
            });
        });
    }

    /* ---------------- para ---------------- */
    function renderPara(data) {
        const box = document.getElementById("para-container");
        const para = data.para;
        const transferPanel = document.getElementById("para-transfer-panel");
        if (!para) {
            box.innerHTML = `
                <div class="para-empty">💔 ${t("webapp_para_empty")}</div>
                <div class="geroy-buy-row">
                    <button class="sub-cta stars" id="find-random-para-btn">${t("btn_find_random_para")}</button>
                </div>
            `;
            const btn = document.getElementById("find-random-para-btn");
            btn.addEventListener("click", async () => {
                if (btn.disabled) return;
                btn.disabled = true;
                const oldText = btn.textContent;
                btn.textContent = "...";
                try {
                    const res = await api(API_BASE + "/webapp/api/find_random_para");
                    toast(tf("toast_para_request_sent", { remaining: res.remaining }), "success");
                    btn.textContent = oldText;
                } catch (e) {
                    const errMap = {
                        no_gender: t("toast_no_gender"),
                        pending_request: t("toast_pending_request"),
                        daily_limit: t("toast_daily_limit"),
                        already_has_para: t("toast_already_has_para"),
                        no_match: t("toast_no_match"),
                    };
                    toast(errMap[e.message] || t("toast_generic_error"), "error");
                    btn.textContent = oldText;
                } finally {
                    btn.disabled = false;
                }
            });
            transferPanel.style.display = "none";
            return;
        }
        transferPanel.style.display = "";
        let daysTogether = "";
        if (para.since) {
            const start = new Date(para.since);
            const diff = Math.max(0, Math.floor((Date.now() - start.getTime()) / 86400000));
            daysTogether = diff + " " + t("label_days_together");
        }
        const avatarInner = para.user_id
            ? `<img src="${API_BASE}/webapp/avatar/${para.user_id}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'),{textContent:'💞'}))">`
            : "💞";
        box.innerHTML = `
            <div class="para-card">
                <div class="para-avatar">${avatarInner}</div>
                <div class="para-info">
                    <div class="para-name">${escapeHtml(para.full_name || t("label_unknown"))}</div>
                    ${para.username ? `<span class="para-username">@${escapeHtml(para.username)}</span>` : ""}
                    <span class="para-badge">💑 ${t("webapp_para_partner")}</span>
                </div>
            </div>
            <div class="para-bio">${para.bio ? escapeHtml(para.bio) : t("webapp_para_no_bio")}</div>
            <div class="geroy-stats-grid para-stats-grid">
                <div class="geroy-stat"><b>${escapeHtml(para.since || "—")}</b><span>${t("webapp_para_since")}</span></div>
                <div class="geroy-stat"><b>${daysTogether || "—"}</b><span>${t("webapp_para_days_together")}</span></div>
            </div>
        `;
    }

    /* ---------------- protections ---------------- */
    function renderProtections(data) {
        const box = document.getElementById("protections-container");
        box.innerHTML = "";
        (data.protections || []).forEach((p) => {
            const row = document.createElement("div");
            row.className = "protection-row";
            row.innerHTML = `
                <span class="prot-label">${escapeHtml(p.label)}</span>
                <span class="toggle-switch${p.on ? " on" : ""}"></span>
            `;
            const sw = row.querySelector(".toggle-switch");
            sw.addEventListener("click", () => toggleProtection(p.field, sw));
            box.appendChild(row);
        });
    }

    function renderActiveRoleToggles(data) {
        const panel = document.getElementById("active-role-toggle-panel");
        const box = document.getElementById("active-role-toggle-container");
        box.innerHTML = "";
        const owned = data.owned_active_roles || [];
        if (!owned.length) { panel.style.display = "none"; return; }
        panel.style.display = "";
        owned.forEach((r) => {
            const row = document.createElement("div");
            row.className = "protection-row";
            row.innerHTML = `
                <span class="prot-label">${escapeHtml(r.name)}</span>
                <span class="toggle-switch${r.is_active ? " on" : ""}"></span>
            `;
            const sw = row.querySelector(".toggle-switch");
            sw.addEventListener("click", () => toggleActiveRole(r.id, sw));
            box.appendChild(row);
        });
    }

    async function toggleActiveRole(id, sw) {
        sw.style.pointerEvents = "none";
        try {
            const res = await api(API_BASE + "/webapp/api/toggle_active_role", { id: id });
            sw.classList.toggle("on", res.is_active);
            if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        } finally {
            sw.style.pointerEvents = "";
        }
    }

    async function toggleProtection(field, sw) {
        sw.style.pointerEvents = "none";
        try {
            const res = await api(API_BASE + "/webapp/api/toggle_protection", { field: field });
            sw.classList.toggle("on", res.on);
            if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        } finally {
            sw.style.pointerEvents = "";
        }
    }

    /* ---------------- inventory ---------------- */
    const INVENTORY_ITEM_ICONS = {
        himoya: "🛡", hujjat: "📁", qotildan_himoya: "🔪",
        osishdan_himoya: "⚖️", miltiq: "😀", doridan_himoya: "➕",
        maska: "🎭", slip_himoya: "🪤", geroy_himoya: "🔰",
        qora_materiya: "🌑", virus: "🦠",
    };
    const INVENTORY_ITEM_LABEL_KEYS = {
        himoya: "item_himoya", hujjat: "item_hujjat", qotildan_himoya: "item_qotildan_himoya",
        osishdan_himoya: "item_osishdan_himoya", miltiq: "item_miltiq", doridan_himoya: "item_doridan_himoya",
        maska: "item_maska", slip_himoya: "item_slip_himoya", geroy_himoya: "item_geroy_himoya",
        qora_materiya: "item_qora_materiya", virus: "item_virus",
    };
    const INVENTORY_ITEM_DESC_KEYS = {
        himoya: "item_desc_himoya", hujjat: "item_desc_hujjat", qotildan_himoya: "item_desc_qotildan_himoya",
        osishdan_himoya: "item_desc_osishdan_himoya", miltiq: "item_desc_miltiq", doridan_himoya: "item_desc_doridan_himoya",
        maska: "item_desc_maska", slip_himoya: "item_desc_slip_himoya", geroy_himoya: "item_desc_geroy_himoya",
        qora_materiya: "item_desc_qora_materiya", virus: "item_desc_virus",
    };

    function renderInventory(data) {
        const box = document.getElementById("inventory-container");
        box.innerHTML = "";
        const hasRoles = data.active_roles && data.active_roles.length > 0;
        const ownedItems = Object.keys(INVENTORY_ITEM_ICONS).filter((f) => (data.profile[f] || 0) > 0);

        if (!hasRoles && !ownedItems.length) {
            box.innerHTML = `<span class="inv-empty">${t("webapp_inventory_empty")}</span>`;
            return;
        }

        if (hasRoles) {
            const head = document.createElement("div");
            head.className = "roles-group-head";
            head.textContent = t("webapp_nav_active_shop");
            box.appendChild(head);
            const grid = document.createElement("div");
            grid.className = "roles-grid";
            data.active_roles.forEach((role) => {
                const item = document.createElement("div");
                item.className = "role-item";
                item.innerHTML = `<div class="role-name"><i class="fa-solid fa-star"></i> ${escapeHtml(role.name)}</div><div class="role-desc">${formatRoleDesc(role.description)}</div>`;
                item.addEventListener("click", () => item.classList.toggle("open"));
                grid.appendChild(item);
            });
            box.appendChild(grid);
        }

        if (ownedItems.length) {
            const head = document.createElement("div");
            head.className = "roles-group-head";
            head.textContent = t("webapp_roles_group_items");
            box.appendChild(head);
            const grid = document.createElement("div");
            grid.className = "roles-grid";
            ownedItems.forEach((field) => {
                const card = document.createElement("div");
                card.className = "role-item";
                card.innerHTML = `<div class="role-name">${INVENTORY_ITEM_ICONS[field]} ${escapeHtml(t(INVENTORY_ITEM_LABEL_KEYS[field]))} — <b>${data.profile[field]}</b></div><div class="role-desc">${formatRoleDesc(t(INVENTORY_ITEM_DESC_KEYS[field]))}</div>`;
                card.addEventListener("click", () => card.classList.toggle("open"));
                grid.appendChild(card);
            });
            box.appendChild(grid);
        }
    }

    /* ---------------- shop ---------------- */
    function splitIconLabel(label) {
        if (!label) return { icon: "🛒", text: "" };
        let clean = String(label).replace(/<tg-emoji[^>]*>(.*?)<\/tg-emoji>/gi, "$1").trim();
        const m = /^(\S+)\s+(.*)$/.exec(clean);
        return m ? { icon: m[1], text: m[2] } : { icon: "🛒", text: clean };
    }


    function renderShop(data) {
        const box = document.getElementById("shop-container");
        box.innerHTML = "";
        data.shop_items.forEach((item) => {
            const card = document.createElement("div");
            card.className = "shop-card" + (item.elite ? " shop-card-elite" : "");
            const currencyIcon = item.currency === "diamond" ? "💎" : "$";
            const { icon, text } = splitIconLabel(item.label);
            card.innerHTML = `
                ${item.elite ? `<div class="shop-elite-badge">${t("label_elite")}</div>` : ""}
                <div class="shop-card-banner">${icon}</div>
                <div class="shop-label">${escapeHtml(text)}</div>
                <div class="shop-price">${item.price} ${currencyIcon}</div>
                <button type="button"><i class="fa-solid fa-cart-shopping"></i> ${t("btn_buy")}</button>
            `;
            const btn = card.querySelector("button");
            btn.addEventListener("click", () => buyItem(item.key, btn));
            box.appendChild(card);
        });
        if ((data.active_role_shop || []).length) {
            const head = document.createElement("div");
            head.className = "roles-group-head";
            head.style.gridColumn = "1 / -1";
            head.textContent = t("webapp_nav_active_shop");
            box.appendChild(head);
        }
        (data.active_role_shop || []).forEach((item) => {
            const card = document.createElement("div");
            card.className = "shop-card" + (item.elite ? " shop-card-elite" : "");
            const currencyIcon = item.currency === "diamond" ? "💎" : "$";
            const { icon, text } = splitIconLabel(item.label);
            card.innerHTML = `
                ${item.elite ? `<div class="shop-elite-badge">${t("label_elite")}</div>` : ""}
                <div class="shop-card-banner">${item.image ? `<img class="shop-card-role-poster" src="${item.image}" alt="" onerror="this.replaceWith('${icon}')">` : icon}</div>
                <div class="shop-label">${escapeHtml(text)}</div>
                <div class="shop-price">${item.price} ${currencyIcon}</div>
                <button type="button"><i class="fa-solid fa-cart-shopping"></i> ${t("btn_buy")}</button>
            `;
            const btn = card.querySelector("button");
            btn.addEventListener("click", () => buyActiveRole(item.role, btn));
            box.appendChild(card);
        });
    }

    async function buyItem(itemKey, btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/buy", { item_key: itemKey });
            Object.assign(profileCache.profile, res.profile);
            renderUser(profileCache);
            toast(t("toast_purchase_success"), "success");
            if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : t("toast_generic_error");
            toast(msg, "error");
            if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
        } finally {
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    async function buyActiveRole(role, btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/buy_active_role", { role: role });
            Object.assign(profileCache.profile, res.profile);
            profileCache.active_roles = res.active_roles;
            renderUser(profileCache);
            renderInventory(profileCache);
            toast(t("toast_active_role_bought"), "success");
            if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : t("toast_generic_error");
            toast(msg, "error");
        } finally {
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    /* ---------------- leaderboard ---------------- */
    let leaderboardLoaded = false;
    const LB_ICONS = { wins: "🏆", dollar: "💵 $", diamond: "💎", games_count: "🎮" };

    function setupLeaderboardTabs() {
        document.querySelectorAll("#lb-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#lb-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                loadLeaderboard(btn.dataset.cat);
            });
        });
    }

    async function loadLeaderboard(category) {
        const box = document.getElementById("lb-container");
        box.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/leaderboard", { category: category });
            leaderboardLoaded = true;
            if (!res.leaderboard.length) {
                box.innerHTML = '<div class="lb-empty">Hozircha ma\'lumot yo\'q</div>';
                return;
            }
            const icon = LB_ICONS[category] || "";
            box.innerHTML = "";

            const top3 = res.leaderboard.filter((r) => r.rank <= 3);
            const rest = res.leaderboard.filter((r) => r.rank > 3);

            if (top3.length) {
                const podium = document.createElement("div");
                podium.className = "lb-podium";
                const order = [2, 1, 3];
                podium.innerHTML = order.map((rank) => {
                    const row = top3.find((r) => r.rank === rank);
                    if (!row) return `<div class="lb-podium-spot lb-podium-empty"></div>`;
                    const medal = rank === 1 ? "🥇" : rank === 2 ? "🥈" : "🥉";
                    const crown = rank === 1 ? `<div class="lb-crown">👑</div>` : "";
                    return `
                        <div class="lb-podium-spot lb-podium-${rank}${row.is_me ? " me" : ""}">
                            ${crown}
                            <div class="lb-podium-avatar">${row.user_id ? `<img src="${API_BASE}/webapp/avatar/${row.user_id}" alt="" onerror="this.remove();">` : ""}</div>
                            <div class="lb-podium-medal">${medal}</div>
                            <div class="lb-podium-name">${escapeHtml(row.full_name)}</div>
                            <div class="lb-podium-value">${fmt(row[category])} ${icon}</div>
                            <div class="lb-podium-bar"></div>
                        </div>
                    `;
                }).join("");
                box.appendChild(podium);
            }

            rest.forEach((row) => {
                const el = document.createElement("div");
                el.className = "lb-row" + (row.is_me ? " me" : "");
                el.innerHTML = `
                    <div class="lb-rank">${row.rank}</div>
                    <div class="lb-avatar">${row.user_id ? `<img src="${API_BASE}/webapp/avatar/${row.user_id}" alt="" onerror="this.remove();">` : ""}</div>
                    <div class="lb-name">${escapeHtml(row.full_name)}</div>
                    <div class="lb-value">${fmt(row[category])} ${icon}</div>
                `;
                box.appendChild(el);
            });
        } catch (e) {
            box.innerHTML = '<div class="lb-empty">' + t("toast_load_error") + '</div>';
        }
    }

    /* ---------------- history ---------------- */
    let historyLoaded = false;

    /* ---------------- support chat (foydalanuvchi) ---------------- */
    let supportChatTimer = null;
    let supportChatLastId = 0;

    function renderSupportMessages(messages, append) {
        const box = document.getElementById("support-chat-messages");
        if (!append) box.innerHTML = "";
        if (!messages.length && !append && supportChatLastId === 0) {
            box.innerHTML = `<div class="support-chat-empty">${escapeHtml(t("webapp_support_empty_hint"))}</div>`;
            return;
        }
        if (messages.length) {
            const emptyHint = box.querySelector(".support-chat-empty");
            if (emptyHint) emptyHint.remove();
        }
        messages.forEach((m) => {
            if (m.id <= supportChatLastId) return;
            supportChatLastId = Math.max(supportChatLastId, m.id);
            const el = document.createElement("div");
            el.className = "support-msg " + (m.is_from_admin ? "theirs" : "mine");
            const img = m.image_url ? `<img class="support-msg-img" src="${escapeHtml(m.image_url)}" alt="" onclick="window.open(this.src,'_blank')">` : "";
            const ticks = !m.is_from_admin ? `<i class="fa-solid ${m.is_read ? "fa-check-double read" : "fa-check"} support-msg-ticks${m.is_read ? " read" : ""}"></i>` : "";
            el.innerHTML = `${img}${m.text ? escapeHtml(m.text) : ""}<span class="support-msg-time">${escapeHtml((m.date || "").split(" ").pop())}${ticks}</span>`;
            box.appendChild(el);
            if (m.is_from_admin) updateSupportChatHeader(m.admin_user_id, m.admin_name);
        });
        box.scrollTop = box.scrollHeight;
    }

    function updateSupportChatHeader(adminUserId, adminName) {
        const header = document.getElementById("support-chat-header");
        const messagesBox = document.getElementById("support-chat-messages");
        if (!adminUserId) { header.style.display = "none"; return; }
        header.style.display = "";
        header.innerHTML = `
            <img class="admin-support-customer-avatar" src="${API_BASE}/webapp/avatar/${adminUserId}" alt="" onerror="this.style.display='none';">
            <div class="admin-support-customer-info">
                <div class="admin-support-customer-name">🎧 ${escapeHtml(adminName || "Operator")}</div>
            </div>
        `;
        if (messagesBox) setChatWallpaper(messagesBox, tgUser && tgUser.id);
    }

    async function loadSupportChatHistory() {
        try {
            const res = await api(API_BASE + "/webapp/api/support_history");
            supportChatLastId = 0;
            renderSupportMessages(res.messages || [], false);
            refreshSupportFabBadge();
        } catch (e) { /* jim */ }
    }

    async function pollSupportChat() {
        try {
            const res = await api(API_BASE + "/webapp/api/support_history");
            renderSupportMessages((res.messages || []).filter((m) => m.id > supportChatLastId), true);
        } catch (e) { /* jim */ }
    }

    function startSupportChatPolling() {
        loadSupportChatHistory();
        if (supportChatTimer) clearInterval(supportChatTimer);
        supportChatTimer = setInterval(pollSupportChat, 4000);
    }
    function stopSupportChatPolling() {
        if (supportChatTimer) clearInterval(supportChatTimer);
        supportChatTimer = null;
    }

    function setupSupportChat() {
        const input = document.getElementById("support-chat-input");
        const sendBtn = document.getElementById("support-chat-send-btn");
        const photoBtn = document.getElementById("support-chat-photo-btn");
        const photoInput = document.getElementById("support-chat-photo-input");
        const clearBtn = document.getElementById("support-chat-clear-btn");

        const messagesBox = document.getElementById("support-chat-messages");
        messagesBox.style.backgroundSize = "cover";
        messagesBox.style.backgroundPosition = "center";
        messagesBox.style.backgroundRepeat = "no-repeat";
        setChatWallpaper(messagesBox, tgUser && tgUser.id);

        clearBtn.addEventListener("click", async () => {
            if (!(await tgConfirm(t("webapp_support_clear_confirm")))) return;
            try {
                await api(API_BASE + "/webapp/api/support_clear_chat", {});
                supportChatLastId = 0;
                renderSupportMessages([], false);
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        });
        const send = async (imageUrl) => {
            const text = input.value.trim();
            if (!text && !imageUrl) return;
            input.value = "";
            input.style.height = "auto";
            try {
                const res = await api(API_BASE + "/webapp/api/support_send", { text, image_url: imageUrl || "" });
                renderSupportMessages([res.message], true);
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            }
        };
        sendBtn.addEventListener("click", () => send());
        input.addEventListener("input", () => {
            input.style.height = "auto";
            input.style.height = input.scrollHeight + "px";
        });
        photoBtn.addEventListener("click", () => photoInput.click());
        photoInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            photoBtn.classList.add("uploading");
            try {
                const url = await uploadSupportImage(file);
                await send(url);
            } catch (err) {
                toast(t("toast_generic_error"), "error");
            } finally {
                photoBtn.classList.remove("uploading");
                e.target.value = "";
            }
        });
    }


    async function loadHistory() {
        const box = document.getElementById("history-container");
        box.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/history");
            historyLoaded = true;
            if (!res.history.length) {
                box.innerHTML = '<div class="hist-empty">Hali o\'tkazma yo\'q</div>';
                return;
            }
            box.innerHTML = "";
            const typeIcon = { dollar: "💵", diamond: "💎" };
            const reasonMap = { admin: t("webapp_history_reason_admin"), webapp: t("webapp_history_reason_webapp") };
            res.history.forEach((row) => {
                const isIn = row.direction === "in";
                const el = document.createElement("div");
                el.className = "hist-row";
                const idLine = [
                    row.counterparty_username ? "@" + row.counterparty_username : null,
                    row.counterparty_user_id ? "ID: " + row.counterparty_user_id : null,
                ].filter(Boolean).join(" · ");
                const reason = row.caption ? (reasonMap[row.caption] || row.caption) : "";
                const initial = (row.counterparty || "?").trim().charAt(0).toUpperCase() || "?";
                const avatarHtml = row.counterparty_user_id
                    ? `<img src="${API_BASE}/webapp/avatar/${row.counterparty_user_id}" alt="" onerror="var p=this.parentElement; this.remove(); if(p) p.textContent='${escapeHtml(initial)}';">`
                    : escapeHtml(initial);
                el.innerHTML = `
                    <div class="hist-avatar">${avatarHtml}</div>
                    <div class="hist-info">
                        <div class="hist-role">
                            <span class="hist-dir ${isIn ? "win" : "lose"}"><i class="fa-solid ${isIn ? "fa-arrow-down" : "fa-arrow-up"}"></i></span>
                            ${isIn ? t("webapp_history_received") : t("webapp_history_sent")} — ${escapeHtml(row.counterparty)}
                        </div>
                        ${idLine ? `<div class="hist-id">${escapeHtml(idLine)}</div>` : ""}
                        <div class="hist-meta">${escapeHtml(row.date)}${reason ? " · " + escapeHtml(reason) : ""}</div>
                    </div>
                    <div class="hist-badge ${isIn ? "win" : "lose"}">${isIn ? "+" : "-"}${fmt(row.amount)} ${typeIcon[row.type] || ""}</div>
                `;
                box.appendChild(el);
            });
        } catch (e) {
            box.innerHTML = '<div class="hist-empty">' + t("toast_load_error") + '</div>';
        }
    }

    /* ---------------- group settings ---------------- */
    let groupsLoaded = false;

    async function loadGroups() {
        try {
            const res = await api(API_BASE + "/webapp/api/my_groups");
            groupsLoaded = true;
            const sel = document.getElementById("group-select");
            sel.innerHTML = "";
            if (!res.groups.length) {
                sel.innerHTML = '<option>' + t("groups_not_found") + '</option>';
                return;
            }
            res.groups.forEach((g) => {
                const opt = document.createElement("option");
                opt.value = g.chat_id;
                opt.textContent = g.title;
                sel.appendChild(opt);
            });
            sel.addEventListener("change", () => loadGroupSettings(sel.value));
            currentGroupChatId = res.groups[0].chat_id;
            loadGroupSettings(currentGroupChatId);
        } catch (e) {
            toast(t("toast_groups_load_error"), "error");
        }
    }

    async function loadGroupSettings(chatId) {
        currentGroupChatId = chatId;
        const weaponsBox = document.getElementById("group-weapons-container");
        const moreBox = document.getElementById("group-more-container");
        weaponsBox.innerHTML = '<div class="skeleton-list"></div>';
        moreBox.innerHTML = '<div class="skeleton-list"></div>';
        try {
            const res = await api(API_BASE + "/webapp/api/group_settings", { chat_id: Number(chatId) });
            weaponsBox.innerHTML = "";
            res.weapons.forEach((w) => {
                const row = document.createElement("div");
                row.className = "toggle-row";
                row.innerHTML = `<span class="toggle-label">${escapeHtml(w.label)}</span><span class="toggle-switch${w.on ? " on" : ""}"></span>`;
                const sw = row.querySelector(".toggle-switch");
                sw.addEventListener("click", () => toggleGroupField("weapons", w.field, sw));
                weaponsBox.appendChild(row);
            });
            moreBox.innerHTML = "";
            res.more.forEach((m) => {
                const row = document.createElement("div");
                row.className = "toggle-row";
                row.innerHTML = `<span class="toggle-label">${escapeHtml(m.label)}</span><span class="toggle-switch${m.on ? " on" : ""}"></span>`;
                const sw = row.querySelector(".toggle-switch");
                sw.addEventListener("click", () => toggleGroupField("more", m.field, sw));
                moreBox.appendChild(row);
            });
        } catch (e) {
            weaponsBox.innerHTML = '<div class="hist-empty">' + t("toast_load_error") + '</div>';
            moreBox.innerHTML = "";
        }
    }

    async function toggleGroupField(groupKey, field, sw) {
        sw.style.pointerEvents = "none";
        try {
            const res = await api(API_BASE + "/webapp/api/group_toggle", { chat_id: Number(currentGroupChatId), group: groupKey, field: field });
            sw.classList.toggle("on", res.on);
            if (tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        } finally {
            sw.style.pointerEvents = "";
        }
    }

    /* ---------------- geroy ---------------- */
    const ITEM_ICONS = {
        himoya: "🛡", hujjat: "📁", qotildan_himoya: "🔪",
        osishdan_himoya: "⚖️", miltiq: "😀", doridan_himoya: "➕",
        maska: "🎭", slip_himoya: "🪤", geroy_himoya: "🔰",
    };
    const ITEM_LABEL_KEYS = {
        himoya: "item_himoya", hujjat: "item_hujjat", qotildan_himoya: "item_qotildan_himoya",
        osishdan_himoya: "item_osishdan_himoya", miltiq: "item_miltiq", doridan_himoya: "item_doridan_himoya",
        maska: "item_maska", slip_himoya: "item_slip_himoya", geroy_himoya: "item_geroy_himoya",
    };
    function getItemLabels() {
        const out = {};
        Object.keys(ITEM_ICONS).forEach((field) => {
            out[field] = ITEM_ICONS[field] + " " + t(ITEM_LABEL_KEYS[field]);
        });
        return out;
    }

    async function loadGeroy() {
        const box = document.getElementById("geroy-container");
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_status");
            geroyLoaded = true;
            renderGeroy(res);
        } catch (e) {
            box.innerHTML = '<div class="hist-empty">' + t("toast_load_error") + '</div>';
        }
    }

    function renderGeroy(res) {
        const box = document.getElementById("geroy-container");
        if (!res.has_geroy) {
            box.innerHTML = `
                <div class="panel geroy-empty-card">
                    <img class="geroy-empty-img" src="${API_BASE}/webapp/assets/geroy-avatar.svg" alt="Hero">
                    <div class="sub-title">${t("webapp_geroy_no_hero")}</div>
                    <div class="sub-desc">Shaxsiy Geroy sotib olib, jangda ishlatishingiz mumkin</div>
                    <div class="geroy-buy-row">
                        <button class="sub-cta" id="geroy-buy-diamond">💎 ${res.diamond_price} ${t("label_via")}</button>
                        <button class="sub-cta stars" id="geroy-buy-stars">⭐️ ${res.stars_price} ${t("label_via")}</button>
                    </div>
                </div>
            `;
            box.querySelector("#geroy-buy-diamond").addEventListener("click", (e) => buyGeroy(e.target));
            box.querySelector("#geroy-buy-stars").addEventListener("click", (e) => buyGeroyWithStars(e.target));
            return;
        }
        const g = res.geroy;
        box.innerHTML = `
            <div class="panel geroy-card">
                <div class="geroy-header">
                    <div class="geroy-avatar geroy-avatar-editable" id="geroy-avatar-upload">
                        <img src="${g.photo_url || API_BASE + "/webapp/assets/geroy-avatar.svg"}" alt="Hero">
                        <span class="geroy-avatar-edit-badge">📷</span>
                    </div>
                    <input type="file" id="geroy-photo-input" accept="image/*" style="display:none;">
                    <div>
                        <h3 class="geroy-header-name">${escapeHtml(g.name)}</h3>
                        <span class="geroy-header-level">${tf("geroy_level", { level: g.level })}</span>
                    </div>
                </div>
                <div class="geroy-stats-grid">
                    <div class="geroy-stat"><b>${g.patron}/10</b><span>${t("geroy_charge")}</span></div>
                    <div class="geroy-stat"><b>${g.himoya}/${g.max_himoya}</b><span>${t("item_himoya")}</span></div>
                    <div class="geroy-stat"><b>${fmt(g.ball)}</b><span>${t("geroy_ball_label")}</span></div>
                    <div class="geroy-stat"><b>${fmt(g.next_level_ball)}</b><span>${t("geroy_next_level")}</span></div>
                </div>
                <div class="geroy-action-row">
                    <button class="geroy-action-btn" id="geroy-reload"><span class="gab-icon">🩸</span><span class="gab-label">${t("webapp_geroy_reload")}</span><span class="gab-price">${fmt(g.reload_price)} $</span></button>
                    <button class="geroy-action-btn" id="geroy-shield"><span class="gab-icon">🛡</span><span class="gab-label">${t("item_himoya")}</span><span class="gab-price">${fmt(g.shield_price)} $</span></button>
                    <button class="geroy-action-btn" id="geroy-ball"><span class="gab-icon">➕</span><span class="gab-label">${t("geroy_ball_action")}</span><span class="gab-price">${g.ball_price} 💎</span></button>
                </div>
                <div class="geroy-name-input">
                    <input type="text" id="geroy-name-input" placeholder="${tf("geroy_name_placeholder", { price: fmt(g.name_price) })}" maxlength="60">
                    <button class="sub-cta" id="geroy-rename">${t("btn_change")}</button>
                </div>
            </div>
        `;
        box.querySelector("#geroy-reload").addEventListener("click", (e) => geroyAction("reload", e.target));
        box.querySelector("#geroy-shield").addEventListener("click", (e) => geroyAction("shield", e.target));
        box.querySelector("#geroy-ball").addEventListener("click", (e) => geroyAction("ball", e.target));
        box.querySelector("#geroy-rename").addEventListener("click", (e) => {
            const name = document.getElementById("geroy-name-input").value;
            geroyAction("rename", e.target, { name });
        });

        const photoInput = document.getElementById("geroy-photo-input");
        box.querySelector("#geroy-avatar-upload").addEventListener("click", () => photoInput.click());
        photoInput.addEventListener("change", async () => {
            const file = photoInput.files[0];
            if (!file) return;
            const avatarBox = document.getElementById("geroy-avatar-upload");
            avatarBox.classList.add("uploading");
            try {
                const photoUrl = await uploadGeroyPhoto(file);
                const res = await api(API_BASE + "/webapp/api/geroy_action", { action: "photo", photo_url: photoUrl });
                toast(t("toast_action_done"), "success");
                renderGeroy({ ok: true, has_geroy: true, geroy: res.geroy });
            } catch (e) {
                toast(t("toast_generic_error"), "error");
                avatarBox.classList.remove("uploading");
            }
        });
    }

    async function uploadGeroyPhoto(file) {
        const fd = new FormData();
        fd.append("initData", initData);
        fd.append("file", file);
        const res = await fetch(API_BASE + "/webapp/api/support_upload_image", { method: "POST", body: fd });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || "upload_failed");
        return data.url;
    }

    async function buyGeroy(btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/buy_geroy");
            profileCache.profile.diamond = res.profile.diamond;
            renderUser(profileCache);
            toast(t("toast_geroy_bought"), "success");
            loadGeroy();
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : t("toast_generic_error");
            toast(msg, "error");
            btn.disabled = false;
        }
    }

    async function buyGeroyWithStars(btn) {
        if (btn.disabled || !tg) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_invoice");
            tg.openInvoice(res.link, (status) => {
                btn.disabled = false;
                if (status === "paid") {
                    toast(t("toast_geroy_bought"), "success");
                    loadGeroy();
                }
            });
        } catch (e) {
            toast(t("toast_generic_error"), "error");
            btn.disabled = false;
        }
    }

    async function geroyAction(action, btn, extra) {
        if (btn.disabled) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_action", Object.assign({ action }, extra || {}));
            Object.assign(profileCache.profile, res.profile);
            renderUser(profileCache);
            toast(t("toast_action_done"), "success");
            renderGeroy({ ok: true, has_geroy: true, geroy: res.geroy });
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : e.message === "already_max" ? t("toast_already_max") : t("toast_generic_error");
            toast(msg, "error");
        } finally {
            btn.disabled = false;
        }
    }

    /* ---------------- geroy market ---------------- */
    async function confirmAction(msgKey) {
        const msg = t(msgKey);
        return (tg && tg.showConfirm)
            ? await new Promise((resolve) => tg.showConfirm(msg, resolve))
            : window.confirm(msg);
    }

    function initGeroyMarket() {
        document.querySelectorAll('#geroy-market-tabs [data-gm-tab]').forEach((btn) => {
            btn.addEventListener("click", () => {
                const tab = btn.dataset.gmTab;
                document.querySelectorAll('#geroy-market-tabs [data-gm-tab]').forEach((b) => b.classList.toggle("active", b === btn));
                document.getElementById("gm-panel-browse").style.display = tab === "browse" ? "" : "none";
                document.getElementById("gm-panel-mine").style.display = tab === "mine" ? "" : "none";
                document.getElementById("gm-panel-admin").style.display = tab === "admin" ? "" : "none";
                if (tab === "browse") loadGeroyMarketBrowse();
                if (tab === "mine") loadGeroyMarketMine();
                if (tab === "admin") loadGeroyMarketAdminList();
            });
        });
        document.getElementById("gm-admin-create-btn").addEventListener("click", createAdminGeroyListing);
        loadGeroyMarketBrowse();
    }

    function geroyMarketCardHtml(listing) {
        const g = listing.geroy;
        const sellerLabel = listing.is_own ? t("geroy_market_own_label") : escapeHtml(listing.seller_name);
        return `
            <div class="panel gm-card gm-card-compact">
                <div class="gm-card-top">
                    <div class="geroy-avatar gm-avatar-lg"><img src="${g.photo_url || API_BASE + "/webapp/assets/geroy-avatar.svg"}" alt="Hero"></div>
                    <div class="gm-card-info">
                        <div class="gm-card-name-row">
                            <h3 class="geroy-header-name">${escapeHtml(g.name)}</h3>
                            <span class="geroy-header-level">${tf("geroy_level", { level: g.level })}</span>
                        </div>
                        <div class="gm-chip-row">
                            <span class="gm-chip">🩸 ${g.patron}/10</span>
                            <span class="gm-chip">🛡 ${g.himoya}/${g.max_himoya}</span>
                            <span class="gm-chip">⭐ ${fmt(g.ball)}</span>
                        </div>
                        <div class="gm-seller-line">${t("geroy_market_seller_label")}: <b>${sellerLabel}</b></div>
                    </div>
                </div>
                <div class="gm-buy-row">
                    <span class="gm-price">💎 ${fmt(listing.price)}</span>
                    ${listing.is_own
                        ? ""
                        : `<button class="sub-cta" data-listing-id="${listing.id}">${t("geroy_market_buy_btn")}</button>`}
                </div>
            </div>
        `;
    }

    async function loadGeroyMarketBrowse(page) {
        geroyMarketPage = page || 1;
        const box = document.getElementById("geroy-market-browse-container");
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_market/list", { page: geroyMarketPage });
            geroyMarketHasMore = !!res.has_more;
            if (!res.listings.length) {
                box.innerHTML = `<div class="hist-empty">${t("geroy_market_empty")}</div>`;
                return;
            }
            box.innerHTML = res.listings.map(geroyMarketCardHtml).join("") +
                (geroyMarketHasMore ? `<button class="sub-cta" id="gm-load-more">➕</button>` : "");
            box.querySelectorAll("[data-listing-id]").forEach((btn) => {
                btn.addEventListener("click", () => buyGeroyListing(parseInt(btn.dataset.listingId, 10), btn));
            });
            const moreBtn = document.getElementById("gm-load-more");
            if (moreBtn) moreBtn.addEventListener("click", () => loadGeroyMarketBrowse(geroyMarketPage + 1));
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_load_error")}</div>`;
        }
    }

    async function buyGeroyListing(listingId, btn) {
        if (btn.disabled) return;
        if (!(await confirmAction("geroy_market_buy_confirm"))) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_market/buy", { listing_id: listingId });
            profileCache.profile.diamond = res.profile.diamond;
            renderUser(profileCache);
            toast(t("toast_geroy_market_bought"), "success");
            loadGeroyMarketBrowse(geroyMarketPage);
        } catch (e) {
            toast(e.message || t("toast_generic_error"), "error");
            btn.disabled = false;
        }
    }

    function geroyMarketMineListingHtml(listing) {
        const statusKey = { active: "geroy_market_status_active", sold: "geroy_market_status_sold", cancelled: "geroy_market_status_cancelled" }[listing.status] || listing.status;
        return `<div class="admin-tlist-row"><span class="atl-info">${escapeHtml(listing.geroy.name)} — 💎 ${fmt(listing.price)}<span class="atl-meta">${t(statusKey)}</span></span></div>`;
    }

    async function loadGeroyMarketMine() {
        const box = document.getElementById("geroy-market-mine-container");
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_market/my");
            const active = res.listings.find((l) => l.status === "active");
            let html = "";
            if (active) {
                html += `
                    <div class="panel gm-card gm-card-compact">
                        <div class="panel-head"><h3>${t("geroy_market_active_listing_title")}</h3></div>
                        <div class="gm-card-top">
                            <div class="geroy-avatar gm-avatar-lg"><img src="${active.geroy.photo_url || API_BASE + "/webapp/assets/geroy-avatar.svg"}" alt="Hero"></div>
                            <div class="gm-card-info">
                                <div class="gm-card-name-row"><h3 class="geroy-header-name">${escapeHtml(active.geroy.name)}</h3></div>
                                <span class="gm-price">💎 ${fmt(active.price)}</span>
                            </div>
                        </div>
                        <div class="admin-action-row">
                            <input type="number" id="gm-mine-new-price" data-i18n-placeholder="geroy_market_price_placeholder" placeholder="${t("geroy_market_price_placeholder")}" min="20">
                            <button class="sub-cta" id="gm-mine-update-price-btn">${t("geroy_market_update_price_btn")}</button>
                        </div>
                        <div class="admin-action-row">
                            <button class="sub-cta danger" id="gm-mine-cancel-btn">${t("geroy_market_cancel_btn_webapp")}</button>
                        </div>
                    </div>
                `;
            } else if (res.has_geroy && res.geroy) {
                html += `
                    <div class="panel gm-card">
                        <div class="gm-seller-row"><span>${escapeHtml(res.geroy.name)}</span></div>
                        <div class="admin-action-row">
                            <input type="number" id="gm-mine-price" data-i18n-placeholder="geroy_market_price_placeholder" placeholder="${t("geroy_market_price_placeholder")}" min="20">
                            <button class="sub-cta" id="gm-mine-list-btn">${t("geroy_market_list_btn")}</button>
                        </div>
                    </div>
                `;
            } else {
                html += `<div class="hist-empty">${t("geroy_market_no_hero")}</div>`;
            }

            const history = res.listings.filter((l) => l.status !== "active");
            if (history.length) {
                html += `<div class="panel" style="margin-top:16px;"><div class="panel-head"><h3>${t("geroy_market_history_title")}</h3></div><div>${history.map(geroyMarketMineListingHtml).join("")}</div></div>`;
            }
            box.innerHTML = html;

            const listBtn = document.getElementById("gm-mine-list-btn");
            if (listBtn) listBtn.addEventListener("click", () => createGeroyListing(document.getElementById("gm-mine-price").value, listBtn));
            const updateBtn = document.getElementById("gm-mine-update-price-btn");
            if (updateBtn) updateBtn.addEventListener("click", () => updateGeroyListingPrice(active.id, document.getElementById("gm-mine-new-price").value, updateBtn));
            const cancelBtn = document.getElementById("gm-mine-cancel-btn");
            if (cancelBtn) cancelBtn.addEventListener("click", () => cancelGeroyListing(active.id, cancelBtn));
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_load_error")}</div>`;
        }
    }

    async function createGeroyListing(priceStr, btn) {
        if (btn.disabled) return;
        const price = parseInt(priceStr, 10);
        if (!price || price < 20) { toast(t("toast_geroy_market_bad_price"), "error"); return; }
        btn.disabled = true;
        try {
            await api(API_BASE + "/webapp/api/geroy_market/create", { price });
            toast(t("toast_geroy_market_listed"), "success");
            loadGeroyMarketMine();
        } catch (e) {
            const map = { already_in_market: "toast_geroy_market_already_listed", no_geroy: "toast_geroy_market_no_hero", bad_price: "toast_geroy_market_bad_price" };
            toast(t(map[e.message] || "toast_generic_error"), "error");
            btn.disabled = false;
        }
    }

    async function cancelGeroyListing(listingId, btn) {
        if (btn.disabled) return;
        if (!(await confirmAction("geroy_market_cancel_confirm"))) return;
        btn.disabled = true;
        try {
            await api(API_BASE + "/webapp/api/geroy_market/cancel", { listing_id: listingId });
            toast(t("toast_geroy_market_cancelled"), "success");
            loadGeroyMarketMine();
        } catch (e) {
            toast(t("toast_generic_error"), "error");
            btn.disabled = false;
        }
    }

    async function updateGeroyListingPrice(listingId, priceStr, btn) {
        if (btn.disabled) return;
        const price = parseInt(priceStr, 10);
        if (!price || price < 20) { toast(t("toast_geroy_market_bad_price"), "error"); return; }
        btn.disabled = true;
        try {
            await api(API_BASE + "/webapp/api/geroy_market/update_price", { listing_id: listingId, price });
            toast(t("toast_geroy_market_price_updated"), "success");
            loadGeroyMarketMine();
        } catch (e) {
            toast(t("toast_generic_error"), "error");
            btn.disabled = false;
        }
    }

    async function loadGeroyMarketAdminList() {
        const box = document.getElementById("geroy-market-admin-list");
        try {
            const res = await api(API_BASE + "/webapp/api/geroy_market/admin/list");
            if (!res.listings.length) {
                box.innerHTML = `<div class="hist-empty">${t("geroy_market_empty")}</div>`;
                return;
            }
            box.innerHTML = res.listings.map((l) => `
                <div class="admin-tlist-row">
                    <span class="atl-info">${escapeHtml(l.geroy.name)} — 💎 ${fmt(l.price)}<span class="atl-meta">${escapeHtml(l.seller_name)}</span></span>
                    <button class="sub-cta danger" data-admin-cancel-id="${l.id}" style="width:auto; padding:0 14px;">${t("geroy_market_cancel_btn_webapp")}</button>
                </div>
            `).join("");
            box.querySelectorAll("[data-admin-cancel-id]").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    if (btn.disabled) return;
                    if (!(await confirmAction("geroy_market_cancel_confirm"))) return;
                    btn.disabled = true;
                    try {
                        await api(API_BASE + "/webapp/api/geroy_market/admin/cancel", { listing_id: parseInt(btn.dataset.adminCancelId, 10) });
                        toast(t("toast_geroy_market_cancelled"), "success");
                        loadGeroyMarketAdminList();
                    } catch (e) {
                        toast(t("toast_generic_error"), "error");
                        btn.disabled = false;
                    }
                });
            });
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_load_error")}</div>`;
        }
    }

    async function createAdminGeroyListing() {
        const btn = document.getElementById("gm-admin-create-btn");
        if (btn.disabled) return;
        const name = document.getElementById("gm-admin-name").value.trim();
        const level = parseInt(document.getElementById("gm-admin-level").value, 10) || 1;
        const price = parseInt(document.getElementById("gm-admin-price").value, 10);
        if (!name || !price || price < 20) { toast(t("toast_geroy_market_bad_price"), "error"); return; }
        btn.disabled = true;
        try {
            await api(API_BASE + "/webapp/api/geroy_market/admin/create", { name, level, price });
            toast(t("toast_geroy_market_listed"), "success");
            document.getElementById("gm-admin-name").value = "";
            document.getElementById("gm-admin-price").value = "";
            loadGeroyMarketAdminList();
        } catch (e) {
            toast(t("toast_generic_error"), "error");
        } finally {
            btn.disabled = false;
        }
    }

    /* ---------------- NFT Market ---------------- */
    const nftLottieInstances = [];

    function renderNftSticker(container, stickerPath) {
        if (!stickerPath || !container) return;
        // .jpg — oddiy statik rasm (yengil, tez). .json — Lottie animatsiya
        // (og'ir, faqat rasm topilmagan taqdirda zaxira sifatida ishlatiladi).
        if (stickerPath.endsWith(".jpg")) {
            const img = document.createElement("img");
            img.src = stickerPath;
            img.style.width = "100%";
            img.style.height = "100%";
            img.style.objectFit = "contain";
            container.appendChild(img);
            return;
        }
        if (typeof lottie === "undefined") return;
        try {
            const anim = lottie.loadAnimation({
                container, renderer: "svg", loop: false, autoplay: false,
                path: stickerPath,
            });
            anim.addEventListener("DOMLoaded", () => anim.goToAndStop(0, true));
            nftLottieInstances.push(anim);
        } catch (e) { /* animatsiya yuklanmasa ham karta ko'rinib tursin */ }
    }

    function clearNftLottieInstances() {
        nftLottieInstances.forEach((a) => { try { a.destroy(); } catch (e) {} });
        nftLottieInstances.length = 0;
    }

    async function loadNftStarsBalance() {
        if (!isAdminUser) return;
        const topBox = document.getElementById("nft-stars-balance-top");
        const panelBox = document.getElementById("nft-stars-balance");
        const infoBox = document.getElementById("nft-budget-info");
        const editRow = document.getElementById("nft-budget-edit-row");
        const budgetInput = document.getElementById("nft-budget-input");
        topBox.style.display = "";
        try {
            const res = await api(API_BASE + "/webapp/api/admin_nft_stars_balance", {});
            const text = tf("nft_stars_balance_text", { balance: fmt(res.balance) });
            topBox.textContent = text;
            if (panelBox) panelBox.textContent = text;
            if (infoBox) {
                infoBox.textContent = res.budget
                    ? `Byudjet: ${fmt(res.budget)}⭐ · Sarflandi: ${fmt(res.spent)}⭐ · Real hisobda: ${fmt(res.real_balance)}⭐`
                    : `Byudjet cheklanmagan · Real hisobda: ${fmt(res.real_balance)}⭐`;
            }
            if (editRow) editRow.style.display = res.can_edit_budget ? "" : "none";
            if (budgetInput && res.can_edit_budget) budgetInput.value = res.budget || "";
        } catch (e) {
            topBox.textContent = t("nft_stars_balance_unknown");
            if (panelBox) panelBox.textContent = t("nft_stars_balance_unknown");
        }
    }

    function initNftMarket() {
        loadNftStarsBalance();
        const budgetSaveBtn = document.getElementById("nft-budget-save-btn");
        if (budgetSaveBtn) {
            budgetSaveBtn.addEventListener("click", async () => {
                const raw = document.getElementById("nft-budget-input").value.trim();
                budgetSaveBtn.disabled = true;
                try {
                    await api(API_BASE + "/webapp/api/admin_nft_set_budget", { budget: raw || null });
                    toast(t("admin_action_success"), "success");
                    loadNftStarsBalance();
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                } finally {
                    budgetSaveBtn.disabled = false;
                }
            });
        }
        document.querySelectorAll('#nft-market-tabs [data-nft-tab]').forEach((btn) => {
            btn.addEventListener("click", () => {
                const tab = btn.dataset.nftTab;
                document.querySelectorAll('#nft-market-tabs [data-nft-tab]').forEach((b) => b.classList.toggle("active", b === btn));
                document.getElementById("nft-panel-browse").style.display = tab === "browse" ? "" : "none";
                document.getElementById("nft-panel-mine").style.display = tab === "mine" ? "" : "none";
                document.getElementById("nft-panel-storeedit").style.display = tab === "storeedit" ? "" : "none";
                document.getElementById("nft-panel-resale").style.display = tab === "resale" ? "" : "none";
                document.getElementById("nft-panel-premium").style.display = tab === "premium" ? "" : "none";
                document.getElementById("nft-panel-admin").style.display = tab === "admin" ? "" : "none";
                if (tab === "browse") loadNftMarketBrowse();
                if (tab === "mine") loadNftMyPurchases();
                if (tab === "storeedit") loadNftStoreEditList();
                if (tab === "resale") loadResaleMarketBrowse();
                if (tab === "premium") loadPremiumMarketBrowse();
                if (tab === "admin") { loadNftAdminList(); loadNftPurchaseHistory(); loadResaleAdminHistory(); loadPremiumAdminHistory(); }
            });
        });
        document.querySelectorAll('#nft-admin-filter-tabs [data-nft-filter]').forEach((btn) => {
            btn.addEventListener("click", async () => {
                nftAdminFilter = btn.dataset.nftFilter;
                document.querySelectorAll('#nft-admin-filter-tabs [data-nft-filter]').forEach((b) => b.classList.toggle("active", b === btn));
                if (nftAdminFilter === "resale" && !resaleAdminAllItems.length) {
                    document.getElementById("nft-admin-list").innerHTML = `<div class="skeleton-list"></div>`;
                    await loadResaleAdminList();
                }
                if (nftAdminFilter === "premium" && !premiumAdminAllItems.length) {
                    document.getElementById("nft-admin-list").innerHTML = `<div class="skeleton-list"></div>`;
                    await loadPremiumAdminList();
                }
                renderNftAdminList();
            });
        });
        document.getElementById("nft-admin-sync-btn").addEventListener("click", async () => {
            const btn = document.getElementById("nft-admin-sync-btn");
            btn.disabled = true;
            try {
                const res = await api(API_BASE + "/webapp/api/admin_nft_sync", {});
                toast(tf("nft_sync_toast", { count: res.count }), "success");
                loadNftAdminList();
            } catch (e) {
                toast(t("toast_generic_error"), "error");
            } finally {
                btn.disabled = false;
            }
        });
        const resaleSyncBtn = document.getElementById("resale-admin-sync-btn");
        if (resaleSyncBtn) {
            resaleSyncBtn.addEventListener("click", async () => {
                resaleSyncBtn.disabled = true;
                try {
                    const res = await api(API_BASE + "/webapp/api/admin_nft_resale_sync", {});
                    toast(`Sinxronlandi: ${res.count} ta Collectible`, "success");
                    loadResaleAdminList();
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                } finally {
                    resaleSyncBtn.disabled = false;
                }
            });
        }
        const premiumSyncBtn = document.getElementById("premium-admin-sync-btn");
        if (premiumSyncBtn) {
            premiumSyncBtn.addEventListener("click", async () => {
                premiumSyncBtn.disabled = true;
                try {
                    const res = await api(API_BASE + "/webapp/api/admin_premium_sync", {});
                    toast(`Sinxronlandi: ${res.count} ta Premium variant`, "success");
                    await loadPremiumAdminList();
                    if (nftAdminFilter === "premium") renderNftAdminList();
                } catch (e) {
                    toast(t("toast_generic_error"), "error");
                } finally {
                    premiumSyncBtn.disabled = false;
                }
            });
        }
        loadNftMarketBrowse();
    }

    async function loadResaleMarketBrowse() {
        const box = document.getElementById("resale-market-browse-container");
        clearNftLottieInstances();
        try {
            const res = await api(API_BASE + "/webapp/api/resale_market_list", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<div class="hist-empty">${t("resale_empty_store")}</div>`;
                return;
            }
            box.innerHTML = `<div class="nft-grid" id="resale-market-grid"></div>`;
            const grid = document.getElementById("resale-market-grid");
            const tileColors = ["#3a6ea5", "#7a4fb5", "#b5824f", "#4fb587", "#b54f6e", "#4f8fb5"];
            items.forEach((item, i) => {
                const card = document.createElement("div");
                card.className = "nft-card";
                card.innerHTML = `
                    <div class="nft-card-image" style="background:${tileColors[i % tileColors.length]};">
                        <div class="nft-card-anim" id="resale-anim-${item.id}"></div>
                    </div>
                    <div class="nft-card-body">
                        <div style="font-size:11.5px; color:var(--text-2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(item.title)}${item.num ? " #" + item.num : ""}</div>
                        <div class="nft-card-price">💎 ${fmt(item.diamond_price)}</div>
                        <button class="sub-cta nft-card-buy" data-resale-buy="${item.id}">${t("nft_buy_btn")}</button>
                    </div>
                `;
                grid.appendChild(card);
                renderNftSticker(document.getElementById(`resale-anim-${item.id}`), item.sticker_path);
            });
            grid.querySelectorAll("[data-resale-buy]").forEach((btn) => {
                btn.addEventListener("click", () => buyResaleListing(parseInt(btn.dataset.resaleBuy, 10), btn));
            });
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_generic_error")}</div>`;
        }
    }

    async function buyResaleListing(id, btn) {
        if (!(await tgConfirm(t("nft_buy_confirm")))) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/resale_market_buy", { id });
            if (res.profile) {
                profileCache.profile.diamond = res.profile.diamond;
                renderUser(profileCache);
            }
            toast(t("nft_buy_success"), "success");
            loadResaleMarketBrowse();
        } catch (e) {
            const code = e && e.message;
            if (code === "username_required") {
                toast(t("nft_username_required"), "error");
            } else if (code === "not_enough_diamond") {
                toast(t("nft_not_enough_diamond"), "error");
            } else if (code === "stars_balance_low") {
                toast(t("nft_stars_balance_low"), "error");
            } else {
                toast(t("toast_generic_error"), "error");
            }
        } finally {
            btn.disabled = false;
        }
    }

    let resaleAdminAllItems = [];
    let resaleAdminPage = 1;
    let resaleAdminHasMore = false;

    async function loadResaleAdminList(page, append) {
        page = page || 1;
        try {
            const res = await api(API_BASE + "/webapp/api/admin_nft_resale_list", { page });
            const items = res.items || [];
            resaleAdminAllItems = append ? resaleAdminAllItems.concat(items) : items;
            resaleAdminPage = page;
            resaleAdminHasMore = !!res.has_more;
        } catch (e) {
            if (!append) resaleAdminAllItems = [];
        }
    }

    async function loadMoreResaleAdmin() {
        await loadResaleAdminList(resaleAdminPage + 1, true);
        renderNftAdminList();
    }

    async function loadResaleAdminHistory() {
        const box = document.getElementById("resale-admin-history");
        try {
            const res = await api(API_BASE + "/webapp/api/admin_nft_resale_purchase_history", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<span class="inv-empty">${t("nft_empty_history")}</span>`;
                return;
            }
            box.innerHTML = items.map((it) => `
                <div class="admin-tlist-row">
                    <span class="atl-info">
                        ${escapeHtml(it.buyer_name)}${it.buyer_username ? " @" + escapeHtml(it.buyer_username) : ""} — ${escapeHtml(it.title || "")}
                        <span class="atl-meta">💎 ${fmt(it.diamond_price)} · ${escapeHtml(it.date)} · ${NFT_STATUS_LABELS[it.status] || it.status}${it.error_text ? " — " + escapeHtml(it.error_text) : ""}</span>
                    </span>
                </div>
            `).join("");
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }


    let premiumAdminAllItems = [];

    async function loadPremiumAdminList() {
        try {
            const res = await api(API_BASE + "/webapp/api/admin_premium_list", {});
            premiumAdminAllItems = res.items || [];
        } catch (e) {
            premiumAdminAllItems = [];
        }
    }

    async function loadPremiumAdminHistory() {
        const box = document.getElementById("premium-admin-history");
        try {
            const res = await api(API_BASE + "/webapp/api/admin_premium_purchase_history", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<span class="inv-empty">${t("nft_empty_history")}</span>`;
                return;
            }
            box.innerHTML = items.map((it) => `
                <div class="admin-tlist-row">
                    <span class="atl-info">
                        ${escapeHtml(it.buyer_name)}${it.buyer_username ? " @" + escapeHtml(it.buyer_username) : ""} — 👑 ${it.months} oy
                        <span class="atl-meta">💎 ${fmt(it.diamond_price)} · ${escapeHtml(it.date)} · ${NFT_STATUS_LABELS[it.status] || it.status}${it.error_text ? " — " + escapeHtml(it.error_text) : ""}</span>
                    </span>
                </div>
            `).join("");
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    async function loadPremiumMarketBrowse() {
        const box = document.getElementById("premium-market-browse-container");
        try {
            const res = await api(API_BASE + "/webapp/api/premium_market_list", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<div class="hist-empty">Hozircha sotuvda Premium variant yo'q</div>`;
                return;
            }
            box.innerHTML = `<div class="nft-grid" id="premium-market-grid"></div>`;
            const grid = document.getElementById("premium-market-grid");
            items.forEach((item) => {
                const card = document.createElement("div");
                card.className = "nft-card";
                card.innerHTML = `
                    <div class="nft-card-image" style="background:linear-gradient(135deg,#3a6ea5,#7a4fb5); display:flex; align-items:center; justify-content:center; font-size:42px;">👑</div>
                    <div class="nft-card-body">
                        <div style="font-size:13px; color:var(--text-0); font-weight:700;">${item.months} oy</div>
                        <div class="nft-card-price">💎 ${fmt(item.diamond_price)}</div>
                        <button class="sub-cta nft-card-buy" data-premium-buy="${item.id}">${t("nft_buy_btn")}</button>
                    </div>
                `;
                grid.appendChild(card);
            });
            grid.querySelectorAll("[data-premium-buy]").forEach((btn) => {
                btn.addEventListener("click", () => buyPremiumListing(parseInt(btn.dataset.premiumBuy, 10), btn));
            });
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_generic_error")}</div>`;
        }
    }

    async function buyPremiumListing(id, btn) {
        if (!(await tgConfirm(t("nft_buy_confirm")))) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/premium_market_buy", { id });
            if (res.profile) {
                profileCache.profile.diamond = res.profile.diamond;
                renderUser(profileCache);
            }
            toast(t("nft_buy_success"), "success");
            loadPremiumMarketBrowse();
        } catch (e) {
            const code = e && e.message;
            if (code === "username_required") {
                toast(t("nft_username_required"), "error");
            } else if (code === "not_enough_diamond") {
                toast(t("nft_not_enough_diamond"), "error");
            } else if (code === "stars_balance_low") {
                toast(t("nft_stars_balance_low"), "error");
            } else {
                toast(t("toast_generic_error"), "error");
            }
        } finally {
            btn.disabled = false;
        }
    }


    async function loadNftMyPurchases() {
        const box = document.getElementById("nft-market-mine-container");
        clearNftLottieInstances();
        try {
            const res = await api(API_BASE + "/webapp/api/nft_market_my_purchases", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<div class="hist-empty">${t("nft_empty_purchases_mine")}</div>`;
                return;
            }
            box.innerHTML = items.map((it) => `
                <div class="admin-tlist-row">
                    <span class="atl-info" style="display:flex; align-items:center; gap:10px;">
                        <div id="nft-mine-anim-${it.id}" style="width:36px; height:36px; flex-shrink:0; display:inline-block;"></div>
                        <span>💎 ${fmt(it.diamond_price)}${it.buyer !== undefined ? ` · @${escapeHtml(String(it.buyer))}` : ""}<span class="atl-meta">${escapeHtml(it.date)} · ${NFT_STATUS_LABELS[it.status] || it.status}</span></span>
                    </span>
                </div>
            `).join("");
            items.forEach((it) => renderNftSticker(document.getElementById(`nft-mine-anim-${it.id}`), it.sticker_path));
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_generic_error")}</div>`;
        }
    }

    async function loadNftMarketBrowse() {
        const box = document.getElementById("nft-market-browse-container");
        clearNftLottieInstances();
        try {
            const res = await api(API_BASE + "/webapp/api/nft_market_list", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<div class="hist-empty">${t("nft_empty_store")}</div>`;
                return;
            }
            box.innerHTML = `<div class="nft-grid" id="nft-market-grid"></div>`;
            const grid = document.getElementById("nft-market-grid");
            const tileColors = ["#3a6ea5", "#7a4fb5", "#b5824f", "#4fb587", "#b54f6e", "#4f8fb5"];
            items.forEach((item, i) => {
                const card = document.createElement("div");
                card.className = "nft-card";
                card.innerHTML = `
                    <div class="nft-card-image" style="background:${tileColors[i % tileColors.length]};">
                        <div class="nft-card-anim" id="nft-anim-${item.id}"></div>
                    </div>
                    <div class="nft-card-body">
                        <div class="nft-card-price">💎 ${fmt(item.diamond_price)}</div>
                        <button class="sub-cta nft-card-buy" data-nft-buy="${item.id}">${t("nft_buy_btn")}</button>
                    </div>
                `;
                grid.appendChild(card);
                renderNftSticker(document.getElementById(`nft-anim-${item.id}`), item.sticker_path);
            });
            grid.querySelectorAll("[data-nft-buy]").forEach((btn) => {
                btn.addEventListener("click", () => buyNftListing(parseInt(btn.dataset.nftBuy, 10), btn));
            });
        } catch (e) {
            box.innerHTML = `<div class="hist-empty">${t("toast_generic_error")}</div>`;
        }
    }

    async function buyNftListing(id, btn) {
        if (!(await tgConfirm(t("nft_buy_confirm")))) return;
        btn.disabled = true;
        try {
            const res = await api(API_BASE + "/webapp/api/nft_market_buy", { id });
            if (res.profile) {
                profileCache.profile.diamond = res.profile.diamond;
                renderUser(profileCache);
            }
            toast(t("nft_buy_success"), "success");
        } catch (e) {
            const code = e && e.message;
            if (code === "username_required") {
                toast(t("nft_username_required"), "error");
            } else if (code === "not_enough_diamond") {
                toast(t("nft_not_enough_diamond"), "error");
            } else if (code === "stars_balance_low") {
                toast(t("nft_stars_balance_low"), "error");
            } else {
                toast(t("toast_generic_error"), "error");
            }
        } finally {
            btn.disabled = false;
        }
    }

    let nftAdminAllItems = [];
    let nftAdminFilter = "all";

    function renderNftCardEditGrid(containerId, items, emptyText, onSaved, opts) {
        opts = opts || {};
        const endpoint = opts.endpoint || API_BASE + "/webapp/api/admin_nft_set_price";
        const showTitle = !!opts.showTitle;
        const box = document.getElementById(containerId);
        if (!items.length) {
            box.innerHTML = `<span class="inv-empty">${emptyText}</span>`;
            return;
        }
            box.innerHTML = `<div class="nft-grid nft-admin-grid">${items.map((it) => `
                <div class="nft-card">
                    <div class="nft-card-image">
                        <div id="nft-admin-anim-${it.id}" class="nft-card-anim"></div>
                    </div>
                    <div class="nft-card-body">
                        ${showTitle ? `<div style="font-size:11px; color:var(--text-2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(it.title || "")}${it.num ? " #" + it.num : ""}</div>` : ""}
                        <div class="nft-card-price">⭐ ${it.stars_price}</div>
                        <div class="nft-price-edit-row">
                            <div class="nft-price-input-wrap">
                                <span class="nft-price-diamond">💎</span>
                                <input type="text" data-nft-price="${it.id}" placeholder="${t("nft_price_placeholder")}" inputmode="numeric" value="${it.diamond_price || ""}">
                            </div>
                            <button data-nft-save="${it.id}">${t("nft_save_btn")}</button>
                        </div>
                    </div>
                </div>
            `).join("")}</div>`;
            clearNftLottieInstances();
            // Ko'p katalog elementi bor — hammasini bir vaqtda animatsiya qilish
            // brauzerni qiynaydi. Faqat ekranda ko'rinayotganini yuklaymiz (lazy-load).
            const nftAdminObserver = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const el = entry.target;
                        const giftId = el.dataset.giftId;
                        const item = items.find((x) => String(x.id) === giftId);
                        if (item && !el.dataset.rendered) {
                            el.dataset.rendered = "1";
                            renderNftSticker(el, item.sticker_path);
                        }
                        nftAdminObserver.unobserve(el);
                    }
                });
            }, { root: box, rootMargin: "200px" });
            items.forEach((it) => {
                const el = document.getElementById(`nft-admin-anim-${it.id}`);
                if (el) { el.dataset.giftId = it.id; nftAdminObserver.observe(el); }
            });
            box.querySelectorAll("[data-nft-save]").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    const id = btn.dataset.nftSave;
                    const priceInput = box.querySelector(`[data-nft-price="${id}"]`);
                    const price = parseInt(priceInput.value, 10) || 0;
                    try {
                        await api(endpoint, { id, diamond_price: price, is_active: true });
                        const cached = items.find((x) => String(x.id) === String(id));
                        if (cached) cached.diamond_price = price;
                        toast(t("admin_action_success"), "success");
                        if (onSaved) onSaved();
                    } catch (e) {
                        toast(t("toast_generic_error"), "error");
                    }
                });
            });
    }

    function renderNftAdminList() {
        if (nftAdminFilter === "premium") {
            const box = document.getElementById("nft-admin-list");
            if (!premiumAdminAllItems.length) {
                box.innerHTML = `<span class="inv-empty">Ro'yxat bo'sh — "Sinxronlash" tugmasini bosing</span>`;
                return;
            }
            box.innerHTML = premiumAdminAllItems.map((it) => `
                <div class="admin-tlist-row" style="padding:14px 16px;">
                    <span style="display:flex; flex-direction:column; gap:4px; flex-shrink:0;">
                        <span style="font-weight:700; font-size:16px;">👑 ${it.months} oy</span>
                        <span class="atl-meta" style="font-size:13px;">⭐ ${it.stars_price}</span>
                    </span>
                    <span style="display:flex; gap:8px; align-items:center; flex-shrink:0;">
                        <span style="color:var(--diamond); font-size:15px;">💎</span>
                        <input type="text" class="admin-item-input" data-premium-price="${it.id}" placeholder="${t("nft_price_placeholder")}" inputmode="numeric" value="${it.diamond_price || ""}" style="width:70px; padding:9px 10px; font-size:14px;">
                        <button data-premium-save="${it.id}" style="background:rgba(255,209,102,.14); color:var(--dollar-gold); padding:9px 14px; font-size:13.5px;">${t("nft_save_btn")}</button>
                    </span>
                </div>
            `).join("");
            box.querySelectorAll("[data-premium-save]").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    const id = btn.dataset.premiumSave;
                    const priceInput = box.querySelector(`[data-premium-price="${id}"]`);
                    const price = parseInt(priceInput.value, 10) || 0;
                    try {
                        await api(API_BASE + "/webapp/api/admin_premium_set_price", { id, diamond_price: price, is_active: true });
                        const cached = premiumAdminAllItems.find((x) => String(x.id) === String(id));
                        if (cached) cached.diamond_price = price;
                        toast(t("admin_action_success"), "success");
                    } catch (e) {
                        toast(t("toast_generic_error"), "error");
                    }
                });
            });
            return;
        }
        if (nftAdminFilter === "resale") {
            renderNftCardEditGrid("nft-admin-list", resaleAdminAllItems, t("resale_empty_catalog"), () => renderNftAdminList(), {
                endpoint: API_BASE + "/webapp/api/admin_nft_resale_set_price", showTitle: true,
            });
            if (resaleAdminHasMore) {
                const box = document.getElementById("nft-admin-list");
                const moreBtn = document.createElement("button");
                moreBtn.className = "sub-cta";
                moreBtn.style.cssText = "width:100%; margin-top:12px;";
                moreBtn.textContent = "⬇️ Yana ko'rsatish";
                moreBtn.addEventListener("click", () => { moreBtn.disabled = true; loadMoreResaleAdmin(); });
                box.appendChild(moreBtn);
            }
            return;
        }
        const items = nftAdminFilter === "listed"
            ? nftAdminAllItems.filter((it) => it.diamond_price)
            : nftAdminAllItems;
        const emptyText = nftAdminFilter === "listed" ? t("nft_empty_listed") : t("nft_empty_catalog");
        renderNftCardEditGrid("nft-admin-list", items, emptyText, () => { if (nftAdminFilter === "listed") renderNftAdminList(); });
    }

    async function loadNftAdminList() {
        const box = document.getElementById("nft-admin-list");
        try {
            const res = await api(API_BASE + "/webapp/api/admin_nft_list", {});
            nftAdminAllItems = res.items || [];
            renderNftAdminList();
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    async function loadNftStoreEditList() {
        const box = document.getElementById("nft-storeedit-list");
        try {
            const res = await api(API_BASE + "/webapp/api/admin_nft_list", {});
            nftAdminAllItems = res.items || [];
            const listed = nftAdminAllItems.filter((it) => it.diamond_price);
            renderNftCardEditGrid("nft-storeedit-list", listed, t("nft_empty_listed"), () => loadNftStoreEditList());
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }

    const NFT_STATUS_LABELS = {
        get sent() { return t("nft_status_sent"); },
        get refunded() { return t("nft_status_refunded"); },
        get pending() { return t("nft_status_pending"); },
    };

    async function loadNftPurchaseHistory() {
        const box = document.getElementById("nft-admin-history");
        try {
            const res = await api(API_BASE + "/webapp/api/admin_nft_purchase_history", {});
            const items = res.items || [];
            if (!items.length) {
                box.innerHTML = `<span class="inv-empty">${t("nft_empty_history")}</span>`;
                return;
            }
            box.innerHTML = items.map((it) => `
                <div class="admin-tlist-row">
                    <span class="atl-info">
                        ${escapeHtml(it.buyer_name)}${it.buyer_username ? " @" + escapeHtml(it.buyer_username) : ""}
                        <span class="atl-meta">💎 ${fmt(it.diamond_price)} · ${escapeHtml(it.date)} · ${NFT_STATUS_LABELS[it.status] || it.status}${it.error_text ? " — " + escapeHtml(it.error_text) : ""}</span>
                    </span>
                </div>
            `).join("");
        } catch (e) {
            box.innerHTML = `<span class="inv-empty">${t("toast_generic_error")}</span>`;
        }
    }


    /* ---------------- currency shop ---------------- */
    function buildCustomAmountCard(kind, icon, baseRate, minCount) {
        const card = document.createElement("div");
        card.className = "pack-card pack-card-custom";
        card.innerHTML = `
            <div class="pack-amount">${icon} <span data-i18n="custom_amount_label">${t("custom_amount_label")}</span></div>
            <input type="number" class="custom-amount-input" min="${minCount}" step="1" placeholder="${minCount}+">
            <div class="pack-price custom-amount-price">⭐️ —</div>
            <button class="sub-cta stars" disabled>${t("btn_buy")}</button>
        `;
        const input = card.querySelector(".custom-amount-input");
        const priceEl = card.querySelector(".custom-amount-price");
        const btn = card.querySelector("button");
        input.addEventListener("input", () => {
            const val = parseInt(input.value, 10);
            if (!val || val < minCount) {
                priceEl.textContent = "⭐️ —";
                btn.disabled = true;
                return;
            }
            const stars = Math.max(1, Math.ceil(val * baseRate));
            priceEl.textContent = `⭐️ ${fmt(stars)}`;
            btn.disabled = false;
        });
        btn.addEventListener("click", (e) => {
            const val = parseInt(input.value, 10);
            if (!val || val < minCount) return;
            buyCurrencyStars(kind, val, e.target);
        });
        return card;
    }

    function renderCurrencyPacks() {
        const diaStarsBox = document.getElementById("diamond-stars-container");
        const diaDollarBox = document.getElementById("diamond-dollar-container");
        const dolBox = document.getElementById("dollar-packs-container");
        diaStarsBox.innerHTML = "";
        diaDollarBox.innerHTML = "";
        dolBox.innerHTML = "";

        const starDiamondPrices = { 10: 70, 30: 200, 70: 450, 250: 1300 };
        Object.keys(starDiamondPrices).forEach((countStr) => {
            const count = Number(countStr);
            const card = document.createElement("div");
            card.className = "pack-card";
            card.innerHTML = `<div class="pack-amount">💎 ${fmt(count)}</div><div class="pack-price">⭐️ ${fmt(starDiamondPrices[count])}</div><button class="sub-cta stars">${t("btn_buy")}</button>`;
            card.querySelector("button").addEventListener("click", (e) => buyCurrencyStars("diamond", count, e.target));
            diaStarsBox.appendChild(card);
        });
        diaStarsBox.appendChild(buildCustomAmountCard("diamond", "💎", 7, 1));

        [1, 5, 10, 30].forEach((count) => {
            const card = document.createElement("div");
            card.className = "pack-card";
            card.innerHTML = `<div class="pack-amount">💎 ${fmt(count)}</div><div class="pack-price">💵 ${fmt(count * 1000)}</div><button class="sub-cta">${t("btn_buy_with_dollar")}</button>`;
            card.querySelector("button").addEventListener("click", (e) => buyDiamondWithDollar(count, e.target));
            diaDollarBox.appendChild(card);
        });

        document.querySelectorAll("#diamond-method-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#diamond-method-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                const method = btn.dataset.method;
                diaStarsBox.style.display = method === "stars" ? "" : "none";
                diaDollarBox.style.display = method === "dollar" ? "" : "none";
            });
        });

        const starDollarPacks = { 1000: 7, 10000: 70, 30000: 200 };
        Object.keys(starDollarPacks).forEach((countStr) => {
            const count = Number(countStr);
            const card = document.createElement("div");
            card.className = "pack-card";
            card.innerHTML = `<div class="pack-amount">💵 ${fmt(count)}</div><div class="pack-price">⭐️ ${fmt(starDollarPacks[count])}</div><button class="sub-cta stars">${t("btn_buy")}</button>`;
            card.querySelector("button").addEventListener("click", (e) => buyCurrencyStars("dollar", count, e.target));
            dolBox.appendChild(card);
        });
        dolBox.appendChild(buildCustomAmountCard("dollar", "💵", 7 / 1000, 100));

        const dolDiaBox = document.getElementById("dollar-diamond-container");
        dolDiaBox.innerHTML = "";
        const diamondToDollar = { 1: 1000, 2: 2000, 4: 4000, 5: 5000, 10: 10000, 20: 20000 };
        Object.keys(diamondToDollar).forEach((diaStr) => {
            const diaCount = Number(diaStr);
            const card = document.createElement("div");
            card.className = "pack-card";
            card.innerHTML = `<div class="pack-amount">💵 ${fmt(diamondToDollar[diaCount])}</div><div class="pack-price">💎 ${diaCount}</div><button class="sub-cta">${t("btn_buy_with_diamond")}</button>`;
            card.querySelector("button").addEventListener("click", (e) => sellDiamondForDollar(diaCount, e.target));
            dolDiaBox.appendChild(card);
        });

        document.querySelectorAll("#dollar-method-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#dollar-method-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                const method = btn.dataset.method;
                dolBox.style.display = method === "stars" ? "" : "none";
                dolDiaBox.style.display = method === "diamond" ? "" : "none";
            });
        });
    }

    async function sellDiamondForDollar(diamond, btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/sell_diamond_for_dollar", { diamond });
            Object.assign(profileCache.profile, res.profile);
            renderUser(profileCache);
            toast(t("toast_purchase_success"), "success");
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : t("toast_generic_error");
            toast(msg, "error");
        } finally {
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    async function buyCurrencyStars(kind, count, btn) {
        if (btn.disabled || !tg) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/currency_invoice", { kind, count });
            tg.openInvoice(res.link, (status) => {
                btn.disabled = false;
                btn.textContent = oldText;
                if (status === "paid") {
                    toast(t("toast_purchase_success"), "success");
                }
            });
        } catch (e) {
            toast(t("toast_generic_error"), "error");
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    async function buyDiamondWithDollar(count, btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        const oldText = btn.textContent;
        btn.textContent = "...";
        try {
            const res = await api(API_BASE + "/webapp/api/buy_diamond_with_dollar", { count });
            Object.assign(profileCache.profile, res.profile);
            renderUser(profileCache);
            toast(t("toast_purchase_success"), "success");
        } catch (e) {
            const msg = e.message === "not_enough_balance" ? t("toast_not_enough_balance") : t("toast_generic_error");
            toast(msg, "error");
        } finally {
            btn.disabled = false;
            btn.textContent = oldText;
        }
    }

    /* ---------------- gift vip ---------------- */
    function setupGiftVip() {
        let giftDays = 7;
        let giftTargetType = "username";
        const diaBtn = document.getElementById("gift-vip-diamond-btn");
        const starBtn = document.getElementById("gift-vip-stars-btn");
        const plans = { 7: { diamond: 8, stars: 50 }, 14: { diamond: 15, stars: 100 }, 30: { diamond: 30, stars: 200 } };

        function refreshLabels() {
            diaBtn.textContent = `💎 ${plans[giftDays].diamond} ${t("label_via")}`;
            starBtn.textContent = `⭐️ ${plans[giftDays].stars} ${t("label_via")}`;
        }

        document.querySelectorAll("#gift-vip-plan-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#gift-vip-plan-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                giftDays = Number(btn.dataset.days);
                refreshLabels();
            });
        });

        const giftTargetPreview = wireTargetPreview({
            usernameInputId: "gift-vip-username",
            idInputId: "gift-vip-target-id",
            previewBoxId: "gift-vip-target-preview",
            getTargetType: () => giftTargetType,
        });

        document.querySelectorAll("#gift-vip-target-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#gift-vip-target-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                giftTargetType = btn.dataset.targetType;
                document.getElementById("gift-vip-username").style.display = giftTargetType === "username" ? "" : "none";
                document.getElementById("gift-vip-target-id").style.display = giftTargetType === "id" ? "" : "none";
                giftTargetPreview.refresh();
            });
        });

        function buildTargetBody() {
            const body = { target_type: giftTargetType };
            if (giftTargetType === "username") {
                const val = document.getElementById("gift-vip-username").value.trim();
                if (!val) { toast(t("toast_enter_username"), "error"); return null; }
                body.username = val;
            } else if (giftTargetType === "id") {
                const val = document.getElementById("gift-vip-target-id").value.trim();
                if (!val) { toast(t("toast_enter_friend_id"), "error"); return null; }
                body.target_user_id = val;
            }
            return body;
        }

        diaBtn.addEventListener("click", async () => {
            const targetBody = buildTargetBody();
            if (!targetBody || diaBtn.disabled) return;
            diaBtn.disabled = true;
            try {
                const res = await api(API_BASE + "/webapp/api/gift_vip", Object.assign({ days: giftDays }, targetBody));
                profileCache.profile.diamond = res.profile.diamond;
                renderUser(profileCache);
                toast(t("toast_vip_gifted"), "success");
            } catch (e) {
                const errMap = { not_enough_balance: t("toast_not_enough_balance"), target_not_found: t("toast_user_not_found"), already_vip: t("toast_friend_already_vip"), self_transfer: t("toast_self_gift"), no_para: t("toast_no_para") };
                toast(errMap[e.message] || t("toast_generic_error"), "error");
            } finally {
                diaBtn.disabled = false;
            }
        });

        starBtn.addEventListener("click", async () => {
            const targetBody = buildTargetBody();
            if (!targetBody || starBtn.disabled || !tg) return;
            starBtn.disabled = true;
            try {
                const res = await api(API_BASE + "/webapp/api/gift_vip_invoice", Object.assign({ days: giftDays }, targetBody));
                tg.openInvoice(res.link, (status) => {
                    starBtn.disabled = false;
                    if (status === "paid") toast(t("toast_vip_gifted"), "success");
                });
            } catch (e) {
                const errMap = { target_not_found: t("toast_user_not_found"), already_vip: t("toast_friend_already_vip"), self_transfer: t("toast_self_gift"), no_para: t("toast_no_para") };
                toast(errMap[e.message] || t("toast_generic_error"), "error");
                starBtn.disabled = false;
            }
        });

        return { refreshLabels };
    }

    /* ---------------- transfer ---------------- */
    function setupParaTransfer() {
        let kind = "dollar";
        document.querySelectorAll("#para-transfer-kind-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#para-transfer-kind-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                kind = btn.dataset.kind;
                document.getElementById("para-transfer-amount-row").style.display = kind === "item" ? "none" : "";
                document.getElementById("para-transfer-item-row").style.display = kind === "item" ? "" : "none";
                const note = document.getElementById("para-transfer-fee-note");
                note.textContent = kind === "dollar" ? (t("webapp_transfer_commission") + ": 10 $") : kind === "diamond" ? t("webapp_transfer_no_commission") : t("webapp_transfer_item_note");
            });
        });

        const itemSelect = document.getElementById("para-transfer-item-field");
        itemSelect.innerHTML = "";
        const _itemLabels = getItemLabels();
        Object.keys(_itemLabels).forEach((field) => {
            const opt = document.createElement("option");
            opt.value = field;
            opt.textContent = _itemLabels[field];
            itemSelect.appendChild(opt);
        });

        document.getElementById("para-transfer-submit-btn").addEventListener("click", async (e) => {
            const btn = e.target;
            if (btn.disabled) return;
            const body = { target_type: "para", kind };
            if (kind === "item") {
                body.field = itemSelect.value;
            } else {
                const amt = document.getElementById("para-transfer-amount").value.trim();
                if (!amt) { toast(t("toast_enter_amount"), "error"); return; }
                body.amount = amt;
            }
            btn.disabled = true;
            const oldText = btn.textContent;
            btn.textContent = "...";
            try {
                const res = await api(API_BASE + "/webapp/api/transfer", body);
                if (res.profile) Object.assign(profileCache.profile, res.profile);
                renderUser(profileCache);
                toast(t("toast_transfer_to_para"), "success");
                document.getElementById("para-transfer-amount").value = "";
                if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
            } catch (err) {
                const errMap = { not_enough_balance: t("toast_not_enough_balance"), no_para: t("toast_no_para") };
                toast(errMap[err.message] || t("toast_generic_error"), "error");
            } finally {
                btn.disabled = false;
                btn.textContent = oldText;
            }
        });
    }

    function wireTargetPreview({ usernameInputId, idInputId, previewBoxId, getTargetType }) {
        const previewBox = document.getElementById(previewBoxId);
        const usernameInput = document.getElementById(usernameInputId);
        const idInput = document.getElementById(idInputId);
        let lookupTimer = null;

        function clearPreview() {
            previewBox.style.display = "none";
            previewBox.className = "target-preview";
            previewBox.innerHTML = "";
        }

        async function runLookup(body) {
            try {
                const res = await api(API_BASE + "/webapp/api/lookup_user", body);
                const u = res.user;
                previewBox.className = "target-preview";
                previewBox.innerHTML = `
                    <img src="${API_BASE}/webapp/avatar/${u.user_id}" alt="" onerror="this.style.display='none'">
                    <div>
                        <div class="target-preview-name">${escapeHtml(u.full_name || t("label_unknown"))}</div>
                        <div class="target-preview-id">ID: ${u.user_id}${u.is_self ? " (" + t("label_this_is_you") + ")" : ""}</div>
                    </div>
                `;
                previewBox.style.display = "flex";
            } catch (e) {
                previewBox.className = "target-preview not-found";
                previewBox.innerHTML = `<div class="target-preview-name">❌ Foydalanuvchi topilmadi</div>`;
                previewBox.style.display = "flex";
            }
        }

        function refresh() {
            clearTimeout(lookupTimer);
            const targetType = getTargetType();
            if (targetType === "para") { clearPreview(); return; }
            const val = targetType === "username" ? usernameInput.value.trim() : idInput.value.trim();
            if (!val) { clearPreview(); return; }
            lookupTimer = setTimeout(() => {
                const body = targetType === "username" ? { target_type: "username", username: val } : { target_type: "id", target_user_id: val };
                runLookup(body);
            }, 500);
        }

        usernameInput.addEventListener("input", refresh);
        idInput.addEventListener("input", refresh);

        return { refresh, clear: clearPreview };
    }

    function setupTransferForm() {
        let targetType = "username";
        let kind = "dollar";

        const targetPreview = wireTargetPreview({
            usernameInputId: "transfer-target-username",
            idInputId: "transfer-target-id",
            previewBoxId: "transfer-target-preview",
            getTargetType: () => targetType,
        });

        document.querySelectorAll("#transfer-target-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#transfer-target-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                targetType = btn.dataset.targetType;
                document.getElementById("transfer-target-username").style.display = targetType === "username" ? "" : "none";
                document.getElementById("transfer-target-id").style.display = targetType === "id" ? "" : "none";
                targetPreview.refresh();
            });
        });

        document.querySelectorAll("#transfer-kind-tabs .seg").forEach((btn) => {
            btn.addEventListener("click", () => {
                document.querySelectorAll("#transfer-kind-tabs .seg").forEach((b) => b.classList.remove("active"));
                btn.classList.add("active");
                kind = btn.dataset.kind;
                document.getElementById("transfer-amount-row").style.display = kind === "item" ? "none" : "";
                document.getElementById("transfer-item-row").style.display = kind === "item" ? "" : "none";
                const note = document.getElementById("transfer-fee-note");
                note.textContent = kind === "dollar" ? (t("webapp_transfer_commission") + ": 10 $") : kind === "diamond" ? t("webapp_transfer_no_commission") : t("webapp_transfer_item_note");
            });
        });

        const itemSelect = document.getElementById("transfer-item-field");
        itemSelect.innerHTML = "";
        const _itemLabels = getItemLabels();
        Object.keys(_itemLabels).forEach((field) => {
            const opt = document.createElement("option");
            opt.value = field;
            opt.textContent = _itemLabels[field];
            itemSelect.appendChild(opt);
        });

        document.getElementById("transfer-submit-btn").addEventListener("click", async (e) => {
            const btn = e.target;
            if (btn.disabled) return;
            const body = { target_type: targetType, kind };
            if (targetType === "id") {
                const idVal = document.getElementById("transfer-target-id").value.trim();
                if (!idVal) { toast(t("toast_enter_id"), "error"); return; }
                body.target_user_id = idVal;
            }
            if (targetType === "username") {
                const uname = document.getElementById("transfer-target-username").value.trim();
                if (!uname) { toast(t("toast_enter_username_plain"), "error"); return; }
                body.username = uname;
            }
            if (kind === "item") {
                body.field = itemSelect.value;
            } else {
                const amt = document.getElementById("transfer-amount").value.trim();
                if (!amt) { toast(t("toast_enter_amount"), "error"); return; }
                body.amount = amt;
            }
            btn.disabled = true;
            const oldText = btn.textContent;
            btn.textContent = "...";
            try {
                const res = await api(API_BASE + "/webapp/api/transfer", body);
                if (res.profile) Object.assign(profileCache.profile, res.profile);
                renderUser(profileCache);
                toast(t("toast_transfer_success"), "success");
                document.getElementById("transfer-amount").value = "";
                if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
            } catch (err) {
                const errMap = {
                    not_enough_balance: t("toast_not_enough_balance"),
                    target_not_found: t("toast_user_not_found"),
                    no_para: t("toast_no_para"),
                    self_transfer: t("toast_cant_self"),
                    bad_target: t("toast_bad_id"),
                };
                toast(errMap[err.message] || t("toast_generic_error"), "error");
            } finally {
                btn.disabled = false;
                btn.textContent = oldText;
            }
        });
    }

    /* ---------------- boot ---------------- */
    const LANGUAGES = [
        { code: "uz", label: "🇺🇿 O'zbekcha" },
        { code: "ru", label: "🇷🇺 Русский" },
        { code: "en", label: "🇺🇸 English" },
        { code: "ar", label: "🇸🇦 العربية" },
        { code: "id", label: "🇮🇩 Indonesia" },
        { code: "kk", label: "🇰🇿 Қазақша" },
        { code: "tr", label: "🇹🇷 Türkçe" },
        { code: "ko", label: "🇰🇷 한국어" },
    ];

    function setupLangSwitcher() {
        const btn = document.getElementById("lang-switcher-btn");
        const menu = document.getElementById("lang-switcher-menu");
        document.body.appendChild(menu);

        function renderMenu(currentLang) {
            menu.innerHTML = "";
            LANGUAGES.forEach((l) => {
                const opt = document.createElement("button");
                opt.className = "lang-option" + (l.code === currentLang ? " active" : "");
                opt.textContent = l.label;
                opt.addEventListener("click", async () => {
                    menu.classList.remove("open");
                    if (l.code === currentLang) return;
                    try {
                        const res = await api(API_BASE + "/webapp/api/set_lang", { lang: l.code });
                        applyI18n(res.ui);
                        renderMenu(res.lang);
                        const data = await api(API_BASE + "/webapp/api/profile");
                        profileCache = data;
                        applyI18n(data.ui);
                        safe(() => renderCurrencyPacks(), "renderCurrencyPacks");
                        safe(() => renderUser(data), "renderUser");
                        safe(() => renderGlobalStats(data), "renderGlobalStats");
                        safe(() => renderSubs(data), "renderSubs");
                        safe(() => renderStats(data), "renderStats");
                        safe(() => renderPara(data), "renderPara");
                        safe(() => renderProtections(data), "renderProtections");
                        safe(() => renderActiveRoleToggles(data), "renderActiveRoleToggles");
                        safe(() => renderRoles(data), "renderRoles");
                        safe(() => renderInventory(data), "renderInventory");
                        safe(() => renderShop(data), "renderShop");
                        tournamentLoaded = true;
                        safe(() => loadTournament(), "loadTournament");
                        toast(t("toast_action_done"), "success");
                    } catch (e) {
                        console.error("lang switch failed:", e);
                        toast(t("toast_generic_error"), "error");
                    }
                });
                menu.appendChild(opt);
            });
        }
        renderMenu(profileCache && profileCache.lang ? profileCache.lang : "uz");

        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = menu.classList.contains("open");
            if (isOpen) {
                menu.classList.remove("open");
                return;
            }
            const rect = btn.getBoundingClientRect();
            menu.style.top = (rect.bottom + 8) + "px";
            menu.style.right = (window.innerWidth - rect.right) + "px";
            menu.classList.add("open");
        });
        document.addEventListener("click", (e) => {
            if (!menu.contains(e.target) && e.target !== btn) menu.classList.remove("open");
        });

        return { renderMenu };
    }

    function applyI18n(ui) {
        if (!ui) return;
        UI = ui;
        document.querySelectorAll("[data-i18n]").forEach((el) => {
            const key = el.getAttribute("data-i18n");
            if (ui[key]) el.textContent = ui[key];
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
            const key = el.getAttribute("data-i18n-placeholder");
            if (ui[key]) el.placeholder = ui[key];
        });
        document.querySelectorAll("[data-i18n-title]").forEach((el) => {
            const key = el.getAttribute("data-i18n-title");
            if (ui[key]) el.title = ui[key];
        });
        document.querySelectorAll("[data-i18n-days]").forEach((el) => {
            const days = el.getAttribute("data-i18n-days");
            el.textContent = days + " " + t("label_days_short");
        });
        if (ui.webapp_title) document.title = ui.webapp_title;
    }

    function safe(fn, label) {
        try {
            return fn();
        } catch (e) {
            console.error("safe() caught in " + label + ":", e);
            return undefined;
        }
    }

    async function boot() {
        safe(setupNav, "setupNav");
        safe(setupLeaderboardTabs, "setupLeaderboardTabs");
        safe(setupTransferForm, "setupTransferForm");
        safe(setupGiftVip, "setupGiftVip");
        safe(setupParaTransfer, "setupParaTransfer");
        safe(setupAdminPanel, "setupAdminPanel");
        safe(setupSupportChat, "setupSupportChat");
        safe(() => document.getElementById("daily-claim-btn").addEventListener("click", claimDaily), "daily-claim-btn");
        const langSwitcher = safe(setupLangSwitcher, "setupLangSwitcher");
        try {
            const data = await api(API_BASE + "/webapp/api/profile");
            profileCache = data;
            safe(() => applyI18n(data.ui), "applyI18n");
            safe(() => langSwitcher && langSwitcher.renderMenu(data.lang), "langSwitcher.renderMenu");
            safe(renderCurrencyPacks, "renderCurrencyPacks");
            safe(() => renderUser(data), "renderUser");
            safe(() => renderGlobalStats(data), "renderGlobalStats");
            safe(() => { loadTournament(); tournamentLoaded = true; }, "loadTournament");
            safe(() => { loadHoliday(); holidayLoaded = true; }, "loadHoliday");
            safe(() => renderSubs(data), "renderSubs");
            safe(() => renderStats(data), "renderStats");
            safe(() => renderPara(data), "renderPara");
            safe(() => renderProtections(data), "renderProtections");
            safe(() => renderActiveRoleToggles(data), "renderActiveRoleToggles");
            safe(() => renderRoles(data), "renderRoles");
            safe(() => renderInventory(data), "renderInventory");
            safe(() => renderShop(data), "renderShop");
        } catch (e) {
            document.getElementById("user-name").textContent = t("label_error");
            document.getElementById("user-username").textContent = t("webapp_no_user");
            toast(t("toast_error_prefix") + e.message, "error");
        }
    }

    /* ---------------- auto-update: deploy bo'lganda foydalanuvchi qo'lda
       sahifani yangilamasdan, o'zi avtomatik yangi versiyani yuklab olsin ---------------- */
    let knownAppVersion = null;
    async function checkAppVersion() {
        try {
            const r = await fetch(API_BASE + "/webapp/api/version", { cache: "no-store" });
            const data = await r.json();
            if (!data || !data.version) return;
            if (knownAppVersion === null) {
                knownAppVersion = data.version;
                return;
            }
            if (data.version !== knownAppVersion) {
                location.reload();
            }
        } catch (e) { /* tarmoq muammosi — indamay o'tkazib yuboramiz */ }
    }
    checkAppVersion();
    setInterval(checkAppVersion, 30000);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") checkAppVersion();
    });

    boot();
})();
