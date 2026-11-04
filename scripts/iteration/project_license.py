"""Check the selected MIT decision and actual package bytes without a release claim.

Development-only license delta entry. The formal e11_package CLI keeps its stable
version gate; neither entry executes a layout or imports the product package.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from e11_package import ROOT, check_artifacts, check_source

EXPRESSION = 'MIT AND (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0'


def check(wheel=None, sdist=None):
    result = (check_artifacts(wheel, sdist, require_stable=False) if wheel is not None
              else check_source(require_stable=False))
    try:
        decision = json.loads((ROOT/'docs/decisions/0009-project-license.json').read_bytes())
        if not (decision['originalCodeLicense'] == 'MIT' and
                decision['distributionExpression'] == EXPRESSION and
                decision['upstreamDeclarationsPreserved'] is True and
                decision['publicationAuthorizedByThisRecord'] is False):
            raise ValueError('Selected MIT scope or upstream preservation differs')
        text = (ROOT/'LICENSE').read_text(encoding='utf8')
        if not (text.startswith('MIT License\n') and 'Permission is hereby granted, free of charge' in text
                and 'THE SOFTWARE IS PROVIDED "AS IS"' in text):
            raise ValueError('Expected root MIT license text')
    except (ValueError, KeyError, OSError) as error:
        result = {**result, 'passed': False, 'errors': [*result['errors'], str(error)]}
    return {**result, 'validationScope': 'license-and-package-delta-only',
            'formalCandidateAccepted': False, 'published': False,
            'productExecutions': 0, 'fullValidation': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--sdist', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if (args.wheel is None) != (args.sdist is None):
        parser.error('Supply both --wheel and --sdist, or neither')
    result = check(args.wheel, args.sdist)
    result['verifierSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('passed', 'errors', 'validationScope', 'productExecutions')}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
