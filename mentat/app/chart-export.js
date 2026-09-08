/* Local chart downloads. No external renderer or upload. */
(() => {
  'use strict';
  function download(content, type, name) {
    const url = URL.createObjectURL(content instanceof Blob ? content : new Blob([content], {type}));
    const link = document.createElement('a'); link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function image(source, format, title, context, name='mentat-chart') {
    if (!source) throw new Error('Create a chart before exporting.');
    const svg = source.cloneNode(true), ns = 'http://www.w3.org/2000/svg';
    const box = source.viewBox.baseVal, width = box.width, height = box.height;
    const lines = String(context).match(new RegExp('.{1,' + Math.floor(width / 7) + '}(?:\\s|$)|.{1,' + Math.floor(width / 7) + '}', 'g')) || [];
    const fullHeight = height + 65 + lines.length * 17;
    svg.setAttribute('xmlns', ns); svg.setAttribute('viewBox', `0 0 ${width} ${fullHeight}`);
    svg.setAttribute('width', width); svg.setAttribute('height', fullHeight);
    svg.removeAttribute('class');
    const background = document.createElementNS(ns, 'rect');
    for (const [k,v] of Object.entries({width, height:fullHeight, fill:'#ffffff'})) background.setAttribute(k,v);
    svg.prepend(background);
    const text = (value,y,bold=false) => {
      const node = document.createElementNS(ns,'text'); node.textContent=value;
      for (const [k,v] of Object.entries({x:16,y,fill:'#29485e','font-size':12,'font-family':'Segoe UI, Arial, sans-serif','font-weight':bold?600:400})) node.setAttribute(k,v);
      svg.append(node);
    };
    text(title,height+24,true); lines.forEach((line,i)=>text(line.trim(),height+47+i*17));
    const content = new XMLSerializer().serializeToString(svg);
    if (format === 'svg') {download(content,'image/svg+xml',name+'.svg'); return;}
    if (format !== 'png') throw new Error('Choose SVG or PNG.');
    const url=URL.createObjectURL(new Blob([content],{type:'image/svg+xml'}));
    try {
      const img=new Image();
      await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error('Could not render PNG. Try SVG export.'));img.src=url;});
      const canvas=document.createElement('canvas'); canvas.width=width*2;canvas.height=fullHeight*2;
      canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
      if(!blob)throw new Error('PNG export unavailable. Try SVG export.');
      download(blob,'image/png',name+'.png');
    } finally {URL.revokeObjectURL(url);}
  }
  globalThis.MentatExport={download,image};
})();
