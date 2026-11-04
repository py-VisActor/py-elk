"""Recompute only the E10 platform/performance change batch from saved raw data."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e10
import e10_benchmark
import e10_instrument

ROOT=Path(__file__).resolve().parents[2]


def check(root=ROOT):
    root=Path(root)
    index=e10.load(root/'references/e10-platform-matrix.json')
    for name,expected in index['originalFilesSha256'].items():
        e10.require(e10.sha256(e10.contained(root,name))==expected,'Original platform receipt bytes differ: '+name)
    matrix=e10.validate_matrix([e10.load(e10.contained(root,p)) for p in index['cells']],root)
    e10.require(matrix['passed'],'Platform matrix failed: '+str(matrix['errors']))
    sources=[e10.validate_cell(e10.load(e10.contained(root,p)),root) for p in index['sdistRepresentativeCells']]
    e10.require(len(sources)==2 and all(v['passed'] and v['artifactKind']=='sdist' for v in sources) and
                {(v['os'],v['pythonMinor']) for v in sources}=={('Windows','3.13'),('Linux','3.14')},
                'Two source-install representatives failed or differ')
    public=e10.load(root/'references/e10-benchmark.json')
    performance=e10_benchmark.validate(public,root)
    e10.require(performance['passed'],'Public benchmark failed: '+str(performance['errors']))
    instrument=e10_instrument.validate(e10.load(root/'references/e10-instrumented.json'),public,root)
    e10.require(instrument['passed'],'Instrumented cost sample failed: '+str(instrument['errors']))
    reviews=e10.load(root/'references/e10-reviews/index.json')['filesSha256']
    e10.require(len(reviews)==6,'Expected six independent source/verifier reviews')
    for name,expected in reviews.items():
        p=e10.contained(root,name);e10.require(e10.sha256(p)==expected,'Review original bytes changed')
        review=e10.load(p)
        e10.require(review['accepted'] is True and review['blockers']==[],'Independent review has blockers')
        for source,expected_sha in review['filesSha256'].items():
            e10.require(e10.sha256(e10.contained(root,source))==expected_sha,'Reviewed source changed: '+source)
    names=['references/e10-platform-matrix.json','references/e10-benchmark.json','references/e10-instrumented.json',
           'references/e10-reviews/index.json',*index['originalFilesSha256'],*reviews]
    return {'schema':'py-elk-e10-runtime-audit/v1','status':'E10_CHANGE_BATCH_VALIDATED','passed':True,
            'platform':matrix,'sourceInstallRepresentatives':sources,'publicPerformance':performance,
            'instrumentedCostSamples':instrument,'independentReviews':reviews,
            'evidenceFilesSha256':{n:e10.sha256(root/n) for n in names},
            'verifierSourcesSha256':{p.relative_to(root).as_posix():e10.sha256(p)
                                    for p in sorted((root/'scripts').rglob('*.py'))},
            'wheelSha256':matrix['cells'][0]['wheelSha256'],'fullValidation':False,'runtimeReexecuted':False,
            'pythonAlgorithmsVerified':0,'packagePublished':False,'historicalExecutionAuthenticated':False,
            'limits':['Eight wheel cells; two explicitly named sdist representatives, not eight sdist cells.',
                      'Performance only on the recorded Linux CPython3.14 host and three bounded inputs.',
                      'Instrumented samples are separate from public statistics; no hard resource quota.',
                      'Full migration validation remains deferred until all planned features are implemented.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=check()
        from layout_checks import write
        write(args.out,result)
        print(json.dumps({'status':result['status'],'wheelCells':8,'sdistRepresentatives':2,
                          'publicCaptures':18,'instrumentedCases':3,'fullValidation':False}))
        return 0
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as error:
        print(json.dumps({'passed':False,'error':str(error)}));return 1


if __name__=='__main__':raise SystemExit(main())
