"""Recompute the new original Stress interactive inline-default witness.

Usage: python check_stress_inline.py ORACLE REPORT
No Python candidate defines the expected geometry.
"""
import base64
import hashlib
import json
from pathlib import Path
import sys


def main():
    oracle, report = map(Path, sys.argv[1:])
    digest = lambda b: hashlib.sha256(b).hexdigest()
    value = json.loads(oracle.read_bytes())
    assert value['upstream']['distributionSha256']['lib/elk-worker.js'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert len(value['cases']) == 1
    row = value['cases'][0]
    request_raw = base64.b64decode(row['requestBytesBase64'], validate=True)
    observation_raw = base64.b64decode(row['observationBytesBase64'], validate=True)
    assert digest(request_raw) == row['requestSha256'] and digest(observation_raw) == row['observationSha256']
    request, observed = json.loads(request_raw), json.loads(observation_raw)
    assert observed['requestSha256'] == digest(request_raw) and observed['outcome'] == 'returned'
    graph = request['graph']
    assert graph['layoutOptions'] == {'org.eclipse.elk.algorithm':'stress','org.eclipse.elk.interactive':True}
    assert not request['constructor'] and not request['layoutArguments']
    assert all(node['layoutOptions']['org.eclipse.elk.stress.fixed'] is True for node in graph['children'])
    assert 'layoutOptions' not in graph['edges'][0]['labels'][0]
    result = observed['result']
    first, second = result['children']
    sx, sy = first['x']+first['width']/2, first['y']+first['height']/2
    tx, ty = second['x']+second['width']/2, second['y']+second['height']/2
    assert sx < tx and sy < ty
    label = result['edges'][0]['labels'][0]
    # Original FLabel fourth quadrant, false, with source property spacing5.
    false_position = {'x':sx+(tx-sx)/2+5,'y':sy+(ty-sy)/2-5-label['height']}
    true_position = {'x':sx+(tx-sx)*.5-label['width']*.5,'y':sy+(ty-sy)*.5-label['height']*.5}
    actual = {key:label[key] for key in ('x','y')}
    assert actual == false_position and actual != true_position
    value = dict(passed=True,actual=actual,falsePropertyFormula=false_position,trueInlineFormula=true_position,
                 observedPropertyDefault=False,metadataSupportDefaultIsSeparate=True,
                 requestSha256=digest(request_raw),observationSha256=digest(observation_raw),oracleSha256=digest(oracle.read_bytes()),
                 checkerSha256=digest(Path(__file__).read_bytes()),candidateExecuted=False,fullValidation=False,
                 scope='Only this original interactive fixed-nodes label witness; no lifecycle acceptance')
    with report.open('x', encoding='utf-8') as handle: json.dump(value,handle,indent=2,allow_nan=False)
    print(json.dumps(value))


if __name__ == '__main__': main()
