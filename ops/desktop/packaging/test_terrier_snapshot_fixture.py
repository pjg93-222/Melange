"""Native-test-only synthetic fixture derived from Geo d6cf452 v3_testkit; no django.test dependency."""
import copy
import hashlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from shapely.geometry import box, mapping
from shapely.ops import unary_union

from tools import area_layers as AL
from tools import make_scores_fixture as MF
from tools.build_bundle_v4 import apply_v4_manifest, make_area_file, neighbours
from tools.geography_levels import EXTRA_LEVELS

from django.conf import settings
from tools.measures import MEASURES, MEASURE_RANGES
from tools.geography_levels import SOURCES, label

def hierarchy_bundle():
    # Explicitly synthetic aggregates; no installed user data or sample archive is read.
    manifest = {key: 'synthetic fixture' for key in ['label','source_name','source_date','source_date_basis',
        'created_at','encoding','scope','vintage_validation','privacy']}
    manifest.update(schema='cu-summary-v3',snapshot='co-cd005-123456789abc',source_sha256='a'*64,
        support_likelihood='Not measured',persistent_voices='Not measured',
        input={key: (120 if key in ('input_rows','accepted_unique_profiles') else 0) for key in
            ['input_rows','column_count','duplicate_rows_collapsed','conflicting_ids_quarantined','accepted_unique_profiles','malformed_width_rows']},
        bases={basis:{'imported':120,'mapped':120,'unplaced':0,'coverage':1,'excluded':{},'zcta_mapped':120,'zcta_unassigned':0} for basis in ['registration','residential']},
        measures=copy.deepcopy(MEASURES),measure_methodology='Synthetic aggregate fixture',
        geography={'block_vintage':'2020','district_vintage':'2025','zcta_vintage':'2020','street_vintage':'2025',
          'sources':{key:'https://www2.census.gov/synthetic-fixture' for key in ['blocks','districts','roads','zcta']},
          'street_method':'synthetic geometry','street_polygons':0,'street_unclosed_parts':0,'street_invalid_parts':0,
          'bounds':[-105,38,-104,39],'hashes':{key:'a'*64 for key in ['blocks.zip','districts.zip',*[Path(f).name for f in settings.DISTRICT['road_files']]]}})
    mean=next(item for item in MEASURES if item['id'] in MEASURE_RANGES);low,high=MEASURE_RANGES[mean['id']]
    rows=[]
    for ident,index in [('80901',25),('80902',75)]:
        cells={item['id']:[None,None,None,None,'unavailable'] for item in MEASURES}
        cells[mean['id']]=[low+(high-low)*index/100,60,1,index,'ok']
        rows.append({'id':ident,'basis':'registration','level':'postal_zip','label':'Postal ZIP '+ident,'count':60,
            'source_count':60,'status':'ok','partial':False,'share':.5,'coverage':1,'measures':cells})
    payload={'manifest.json':manifest,'rows.json':rows,'geometry.json':{'block':{},'zcta':{}},
        'streets.geojson':{'type':'FeatureCollection','features':[]},'district.geojson':{'type':'FeatureCollection','features':[]}}
    manifest['hierarchy']={'method':'geographic-extension-1','sources':SOURCES.copy(),'hashes':{level:'a'*64 for level in SOURCES},
        'reconciliation':{basis:{level:{'assigned':120,'unassigned':0} for level in EXTRA_LEVELS} for basis in manifest['bases']},
        'region_definition':'Synthetic test district','assignment':'Unique official polygon membership'}
    for level in EXTRA_LEVELS:
        ident='08041' if level=='county' else '08001' if level.startswith('state_') else '0805'
        payload['geometry.json'][level]={ident:{'id':ident,'geometry':json.loads(json.dumps(mapping(box(-105,38,-104,39)))),'bbox':[-105,38,-104,39]}}
        for basis in manifest['bases']:
            row=copy.deepcopy(rows[0]);row.update(id=ident,level=level,basis=basis,label=label(level,ident),count=120,source_count=None,coverage=None,share=1)
            for cell in row['measures'].values():
                if cell[4]=='ok':cell[1]=120;cell[3]=50
            payload['rows.json'].append(row)
    return payload



class World:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def polygon(ident, geom):
    minx, miny, maxx, maxy = geom.bounds
    return {'id': ident, 'geometry': json.loads(json.dumps(mapping(geom))), 'bbox': [minx, miny, maxx, maxy]}


def modal_pairs(first, second):
    """{first value: second value with the most rows (ties: smaller)} and the distinct-pair counts per first value."""
    counts = {}
    for a, b in zip(first, second):
        counts.setdefault(a, {}).setdefault(b, 0)
        counts[a][b] += 1
    modal = {a: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for a, c in counts.items()}
    return modal, {a: len(c) for a, c in counts.items()}


def v4_payload(fixture):
    """A valid in-memory cu-summary-v4 payload built from the fixture's area table (small geometry, real relations)."""
    data = fixture.data
    payload = hierarchy_bundle()
    reg_block = np.asarray(data['reg_block']).astype(str)
    reg_precinct = np.asarray(data['reg_precinct']).astype(str)
    reg_tract = np.asarray(data['reg_tract']).astype(str)
    reg_zip = np.asarray(data['reg_zip']).astype(str)
    block_ids = sorted(set(reg_block.tolist()))
    block_geoms = {}
    for tract_index, tract in enumerate(MF.TRACTS):
        for k, ident in enumerate(i for i in block_ids if i[:11] == tract):
            block_geoms[ident] = box(-104.90 + 0.02 * tract_index + 0.003 * k, 38.80, -104.90 + 0.02 * tract_index
                                     + 0.003 * k + 0.0025, 38.8025)
    tract_geoms = {t: unary_union([g for i, g in block_geoms.items() if i[:11] == t]) for t in MF.TRACTS}
    precinct_geoms = {p: box(-104.90 + 0.003 * k, 38.81, -104.90 + 0.003 * k + 0.0028, 38.8125)
                      for k, p in enumerate(MF.PRECINCTS)}
    zcta_geoms = {z: box(-104.90 + 0.02 * k, 38.82, -104.90 + 0.02 * k + 0.0195, 38.83) for k, z in enumerate(MF.ZIPS)}
    geometry = payload['geometry.json']
    geometry['block'] = {i: polygon(i, g) for i, g in block_geoms.items()}
    geometry['tract'] = {i: polygon(i, g) for i, g in tract_geoms.items()}
    geometry['precinct'] = {i: polygon(i, g) for i, g in precinct_geoms.items()}
    geometry['zcta'] = {i: polygon(i, g) for i, g in zcta_geoms.items()}
    adjacency = {'precinct': neighbours(precinct_geoms), 'tract': neighbours(tract_geoms),
                 'zip': neighbours(zcta_geoms)}

    block_precinct, _ = modal_pairs(reg_block.tolist(), reg_precinct.tolist())
    precinct_tract, precinct_ntracts = modal_pairs(reg_precinct.tolist(), reg_tract.tolist())
    _, precinct_nblocks = modal_pairs(reg_precinct.tolist(), reg_block.tolist())
    _, tract_nblocks = modal_pairs(reg_tract.tolist(), reg_block.tolist())
    _, zip_nblocks = modal_pairs(reg_zip.tolist(), reg_block.tolist())

    def relations_for(basis, level, ident):
        if basis != 'registration':
            return {}
        if level == 'block':
            return {'precinct': block_precinct.get(ident)}
        if level == 'precinct':
            return {'tract': precinct_tract.get(ident), 'n_tracts': precinct_ntracts.get(ident),
                    'n_blocks': precinct_nblocks.get(ident)}
        if level == 'tract':
            return {'n_blocks': tract_nblocks.get(ident)}
        return {'n_blocks': zip_nblocks.get(ident)}

    area_file = make_area_file(fixture.area_rows, relations_for)
    manifest = payload['manifest.json']
    base_key = manifest['snapshot']
    district = unary_union(list(tract_geoms.values()) + list(zcta_geoms.values())).envelope
    payload['district.geojson'] = {'type': 'FeatureCollection', 'features': [{
        'type': 'Feature', 'properties': {'id': settings.DISTRICT['district_id'], 'label': settings.DISTRICT['label']},
        'geometry': json.loads(json.dumps(mapping(district)))}]}
    apply_v4_manifest(
        manifest, area_file['rows'], adjacency, base_key=base_key, area_sha=fixture.area_sha,
        frozen=dict(AL.FROZEN_SHA256), run_id='fixture-run', created_at='Synthetic fixture for the v3 tests',
        concordance={'precinct_person_share': 0.9, 'zip_person_share': 0.9, 'precincts_without_block_majority': 0,
                     'zips_without_zcta': 0, 'blocks_added_from_source': 0, 'without_polygon': 0})
    payload['area_indices.json'] = area_file
    payload['adjacency.json'] = adjacency
    return payload


def retarget(payload):
    """Recompute the manifest's content hashes (and snapshot-independent checks) after a test edits the files."""
    rf = payload['manifest.json']['row_framework']
    rows = payload['area_indices.json']['rows']
    rf['area_indices_sha256'] = AL.sha256_json(rows)
    rf['adjacency_sha256'] = AL.sha256_json(payload['adjacency.json'])
    return payload


def write_zip(payload, path):
    """Write the payload as a ZIP (deterministic) and return its sha256."""
    path = Path(path)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, json.dumps(payload[name], separators=(',', ':')))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_world(directory, n=1500, seed=MF.SEED):
    directory = Path(directory)
    # The production package intentionally omits test-generator JSON resources.
    # Redirect only this fixture generator's exact schema read to the pinned
    # test resource; validation and Django activation still use shipped code.
    schema = Path(MF.__file__).with_name('p1_schema.json')
    resource = Path(__file__).with_name('test_terrier_p1_schema.json')
    def fixture_open(file, *args, **kwargs):
        return open(resource if isinstance(file, (str, Path)) and Path(file) == schema else file, *args, **kwargs)
    with patch.object(MF, 'open', fixture_open, create=True):
        fixture = MF.make_store(directory, n=n, seed=seed)
    payload = v4_payload(fixture)
    zip_path = directory / ('%s.zip' % payload['manifest.json']['snapshot'])
    sha = write_zip(payload, zip_path)
    return World(directory=directory, fixture=fixture, payload=payload, zip_path=zip_path, zip_sha256=sha,
                 snapshot=payload['manifest.json']['snapshot'])
