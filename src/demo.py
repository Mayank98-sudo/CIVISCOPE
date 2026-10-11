"""Restore the public, immutable analytical snapshot without network access."""
import hashlib
import json
from pathlib import Path
import zipfile

from src.core.config import ROOT


def prepare_demo(root=ROOT):
    root=Path(root)
    target=root/'data'/'demo'/'processed'
    with zipfile.ZipFile(root/'demo-data.zip') as archive:
        manifest=json.loads(archive.read('latest_run.json'))
        directory=Path(manifest['directory'])
        if directory.is_absolute() or '..' in directory.parts:
            raise ValueError('Invalid demo directory')
        expected={'latest_run.json',f'{directory.as_posix()}/manifest.json'}
        for name,digest in manifest['files'].items():
            if Path(name).name!=name: raise ValueError('Invalid demo output name')
            member=f'{directory.as_posix()}/{name}'
            content=archive.read(member)
            if hashlib.sha256(content).hexdigest()!=digest:
                raise ValueError('Demo output checksum failed')
            expected.add(member)
        if set(archive.namelist())!=expected:
            raise ValueError('Unexpected demo archive members')
        # Validate every member before making any writes; never extract arbitrary paths.
        for member in expected:
            content=archive.read(member)
            path=target/member
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists() or path.read_bytes()!=content:
                path.write_bytes(content)
    return target.parent,manifest['generated_at']
