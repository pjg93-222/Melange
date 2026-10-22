"""In-memory hostile producer fixtures; no original HTML or data exports."""
import ast
import html
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import module_data_islands as islands
from module_data_islands import (Array,Boolean,CompiledPage,Integer,Keyed,Literal,Null,Number,Object,OneOf,
    PassiveExplanation,Slot,Text,PRODUCTION_PAGE_CONTRACTS,encode_slot,parse_passive_explanation,render_passive_explanation)

TEMPLATE=b'<main>compiled application source</main><script>const DATA=__DATA__;const EXTRA=__EXTRA__;</script>'
SCHEMA=Object({'schemaVersion':Literal(1),'label':Text(1024),'values':Array(Integer(-100,100),8),'explanation':PassiveExplanation()})
EXTRA=Object({'available':Boolean(),'ratio':OneOf((Number(-2,2),Null()))})

def page():
    return CompiledPage('synthetic.html',TEMPLATE,(Slot('network','__DATA__',SCHEMA,4096),Slot('extra','__EXTRA__',EXTRA,1024)))
def values():return {'schemaVersion':1,'label':'Fabricated <text> & unicode ·','values':[0,1],'explanation':''}
def built(first=None,second=None,**format_options):
    return TEMPLATE.replace(b'__DATA__',encode_slot(values() if first is None else first,**format_options).encode()).replace(b'__EXTRA__',encode_slot({'available':True,'ratio':None} if second is None else second,**format_options).encode())

def trusted_explanation():
    # Compile only the existing trusted passive renderer and numeric formatter;
    # no producer pipeline, data reads, scoring or forecasting is executed.
    source=Path(__file__).resolve().parents[3]/'fec/engine/effectiveness_integration.py'
    tree=ast.parse(source.read_bytes())
    functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('_number','render_explanation')]
    assert {node.name for node in functions}=={'_number','render_explanation'}
    scope={'html':html,'json':json,'math':math}
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),scope)
    return scope['render_explanation']({'institutional_context':['<script>alert(1)</script>'],
        'coverage':{'fixture':'& " < >'},'explanation':[{'source':'https://example.invalid/metadata','fixture':'plain text'}]},
        {'congress':1,'as_of':'2024-01-01','terms':{}})

class CompiledSlotsTests(unittest.TestCase):
    def test_all_four_existing_producer_formats_extract_inert_values(self):
        for ascii in (False,True):
            for sorted_keys in (False,True):
                result=page().extract(built(ensure_ascii=ascii,sort_keys=sorted_keys))
                self.assertEqual(result['slots']['network']['label'],values()['label'])
                self.assertIsNone(result['slots']['network']['explanation'])
                self.assertEqual(result['coverage'],{'closedSlots':True,'fullPage':False,'fullApplication':False})
        self.assertEqual(dict(PRODUCTION_PAGE_CONTRACTS),{})
    def test_source_residuals_cannot_change_even_with_well_formed_data(self):
        for document in (built().replace(b'compiled application source',b'downloaded code'),built()+b'<script>bad()</script>',
            built().replace(b'const EXTRA=',b'other();const EXTRA='),built().replace(b'<main>',b'<main onload="bad()">')):
            with self.assertRaises(ValueError):page().extract(document)
    def test_missing_duplicate_or_unmapped_slots_fail_at_contract_construction(self):
        slot=Slot('network','__DATA__',SCHEMA,4096)
        for template,slots in ((b'<x>__DATA__ __DATA__</x>',(slot,)),(b'<x>__OTHER__</x>',(slot,)),(TEMPLATE,(slot,)),(b'<x>__DATA__</x>',(slot,slot))):
            with self.assertRaises(ValueError):CompiledPage('synthetic.html',template,slots)
    def test_every_nested_field_is_explicitly_typed_and_closed(self):
        for change in (lambda d:d.update(extra='unknown'),lambda d:d.pop('label'),lambda d:d.update(schemaVersion=True),
            lambda d:d.update(values=[True]),lambda d:d.update(values=[0]*9),lambda d:d.update(values=[101]),lambda d:d.update(label={'untyped':'object'})):
            first=values();change(first)
            with self.assertRaises(ValueError):page().extract(built(first))
        with self.assertRaises(ValueError):CompiledPage('synthetic.html',b'<x>__DATA__</x>',(Slot('network','__DATA__',Object({'anything':None}),4096),))
    def test_duplicate_prototype_nonfinite_overflow_and_trailing_tokens_reject(self):
        valid=encode_slot(values()).encode()
        for raw in (valid.replace(b'"schemaVersion":1',b'"schemaVersion":1,"schemaVersion":1'),
            valid.replace(b'"schemaVersion":1',b'"schemaVersion":1,"__proto__":{}'),valid+b';evil()'):
            document=built().replace(valid,raw)
            with self.assertRaises(ValueError):page().extract(document)
        ordinary=built(second={'available':True,'ratio':0})
        for raw in (b'NaN',b'Infinity',b'-Infinity',b'1e9999',b'1'*100):
            with self.assertRaises(ValueError):page().extract(ordinary.replace(b'"ratio":0',b'"ratio":'+raw))
    def test_page_encoding_and_script_terminator_are_not_interpreted(self):
        for document in (built().decode().encode('utf-16'),b'\xef\xbb\xbf'+built(),built().replace(b'Fabricated',b'\xff')):
            with self.assertRaises(ValueError):page().extract(document)
        first=values();first['label']='</script><script>bad()</script>'
        # The source serialization escapes HTML delimiters; output is text data.
        self.assertEqual(page().extract(built(first))['slots']['network']['label'],first['label'])
        unsafe=json.dumps(first,separators=(',',':'),ensure_ascii=False).encode()
        with self.assertRaises(ValueError):page().extract(built().replace(encode_slot(values()).encode(),unsafe))
    def test_slot_page_and_nested_collection_budgets_fail_closed(self):
        small=CompiledPage('synthetic.html',b'<x>__DATA__</x>',(Slot('network','__DATA__',Object({'label':Text(100)}),16),),max_bytes=200)
        with self.assertRaises(ValueError):small.extract(b'<x>'+encode_slot({'label':'a'*50}).encode()+b'</x>')
        with self.assertRaises(ValueError):small.extract(b'x'*201)
        nested=b'['*60+b'0'+b']'*60
        with self.assertRaises(ValueError):page().extract(built().replace(encode_slot(values()).encode(),b'{"nested":'+nested+b'}'))
    def test_keyed_and_optional_schemas_are_closed_without_any_values(self):
        schema=Object({'rows':Keyed('[a-z0-9_-]{1,32}',Object({'value':Integer(0,3)}),2),'note':Text(30)},optional={'note'})
        contract=CompiledPage('synthetic.html',b'<x>__DATA__</x>',(Slot('network','__DATA__',schema,1024),))
        self.assertEqual(contract.extract(b'<x>'+encode_slot({'rows':{'fixture':{'value':1}}}).encode()+b'</x>')['slots']['network']['rows']['fixture']['value'],1)
        for rows in ({'bad/name':{'value':1}},{'fixture':{'untyped':1}}):
            with self.assertRaises(ValueError):contract.extract(b'<x>'+encode_slot({'rows':rows}).encode()+b'</x>')
    def test_invalid_key_patterns_are_refused_when_constructed_before_any_values(self):
        for pattern in ('[a-z]{99,1}','[z-a]{1,2}','[\\]{1,2}','[a-z]+',None):
            with self.subTest(pattern=pattern),self.assertRaises(ValueError):
                Keyed(pattern,Integer(0,3),2)
    def test_keyed_contract_reuses_its_validated_pattern_including_empty_dictionary(self):
        schema=Object({'rows':Keyed('[a-z0-9_-]{1,32}',Integer(0,3),2)})
        contract=CompiledPage('synthetic.html',b'<x>__DATA__</x>',(Slot('network','__DATA__',schema,128),))
        # Pattern compilation/shape checks belong to contract construction,
        # including contracts later applied only to an empty dictionary.
        with patch.object(islands.re,'fullmatch',side_effect=AssertionError('late pattern validation')):
            for rows in ({},{'fixture':1}):
                result=contract.extract(b'<x>'+encode_slot({'rows':rows}).encode()+b'</x>')
                self.assertEqual(result['slots']['network']['rows'],rows)
    def test_slot_json_decoder_receives_only_the_byte_bounded_window(self):
        limit=16
        contract=CompiledPage('synthetic.html',b'<x>__DATA__</x>',(Slot('network','__DATA__',Object({'label':Text(20000)}),limit),),max_bytes=60000)
        original=islands._DECODER
        observed=[]
        class BoundedDecoder:
            def raw_decode(self,window,idx=0):
                observed.append(len(window.encode('utf-8')))
                self_test.assertLessEqual(observed[-1],limit)
                return original.raw_decode(window,idx)
        self_test=self
        with patch.object(islands,'_DECODER',BoundedDecoder()):
            for label in ('a'*10000,'\U0001f4a1'*10000):
                with self.assertRaises(ValueError):
                    contract.extract(b'<x>'+encode_slot({'label':label}).encode()+b'</x>')
        self.assertEqual(len(observed),2)
    def test_exact_utf8_slot_budget_preserves_a_truncated_following_literal(self):
        raw=encode_slot({'label':'\u00e9'}).encode('utf-8')
        template=b'<x>__DATA__'+'\U0001f4a1</x>'.encode('utf-8')
        document=template.replace(b'__DATA__',raw)
        for limit in (len(raw),len(raw)+1):
            contract=CompiledPage('synthetic.html',template,(Slot('network','__DATA__',Object({'label':Text(10)}),limit),))
            self.assertEqual(contract.extract(document)['slots']['network'],{'label':'\u00e9'})
        contract=CompiledPage('synthetic.html',template,(Slot('network','__DATA__',Object({'label':Text(10)}),len(raw)-1),))
        with self.assertRaises(ValueError):contract.extract(document)

class PassiveMarkupTests(unittest.TestCase):
    def setUp(self):self.fragment=trusted_explanation()
    def test_existing_trusted_renderer_roundtrips_without_executable_data(self):
        document=parse_passive_explanation(self.fragment)
        self.assertEqual(render_passive_explanation(document),self.fragment)
        self.assertIn('<script>alert(1)</script>',document['context'])
        self.assertNotIn('<script>',render_passive_explanation(document))
        self.assertIn('https://example.invalid/metadata',document['evidence'])
        self.assertNotIn('href=',render_passive_explanation(document))
    def test_only_exact_tag_attribute_and_hierarchy_grammar_is_accepted(self):
        for fragment in (self.fragment.replace('<details class="effectiveness-shadow">','<details class="effectiveness-shadow" onclick="bad()">',1),
            self.fragment.replace('<p>','<p style="background:url(javascript:bad())">',1),self.fragment.replace('<p>','<a href="https://outside.invalid">',1),
            self.fragment.replace('<pre>','<svg><foreignObject>',1),self.fragment+'<script>bad()</script>',self.fragment.replace('</pre>','</pre><!--comment-->',1),
            '<!DOCTYPE html>'+self.fragment,self.fragment.replace('<details>','<details open>',1),self.fragment.replace('<summary>','<summary id="x">',1)):
            with self.assertRaises(ValueError):parse_passive_explanation(fragment)
    def test_noncanonical_entities_encodings_and_controls_are_rejected(self):
        for fragment in (self.fragment.replace('&lt;script&gt;','&#x3c;script&#x3e;'),self.fragment.replace('Congress','Congress &bogus;',1),
            self.fragment+'\x00',self.fragment.replace('Congress','Congress \ud800',1)):
            with self.assertRaises(ValueError):parse_passive_explanation(fragment)
        with self.assertRaises(ValueError):parse_passive_explanation(self.fragment.encode('utf-16'))
    def test_structured_renderer_cannot_add_active_attributes_or_untype_fields(self):
        document=parse_passive_explanation(self.fragment)
        for mutate in (lambda d:d.update(onclick='bad()'),lambda d:d.update(paragraphs=['only one']),lambda d:d.update(schemaVersion=True)):
            bad={**document,'paragraphs':list(document['paragraphs'])};mutate(bad)
            with self.assertRaises(ValueError):render_passive_explanation(bad)
        document['paragraphs'][0]='<img src=x onerror=bad()> & " '
        rendered=render_passive_explanation(document)
        self.assertNotIn('<img',rendered);self.assertIn('&lt;img',rendered)
    def test_passive_fields_are_bound_by_the_closed_slot_schema(self):
        first=values();first['explanation']=self.fragment
        document=page().extract(built(first))['slots']['network']['explanation']
        self.assertEqual(render_passive_explanation(document),self.fragment)
        first['explanation']='<script>bad()</script>'
        with self.assertRaises(ValueError):page().extract(built(first))
    def test_empty_and_oversized_fragments_have_explicit_behavior(self):
        self.assertIsNone(parse_passive_explanation(''));self.assertEqual(render_passive_explanation(None),'')
        # Keep the complete valid grammar: only its text-byte budget changes.
        oversized=self.fragment.replace('Congress ','Congress '+'x'*(2*1024**2),1)
        with self.assertRaises(ValueError):parse_passive_explanation(oversized)

if __name__=='__main__':unittest.main()
