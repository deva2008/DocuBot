# Quick Start: WebSocket Fix for Blank Upload Screen

## The Problem
Clicking "Upload Document" shows a blank screen because WebSocket connections (`wss://.../_logstream`) are failing inside the iframe.

## The Solution (3 Steps)

### Step 1: Test A - Quick Verification (2 minutes)

Replace your iframe with this exact code:

```html
<!-- QUICK TEST: remove sandbox entirely (debug only) -->
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  title="DocuBot Studio (test)">
</iframe>
```

**Verify it works:**
1. Open DevTools: `F12` or `Cmd+Option+I`
2. Go to **Network** tab
3. Filter by **"WS"**
4. Reload page
5. Look for `wss://docubot-studio.streamlit.app/_logstream` with status **101 Switching Protocols**

**Result:**
- ✅ Upload UI appears → WebSocket was the blocker, proceed to Step 2
- ❌ Still blank → Check headers with `curl -I https://docubot-studio.streamlit.app`

---

### Step 2: Test B - Production Fix (1 minute)

If Step 1 worked, use this for production:

```html
<!-- SAFER: allow scripts but NOT allow-same-origin -->
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio">
</iframe>
```

**Verify it works:**
1. Repeat WebSocket verification from Step 1
2. Verify upload UI appears
3. Try uploading a PDF

**Result:**
- ✅ Works → Use this in production ✅
- ❌ Still blank → Proceed to Step 3

---

### Step 3: Test C - Reverse Proxy (If A & B Fail)

If both A and B fail, you need a reverse proxy. This requires server access.

**Check if you need this:**
```bash
curl -I https://docubot-studio.streamlit.app | grep -i "x-frame-options\|content-security-policy"
```

If output shows `X-Frame-Options: DENY` or `frame-ancestors 'none'`, you must use a reverse proxy.

**Setup (nginx):**

1. Add this to your nginx config:
```nginx
location /docubot/ {
    proxy_pass https://docubot-studio.streamlit.app/;
    proxy_set_header Host docubot-studio.streamlit.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket support (CRITICAL)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    proxy_buffering off;
    proxy_read_timeout 86400;
}
```

2. Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

3. Update iframe:
```html
<iframe
  src="https://yourdomain.com/docubot/"
  style="width:100%; height:900px; border:0;"
  title="DocuBot Studio">
</iframe>
```

---

## Decision Tree

```
Step 1: Test A works?
├─ YES → Use Step 2 (Test B) for production ✅
└─ NO → Check headers with curl
   ├─ Shows X-Frame-Options: DENY? → Use Step 3 (reverse proxy)
   └─ No blocking headers? → Try Step 2 anyway
      ├─ YES → Use Step 2 for production ✅
      └─ NO → Use Step 3 (reverse proxy)
```

---

## What Changed

| Before | After |
|--------|-------|
| `sandbox="allow-scripts allow-forms allow-popups allow-same-origin"` | `sandbox="allow-scripts allow-forms allow-popups"` |
| WebSocket blocked | WebSocket allowed |
| Blank upload screen | Upload UI renders |

**Key change:** Removed `allow-same-origin` which was blocking WebSocket handshakes.

---

## Files for Reference

- **`WEBSOCKET_FIX.md`** - Comprehensive guide with troubleshooting
- **`iframe-test.html`** - Interactive test page with all three solutions
- **`IFRAME_TROUBLESHOOTING.md`** - Original troubleshooting guide

---

## Support

If still not working:
1. Check WebSocket in DevTools (Network → filter WS)
2. Check headers: `curl -I https://docubot-studio.streamlit.app`
3. Check console errors: DevTools → Console
4. Try incognito mode (extensions can block WebSocket)
5. See `WEBSOCKET_FIX.md` for detailed troubleshooting

