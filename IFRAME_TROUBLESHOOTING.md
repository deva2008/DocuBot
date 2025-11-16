# DocuBot Studio - Iframe Embedding Troubleshooting Guide

## Quick Start

1. **Open the test page** in your browser:
   ```
   file:///Users/pavandevarapalli/Documents/DocuBots/DocuBot/iframe-test.html
   ```

2. **Follow the tests in order** to identify the blocker.

---

## Step-by-Step Fixes

### Step 1: Fast Test — Remove Sandbox (Temporary)
**Status in test page:** Test 1 (ACTIVE by default)

The test page loads this by default:
```html
<iframe
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0;"
  title="DocuBot Studio (test)">
</iframe>
```

**Result:**
- ✅ **App loads** → Sandbox is the blocker. Proceed to Step 2.
- ❌ **App doesn't load** → Issue is not sandbox. Check WebSocket (Step 5) or headers (Step 4).

---

### Step 2: Safer Fix — Keep Sandbox but Remove `allow-same-origin` (RECOMMENDED)
**Status in test page:** Test 2 (Click "Enable Test 2" button)

Use this configuration:
```html
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio">
</iframe>
```

**Why this works:**
- `allow-scripts` → Streamlit JavaScript runs
- `allow-forms` → Form submissions work
- `allow-popups` → Popups/modals work
- **No** `allow-same-origin` → Prevents sandbox escape (secure)

**Storage isolation:** The iframe cannot access parent's cookies or localStorage (safe).

**Result:**
- ✅ **App loads** → Use this in production!
- ❌ **App doesn't load** → Check Step 3 (iframeResizer) or Step 4 (headers).

---

### Step 3: If You Use iframeResizer (Auto-sizing)
**Status in test page:** Test 3 (Click "Enable Test 3" button)

If your parent page auto-sizes iframes based on content:

```html
<!-- Parent page -->
<script src="/path/to/iframeResizer.min.js"></script>

<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:1px; min-width:100%; height:900px; border:0;"
  sandbox="allow-scripts allow-forms allow-popups"
  title="DocuBot Studio"></iframe>

<script>
  iFrameResize({ log: false, checkOrigin: false }, '#docubot');
</script>
```

**Important:** Serve `iframeResizer.min.js` locally or from a trusted CDN.

---

### Step 4: If Host Blocks Framing via Headers (Reverse Proxy)
**Status in test page:** Test 4 (Click "Check Headers" button)

**Check for blocking headers:**
```bash
curl -I https://docubot-studio.streamlit.app
```

Look for:
- `X-Frame-Options: DENY` or `SAMEORIGIN`
- `Content-Security-Policy: frame-ancestors 'none'`

**If headers block framing, use a reverse proxy:**

#### Nginx Example:
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # SSL directives (ensure ssl_certificate and ssl_certificate_key are set)

    location /docubot/ {
        proxy_pass https://docubot-studio.streamlit.app/;
        proxy_set_header Host docubot-studio.streamlit.app;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Then embed using your proxied URL:
```html
<iframe 
  src="https://yourdomain.com/docubot/" 
  style="width:100%; height:900px; border:0;" 
  title="DocuBot Studio">
</iframe>
```

---

### Step 5: Streamlit Config (If You Host the App)
**File:** `.streamlit/config.toml`

If you control the Streamlit app and want to disable CORS for testing:
```toml
[server]
enableCORS = false
```

**⚠️ Warning:** Only for testing. Re-enable in production.

---

### Step 6: WebSocket Check
**Status in test page:** Test 5 (See instructions)

Streamlit requires WebSocket (wss://) connections.

**How to check:**
1. Open DevTools: `F12` or `Cmd+Option+I` (Mac)
2. Go to **Network** tab
3. Filter by **"WS"** (WebSocket)
4. Enable Test 1 or Test 2 above
5. Look for `wss://` connections

**Result:**
- ✅ **wss:// connection succeeds** → WebSocket is OK
- ❌ **No wss:// appears or fails** → WebSocket is blocked (likely by proxy/firewall)

---

### Step 7: Clean Up Allow Attribute Warnings
If your iframe has an `allow` attribute with many tokens, simplify it:

**Remove noisy tokens:**
```html
<!-- Avoid unsupported allow tokens -->
<iframe src="..." allow="" ...></iframe>
```

**Or only allow needed features:**
```html
allow="microphone; camera; geolocation"
```

---

## Decision Tree

```
Does the app load in Test 1 (no sandbox)?
├─ YES → Go to Step 2 (safer sandbox)
│  └─ Does app load in Test 2 (safer sandbox)?
│     ├─ YES → ✅ Use Step 2 config in production
│     └─ NO → Check Step 4 (headers) or Step 5 (WebSocket)
└─ NO → Check Step 4 (headers) or Step 5 (WebSocket)
```

---

## Production Checklist

- [ ] Test 2 (safer sandbox) works
- [ ] WebSocket connections (wss://) succeed
- [ ] No X-Frame-Options or CSP blocking headers
- [ ] Use this iframe config:
  ```html
  <iframe
    id="docubot"
    src="https://docubot-studio.streamlit.app"
    style="width:100%; height:900px; border:0;"
    sandbox="allow-scripts allow-forms allow-popups"
    title="DocuBot Studio">
  </iframe>
  ```
- [ ] If headers block framing, set up reverse proxy
- [ ] If auto-sizing needed, add iframeResizer (Step 3)

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| App loads in Test 1 but not Test 2 | Sandbox is too restrictive | Use Step 2 config or check CSP |
| App doesn't load in either test | Headers block framing | Use reverse proxy (Step 4) |
| App loads but WebSocket fails | Proxy/firewall blocks wss:// | Configure proxy to support WebSocket |
| Iframe appears but is blank | CORS or CSP issue | Check headers, disable CORS in Streamlit config |
| "Refused to frame" error in console | X-Frame-Options header | Use reverse proxy or contact host |

---

## Need Help?

1. **Check browser console** (F12 → Console tab) for error messages
2. **Check Network tab** for failed requests or WebSocket failures
3. **Run header check** (Step 4) to see what headers are blocking
4. **Share the error message** from console or network tab

