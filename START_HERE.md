# START HERE - WebSocket Debug & Fix

## 🚀 Do This Right Now (5 Minutes)

### Step 1: Open Test Page

Open this file in your browser:
```
IFRAME_TEST_TEMPLATE.html
```

This page has **Test 1 (no sandbox)** already active.

### Step 2: Test Browse Files

1. In the iframe on that page, try clicking **"Browse files"**
2. Does it work or does the iframe go blank?

### Step 3: Check WebSocket

1. Open DevTools: `F12` or `Cmd+Option+I` (Mac)
2. Go to **Network** tab
3. Filter by **"WS"** (WebSocket)
4. Reload the page
5. Look for `wss://docubot-studio.streamlit.app/_logstream`
6. Check the status:
   - ✅ **101 Switching Protocols** = WebSocket works
   - ❌ **failed** = WebSocket blocked

### Step 4: Report Results

**If Browse files works AND WebSocket shows 101:**
```
✅ SUCCESS! Sandbox is the blocker.
→ Use the "Test 2 (Safe Sandbox)" code in your production iframe
→ Done!
```

**If Browse files blanks OR WebSocket shows failed:**
```
❌ WebSocket still blocked.
→ Copy the full failing WebSocket URL from DevTools
→ Capture last 40 lines of Streamlit server logs
→ Paste both here for exact fix
```

---

## 📋 What to Paste If It Fails

If Test 1 fails, paste these two things:

### 1. Full WebSocket URL
In DevTools → Network tab, right-click the failing WS entry → Copy → Copy link address

Example:
```
wss://docubot-studio.streamlit.app/~/logstream
```

### 2. Streamlit Server Logs (Last 40 Lines)
```bash
# If running locally, check your terminal

# If using systemd:
journalctl -u streamlit -n 40 --no-pager

# If using Docker:
docker logs your-container --tail 40
```

---

## 📚 Files to Reference

| File | Purpose |
|------|---------|
| `IFRAME_TEST_TEMPLATE.html` | **USE THIS** - Interactive test page |
| `DIAGNOSTIC_GUIDE.md` | Complete troubleshooting guide |
| `nginx.conf.example` | Nginx reverse proxy configuration |
| `QUICK_REFERENCE.md` | Quick reference card |
| `CONFIGURATION_GUIDE.md` | Step-by-step configuration |

---

## 🎯 Expected Outcomes

### Outcome 1: Test 1 Works (Best Case)
- Browse files renders without blanking
- WebSocket shows status 101
- **Action:** Use Test 2 (safe sandbox) code in production

### Outcome 2: Test 1 Fails (Needs Diagnosis)
- Browse files blanks or WebSocket shows failed
- **Action:** Paste WebSocket URL and Streamlit logs for exact fix

---

## ⚡ Quick Fixes (Most Likely)

### Fix 1: Remove `allow-same-origin` from Sandbox
```html
<!-- WRONG (blocks WebSocket) -->
<iframe sandbox="allow-scripts allow-forms allow-popups allow-same-origin" ...>

<!-- RIGHT (allows WebSocket) -->
<iframe sandbox="allow-scripts allow-forms allow-popups" ...>
```

### Fix 2: Nginx Proxy Path Rewriting
If WebSocket URL shows `/~/logstream`, add to nginx:
```nginx
location /docubot/ {
    rewrite ^/docubot/~/(.*)$ /$1 break;
    proxy_pass https://docubot-studio.streamlit.app/;
    ...
}
```

### Fix 3: Nginx Trailing Slash
```nginx
# WRONG (no trailing slash)
proxy_pass https://docubot-studio.streamlit.app;

# RIGHT (with trailing slash)
proxy_pass https://docubot-studio.streamlit.app/;
```

---

## 📞 Support

**For detailed help:**
- See `DIAGNOSTIC_GUIDE.md` for complete troubleshooting
- See `CONFIGURATION_GUIDE.md` for step-by-step setup
- See `nginx.conf.example` for proxy configuration

**Quick commands:**
```bash
# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check Streamlit logs
journalctl -u streamlit -n 40 --no-pager
```

---

## ✨ Summary

1. **Open `IFRAME_TEST_TEMPLATE.html`** in browser
2. **Try clicking "Browse files"** in the iframe
3. **Check WebSocket** in DevTools (Network → filter WS)
4. **Report results:**
   - ✅ Works? Use Test 2 code in production
   - ❌ Fails? Paste WebSocket URL and logs

**Commit:** `d67a122`

