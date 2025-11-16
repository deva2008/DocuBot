# WebSocket Connection Fix - Streamlit Iframe Blank Screen

## 🔴 Root Cause

The blank screen on upload is caused by **Streamlit's WebSocket connection failing** inside the iframe. The iframe sandbox configuration blocks WebSocket handshakes (`wss://.../_logstream`), preventing the Streamlit client from initializing.

**Evidence from your Network tab:**
- Multiple `wss://.../_logstream` connections showing `failed`
- Repeated `503` and `404` errors
- No `101 Switching Protocols` response

---

## ✅ Three Solutions (Test in Order)

### Solution A: Quick Test — Remove Sandbox (Debug Only)

**Use this to confirm WebSocket is the blocker:**

```html
<!-- QUICK TEST: remove sandbox entirely (debug only) -->
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  title="DocuBot Studio (test)">
</iframe>
```

**What to expect:**
- ✅ Upload UI renders (no white screen)
- ✅ DevTools → Network → filter "WS" shows `wss://.../_logstream` with status `101 Switching Protocols`
- ✅ Console errors about WebSocket failures disappear

**If this works:** Move to Solution B for production.

---

### Solution B: Safer Sandbox (Recommended Production)

**Use this in production. Allows WebSocket while keeping sandbox protection:**

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

**Why this works:**
- `allow-scripts` → Streamlit JavaScript runs
- `allow-forms` → Form submissions work
- `allow-popups` → Modals/popups work
- **NO** `allow-same-origin` → Prevents sandbox escape (secure)

**Key insight:** Removing `allow-same-origin` prevents browser warnings while still allowing WebSocket connections. Streamlit only needs scripts and postMessage, not same-origin access.

**What to expect:**
- ✅ Upload UI renders
- ✅ WebSocket connection succeeds
- ✅ No console warnings about sandbox

**If this works:** Use this configuration in production. ✅

**If this fails:** Try Solution C (reverse proxy).

---

### Solution C: Reverse Proxy (Robust Production Option)

**Use if:**
- Solutions A & B both fail
- You need same-origin access
- Host blocks framing via `X-Frame-Options` or CSP headers

#### Step 1: Configure Nginx Reverse Proxy

Add this to your nginx server block:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # Add your SSL certificate configuration here
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

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
}
```

#### Step 2: Reload Nginx

```bash
sudo nginx -t  # Test config
sudo systemctl reload nginx
```

#### Step 3: Update Iframe to Use Proxied URL

```html
<iframe
  src="https://yourdomain.com/docubot/"
  style="width:100%; height:900px; border:0;"
  title="DocuBot Studio (proxy)">
</iframe>
```

**Why this works:**
- Browser sees same-origin → no CORS issues
- WebSocket upgrade headers are preserved
- X-Frame-Options headers from upstream are bypassed
- Streaming and postMessage work reliably

---

## 🔍 Verification Steps

### Step 1: Check WebSocket Connection

1. Open DevTools: `F12` or `Cmd+Option+I` (Mac)
2. Go to **Network** tab
3. Filter by **"WS"** (WebSocket)
4. Reload the page or enable a test
5. Look for `wss://docubot-studio.streamlit.app/_logstream`
6. Check the status:
   - ✅ **101 Switching Protocols** = Success
   - ❌ **failed** or missing = Blocked

### Step 2: Check Response Headers

```bash
curl -I https://docubot-studio.streamlit.app
```

Look for:
- `X-Frame-Options: DENY` or `SAMEORIGIN` → Blocks framing (use reverse proxy)
- `Content-Security-Policy: frame-ancestors 'none'` → Blocks framing (use reverse proxy)
- No such headers → Framing is allowed

### Step 3: Check Console for Errors

Open DevTools → **Console** tab. Look for:
- `WebSocket connection to 'wss://...' failed` → WebSocket is blocked
- `Refused to frame '...'` → Framing is blocked
- `Uncaught SyntaxError` → JavaScript execution issue

---

## 📋 Quick Decision Tree

```
Does Test A (no sandbox) work?
├─ YES → App loads, WebSocket succeeds
│  └─ Use Test B (safer sandbox) for production ✅
└─ NO → WebSocket is still blocked
   ├─ Check curl headers
   │  ├─ X-Frame-Options: DENY? → Use reverse proxy (C)
   │  └─ No blocking headers? → Check network/firewall
   └─ Try Test B anyway (sometimes works despite A failing)
      ├─ YES → Use Test B for production ✅
      └─ NO → Must use reverse proxy (C)
```

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Test A works but Test B doesn't | Sandbox is too restrictive | Check if `allow-same-origin` is needed (unlikely) |
| WebSocket shows `failed` in Network | Sandbox blocks WebSocket | Try Test A first, then Test B |
| WebSocket shows `503` or `404` | Upstream server issue | Check if app is running/deployed |
| Console shows "Refused to frame" | X-Frame-Options header | Use reverse proxy (C) |
| Upload UI renders but no interaction | postMessage blocked | Ensure `allow-scripts` is in sandbox |
| App works locally but not in production | CORS or header differences | Check production server headers |

---

## 🚀 Implementation Checklist

### For Test A (Quick Verification)
- [ ] Replace iframe with no-sandbox version
- [ ] Open DevTools → Network → filter WS
- [ ] Reload page
- [ ] Verify `wss://.../_logstream` shows `101 Switching Protocols`
- [ ] Verify upload UI renders

### For Test B (Production)
- [ ] Update iframe sandbox to `allow-scripts allow-forms allow-popups`
- [ ] Remove `allow-same-origin`
- [ ] Test in browser
- [ ] Verify WebSocket connection succeeds
- [ ] Deploy to production

### For Test C (Reverse Proxy)
- [ ] Add nginx location block
- [ ] Test nginx config: `sudo nginx -t`
- [ ] Reload nginx: `sudo systemctl reload nginx`
- [ ] Update iframe src to proxied URL
- [ ] Test in browser
- [ ] Verify WebSocket connection succeeds

---

## 📚 Reference: Sandbox Attributes

| Attribute | Effect | Needed for Streamlit? |
|-----------|--------|----------------------|
| `allow-scripts` | Allow JavaScript execution | ✅ YES |
| `allow-forms` | Allow form submissions | ✅ YES |
| `allow-popups` | Allow modals/popups | ✅ YES |
| `allow-same-origin` | Allow same-origin access | ❌ NO (causes warnings) |
| `allow-top-navigation` | Allow navigation to parent | ❌ NO |
| `allow-pointer-lock` | Allow pointer lock | ❌ NO |

**Recommended:** `sandbox="allow-scripts allow-forms allow-popups"`

---

## 🔐 Security Notes

- **Solution A (no sandbox):** Only for testing. Never use in production.
- **Solution B (safer sandbox):** Safe for production. Prevents sandbox escape.
- **Solution C (reverse proxy):** Most secure. Proxy is under your control.

---

## 📞 Still Having Issues?

1. **Check WebSocket:** DevTools → Network → filter WS
2. **Check headers:** `curl -I https://docubot-studio.streamlit.app`
3. **Check console:** DevTools → Console for error messages
4. **Try incognito:** Extensions sometimes block WebSocket
5. **Clear cache:** Browser cache can cause issues

