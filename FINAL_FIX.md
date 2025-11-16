# ✅ FINAL FIX - Remove `allow-same-origin` from Iframe Sandbox

## 🎯 The Problem

Your iframe sandbox attribute includes `allow-same-origin`, which blocks WebSocket handshakes. This prevents Streamlit's client from initializing, resulting in a blank screen when users click "Browse files".

### Evidence

From your DevTools Network tab:
- ❌ `wss://docubot-studio.streamlit.app/_logstream` shows status **failed**
- ❌ Multiple **503** and **404** errors
- ❌ No **101 Switching Protocols** response

---

## ✅ Quick Fix (Copy-Paste This)

### Replace Your Current Iframe With This Exact Code

```html
<!-- Replace current iframe with this -->
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0; min-height:720px;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio">
</iframe>
```

### Key Change

**Before (Broken):**
```html
sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
```

**After (Fixed):**
```html
sandbox="allow-scripts allow-forms allow-popups"
```

**What was removed:** `allow-same-origin` ← This was blocking WebSocket handshakes

---

## 🧪 Verify It Works (5 Steps)

1. **Open DevTools:** `F12` or `Cmd+Option+I` (Mac)
2. **Go to Network tab**
3. **Filter by "WS"** (WebSocket)
4. **Reload the page**
5. **Look for:** `wss://docubot-studio.streamlit.app/_logstream`

### Expected Result

- ✅ Status shows **101 Switching Protocols** (not "failed")
- ✅ Try uploading a PDF — UI should appear (not blank screen)
- ✅ No more WebSocket connection errors in console

---

## ⚙️ Streamlit Configuration (Already Correct)

Your `.streamlit/config.toml` is already properly configured:

```toml
[server]
maxUploadSize = 500          # Allow 500 MB uploads
enableCORS = false           # Enable iframe embedding
allowRunOnSave = true        # Iframe support
```

**Status:** ✅ Already set correctly

---

## 📋 Implementation Checklist

- [ ] Find your parent page HTML file
- [ ] Locate the `<iframe>` tag for DocuBot
- [ ] Replace the entire iframe tag with the fixed code above
- [ ] Save the file
- [ ] Open the page in Incognito window (disable extensions)
- [ ] Open DevTools (F12)
- [ ] Go to Network tab
- [ ] Filter by "WS"
- [ ] Reload page
- [ ] Verify `wss://.../_logstream` shows status **101**
- [ ] Try uploading a PDF
- [ ] Verify upload UI appears (no blank screen)

---

## 🔍 What Each Sandbox Attribute Does

| Attribute | Purpose | Needed? |
|-----------|---------|---------|
| `allow-scripts` | Allow JavaScript execution | ✅ YES (Streamlit needs this) |
| `allow-forms` | Allow form submissions | ✅ YES (file upload) |
| `allow-popups` | Allow modals/popups | ✅ YES (Streamlit modals) |
| `allow-same-origin` | Allow same-origin access | ❌ NO (blocks WebSocket!) |

---

## 🚀 If You Use Nginx Reverse Proxy

If you proxy the app at `https://yourdomain.com/docubot/`, use this nginx config:

```nginx
location /docubot/ {
    # IMPORTANT: trailing slash on proxy_pass
    proxy_pass https://docubot-studio.streamlit.app/;

    proxy_set_header Host docubot-studio.streamlit.app;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebSocket support (REQUIRED)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $http_connection;

    # Avoid buffering
    proxy_buffering off;
    proxy_request_buffering off;
    
    # Increase timeouts
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

Then embed using:
```html
<iframe
  src="https://yourdomain.com/docubot/"
  style="width:100%; height:900px; border:0;"
  title="DocuBot Studio">
</iframe>
```

---

## 🎯 Why This Fix Works

| Issue | Cause | Solution |
|-------|-------|----------|
| WebSocket blocked | `allow-same-origin` in sandbox | Remove `allow-same-origin` |
| Browser warning | `allow-same-origin` + `allow-scripts` | Removing `allow-same-origin` eliminates warning |
| Upload UI blank | WebSocket can't initialize | WebSocket now works with 101 status |
| File picker doesn't appear | Streamlit client can't start | Client initializes properly now |

---

## ✨ Summary

**The Fix:**
1. Remove `allow-same-origin` from iframe sandbox attribute
2. Keep: `allow-scripts allow-forms allow-popups`
3. Verify WebSocket shows status 101 in DevTools

**Result:**
- ✅ Upload UI renders properly
- ✅ WebSocket connections work
- ✅ File picker appears when clicking "Browse files"
- ✅ Users can upload PDFs successfully

**Time to implement:** 2 minutes

---

## 📞 If It Still Doesn't Work

1. **Clear browser cache** (Ctrl+Shift+Delete or Cmd+Shift+Delete)
2. **Try Incognito window** (extensions can block WebSocket)
3. **Check DevTools Console** for error messages
4. **Verify nginx config** if using reverse proxy
5. **Check Streamlit logs** for server errors

See `DIAGNOSTIC_GUIDE.md` for detailed troubleshooting.

