"""Generate static component rules from independently accepted source spans."""
import argparse,base64,hashlib,json,re
from pathlib import Path


def build(packet_path,review_paths,output,base_only=False):
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    packet=json.loads(packet_path.read_text('utf-8'));packet_sha=sha(packet_path)
    spans={s['id']:s for s in packet['sourceSpans']};approved=set()
    for review_path in review_paths:
        review=json.loads(review_path.read_text('utf-8'))
        assert review['accepted']is True and review['blockers']==[]
        assert review['filesSha256'][packet_path.as_posix()]==packet_sha
        for s in review.get('spans',[]):
            assert s['sha256']==spans[s['id']]['sha256']
            approved.add(s['id'])
    required={'EC01'}if base_only else{'EC01','EC05'}
    assert required<=approved,(required,approved)
    tables=[]
    for id,name in(('EC01','CONSTRAINTS'),('EC05','MODEL_ORDER_CONSTRAINTS')):
        if id not in required:continue
        span=spans[id];data=base64.b64decode(span['base64'])
        assert hashlib.sha256(data).hexdigest()==span['sha256']
        text=data.decode('utf-8')
        rows=re.findall(r'\$put\('+name+r', .*?\b(SIDES_[A-Z_]+)\)?, (SIDES_[A-Z_]+)\);',text)
        assert len(rows)==len(re.findall(r'\$put\('+name+',',text))and rows
        tables.append((name,rows))
    lines=['# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later',
      '# Copyright Kiel University and others. Generated from fixed worker275e6caf.',
      '# build_component_group_rules.py; accepted exact source only, no runtime I/O.',
      'SOURCE_PACKET_SHA256 = '+repr(packet_sha),'']
    for name,rows in tables:
        lines.append(name+'_RULES = (')
        lines.extend('    '+repr(tuple(row))+','for row in rows);lines.extend((')',''))
    output.write_text('\n'.join(lines),encoding='utf-8')
    return {'sourcePacketSha256':packet_sha,'outputSha256':sha(output),'pairs':{name:len(rows)for name,rows in tables},'productsExecuted':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--review',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--base-only',action='store_true')
    args=parser.parse_args();print(json.dumps(build(args.packet,args.review,args.output,args.base_only)))
