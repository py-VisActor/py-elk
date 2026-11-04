"""Compile reviewed provider membership/metadata; no runtime reference reads."""
import argparse,hashlib,json,pprint
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text('utf-8'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();review=load(args.review)
    if review.get('accepted')is not True or type(review.get('blockers'))is not list or review['blockers']!=[]:
        raise ValueError('An accepted independent source review is required')
    bindings=review['filesSha256']
    if not any(Path(k).resolve()==args.source.resolve()and v==sha(args.source)for k,v in bindings.items()):
        raise ValueError('Review must bind the exact registration source packet')
    for name,value in bindings.items():
        if sha(Path(name))!=value:raise ValueError('Reviewed dependency changed: '+name)
    packet=load(args.source)
    for name,value in packet['evidenceSha256'].items():
        if sha(Path(name))!=value:raise ValueError('Source evidence changed: '+name)
    observed=load(Path('test-runs/20261104-HOST-12/root/metadata-registration-original-01/observation.json'))
    groups={row['name']:row for row in observed['observation']['groups']};core=groups['core']
    assert len(core['algorithms'])==3 and len(core['options'])==94 and len(core['categories'])==8
    whole=groups['default'];assert(len(whole['algorithms']),len(whole['options']),len(whole['categories']))==(12,243,8)
    manifest=load(Path('references/metadata/manifest.json'));descriptions={}
    for kind in('algorithms','options','categories'):
        path=Path('references/metadata')/(kind+'.json');assert sha(path)==manifest['files'][path.name]
        rows=load(path);assert len(rows)==manifest['counts'][kind]
        descriptions[kind]={row['id']:row for row in rows}
        actual=whole[kind]if kind!='options'else[row['id']for row in whole[kind]]
        assert list(descriptions[kind])==actual
    base_options=tuple(row['id']for row in core['options']);base_algorithms=tuple(core['algorithms'])
    providers={}
    for key in('layered','force','stress','mrtree','radial','disco','spore','rectpacking'):
        row=groups[key]
        assert tuple(row['algorithms'][:3])==base_algorithms
        assert tuple(r['id']for r in row['options'][:94])==base_options
        providers[key]={'algorithms':tuple(row['algorithms'][3:]),'options':tuple(r['id']for r in row['options'][94:])}
    legacy={row['id']:tuple(row['legacyIds'])for row in whole['options']if row['legacyIds']}
    assert legacy=={'org.eclipse.elk.layered.allowNonFlowPortsToSwitchSides':('org.eclipse.elk.layered.northOrSouthPort',)}
    default=('layered','stress','mrtree','radial','force','disco','sporeOverlap','sporeCompaction','rectpacking')
    values={'DEFAULT_PROVIDERS':default,'CORE_ALGORITHMS':base_algorithms,'CORE_OPTIONS':base_options,
      'CATEGORY_IDS':tuple(core['categories']),'PROVIDER_MEMBERSHIP':providers,'LEGACY_IDS':legacy,
      'ALGORITHM_DESCRIPTIONS':descriptions['algorithms'],'OPTION_DESCRIPTIONS':descriptions['options'],
      'CATEGORY_DESCRIPTIONS':descriptions['categories']}
    text=('# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later\n'
      '# Copyright Kiel University and others; fixed elkjs0.12.1 metadata.\n'
      '# Registration source packet SHA256: '+sha(args.source)+'\n'
      '# Independent review SHA256: '+sha(args.review)+'\n'
      '# Static declarations only; metadata does not certify executable bodies.\n')
    for name,value in values.items():text+=name+' = '+pprint.pformat(value,width=110,sort_dicts=False)+'\n\n'
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8',newline='\n')as f:f.write(text)
    print(json.dumps({'output':str(args.out),'sha256':sha(args.out),'metadataCounts':[12,243,8],
      'providerGroups':len(providers),'legacyOptions':len(legacy),'layoutExecuted':False,'fullValidation':False}))

if __name__=='__main__':main()
