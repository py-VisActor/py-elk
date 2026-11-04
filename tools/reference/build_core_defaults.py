"""Generate actual Core scalar defaults from the independent owner review."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(row):
    value = row['declaredDefault']
    if value is None:
        return 'None'
    if row['type'] == 'ENUM':
        return repr(value['enum'])
    if row['type'] == 'ENUMSET':
        return 'frozenset(' + repr(tuple(v['enum'] for v in value['sequence'])) + ')'
    if row['type'] == 'DOUBLE':
        return repr(float(value))
    assert type(value) in (str, bool, int)
    return repr(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    review = json.loads(args.review.read_text('utf-8'))
    assert review['accepted'] is True and not review['blockers']
    assert review['approvedOwner'] == 'CoreOptions' and review['approvedScalarDefaultCount'] == 68
    for filename, expected in review['filesSha256'].items():
        assert sha(Path(filename)) == expected, filename
    rows = review['declarations']
    assert len(rows) == len({row['id'] for row in rows}) == 68
    text = ('# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later\n'
            '# Copyright Kiel University and others; actual Core Property defaults.\n'
            '# Independent owner review SHA256: ' + sha(args.review) + '\n'
            '# Generated from actual Core assignments, not metadata fallback.\n'
            'from types import MappingProxyType\n\nCORE_SCALAR_DEFAULTS = MappingProxyType({\n'
            + ''.join('    ' + repr(row['id']) + ': ' + literal(row) + ',\n' for row in rows) + '})\n')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as output:
        output.write(text)
    print(json.dumps({'output': str(args.out), 'sha256': sha(args.out), 'actualCoreScalarDefaults': 68,
                      'layoutExecuted': False, 'fullValidation': False}))


if __name__ == '__main__':
    main()
