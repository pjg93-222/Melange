import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import os as _oT
def _tpl(n): return open(_oT.path.join(_oT.path.dirname(_oT.path.abspath(__file__)),'templates',n),encoding='utf-8').read()
import json,os
D=json.load(open(MB_ROOT+r'\dashboard_data.json'))
HTML=_tpl('make_dashboard_html_00.tpl')
out=MB_ROOT+r'\Moneyball Dashboard.html'
open(out,'w',encoding='utf-8').write(HTML.replace('__DATA__',json.dumps(D,separators=(',',':'))))
print('wrote',out,'(%.0f KB)'%(os.path.getsize(out)/1024))
