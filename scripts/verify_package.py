"""Inspect the built installer, including SDK metadata and package hygiene."""
import hashlib
from pathlib import Path, PurePosixPath
import sys
import zipfile
import yaml

path = Path(sys.argv[1])
required = {'manifest.yaml', 'README.md', 'PRIVACY.md', 'LICENSE', 'main.py',
            'agent_safety.py', 'requirements.txt', '_assets/icon.svg',
            'provider/agent_safety_toolkit.py', 'provider/agent_safety_toolkit.yaml',
            'tools/compact_json.py', 'tools/compact_json.yaml',
            'tools/redact_text.py', 'tools/redact_text.yaml'}
with zipfile.ZipFile(path) as package:
    names = set(package.namelist())
    assert required <= names, f'Missing files: {required - names}'
    for name in names:
        parts = PurePosixPath(name).parts
        assert not PurePosixPath(name).is_absolute() and '..' not in parts
        assert not any(p.startswith('.') or p in {'__pycache__', 'tests', 'benchmarks', 'scripts', 'docs', 'dist', 'build', 'venv'} for p in parts), f'Unwanted file: {name}'
        assert not name.endswith(('.pyc', '.pyo', '.difypkg')), f'Unwanted file: {name}'
        assert name != 'project-memory.md'
    manifest = yaml.safe_load(package.read('manifest.yaml'))
    from dify_plugin.core.entities.plugin.setup import PluginConfiguration
    PluginConfiguration.model_validate(manifest)
    assert manifest['privacy'] in names
    assert manifest['version'] in package.read('PRIVACY.md').decode()
    assert manifest['resource']['permission'] == {}
print(f'Verified {len(names)} package entries; SDK manifest valid.')
print(f'SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}  {path}')
