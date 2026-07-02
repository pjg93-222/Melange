# -*- coding: utf-8 -*-
"""Lock the Moneyball dashboard behind ONE password.
AES-256-GCM encrypts the entire self-contained HTML (key = PBKDF2-SHA256 of the password, 250k iters) and
wraps it in a self-decrypting page using the browser's built-in Web Crypto (no external libs). Safe to host
anywhere (even a public URL); only the password decrypts it, in-browser.
Usage:  python fec/lock_dashboard.py "your-password"     (omit to auto-generate a strong one)
"""
import sys, os, base64, hashlib, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SRC = B + r'\Moneyball.html'
OUT = B + r'\deploy\index.html'
ITERS = 250000

pw = sys.argv[1] if len(sys.argv) > 1 else '-'.join(secrets.token_hex(2) for _ in range(4))
html = open(SRC, encoding='utf-8').read().encode('utf-8')
salt = os.urandom(16); iv = os.urandom(12)
key = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, ITERS, dklen=32)
ct = AESGCM(key).encrypt(iv, html, None)
b = lambda x: base64.b64encode(x).decode()

WRAP = r'''<!DOCTYPE html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><meta name=referrer content=no-referrer><title>Moneyball — locked</title>
<style>html,body{margin:0;height:100%;background:#0d1117;color:#e6edf3;font:16px system-ui,Segoe UI,sans-serif}.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center}.box{width:90%;max-width:340px;text-align:center;padding:22px}h2{font-weight:700;margin:0 0 4px}p{color:#8b949e;font-size:13px;margin:6px 0 14px}input{width:100%;padding:13px;font-size:16px;border-radius:9px;border:1px solid #30363d;background:#161b22;color:#e6edf3;box-sizing:border-box}button{margin-top:12px;width:100%;padding:13px;font-size:16px;border-radius:9px;border:0;background:#1f6feb;color:#fff;font-weight:600;cursor:pointer}button:disabled{opacity:.5}.err{color:#ef4444;min-height:18px;font-size:13px;margin-top:10px;line-height:1.4}.note{color:#6e7681;font-size:11px}</style></head>
<body><div class=wrap><div class=box><h2>&#128274; Moneyball Dashboard</h2><p>Enter the password to view. <span class=note>(case-sensitive)</span></p>
<input id=pw type=text autocapitalize=none autocorrect=off autocomplete=off spellcheck=false placeholder=Password autofocus><button id=go>Unlock</button><div class=err id=err></div></div></div>
<script>
var D={s:"__SALT__",i:"__IV__",c:"__CT__",n:__ITERS__};
var err=document.getElementById('err'),go=document.getElementById('go');
function u8(x){return Uint8Array.from(atob(x),function(c){return c.charCodeAt(0);});}
var SECURE=!!(window.crypto&&window.crypto.subtle);
if(!SECURE){err.textContent='⚠ This must be opened from the https:// link. On a plain http:// address (or a file sent directly) the browser blocks decryption — use the https link.';go.disabled=true;}
async function unlock(){if(!SECURE)return;err.textContent='Decrypting…';
 try{
  var pw=document.getElementById('pw').value.trim().replace(/[‐-―−]/g,'-');  // fix smart-dashes + stray spaces
  if(!pw){err.textContent='Enter the password.';return;}
  var enc=new TextEncoder();
  var bk=await crypto.subtle.importKey('raw',enc.encode(pw),'PBKDF2',false,['deriveBits']);
  var bits=await crypto.subtle.deriveBits({name:'PBKDF2',salt:u8(D.s),iterations:D.n,hash:'SHA-256'},bk,256);
  var key=await crypto.subtle.importKey('raw',bits,{name:'AES-GCM'},false,['decrypt']);
  var pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:u8(D.i)},key,u8(D.c));
  document.open();document.write(new TextDecoder().decode(pt));document.close();
 }catch(e){err.textContent='Wrong password — check capitalization and spacing (you can see it above as you type).';}}
go.onclick=unlock;
document.getElementById('pw').addEventListener('keydown',function(e){if(e.key==='Enter')unlock();});
</script></body></html>'''

out = (WRAP.replace('__SALT__', b(salt)).replace('__IV__', b(iv))
           .replace('__CT__', b(ct)).replace('__ITERS__', str(ITERS)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(out)
print('LOCKED -> %s  (%.1f MB)' % (OUT, os.path.getsize(OUT) / 1048576))
print('PASSWORD: %s' % pw)
