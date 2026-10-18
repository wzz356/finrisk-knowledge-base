"""Verify public payloads, then extract and replay the exact portable release."""
import hashlib
import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temp-root',type=Path,help='Existing short writable directory; default is the system temporary directory')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest['schema']!='finrisk-organization-publication-v1':raise ValueError('wrong publication manifest')
    for name,meta in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size!=meta['bytes'] or sha(path)!=meta['sha256']:raise ValueError('publication payload changed: '+name)
    archive=root/manifest['archive']
    temp_root=(args.temp_root or Path(tempfile.gettempdir())).resolve()
    with tempfile.TemporaryDirectory(prefix='knowledge_replay_',dir=temp_root) as tmp:
        target=Path(tmp).resolve()
        if not target.is_relative_to(temp_root) or target==root:raise ValueError('unsafe extraction target')
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not (target/name).resolve().is_relative_to(target):raise ValueError('unsafe ZIP entry')
            z.extractall(target)
        run=subprocess.run([sys.executable,'-S','-X','utf8','-B',str(target/'code/verify_release.py'),'--root',str(target)],cwd=target,capture_output=True,text=True,encoding='utf-8')
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        result=json.loads(run.stdout)
        if result.get('passed') is not True or result.get('API_calls')!=0:raise ValueError('portable verification failed')
    print(json.dumps(dict(passed=True,publication_payloads_verified=len(manifest['files']),archive_sha256=sha(archive),portable_replay=result,new_model_calls=0),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
