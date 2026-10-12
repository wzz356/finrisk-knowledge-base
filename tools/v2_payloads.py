"""Lossless publication and restoration of size-limited payloads; standard library."""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath

LIMIT = 20 * 1024 * 1024


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_path(root, relative):
    name = PurePosixPath(relative)
    if not relative or name.is_absolute() or '..' in name.parts or '\\' in relative or ':' in relative:
        raise ValueError('unsafe payload path')
    path = Path(root) / Path(*name.parts)
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('payload path escapes root')
    return path


def pack_file(source, version, relative, limit=LIMIT):
    source, version = Path(source), Path(version)
    target = safe_path(version, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    meta = {'path': relative, 'bytes': source.stat().st_size, 'sha256': sha(source), 'parts': []}
    if source.stat().st_size <= limit:
        if target.exists():
            if not target.is_file() or target.stat().st_size != meta['bytes'] or sha(target) != meta['sha256']:
                raise ValueError('existing publication copy differs; refusing to overwrite')
        else:
            shutil.copyfile(source, target)
        meta['parts'].append({'path': relative, 'compression': 'none', 'bytes': target.stat().st_size,
                              'sha256': sha(target), 'uncompressed_bytes': target.stat().st_size})
        return meta
    if target.exists():
        saved = target / 'parts.json'
        if not target.is_dir() or not saved.is_file():
            raise ValueError('existing publication split is incomplete')
        old = json.loads(saved.read_text(encoding='utf-8'))
        if any(old[key] != meta[key] for key in ('path', 'bytes', 'sha256')):
            raise ValueError('existing publication split differs')
        for part in old['parts']:
            path = safe_path(version, part['path'])
            if path.stat().st_size != part['bytes'] or sha(path) != part['sha256']:
                raise ValueError('existing split part changed')
        return old
    target.mkdir()
    buffer = bytearray()
    number = 0

    def flush():
        nonlocal number
        if not buffer:
            return
        number += 1
        part = target / f'part-{number:04d}.jsonl.gz'
        with part.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=6) as zipped:
            zipped.write(buffer)
        meta['parts'].append({'path': part.relative_to(version).as_posix(), 'compression': 'gzip',
                              'bytes': part.stat().st_size, 'sha256': sha(part), 'uncompressed_bytes': len(buffer)})
        buffer.clear()

    with source.open('rb') as stream:
        for line in stream:
            if len(line) > limit:
                raise ValueError('one JSONL line exceeds the publication part limit')
            if len(buffer) + len(line) > limit:
                flush()
            buffer.extend(line)
    flush()
    (target / 'parts.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return meta


def payload_chunks(version, meta):
    safe_path(version, meta['path'])
    for part in meta['parts']:
        path = safe_path(version, part['path'])
        if path.stat().st_size != part['bytes'] or sha(path) != part['sha256']:
            raise ValueError('publication part bytes or SHA changed: ' + part['path'])
        opener = gzip.open if part['compression'] == 'gzip' else open
        size = 0
        with opener(path, 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                size += len(chunk)
                yield chunk
        if size != part['uncompressed_bytes']:
            raise ValueError('uncompressed part size differs')


def verify_payload(version, meta):
    digest = hashlib.sha256()
    size = 0
    for chunk in payload_chunks(version, meta):
        digest.update(chunk)
        size += len(chunk)
    if digest.hexdigest() != meta['sha256'] or size != meta['bytes']:
        raise ValueError('restored original SHA or size differs: ' + meta['path'])
    return True


def restore_payloads(version, destination):
    version, destination = Path(version), Path(destination)
    mapping = json.loads((version / 'payload_map.json').read_text(encoding='utf-8'))
    metas = mapping['payloads']
    names = [meta['path'] for meta in metas]
    if len(names) != len(set(names)):
        raise ValueError('duplicate original payload path')
    for meta in metas:
        safe_path(destination, meta['path'])
        for part in meta['parts']:
            safe_path(version, part['path'])
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError('restoration destination must be empty')
    destination.mkdir(parents=True, exist_ok=True)
    for meta in metas:
        target = safe_path(destination, meta['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        with target.open('xb') as stream:
            for chunk in payload_chunks(version, meta):
                stream.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if digest.hexdigest() != meta['sha256'] or size != meta['bytes']:
            raise ValueError('restored original SHA differs: ' + meta['path'])
    return len(metas)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'restored_payloads': restore_payloads(args.version, args.destination), 'hashes_verified': True}))
