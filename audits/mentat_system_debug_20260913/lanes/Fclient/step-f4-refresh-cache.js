/* F4 correctness gap found in review: graphTotalsCache is keyed by the scope
   (run, industry, company, cycle, tier, funding), which is exactly the key that
   does NOT change when "Refresh verified data" picks up a new workbook. The
   strip would then set a fresh Studio total beside a stale Graph total - the
   precise confusion it exists to remove. Refresh clears it with the others. */
'use strict';
module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-Fc',
  eol: 'crlf',
  files: [
    {
      path: 'chart-studio.js',
      eol: 'crlf',
      edits: [
        {
          find: "  el('refresh-data').onclick=()=>{++contributionCacheEpoch;contributionController?.abort();contributionPending=null;contributionCache.clear();memberCache.clear();loadContributions(true);};\n",
          replace: "  el('refresh-data').onclick=()=>{++contributionCacheEpoch;contributionController?.abort();contributionPending=null;contributionCache.clear();memberCache.clear();graphTotalsCache.clear();loadContributions(true);};\n"
        }
      ]
    }
  ]
};
