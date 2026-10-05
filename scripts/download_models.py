#!/usr/bin/env python3
"""Download versioned public model assets and verify pinned SHA256 hashes."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    ('https://github.com/WangWilly/gaze-correction-cam/releases/download/v0.1.1/weights.zip',
     '.downloads/weights.zip', '07279dd9072f784e32c26e0c40bdf10270f98c6f3e9b3effc3254c4ce05fa76a'),
    ('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
     'models/face_landmarker.task', '64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff'),
]


def main():
    for url, relative, digest in ASSETS:
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            temporary = target.with_suffix('.part')
            print(f'Downloading {url}')
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as dest:
                while chunk := response.read(1024 * 1024):
                    dest.write(chunk)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                temporary.unlink()
                raise RuntimeError(f'Checksum mismatch: {url}')
            temporary.replace(target)
        if target.suffix == '.zip':
            with zipfile.ZipFile(target) as archive:
                for entry in archive.infolist():
                    destination = (ROOT / entry.filename).resolve()
                    if not destination.is_relative_to(ROOT / 'weights'):
                        raise RuntimeError(f'Unexpected archive member: {entry.filename}')
                archive.extractall(ROOT)
        print(f'Verified {relative}')


if __name__ == '__main__':
    main()
