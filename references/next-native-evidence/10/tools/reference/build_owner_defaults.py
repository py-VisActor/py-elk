"""Generate scoped actual-owner declarations after independent source review.

This development tool never selects a runtime owner or executes a layout.
The generated table is declarations, not metadata/default fallback policy.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tagged(value):
    """Keep the actual observation's type tag without constructing objects."""
    if isinstance(value,dict):
        if len(value)!=1:
            raise ValueError('An owner default must have one observed type tag')
        key,payload=next(iter(value.items()))
        if key not in ('enum','insets','vector','sequence','negativeZero','nonfinite'):
            raise ValueError('Unmapped owner default requires its own source closure')
        return (key,tagged(payload))
    if isinstance(value,list):
        return tuple(tagged(item)for item in value)
    if value is None or type(value)in(str,bool,int,float):
        return value
    raise TypeError('Unexpected original default view')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('references/next-property-runtime-defaults-sources.json'))
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    review=json.loads(args.review.read_text('utf-8'))
    if review.get('accepted')is not True or type(review.get('blockers'))is not list or review['blockers']!=[]:
        raise ValueError('An accepted independent source review is required')
    bindings=review['filesSha256']
    if not any(Path(name).resolve()==args.source.resolve()and digest==sha(args.source)for name,digest in bindings.items()):
        raise ValueError('The review must bind these exact original owner observations')
    for name,expected in bindings.items():
        if sha(Path(name))!=expected:
            raise ValueError('Reviewed dependency changed: '+name)
    source=json.loads(args.source.read_text('utf-8'))
    if source['workerSha256']!='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86':
        raise ValueError('Unexpected original worker')
    indexed={(owner['owner'],row['symbol']):row for owner in source['owners']for row in owner['properties']}
    keys=[(row['owner'],row['symbol'])for row in review['approvedRows']]
    if not keys or len(keys)!=len(set(keys)):
        raise ValueError('Approved owner/symbol keys must be nonempty and unique')
    rows=[]
    for owner,symbol in keys:
        row=indexed[owner,symbol]
        rows.append((owner,symbol,row['id'],tagged(row['declaredDefault']),row['propertyIdentity'],
                     row['defaultIdentity'],row['sourceCloneableDefault']))
    text=('# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later\n'
          '# Copyright Kiel University and others; actual static Property declarations.\n'
          '# Independent review SHA256: '+sha(args.review)+'\n'
          '# Actual owner observations SHA256: '+sha(args.source)+'\n'
          '# No runtime owner selection, metadata fallback, or object allocation.\n'
          '# Fields: owner, symbol, id, tagged default view, property identity label,\n'
          '# default identity label, source type4 flag. Identity labels are local\n'
          '# to the fixed original observation, not runtime Python identities.\n'
          'OWNER_PROPERTY_DECLARATIONS = (\n'+''.join('    '+repr(row)+',\n'for row in rows)+')\n')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8',newline='\n')as f:
        f.write(text)
    print(json.dumps({'output':str(args.out),'sha256':sha(args.out),'declarations':len(rows),
                      'runtimeOwnerSelected':False,'layoutExecuted':False,'fullValidation':False}))


if __name__=='__main__':
    main()
