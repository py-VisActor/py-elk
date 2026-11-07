"""Version-only documentation release: immutable delta, real installs and readback."""
from pathlib import Path
import argparse
from email.parser import BytesParser
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.request
import urllib.error
import urllib.parse
import zipfile

ROOT=Path(__file__).resolve().parents[1]
API='https://api.github.com/repos/py-VisActor/py-elk'
VERSION='0.1.1'
DOC='https://github.com/py-VisActor/py-elk/blob/main/docs/README.md'

def require(value,message):
    if not value:raise ValueError(message)

def identity(path):
    raw=path.read_bytes();return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def description(value):
    # Core metadata serializers may use CRLF; compare text without changing
    # any content, while distribution bytes retain their separate SHA checks.
    return value.replace('\r\n','\n').strip()

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def guard():
    base='v0.1.0';before=tomllib.loads(git('show',base+':pyproject.toml').decode('utf8'))
    after=tomllib.loads((ROOT/'pyproject.toml').read_text('utf8'))
    require(after['project']['version']==VERSION,'Wrong documentation release version')
    a=after['project'].copy();b=before['project'].copy()
    for key in ('version','urls'):a.pop(key,None);b.pop(key,None)
    require(a==b and after['build-system']==before['build-system'],'Non-documentation project metadata changed')
    require(after['project']['urls']['Documentation']==DOC,'Wrong user documentation URL')
    paths=[p for p in git('ls-tree','-r','--name-only',base,'src/pyelk').decode().splitlines()
           if p.endswith('.py') or p.endswith('py.typed') or '/_licenses/' in p]
    actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'src/pyelk').rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and (p.suffix=='.py' or p.name=='py.typed' or '_licenses' in p.parts)}
    require(set(paths)==actual,'Runtime file set changed')
    changed=[]
    for name in paths:
        original=git('show',base+':'+name);raw=(ROOT/name).read_bytes()
        if raw!=original:
            require(name=='src/pyelk/__init__.py' and raw.replace(b'__version__ = "0.1.1"',b'__version__ = "0.1.0"',1)==original,'Runtime implementation changed: '+name)
            changed.append(name)
    require(changed==['src/pyelk/__init__.py'],'Expected exact version-only runtime delta')
    for name in ('README.md','README.en.md','docs/USAGE.md'):
        require('py-visactor-elk=='+VERSION in (ROOT/name).read_text('utf8'),'Stale installation example: '+name)
    return {'status':'PASS','baselineTag':base,'baselineCommit':git('rev-parse',base+'^{commit}').decode().strip(),
            'version':VERSION,'runtimeFiles':len(paths),'changedRuntimeFiles':changed,'implementationUnchanged':True,
            'dependenciesUnchanged':True,'documentation':DOC,'sourceCommit':git('rev-parse','HEAD').decode().strip()}

def artifacts(dist):
    wheels=list(dist.glob('*.whl'));sdists=list(dist.glob('*.tar.gz'))
    require(len(wheels)==len(sdists)==1,'Expected exactly one wheel and sdist')
    return wheels[0],sdists[0]

def manifest(dist):
    proof=guard();wheel,sdist=artifacts(dist)
    with zipfile.ZipFile(wheel) as z:
        names=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
        require(len(names)==1,'Wheel metadata missing')
        meta=BytesParser().parsebytes(z.read(names[0]))
    require(meta['Name']=='py-visactor-elk' and meta['Version']==VERSION,'Wrong package identity')
    require(dict(v.split(', ',1) for v in meta.get_all('Project-URL'))['Documentation']==DOC,'Wheel Documentation URL differs')
    require(description(meta.get_payload(decode=True).decode('utf8'))==description((ROOT/'README.md').read_text('utf8')),'Wheel description is not the user README')
    with tarfile.open(sdist) as t:
        names=[m for m in t.getmembers() if m.name.endswith('/PKG-INFO') and m.name.count('/')==1]
        require(len(names)==1,'Sdist metadata missing')
        metadata=BytesParser().parsebytes(t.extractfile(names[0]).read())
        require(metadata['Version']==VERSION and description(metadata.get_payload(decode=True).decode('utf8'))==description((ROOT/'README.md').read_text('utf8')),'Sdist description/version differs')
    result={'schema':'pyelk-documentation-release/v1',**proof,'status':'BUILT_NOT_PUBLISHED',
            'distributions':{p.name:identity(p) for p in (wheel,sdist)},'readme':identity(ROOT/'README.md')}
    save(dist/'release-manifest.json',result);return result

def install(dist,out,wheelhouse):
    wheel,sdist=artifacts(dist);out.mkdir(parents=True,exist_ok=False)
    for kind in ('wheel','sdist'):
        argv=[sys.executable,str(ROOT/'scripts/validate_full_package.py'),'--wheel',str(wheel.resolve()),
              '--sdist',str(sdist.resolve()),'--out',str(out/kind),'--install-kind',kind,
              '--exercise-mrtree-cycle',str(ROOT/'tests/fixtures/suites/full-option-effects-nonlayered/requests/mrtree-cycle-bfs.json')]
        if kind=='sdist':argv+=['--wheelhouse',str(wheelhouse.resolve())]
        result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        (out/(kind+'.stdout.log')).write_text(result.stdout,encoding='utf8');(out/(kind+'.stderr.log')).write_text(result.stderr,encoding='utf8')
        save(out/(kind+'.command.json'),{'argv':argv,'exitCode':result.returncode})
        require(result.returncode==0,'Isolated '+kind+' install failed; retained logs in '+str(out))
    return {'status':'PASS','kinds':['wheel','sdist']}

def credentials():
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:return token
    r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,
          env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'})
    values=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
    require(bool(values.get('password')),'No existing GitHub credential');return values['password']

def request(url,method='GET',data=None):
    require(urllib.parse.urlsplit(url).hostname in ('api.github.com','uploads.github.com'),'Unsafe credential destination')
    raw=json.dumps(data).encode() if isinstance(data,dict) else data
    req=urllib.request.Request(url,data=raw,method=method,headers={'Authorization':'Bearer '+credentials(),
        'Accept':'application/vnd.github+json','Content-Type':'application/json' if isinstance(data,dict) else 'application/octet-stream',
        'User-Agent':'py-elk-documentation-release','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req,timeout=120) as response:
        body=response.read();return json.loads(body) if body else None

def readback(dist,out):
    out.mkdir(parents=True,exist_ok=False);expected=manifest(dist)
    for attempt in range(12):
        try:
            with urllib.request.urlopen('https://pypi.org/pypi/py-visactor-elk/'+VERSION+'/json',timeout=60) as r:published=json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code!=404 or attempt==11:raise
            print('Awaiting PyPI metadata',flush=True);time.sleep(10)
    require(published['info']['project_urls']['Documentation']==DOC,'Actual PyPI Documentation URL differs')
    require(description(published['info']['description'])==description((ROOT/'README.md').read_text('utf8')),'Actual PyPI description is not user README')
    files={r['filename']:r for r in published['urls']};require(set(files)==set(expected['distributions']),'PyPI artifact set differs')
    downloaded=out/'packages';downloaded.mkdir()
    for name,checksum in expected['distributions'].items():
        require(files[name]['digests']['sha256']==checksum['sha256'],'PyPI recorded SHA differs')
        with urllib.request.urlopen(files[name]['url'],timeout=120) as r:raw=r.read()
        target=downloaded/name;target.write_bytes(raw);require(identity(target)==checksum,'Actual downloaded bytes differ')
    save(downloaded/'release-manifest.json',expected);save(out/'pypi.json',published)
    proof={'schema':'pyelk-actual-publication/v1','project':'py-visactor-elk','version':VERSION,'published':True,
           'projectDocumentation':DOC,'descriptionMatchesUserREADME':True,'downloadBytesVerified':True,
           'sourceCommit':expected['sourceCommit'],'distributions':expected['distributions']}
    save(out/'publication.json',proof);return proof

def github(dist,out):
    tag='v'+VERSION;expected=json.loads((dist/'release-manifest.json').read_text('utf8'))
    existing=request(API+'/releases?per_page=100');require(not any(r['tag_name']==tag for r in existing),'Release already exists; do not overwrite')
    release=request(API+'/releases','POST',{'tag_name':tag,'name':'py-visactor-elk '+VERSION,'body':(ROOT/'docs/releases/0.1.1.md').read_text('utf8'),'draft':False,'prerelease':False})
    uploads=release['upload_url'].split('{',1)[0];assets=[]
    for p in [*artifacts(dist),dist/'release-manifest.json',out/'publication.json']:
        result=request(uploads+'?name='+urllib.parse.quote(p.name),'POST',p.read_bytes());assets.append({'name':p.name,'url':result['browser_download_url'],**identity(p)})
    proof={'status':'PUBLISHED','url':release['html_url'],'assets':assets};save(out/'github-release.json',proof);return proof

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('guard','manifest','install','readback','github'))
    p.add_argument('--dist',type=Path,default=ROOT/'dist');p.add_argument('--out',type=Path);p.add_argument('--wheelhouse',type=Path)
    args=p.parse_args()
    if args.action=='guard':result=guard()
    elif args.action=='manifest':result=manifest(args.dist)
    elif args.action=='install':result=install(args.dist,args.out,args.wheelhouse)
    elif args.action=='readback':result=readback(args.dist,args.out)
    else:result=github(args.dist,args.out)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
