"""Pure producer boundary for compiled UI slots, not a production data kind.

Templates and schemas must come from reviewed application source. There is no
file/network I/O, script execution, inferred schema, downloaded template hash,
or installed production page contract here. Closed JSON slots do not establish
the outside-input/nested-schema closure of the complete Melange application.
"""
from dataclasses import dataclass
import hashlib
import html
import json
import math
import re
from types import MappingProxyType

MAX_PAGE_BYTES=128*1024**2
MAX_EXPLANATION_BYTES=2*1024**2
PRODUCTION_PAGE_CONTRACTS=MappingProxyType({})

def require(value):
    if not value:raise ValueError('Compiled page data was rejected')

def strict_text(value,limit):
    require(isinstance(value,str) and len(value.encode('utf-8',errors='strict'))<=limit)
    require(not any(ord(c)<32 and c not in '\n\r\t' for c in value))
    return value

@dataclass(frozen=True)
class Text:
    max_bytes:int
@dataclass(frozen=True)
class Integer:
    minimum:int
    maximum:int
@dataclass(frozen=True)
class Number:
    minimum:float
    maximum:float
@dataclass(frozen=True)
class Boolean:pass
@dataclass(frozen=True)
class Null:pass
@dataclass(frozen=True)
class Literal:
    value:object
@dataclass(frozen=True)
class Array:
    item:object
    max_items:int
    min_items:int=0
@dataclass(frozen=True)
class Object:
    fields:object
    optional:object=frozenset()
    def __post_init__(self):
        require(type(self.fields) is dict)
        object.__setattr__(self,'fields',MappingProxyType(dict(self.fields)))
        object.__setattr__(self,'optional',frozenset(self.optional))
@dataclass(frozen=True)
class Keyed:
    key_pattern:str
    item:object
    max_items:int
@dataclass(frozen=True)
class OneOf:
    choices:tuple
@dataclass(frozen=True)
class PassiveExplanation:pass

_SCHEMAS=(Text,Integer,Number,Boolean,Null,Literal,Array,Object,Keyed,OneOf,PassiveExplanation)
_FORBIDDEN_KEYS=frozenset(('__proto__','constructor','prototype'))

def checked_schema(schema,depth=0):
    require(depth<=32 and type(schema) in _SCHEMAS)
    if type(schema) is Text:require(type(schema.max_bytes) is int and 0<=schema.max_bytes<=MAX_PAGE_BYTES)
    elif type(schema) is Integer:
        require(type(schema.minimum) is int and type(schema.maximum) is int and schema.minimum<=schema.maximum and max(abs(schema.minimum),abs(schema.maximum))<10**32)
    elif type(schema) is Number:
        require(all(type(v) in (int,float) and math.isfinite(v) for v in (schema.minimum,schema.maximum)) and schema.minimum<=schema.maximum)
    elif type(schema) is Literal:
        require(type(schema.value) in (str,int,bool,type(None)))
        if type(schema.value) is str:strict_text(schema.value,4096)
        if type(schema.value) is int:require(abs(schema.value)<10**32)
    elif type(schema) is Array:
        require(type(schema.min_items) is int and type(schema.max_items) is int and 0<=schema.min_items<=schema.max_items<=2_000_000)
        checked_schema(schema.item,depth+1)
    elif type(schema) is Object:
        require(len(schema.fields)<=1024 and schema.optional.issubset(schema.fields))
        for key,child in schema.fields.items():
            require(isinstance(key,str) and 0<len(key)<=128 and key not in _FORBIDDEN_KEYS)
            checked_schema(child,depth+1)
    elif type(schema) is Keyed:
        # The finite key grammar is native compiled source, not data-provided
        # regular expressions. Restrict it to character classes plus one bound.
        require(isinstance(schema.key_pattern,str) and re.fullmatch(r'\[[A-Za-z0-9_\\\-:]+\]\{[1-9][0-9]?,[1-9][0-9]{0,2}\}',schema.key_pattern) is not None)
        require(type(schema.max_items) is int and 0<=schema.max_items<=2_000_000)
        checked_schema(schema.item,depth+1)
    elif type(schema) is OneOf:
        require(type(schema.choices) is tuple and 2<=len(schema.choices)<=8)
        for child in schema.choices:checked_schema(child,depth+1)
    return schema

def schema_value(schema,value):
    kind=type(schema)
    if kind is Text:return strict_text(value,schema.max_bytes)
    if kind is Integer:
        require(type(value) is int and schema.minimum<=value<=schema.maximum);return value
    if kind is Number:
        require(type(value) in (int,float) and math.isfinite(value) and schema.minimum<=value<=schema.maximum);return value
    if kind is Boolean:require(type(value) is bool);return value
    if kind is Null:require(value is None);return None
    if kind is Literal:require(type(value) is type(schema.value) and value==schema.value);return value
    if kind is Array:
        require(type(value) is list and schema.min_items<=len(value)<=schema.max_items)
        return [schema_value(schema.item,item) for item in value]
    if kind is Object:
        require(type(value) is dict and not set(value)-set(schema.fields) and not (set(schema.fields)-set(value))-schema.optional)
        return {key:schema_value(schema.fields[key],item) for key,item in value.items()}
    if kind is Keyed:
        require(type(value) is dict and len(value)<=schema.max_items)
        require(all(key not in _FORBIDDEN_KEYS and re.fullmatch(schema.key_pattern,key) is not None for key in value))
        return {key:schema_value(schema.item,item) for key,item in value.items()}
    if kind is OneOf:
        for choice in schema.choices:
            try:return schema_value(choice,value)
            except ValueError:pass
        require(False)
    if kind is PassiveExplanation:return parse_passive_explanation(value)
    require(False)

_HEADING='Legislative results · shadow candidate'
_CONTEXT='Institutional context and coverage'
_EVIDENCE='Measure, role, stage and source evidence'
_FOOTER='Impact classes: commemorative 1, substantive 5, substantive and significant 10. Letters remain substantive advocacy (weight 5); they have no bill-law milestones. Missing evidence is not zero achievement.'
_TEXT=r'((?:[^<&>]|&(?:amp|lt|gt|quot|#x27);)*)'
_PASSIVE=re.compile(r'\A'+re.escape('<details class="effectiveness-shadow"><summary>'+_HEADING+'</summary>')+
    '<p>'+_TEXT+'</p><p>'+_TEXT+'</p><p>'+_TEXT+'</p>'+re.escape('<details><summary>'+_CONTEXT+'</summary><pre>')+
    _TEXT+re.escape('</pre></details><details><summary>'+_EVIDENCE+'</summary><pre>')+_TEXT+
    re.escape('</pre></details><p>'+_FOOTER+'</p></details>')+r'\Z')

def parse_passive_explanation(value):
    """Convert one exact escaped legacy fragment to structured plain text.

    There are no arbitrary attributes, links, styles, comments, foreign tags,
    entities, or raw markup. A URL appearing as evidence text remains plain text;
    no URL can become an href/src or executable browser context.
    """
    strict_text(value,MAX_EXPLANATION_BYTES)
    if value=='':return None
    match=_PASSIVE.fullmatch(value);require(match is not None)
    texts=[]
    for raw in match.groups():
        decoded=html.unescape(raw)
        require(html.escape(decoded,quote=True)==raw)
        texts.append(strict_text(decoded,MAX_EXPLANATION_BYTES))
    return {'schemaVersion':1,'kind':'effectiveness-passive-explanation','paragraphs':texts[:3],'context':texts[3],'evidence':texts[4]}

def render_passive_explanation(document):
    if document is None:return ''
    require(type(document) is dict and set(document)=={'schemaVersion','kind','paragraphs','context','evidence'})
    require(type(document['schemaVersion']) is int and document['schemaVersion']==1 and document['kind']=='effectiveness-passive-explanation')
    paragraphs=document['paragraphs'];require(type(paragraphs) is list and len(paragraphs)==3)
    escaped=[html.escape(strict_text(v,MAX_EXPLANATION_BYTES),quote=True) for v in [*paragraphs,document['context'],document['evidence']]]
    result='<details class="effectiveness-shadow"><summary>'+_HEADING+'</summary>'
    result+=''.join('<p>'+text+'</p>' for text in escaped[:3])
    result+='<details><summary>'+_CONTEXT+'</summary><pre>'+escaped[3]+'</pre></details>'
    result+='<details><summary>'+_EVIDENCE+'</summary><pre>'+escaped[4]+'</pre></details><p>'+_FOOTER+'</p></details>'
    strict_text(result,MAX_EXPLANATION_BYTES)
    return result

def _pairs(items):
    result={}
    for key,value in items:
        require(key not in result and key not in _FORBIDDEN_KEYS);result[key]=value
    return result
def _float(value):
    result=float(value);require(math.isfinite(result));return result
def _int(value):require(len(value)<=33);return int(value)
def _constant(_value):require(False)
_DECODER=json.JSONDecoder(object_pairs_hook=_pairs,parse_float=_float,parse_int=_int,parse_constant=_constant)

def encode_slot(value,*,ensure_ascii=False,sort_keys=False):
    """The four source-producer JSON formats, safe inside a script element."""
    text=json.dumps(value,ensure_ascii=ensure_ascii,sort_keys=sort_keys,separators=(',',':'),allow_nan=False)
    return text.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')

def _tree_budget(value):
    stack=[(value,0)];nodes=0
    while stack:
        item,depth=stack.pop();nodes+=1;require(depth<=48 and nodes<=2_000_000)
        if type(item) is dict:stack.extend((child,depth+1) for child in item.values())
        elif type(item) is list:stack.extend((child,depth+1) for child in item)

@dataclass(frozen=True)
class Slot:
    name:str
    token:str
    schema:Object
    max_bytes:int

class CompiledPage:
    """An app-source residual template and closed, explicitly typed JSON slots.

    No production contract is supplied by this module. Native integration must
    instantiate this from pinned source programs/templates, never a downloaded
    page or its reported hash. No arbitrary outside-island fragments are data.
    """
    def __init__(self,page,template,slots,*,max_bytes=MAX_PAGE_BYTES):
        require(isinstance(page,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',page) is not None)
        require(type(max_bytes) is int and type(template) is bytes and 0<len(template)<=max_bytes<=MAX_PAGE_BYTES)
        text=template.decode('utf-8',errors='strict');require(not text.startswith('\ufeff') and '\x00' not in text)
        require(type(slots) is tuple and 0<len(slots)<=32 and all(type(slot) is Slot for slot in slots))
        names=set();tokens=set();ordered=[]
        for slot in slots:
            require(re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',slot.name) is not None and slot.name not in names)
            require(re.fullmatch(r'__[A-Z][A-Z0-9_]{0,63}__',slot.token) is not None and slot.token not in tokens and text.count(slot.token)==1)
            require(type(slot.schema) is Object and type(slot.max_bytes) is int and 0<slot.max_bytes<=max_bytes)
            checked_schema(slot.schema);names.add(slot.name);tokens.add(slot.token);ordered.append((text.index(slot.token),slot))
        require(set(re.findall(r'__[A-Z][A-Z0-9_]{0,63}__',text))==tokens)
        ordered.sort(key=lambda row:row[0]);literals=[];cursor=0
        for offset,slot in ordered:
            require(offset>cursor);literals.append(text[cursor:offset]);cursor=offset+len(slot.token)
        require(cursor<len(text));literals.append(text[cursor:])
        self.page,self.max_bytes=page,max_bytes
        self.slots=tuple(slot for _offset,slot in ordered);self.literals=tuple(literals)
        self.template_sha256=hashlib.sha256(template).hexdigest()
    def extract(self,document):
        require(type(document) is bytes and len(document)<=self.max_bytes)
        text=document.decode('utf-8',errors='strict');require(not text.startswith('\ufeff') and '\x00' not in text)
        values={};cursor=0
        for index,slot in enumerate(self.slots):
            literal=self.literals[index];require(text.startswith(literal,cursor));cursor+=len(literal)
            start=cursor
            try:value,cursor=_DECODER.raw_decode(text,cursor)
            except (RecursionError,OverflowError) as error:raise ValueError('Compiled page data was rejected') from error
            require(len(text[start:cursor].encode('utf-8'))<=slot.max_bytes)
            _tree_budget(value)
            require(any(encode_slot(value,ensure_ascii=a,sort_keys=s)==text[start:cursor] for a,s in ((False,False),(False,True),(True,False),(True,True))))
            values[slot.name]=schema_value(slot.schema,value)
        require(text[cursor:]==self.literals[-1])
        return {'schemaVersion':1,'kind':'compiled-page-islands','page':self.page,'templateSha256':self.template_sha256,
            'slots':values,'coverage':{'closedSlots':True,'fullPage':False,'fullApplication':False}}
