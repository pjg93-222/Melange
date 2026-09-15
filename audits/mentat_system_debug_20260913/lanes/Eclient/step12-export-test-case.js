/* One more case on the shipped export test: compose() and rasterize() must do
   their work without downloading anything, and caption:false must draw the chart
   alone for the slide that writes its own caption.
   This step inserts text, so it is single-shot: replaying it would insert the
   case again. Restore the .bak before re-running it. */
'use strict';
const fs = require('fs');
const path = require('path');
const read = name => fs.readFileSync(path.join(__dirname, name), 'utf8');

const SPLIT_CASE = [
  '',
  '  // E0 split compose()/rasterize(): the pieces must produce exactly what the',
  '  // download produces, and neither may reach for an anchor of its own - the',
  '  // clipboard, the print sheet and the slide all call them without one.',
  '  const split=await page.evaluate(async()=>{',
  "    fixture.innerHTML='<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"600\" height=\"300\" viewBox=\"0 0 600 300\"><rect x=\"10\" y=\"10\" width=\"40\" height=\"40\" fill=\"#123456\"/></svg>';",
  '    const before=exportNames.length;',
  "    const composed=MentatExport.compose(fixture.firstChild,'Composed once','Receipt basis; source fixture');",
  '    const text=new XMLSerializer().serializeToString(composed.svg);',
  '    const blob=await MentatExport.rasterize(composed,{scale:1});',
  "    const bare=MentatExport.compose(fixture.firstChild,'Composed once','Receipt basis; source fixture',{caption:false});",
  '    const quiet=exportNames.length-before;',
  "    await MentatExport.image(fixture.firstChild,'svg','Composed once','Receipt basis; source fixture','composed');",
  '    return {quiet,type:blob.type,size:blob.size,width:composed.width,height:composed.height,',
  '      bareHeight:bare.height,bareText:bare.svg.textContent,',
  '      same:(await exportBlobs.at(-1).text())===text,name:exportNames.at(-1)};',
  '  });',
  "  assert.equal(split.quiet,0,'compose and rasterize must not download anything on their own');",
  "  assert.equal(split.same,true,'the downloaded SVG must be byte-for-byte what compose built');",
  "  assert.equal(split.type,'image/png');assert.ok(split.size>200);",
  "  assert.equal(split.width,600);assert.ok(split.height>300,'the caption band belongs to the composed drawing');",
  "  assert.equal(split.bareHeight,300,'caption:false draws the chart alone, for a slide that writes its own caption');",
  "  assert.equal(split.bareText,'','caption:false must not bake any text into the drawing');",
  "  assert.equal(split.name,'composed.svg');",
  ''
].join('\n');

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  bak: '.bak-20260914-E',
  eol: 'crlf',
  files: [
    {
      path: '../tests/test_contribution_export_browser.cjs',
      eol: 'lf',
      edits: [
        {find: "  const invalid=await page.evaluate(async()=>{",
         replace: SPLIT_CASE + "  const invalid=await page.evaluate(async()=>{"}
      ]
    }
  ]
};
