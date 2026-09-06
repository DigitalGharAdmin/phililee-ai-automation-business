"""Safe unauthenticated deployment smoke test; prints status only."""
import os
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def check(base_url: str, path: str) -> bool:
    request = Request(base_url.rstrip('/') + path, headers={'User-Agent': 'deployment-smoke-test'})
    with urlopen(request, timeout=10) as response:
        return response.status == 200 and bool(response.headers.get('X-Request-ID')) and response.headers.get('X-Content-Type-Options') == 'nosniff'


def main() -> int:
    base_url = os.environ.get('SMOKE_BASE_URL', '')
    parsed = urlsplit(base_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username:
        print('DEPLOYMENT_SMOKE=FAIL')
        return 1
    try:
        results = {path: check(base_url, path) for path in ('/health', '/ready')}
    except Exception:
        results = {'/health': False, '/ready': False}
    print('HEALTH=' + ('PASS' if results['/health'] else 'FAIL'))
    print('READINESS=' + ('PASS' if results['/ready'] else 'FAIL'))
    print('DEPLOYMENT_SMOKE=' + ('PASS' if all(results.values()) else 'FAIL'))
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
