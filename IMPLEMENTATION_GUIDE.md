# Implementation Guide - WebSocket Fix

## 🎯 Your Situation

- ✅ App loads in iframe
- ❌ Upload button shows blank screen
- ❌ WebSocket connections failing (`wss://.../_logstream`)
- ❌ Network shows 503/404 errors

## ✅ The Fix (Copy-Paste Ready)

### Step 1: Replace Your Iframe (2 minutes)

Find your current iframe code and replace it with this:

```html
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio">
</iframe>
```

**Key change:** Removed `allow-same-origin` from sandbox.

### Step 2: Test It (1 minute)

1. Open DevTools: `F12` or `Cmd+Option+I` (Mac)
2. Go to **Network** tab
3. Filter by **"WS"** (WebSocket)
4. Reload the page
5. Look for `wss://docubot-studio.streamlit.app/_logstream`
6. Check status:
   - ✅ **101 Switching Protocols** = Success
   - ❌ **failed** = Still blocked

### Step 3: Verify Upload Works (1 minute)

1. Try uploading a PDF
2. Click "Build Index"
3. Should see success message instead of blank screen

---

## 🔍 If It Still Doesn't Work

### Option A: Try Without Sandbox (Debug)

Replace iframe with:

```html
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  title="DocuBot Studio">
</iframe>
```

If this works, the issue is sandbox-related. Go back to the safer sandbox version.

### Option B: Check Server Headers

Run this in terminal:

```bash
curl -I https://docubot-studio.streamlit.app
```

Look for:
- `X-Frame-Options: DENY` → Need reverse proxy
- `Content-Security-Policy: frame-ancestors 'none'` → Need reverse proxy
- No such headers → Sandbox issue (use safer version above)

### Option C: Use Reverse Proxy (If Headers Block Framing)

If curl shows blocking headers, you need nginx:

```nginx
location /docubot/ {
    proxy_pass https://docubot-studio.streamlit.app/;
    proxy_set_header Host docubot-studio.streamlit.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    proxy_buffering off;
    proxy_read_timeout 86400;
}
```

Then use:
```html
<iframe
  src="https://yourdomain.com/docubot/"
  style="width:100%; height:900px; border:0;"
  title="DocuBot Studio">
</iframe>
```

---

## 📊 Before & After

### Before (Broken)
```html
<iframe
  sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
  src="https://docubot-studio.streamlit.app"
  ...>
</iframe>
```
- WebSocket blocked
- Upload shows blank screen
- Network shows wss:// failed

### After (Fixed)
```html
<iframe
  sandbox="allow-scripts allow-forms allow-popups"
  src="https://docubot-studio.streamlit.app"
  ...>
</iframe>
```
- WebSocket works
- Upload UI renders
- Network shows wss:// with 101 status

---

## 🛠️ Troubleshooting Checklist

- [ ] Replaced iframe with new code
- [ ] Opened DevTools (F12)
- [ ] Went to Network tab
- [ ] Filtered by "WS"
- [ ] Reloaded page
- [ ] Found `wss://.../_logstream`
- [ ] Status shows 101 (not failed)
- [ ] Upload UI appears
- [ ] Can upload PDF without blank screen

---

## 📞 Still Having Issues?

### WebSocket Still Shows "failed"

1. Try without sandbox (Option A above)
2. If that works, issue is sandbox-related
3. If that doesn't work, check headers (Option B)
4. If headers block framing, use reverse proxy (Option C)

### Upload UI Appears But Upload Doesn't Work

1. Check browser console for errors (DevTools → Console)
2. Check Streamlit logs
3. Verify OPENAI_API_KEY is set (if using LLM features)
4. See `UPLOAD_ISSUE_DIAGNOSIS.md` for environment setup

### WebSocket Works But App Still Blank

1. Check console for JavaScript errors
2. Check Network tab for failed requests
3. Try clearing browser cache
4. Try incognito mode (extensions can block WebSocket)

---

## 📚 Reference Files

| File | Purpose |
|------|---------|
| `WEBSOCKET_FIX.md` | Comprehensive guide with all solutions |
| `QUICK_START_WEBSOCKET_FIX.md` | 3-step quick start |
| `WEBSOCKET_SOLUTION_SUMMARY.md` | Summary of the fix |
| `iframe-test.html` | Interactive test page |
| `IFRAME_TROUBLESHOOTING.md` | Original troubleshooting guide |

---

## ✨ Summary

**Problem:** WebSocket blocked by `allow-same-origin` in iframe sandbox

**Solution:** Remove `allow-same-origin` from sandbox attribute

**Result:** Upload UI renders and app works

**Code change:**
```diff
- sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
+ sandbox="allow-scripts allow-forms allow-popups"
```

That's it! 🎉

