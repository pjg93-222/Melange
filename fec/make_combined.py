# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""
Combines the SNA network dashboard (Moneyball Dashboard.html) and the member desk
(cu-member-desk.html) into ONE self-contained file: Moneyball.html.

Design for a clean merge + minimal antivirus false-positives:
- Single file, NO external loads (no CDN/fonts/script-src), no eval/new Function/document.write.
- Each app's JS is wrapped in its own IIFE (so the two scripts can't collide on globals),
  exposing only a few cross-app hooks on window.
- The SNA stylesheet is scoped under #app-network so its bare-element rules (body/select/header)
  don't bleed into the member desk; the member stylesheet stays global.
- The one ID collision (backbtn) is renamed in the member chunk.
- The SNA "Member details" button and the member "Network view" links switch views in-page
  (no navigation); going back to the network re-selects the member you were viewing.

Run:  python fec/make_combined.py     (after make_dashboard_html.py + make_member_desk.py)
"""
import re, io, os
B = MB_ROOT
def read(p): return io.open(os.path.join(B, p), encoding='utf-8').read()

sna = read('Moneyball Dashboard.html')
md  = read('cu-member-desk.html')

def extract(t):
    css  = re.search(r'<style>(.*?)</style>', t, re.S).group(1)
    body = re.search(r'<body[^>]*>(.*?)<script>', t, re.S).group(1)
    js   = re.search(r'<script>(.*?)</script>', t, re.S).group(1)
    return css, body, js

snacss, snabody, snajs = extract(sna)
mdcss,  mdbody,  mdjs  = extract(md)

# ---- ID collision guard (scan body AND js, since some ids are built in script templates) ----
def ids(t):
    return set(re.findall(r'\bid=([A-Za-z0-9_-]+)', t)) | set(re.findall(r'\bid="([^"]+)"', t))
collide = ids(snabody + snajs) & ids(mdbody + mdjs)
print('id collisions:', sorted(collide))
assert collide <= {'backbtn'}, 'Unexpected id collision(s): %s — handle before merging.' % (collide - {'backbtn'})
# rename the member-desk backbtn everywhere in the member chunks (ID attr is emitted from JS;
# the .backbtn class is member-only and stays). SNA keeps its own #backbtn.
mdbody = mdbody.replace('id=backbtn', 'id=mdback')
mdjs   = mdjs.replace('id=backbtn', 'id=mdback').replace("'#backbtn'", "'#mdback'")

# ---- scope the (flat) SNA CSS under #app-network ----
def scope_sna(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    def scope_flat(block):                                  # scope selectors in a block with no @media
        out = []
        for chunk in block.split('}'):
            chunk = chunk.strip()
            if not chunk or '{' not in chunk:
                continue
            sel, decl = chunk.split('{', 1)
            sels = []
            for s in sel.split(','):
                s = s.strip()
                if not s: continue
                if s == '*':              sels.append('#app-network *')
                elif s in ('body','html'):sels.append('#app-network')
                else:                     sels.append('#app-network ' + s)
            out.append(','.join(sels) + '{' + decl + '}')
        return '\n'.join(out)
    # walk top-level; preserve @media wrappers (scope their INNER selectors, keep the @media{...}) so
    # responsive rules survive scoping — the old split-on-'}' destroyed @media blocks.
    out = []; i = 0; n = len(css)
    while i < n:
        m = re.match(r'\s*@media[^{]*\{', css[i:])
        if m:
            start = i + m.end(); depth = 1; j = start
            while j < n and depth > 0:
                if css[j] == '{': depth += 1
                elif css[j] == '}': depth -= 1
                j += 1
            out.append(css[i:start] + scope_flat(css[start:j-1]) + '}')   # @media...{  scoped-inner  }
            i = j
        else:
            nxt = css.find('@media', i)
            if nxt < 0: nxt = n
            out.append(scope_flat(css[i:nxt]))
            i = nxt
    return '\n'.join(out)
snacss_scoped = scope_sna(snacss)

shell_css = (
 "html,body{margin:0;background:#0d1117;color:#e6edf3}"
 "[hidden]{display:none!important}"
 "#app-network{height:100vh;overflow:hidden}"
 "body.deskmode{overflow:auto}body.netmode{overflow:hidden}"
 "canvas{touch-action:none}"
 "@media(max-width:640px){#app-network{height:auto;overflow:visible}body.netmode{overflow:auto}}"
)

# ---- wrap each script in an IIFE + export cross-app hooks ----
snajs_wrapped = ("(function(){\n" + snajs +
  "\nwindow.__netResize=resize;"
  "window.__netSelect=function(n){var i=DATA.name.indexOf(n);if(i>=0)selectMember(i);};\n})();")
# window.__netCoalition is now defined inside the SNA dashboard template itself (loadCoalition): it highlights the
# coalition members (white ring), frames the camera, and colors the field by who's likely to join. gotoNetworkCoalition
# below calls it. (The old inline version here predated the route/cascade rewrite and is intentionally removed.)
mdjs_wrapped = ("(function(){\n" + mdjs +
  "\nwindow.__deskOpen=function(n){var i=byName[n];if(i!=null)openMember(i);};"
  "window.__deskShow=function(v){setView(v||'ranked');};\n})();")

controller = """
(function(){
 function showApp(w){
  document.getElementById('app-network').hidden=(w!=='network');
  document.getElementById('app-member').hidden=(w!=='member');
  document.body.classList.toggle('netmode',w==='network');
  document.body.classList.toggle('deskmode',w==='member');
  if(w==='network'&&window.__netResize)window.__netResize();
 }
 window.gotoMember=function(name){showApp('member');if(window.__deskOpen)window.__deskOpen(name);window.scrollTo(0,0);};
 window.gotoNetwork=function(name){showApp('network');if(name&&window.__netSelect)window.__netSelect(name);};
 window.gotoNetworkCoalition=function(names){showApp('network');if(window.__netCoalition)window.__netCoalition(names);window.scrollTo(0,0);};
 window.gotoMemberDesk=function(view){showApp('member');if(window.__deskShow)window.__deskShow(view||'ranked');window.scrollTo(0,0);};
 document.addEventListener('click',function(e){
  if(!e.target.closest)return;
  var md=e.target.closest('#mdlink');
  if(md){e.preventDefault();try{var m=new URL(md.href,location.href).searchParams.get('m');if(m)window.gotoMember(m);}catch(x){}return;}
  var dl=e.target.closest('#desklink');
  if(dl){e.preventDefault();window.gotoMemberDesk('ranked');return;}
  var nl=e.target.closest('a.netlink');
  if(nl){e.preventDefault();var open=!document.getElementById('app-member').hidden;
    var h2=document.querySelector('#app-member .mhead h2');
    window.gotoNetwork(open&&h2?h2.textContent.trim():null);return;}
 });
 var qp=new URLSearchParams(location.search).get('m');
 if(qp){window.gotoMember(qp);}else if(innerWidth<=700){window.gotoMemberDesk('ranked');}else{showApp('network');}
})();
"""

HTML = (
 "<!DOCTYPE html><html lang=en><head><meta charset=utf-8>"
 "<meta name=viewport content=\"width=device-width,initial-scale=1\">"
 "<meta name=referrer content=no-referrer>"
 "<title>Moneyball — Influence Dashboard</title>"
 "<style>\n" + mdcss + "\n" + snacss_scoped + "\n" + shell_css + "</style></head>"
 "<body class=netmode>"
 "<div id=app-network>" + snabody + "</div>"
 "<div id=app-member hidden>" + mdbody + "</div>"
 "<script>\n" + snajs_wrapped + "\n</script>"
 "<script>\n" + mdjs_wrapped + "\n</script>"
 "<script>" + controller + "</script>"
 "</body></html>"
)

out = os.path.join(B, 'Moneyball.html')
io.open(out, 'w', encoding='utf-8').write(HTML)
print('wrote %s (%.0f KB)' % (out, os.path.getsize(out)/1024))
