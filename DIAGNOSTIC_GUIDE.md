# Diagnostic Guide - WebSocket & Iframe Issues

## 🎯 Quick Action Plan (Do This Now)

### Step 1: Test No-Sandbox Iframe (5 minutes)

1. Open `IFRAME_TEST_TEMPLATE.html` in your browser
2. This page already has Test 1 (no sandbox) active
3. Try clicking "Browse files" in the iframe
4. Open DevTools: `F12` or `Cmd+Option+I`
5. Go to **Network** tab
6. Filter by **"WS"** (WebSocket)
7. Reload the page
8. Look for `wss://docubot-studio.streamlit.app/_logstream`

### Step 2: Report Results

**If Browse files works and WebSocket shows 101:**
- ✅ Sandbox is the blocker
- Use Test 2 (safe sandbox) code in your production iframe
- Done!

**If Browse files still blanks or WebSocket shows failed:**
- ❌ Issue is deeper (proxy path rewriting or headers)
- Proceed to Step 3

### Step 3: Capture Diagnostic Info

If Test 1 fails, capture these two things:

**A. Full failing WebSocket URL:**
1. In DevTools → Network tab, find the failing WS entry
2. Right-click it → Copy → Copy link address
3. Paste the full URL here (example: `wss://docubot-studio.streamlit.app/~/logstream`)

**B. Streamlit server logs (last 40 lines):**
```bash
# If running locally, check console output
# If using systemd:
journalctl -u streamlit -n 40 --no-pager

# If using Docker:
docker logs your-container --tail 40
```

---

## 🔍 What Each Diagnostic Tells Us

### WebSocket Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| **101 Switching Protocols** | ✅ WebSocket working | Use safe sandbox, you're done |
| **failed** | ❌ WebSocket blocked | Check sandbox, proxy, or headers |
| **(no WS entry)** | ❌ WebSocket not attempted | Sandbox or postMessage blocked |
| **503 Service Unavailable** | ❌ Upstream server issue | Check Streamlit logs |
| **404 Not Found** | ❌ Path rewriting issue | Check nginx proxy path |

### WebSocket URL Patterns

| URL Pattern | Meaning | Fix |
|-------------|---------|-----|
| `wss://docubot-studio.streamlit.app/_logstream` | ✅ Correct | Should work |
| `wss://docubot-studio.streamlit.app/~/logstream` | ❌ Path rewrite issue | Add nginx rewrite rule |
| `wss://yourdomain.com/docubot/~/logstream` | ❌ Proxy path issue | Check proxy_pass trailing slash |
| `wss://yourdomain.com/docubot/_logstream` | ✅ Correct (proxied) | Should work |

### Streamlit Log Patterns

| Log Entry | Meaning | Action |
|-----------|---------|--------|
| `REBOOTING` | Server crashed/restarted | Check error above it |
| `Traceback` | Error occurred | Read the error message |
| `client intended to send body larger than client_max_body_size` | Upload too large | Increase `client_max_body_size` in nginx |
| `WebSocket connection failed` | Client-side error | Check browser console |
| `(no errors)` | Server OK | Issue is client-side or proxy |

---

## 🛠️ Common Fixes

### Fix 1: Remove `allow-same-origin` from Sandbox

**Before (broken):**
```html
<iframe sandbox="allow-scripts allow-forms allow-popups allow-same-origin" ...>
```

**After (fixed):**
```html
<iframe sandbox="allow-scripts allow-forms allow-popups" ...>
```

**Why:** `allow-same-origin` + `allow-scripts` blocks WebSocket handshakes.

---

### Fix 2: Nginx Proxy Path Rewriting

**If WebSocket URL shows `/~/logstream`:**

Add this rewrite rule to your nginx location block:

```nginx
location /docubot/ {
    # Strip /docubot/ and remove any "~/" inserted
    rewrite ^/docubot/~/(.*)$ /$1 break;

    proxy_pass https://docubot-studio.streamlit.app/;
    ... (rest of config)
}
```

---

### Fix 3: Nginx Trailing Slash

**Before (broken):**
```nginx
proxy_pass https://docubot-studio.streamlit.app;  # No trailing slash
```

**After (fixed):**
```nginx
proxy_pass https://docubot-studio.streamlit.app/;  # Trailing slash
```

**Why:** Without trailing slash, nginx may not append the path correctly, causing `/docubot/foo` to become `/docubot/foo` instead of `/foo`.

---

### Fix 4: Streamlit Config

**File:** `.streamlit/config.toml`

```toml
[server]
maxUploadSize = 500
enableCORS = false
```

**Then restart:**
```bash
pkill -f streamlit && streamlit run streamlit_app.py
```

---

## 📊 Decision Tree

```
Does Test 1 (no sandbox) work?
├─ YES: Browse files renders, WebSocket shows 101
│  └─ Use Test 2 (safe sandbox) code in production ✅
│
└─ NO: Browse files blanks or WebSocket shows failed
   ├─ Check WebSocket URL in DevTools
   │  ├─ Contains /~/logstream?
   │  │  └─ Nginx path rewriting issue → Add rewrite rule
   │  │
   │  ├─ Shows 503 or 404?
   │  │  └─ Check Streamlit logs for errors
   │  │
   │  └─ Shows "failed"?
   │     ├─ Check browser console for errors
   │     ├─ Try Incognito mode (extensions can block)
   │     └─ Check X-Frame-Options header (curl -I)
   │
   └─ Check Streamlit logs
      ├─ Contains "REBOOTING" or Traceback?
      │  └─ Fix the error shown
      │
      ├─ Contains "client intended to send body larger"?
      │  └─ Increase client_max_body_size in nginx
      │
      └─ No errors?
         └─ Issue is client-side or proxy headers
```

---

## 🔧 Testing Commands

### Check WebSocket in Browser

```javascript
// Paste in DevTools Console to test WebSocket
const ws = new WebSocket('wss://docubot-studio.streamlit.app/_logstream');
ws.onopen = () => console.log('✅ WebSocket connected');
ws.onerror = (e) => console.log('❌ WebSocket error:', e);
ws.onmessage = (e) => console.log('📨 Message:', e.data);
```

### Check Nginx Config

```bash
# Test nginx config syntax
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Check nginx access log
sudo tail -f /var/log/nginx/access.log
```

### Check Streamlit Logs

```bash
# If running locally
# (check your terminal where you ran `streamlit run`)

# If using systemd
journalctl -u streamlit -n 100 --no-pager

# If using Docker
docker logs your-container --tail 100
```

### Check Response Headers

```bash
# Check if Streamlit app is reachable
curl -I https://docubot-studio.streamlit.app

# Check if nginx proxy is working
curl -I https://yourdomain.com/docubot/

# Look for X-Frame-Options or CSP headers
curl -I https://docubot-studio.streamlit.app | grep -i "x-frame\|content-security"
```

---

## 📋 Checklist for Debugging

- [ ] Opened `IFRAME_TEST_TEMPLATE.html`
- [ ] Tried clicking "Browse files" in Test 1 (no sandbox)
- [ ] Opened DevTools (F12)
- [ ] Went to Network tab
- [ ] Filtered by "WS" (WebSocket)
- [ ] Reloaded page
- [ ] Found `wss://.../_logstream` entry
- [ ] Checked status (101 = good, failed = bad)
- [ ] If failed, copied full WebSocket URL
- [ ] If failed, captured Streamlit logs (last 40 lines)
- [ ] Pasted both pieces of info for diagnosis

---

## 📞 What to Paste If You Need Help

If Test 1 fails, paste these two things:

**1. Full failing WebSocket URL:**
```
(Example: wss://docubot-studio.streamlit.app/~/logstream)
```

**2. Last 40 lines of Streamlit server log:**
```
(Paste the output from journalctl or docker logs)
```

With these two pieces of info, I can give you the exact fix.

---

## ✨ Summary

1. **Test 1 (no sandbox)** rules out sandbox issues
2. **WebSocket URL** tells us if proxy is rewriting paths
3. **Streamlit logs** tell us if server is crashing
4. **Response headers** tell us if upstream blocks framing

**Most likely fixes:**
- Remove `allow-same-origin` from sandbox
- Add trailing slash to nginx `proxy_pass`
- Add nginx rewrite rule if URL contains `/~/`
- Increase `client_max_body_size` if uploads fail

