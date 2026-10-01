"""Fetch only the public official transcripts selected for this bounded pilot."""
from pathlib import Path
import hashlib
import json
import urllib.request
from datetime import datetime,timezone
from pypdf import PdfReader
from .data import ROOT,write_json

OUT=ROOT/'outputs/member_personal_relationships/20260910_hearing_pilot'
SOURCES=[
    dict(id='comer_moskowitz_20231114',date='2023-11-14',meeting_type='hearing',
         url='https://www.govinfo.gov/content/pkg/CHRG-118hhrg54309/pdf/CHRG-118hhrg54309.pdf'),
    dict(id='oversight_markup_20240516',date='2024-05-16',meeting_type='markup',
         url='https://docs.house.gov/meetings/GO/GO00/20240516/117325/HMKP-118-GO00-Transcript-20240516.pdf'),
    dict(id='oversight_organization_20250114',date='2025-01-14',meeting_type='organizational_meeting',
         url='https://docs.house.gov/meetings/GO/GO00/20250114/117774/HMTG-119-GO00-Transcript-20250114.pdf'),
]


def main():
    out=OUT/'sources';out.mkdir(parents=True,exist_ok=True);manifest=[]
    for source in SOURCES:
        path=out/(source['id']+'.pdf')
        if not path.exists():
            req=urllib.request.Request(source['url'],headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=30) as response:body=response.read()
            if not body.startswith(b'%PDF'):raise ValueError('Expected a PDF')
            path.write_bytes(body)
        reader=PdfReader(path)
        pages=[dict(pdf_page=i+1,text=page.extract_text()) for i,page in enumerate(reader.pages)]
        write_json(out/(source['id']+'.pages.json'),pages)
        (out/(source['id']+'.txt')).write_text('\n\n'.join(f"[PDF PAGE {p['pdf_page']}]\n{p['text']}" for p in pages),encoding='utf-8')
        manifest.append(dict(**source,pdf_pages=len(pages),local_path=str(path),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),retrieved_utc=datetime.now(timezone.utc).isoformat()))
        print(source['id'],len(pages),'pages',flush=True)
    write_json(OUT/'source_manifest.json',manifest)


if __name__=='__main__':main()
