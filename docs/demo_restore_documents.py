"""Restore the exported document volume without replacing existing files."""
import os
import tarfile
from pathlib import Path, PurePosixPath

source = Path(os.environ.get('DEMO_BACKUP_DIR', '/demo-backup')) / 'documents.tar.gz'
target = Path(os.environ.get('DEMO_DOCUMENT_DIR', '/app/storage'))
target.mkdir(parents=True, exist_ok=True)
if any(target.iterdir()):
    raise SystemExit('Restore refused: target document volume is not empty.')
with tarfile.open(source, 'r:gz') as archive:
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit('Unsafe document archive entry: ' + member.name)
    archive.extractall(target, filter='data')
print('Uploaded documents restored.')
