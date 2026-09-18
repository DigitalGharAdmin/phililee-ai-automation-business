"""Scan project tracked/nonignored files without printing matched private values."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()


def main():
    paths = set(filter(None, git('ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', '.').split('\0')))
    findings = []
    patterns = {
        'provider token': r'sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{20,}|ya29\.[A-Za-z0-9_-]+',
        'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY',
        'bearer token': r'Bearer\s+[A-Za-z0-9_.-]{20,}',
        'secret assignment': r'''(?im)["']?(?:access_token|refresh_token|client_secret|password|OPENAI_API_KEY)["']?\s*[:=]\s*["']([A-Za-z0-9_./+=-]{20,})["']''',
    }
    for name in sorted(paths):
        path = ROOT / name
        if path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example'):
            findings.append((name, 'environment file'))
        if re.search(r'\.(?:db|sqlite3?)(?:-|$)', name, re.I):
            findings.append((name, 'database file'))
        if re.search(r'(?:credential.*export|export.*credential|debug.*dump)', path.name, re.I):
            findings.append((name, 'private export/debug dump'))
        if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.pdf'}:
            findings.append((name, 'binary evidence requires manual privacy review'))
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeError:
            findings.append((name, 'unreviewed binary'))
            continue
        for category, pattern in patterns.items():
            if re.search(pattern, content):
                findings.append((name, category))
        for domain in re.findall(r'[\w.+-]+@([\w.-]+\.[A-Za-z]{2,})', content):
            if domain.lower() not in {'example.com', 'example.org', 'example.net', 'example.test', 'test.com'}:
                findings.append((name, 'nonexample email'))
        if path.suffix == '.json':
            data = json.loads(content)
            if isinstance(data, dict) and 'nodes' in data:
                if not name.endswith('.sanitized.json'):
                    findings.append((name, 'raw workflow export'))
                for node in data['nodes']:
                    if node.get('credentials') or node.get('webhookId'):
                        findings.append((name, 'account-specific workflow metadata'))
    for name in ['.env', 'lead_generation.db', 'demo_local.db', 'lead_generation.db-wal']:
        result = subprocess.run(['git', 'check-ignore', '-q', '--', name], cwd=ROOT)
        if result.returncode:
            findings.append((name, 'ignore rule missing'))
    for name, category in sorted(set(findings)):
        print(f'{name}: {category}; remediation required')
    print('SECRET/PRIVACY/TRACKING AUDIT: ' + ('FAIL' if findings else 'PASS'))
    return bool(findings)


if __name__ == '__main__':
    raise SystemExit(main())
