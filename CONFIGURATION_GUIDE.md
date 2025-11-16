# Configuration Guide - WebSocket & Upload Fix

## Overview

This guide walks through the three configuration steps to fix the blank upload screen and enable large file uploads.

---

## Step 1: Streamlit Configuration (`.streamlit/config.toml`)

### What to Update

Update your `.streamlit/config.toml` file with these settings:

```toml
[browser]
gatherUsageStats = false

[server]
# Allow file uploads up to 500 MB
maxUploadSize = 500

# Allow cross-origin embedding for testing
enableCORS = false

# Allow iframe embedding
allowRunOnSave = true

# Optional: increase the websocket ping timeout if you have long-running ops
# webSocketPingInterval = 60

[logger]
level = "debug"
```

### What Each Setting Does

| Setting | Value | Purpose |
|---------|-------|---------|
| `maxUploadSize` | 500 | Allow uploads up to 500 MB (prevents Streamlit rejecting large files) |
| `enableCORS` | false | Disable CORS to allow embedding in iframes |
| `allowRunOnSave` | true | Allow app to run when files change (iframe support) |
| `webSocketPingInterval` | 60 | (Optional) Increase WebSocket ping timeout for long operations |

### How to Apply

**If running locally:**
```bash
# 1. Edit the file
nano .streamlit/config.toml

# 2. Paste the configuration above

# 3. Restart Streamlit
pkill -f streamlit
streamlit run streamlit_app.py
```

**If hosted on Streamlit Cloud:**
1. Push the updated `.streamlit/config.toml` to GitHub
2. Streamlit Cloud will automatically redeploy

**If running as a service:**
```bash
# Restart the service
sudo systemctl restart streamlit
# or
docker restart your-container
```

### Verify It Works

```bash
# Check if server is reachable
curl -I https://docubot-studio.streamlit.app

# Expected output: HTTP/2 200 (or 303 if redirecting to auth)
```

Check Streamlit logs for normal startup:
```bash
# If using systemd
journalctl -u streamlit -n 40 --no-pager

# If using Docker
docker logs your-container --tail 40
```

---

## Step 2: Parent Page HTML (Iframe Configuration)

### What to Update

Replace your current iframe with this exact code:

```html
<!-- Parent page: safe sandbox that still permits Streamlit websockets/postMessage -->
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio">
</iframe>
```

### Key Points

- ✅ **Include:** `allow-scripts`, `allow-forms`, `allow-popups`
- ❌ **DO NOT include:** `allow-same-origin` (this blocks WebSocket handshakes)
- ✅ **Include:** `min-height:720px` (ensures iframe doesn't collapse)

### Why This Works

| Attribute | Effect | Needed? |
|-----------|--------|---------|
| `allow-scripts` | Allow JavaScript execution | ✅ YES (Streamlit needs this) |
| `allow-forms` | Allow form submissions | ✅ YES (file upload) |
| `allow-popups` | Allow modals/popups | ✅ YES (Streamlit modals) |
| `allow-same-origin` | Allow same-origin access | ❌ NO (blocks WebSocket) |

### Verify It Works

1. **Open parent page in Incognito window** (disable extensions)
2. **Open DevTools:** `F12` or `Cmd+Option+I` (Mac)
3. **Go to Network tab**
4. **Filter by "WS"** (WebSocket)
5. **Reload the page**
6. **Look for:** `wss://docubot-studio.streamlit.app/_logstream`
7. **Check status:** Should show **101 Switching Protocols** (not "failed")
8. **Try uploading:** Click "Browse" or upload a PDF
9. **Verify:** Upload UI should NOT go blank

---

## Step 3: Nginx Reverse Proxy (Optional - For Production)

### When to Use

Use this if:
- You host the Streamlit app behind nginx
- You need robust production setup
- You want to serve from your own domain
- You need to handle large uploads reliably

### Nginx Configuration

Add this to your nginx `server` block:

```nginx
# inside your server {} block for yourdomain.com
location /docubot/ {
    proxy_pass https://docubot-studio.streamlit.app/;
    proxy_set_header Host docubot-studio.streamlit.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # allow large uploads
    client_max_body_size 500M;

    # WebSocket / streaming support (required by Streamlit)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # avoid buffering to support streaming uploads
    proxy_buffering off;
    proxy_request_buffering off;

    # increase timeouts for long uploads or processing
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

### What Each Setting Does

| Setting | Value | Purpose |
|---------|-------|---------|
| `client_max_body_size` | 500M | Allow 500 MB uploads |
| `proxy_http_version` | 1.1 | Enable WebSocket upgrade |
| `Upgrade` header | $http_upgrade | Pass WebSocket upgrade request |
| `Connection` header | "upgrade" | Upgrade connection to WebSocket |
| `proxy_buffering` | off | Don't buffer (support streaming) |
| `proxy_read_timeout` | 86400 | 24 hour timeout for long uploads |

### How to Apply

1. **Edit nginx config:**
```bash
sudo nano /etc/nginx/sites-available/yourdomain.com
```

2. **Add the location block** inside the `server { }` block

3. **Test config:**
```bash
sudo nginx -t
```

4. **Reload nginx:**
```bash
sudo systemctl reload nginx
```

### Update Iframe to Use Proxy

If using nginx proxy, update your iframe:

```html
<iframe
  src="https://yourdomain.com/docubot/"
  style="width:100%; height:900px; border:0;"
  title="DocuBot Studio (proxy)">
</iframe>
```

### Verify It Works

1. **Check server is reachable:**
```bash
curl -I https://yourdomain.com/docubot/
# Expected: HTTP/2 200 (not blocked by X-Frame-Options)
```

2. **Check WebSocket in DevTools:**
   - Network tab → filter "WS"
   - Should see `wss://yourdomain.com/...` with status 101

3. **Test large upload:**
   - Upload a 100-200 MB file
   - UI should NOT blank
   - Check server logs for no restarts

---

## Troubleshooting

### WebSocket Still Shows "failed"

1. **Check DevTools Console** for errors
2. **Verify iframe has correct sandbox:** `allow-scripts allow-forms allow-popups` (NO `allow-same-origin`)
3. **Try Incognito mode** (extensions can block WebSocket)
4. **Clear browser cache**

### Upload Fails or Restarts

1. **Check Streamlit logs:**
```bash
journalctl -u streamlit -n 40 --no-pager
# or
docker logs your-container --tail 40
```

2. **Look for:** "client intended to send body larger than client_max_body_size"
   - If found, increase `maxUploadSize` in Streamlit config
   - Or increase `client_max_body_size` in nginx

3. **Check file size:** Verify file is under 500 MB

### Iframe Still Blank After Upload

1. **Check console for errors:** DevTools → Console
2. **Check Network tab** for failed requests
3. **Verify OPENAI_API_KEY** is set (if using LLM features)
4. **See `UPLOAD_ISSUE_DIAGNOSIS.md`** for environment setup

### Nginx Proxy Not Working

1. **Test nginx config:**
```bash
sudo nginx -t
```

2. **Check nginx error log:**
```bash
sudo tail -f /var/log/nginx/error.log
```

3. **Verify proxy headers** are correct
4. **Check SSL certificate** is valid

---

## Quick Checklist

### Streamlit Config
- [ ] Updated `.streamlit/config.toml`
- [ ] Set `maxUploadSize = 500`
- [ ] Set `enableCORS = false`
- [ ] Restarted Streamlit app
- [ ] Verified with `curl -I` (HTTP 200)

### Parent Page HTML
- [ ] Updated iframe sandbox to `allow-scripts allow-forms allow-popups`
- [ ] Removed `allow-same-origin` from sandbox
- [ ] Tested in Incognito window
- [ ] Verified WebSocket in DevTools (status 101)
- [ ] Tested upload functionality

### Nginx (If Used)
- [ ] Added location block to nginx config
- [ ] Set `client_max_body_size 500M`
- [ ] Set WebSocket headers correctly
- [ ] Tested nginx config: `sudo nginx -t`
- [ ] Reloaded nginx: `sudo systemctl reload nginx`
- [ ] Verified with `curl -I` (HTTP 200)

---

## Reference Files

- `WEBSOCKET_FIX.md` - WebSocket troubleshooting guide
- `IMPLEMENTATION_GUIDE.md` - Copy-paste ready implementation
- `iframe-test.html` - Interactive test page
- `.streamlit/config.toml` - Streamlit configuration (updated)

---

## Summary

| Component | Change | Effect |
|-----------|--------|--------|
| Streamlit Config | `maxUploadSize = 500` | Allow 500 MB uploads |
| Streamlit Config | `enableCORS = false` | Enable iframe embedding |
| Iframe Sandbox | Remove `allow-same-origin` | Allow WebSocket connections |
| Nginx (Optional) | Add proxy config | Robust production setup |

**Result:** Upload UI renders, WebSocket works, large files upload successfully.

