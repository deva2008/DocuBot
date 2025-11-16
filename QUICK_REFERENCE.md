# Quick Reference Card

## 🎯 The Problem
Upload button shows blank screen → WebSocket blocked → Streamlit client can't initialize

## ✅ The Solution (3 Parts)

### Part 1: Streamlit Config
**File:** `.streamlit/config.toml`
```toml
[server]
maxUploadSize = 500
enableCORS = false
allowRunOnSave = true
```
**Action:** Restart Streamlit app

### Part 2: Iframe HTML
**Replace your iframe with:**
```html
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio">
</iframe>
```
**Key:** NO `allow-same-origin` in sandbox

### Part 3: Nginx (Optional)
**If using nginx, add:**
```nginx
location /docubot/ {
    proxy_pass https://docubot-studio.streamlit.app/;
    proxy_set_header Host docubot-studio.streamlit.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    client_max_body_size 500M;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
    proxy_request_buffering off;
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

---

## 🔍 Verification (5 Steps)

1. **Open DevTools:** `F12` or `Cmd+Option+I`
2. **Go to Network tab**
3. **Filter by "WS"** (WebSocket)
4. **Reload page**
5. **Look for:** `wss://.../_logstream` with status **101 Switching Protocols**

✅ = Success | ❌ = Still blocked

---

## 📋 Checklist

- [ ] Updated `.streamlit/config.toml`
- [ ] Restarted Streamlit
- [ ] Updated iframe (no `allow-same-origin`)
- [ ] Verified WebSocket (status 101)
- [ ] Tested upload (no blank screen)
- [ ] (Optional) Configured nginx

---

## 🚀 Restart Commands

**Local:**
```bash
pkill -f streamlit && streamlit run streamlit_app.py
```

**Service:**
```bash
sudo systemctl restart streamlit
```

**Docker:**
```bash
docker restart your-container
```

---

## 🐛 If Still Broken

| Issue | Check |
|-------|-------|
| WebSocket "failed" | Iframe sandbox correct? No `allow-same-origin`? |
| Upload blanks | DevTools Console for errors |
| Large file fails | `maxUploadSize = 500` set? File < 500 MB? |
| Nginx not working | `sudo nginx -t` | `sudo tail -f /var/log/nginx/error.log` |

---

## 📚 Full Docs

- `CONFIGURATION_GUIDE.md` - Complete setup guide
- `WEBSOCKET_FIX.md` - Troubleshooting
- `ACTION_SUMMARY.md` - What changed
- `iframe-test.html` - Interactive test

---

## ⚡ TL;DR

1. Update `.streamlit/config.toml` (maxUploadSize=500, enableCORS=false)
2. Restart Streamlit
3. Update iframe: `sandbox="allow-scripts allow-forms allow-popups"` (NO allow-same-origin)
4. Verify: DevTools → Network → WS → look for 101 status
5. Done! ✅

