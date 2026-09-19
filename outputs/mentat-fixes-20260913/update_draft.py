from pathlib import Path
p=Path('C:/Users/pgoff/.codex/visualizations/2026/09/13/01a098d0-0ca2-7ed0-9f70-03dc6a336893/mentat-chart-drafts.html')
s=p.read_text();style=s[s.index('<style>'):s.index('</style>')+8]
content=Path(__file__).with_name('draft-content.txt').read_text()
p.write_text('<div id="mentat-chart-drafts" aria-label="Mentat chart creation design drafts">\n'+style+'\n'+content+'\n</div>')
