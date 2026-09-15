/* F1 step 4 - workspace.css build stamp and gold banner, and the README
   launcher contract. Both files are mixed; new lines take the local default. */
'use strict';

const styles = `#evidence-csv-results th:nth-child(3),#evidence-csv-results td:nth-child(3){width:85px}

/* F1 build stamp and stale-build banner. Gold #eca91c, plum text, muted stamp. */
.app-navigation .build-stamp{color:var(--muted);font-size:11px;white-space:nowrap}
.stale-banner{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 20px;padding:12px 16px;border:1px solid #d19412;border-radius:6px;background:var(--acu-gold);color:var(--acu-plum);font-size:14px;font-weight:600;overflow-wrap:anywhere}
.stale-banner button{flex:none;min-height:34px;padding:7px 18px;border:0;border-radius:5px;background:var(--acu-plum);color:var(--acu-ivory);font:inherit;font-size:13px;font-weight:600}
.stale-banner button:hover{background:var(--acu-purple)}
.stale-banner button:disabled{opacity:.6;cursor:wait}
@media(min-width:1100px){
  .app-navigation .build-stamp{display:block;margin:4px 12px 0;font-size:10px;line-height:1.6;white-space:normal}
}
@media(max-width:1099px){
  .app-navigation .build-stamp{order:1;margin-left:12px;font-size:10px}
}`;

const readme = `Each desktop launch checks the server's loaded code hash, report directory and
read/write mode before reusing it. The hash covers every Python module in
\`mentat/app\`, not server.py alone. A server of this same project, data root and
report folder that is running older code, is not read-only, and reports
\`busy: false\` is stopped by process id and replaced on the SAME port, with the
reason printed. A busy server, a read-only preview, a server too old to report
\`busy\`, and any port whose owning process is not a \`server.py\` process are all
left running, and the launcher opens another local port with a printed notice.
An open window titled MENTAT is not sufficient evidence that its server is
current; the console's own status bar now states the build, port, start time
and process id it is talking to, and offers Restart when the code on disk has
moved on.`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat',
  eol: 'lf',
  files: [
    {path: 'app/workspace.css', eol: 'lf',
     edits: [{find: '#evidence-csv-results th:nth-child(3),#evidence-csv-results td:nth-child(3){width:85px}',
              replace: styles}]},
    {path: 'app/README.md', eol: 'lf',
     edits: [{find: `Each desktop launch checks the server's loaded code hash, report directory and
read/write mode before reusing it. An older server can keep managing its existing
work while the launcher opens an updated server on another local port. An open
window titled MENTAT is not sufficient evidence that its server is current.`,
              replace: readme}]}
  ]
};
