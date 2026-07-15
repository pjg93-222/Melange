# -*- coding: utf-8 -*-
"""Fail-closed member identity resolution shared by pipeline joins."""
import re, unicodedata, collections

_SUFFIXES={'jr','sr','ii','iii','iv'}


def normalize_name(value):
    text=unicodedata.normalize('NFKD',str(value or '')).encode('ascii','ignore').decode('ascii').casefold()
    text=re.sub(r"[^a-z0-9]+",' ',text).strip()
    parts=[p for p in text.split() if p not in _SUFFIXES]
    return ' '.join(parts)


class Resolver:
    def __init__(self,names,name_to_bioguide=None):
        self.names=list(names); self.name_set=set(self.names)
        self.by_norm=collections.defaultdict(list); self.by_last=collections.defaultdict(list)
        for name in self.names:
            norm=normalize_name(name); self.by_norm[norm].append(name)
            if norm: self.by_last[norm.split()[-1]].append(name)
        self.by_bio={bio:name for name,bio in (name_to_bioguide or {}).items() if name in self.name_set and bio}

    def resolve(self,name=None,bioguide=None):
        if bioguide and bioguide in self.by_bio: return self.by_bio[bioguide]
        if name in self.name_set: return name
        raw=str(name or '').strip()
        variants=[raw]
        if ',' in raw:
            left,right=raw.split(',',1); variants.append((right+' '+left).strip())
        for variant in variants:
            norm=normalize_name(variant); exact=self.by_norm.get(norm,[])
            if len(exact)==1: return exact[0]
            toks=norm.split()
            if not toks: continue
            candidates=self.by_last.get(toks[-1],[])
            if len(candidates)==1: return candidates[0]
            if candidates:
                fi=toks[0][0]
                narrowed=[c for c in candidates if normalize_name(c).split()[0][0]==fi]
                if len(narrowed)==1: return narrowed[0]
        return None
