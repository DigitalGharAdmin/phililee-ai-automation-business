import json
import unittest
from dataclasses import replace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.security import MemoryRateLimiter, RATE_LIMITER, RedisRateLimiter, SecurityMiddleware, enforce_principal_rate_limit, redact
from app.principals import AuthenticatedPrincipal, AuthenticationMethod, CustomerStatus, PrincipalType
import uuid
from unittest.mock import AsyncMock
from app.settings import SETTINGS


class TestSecurityMiddleware(unittest.TestCase):
    def make_client(self, **changes):
        defaults = {'trusted_hosts': ('testserver',), 'cors_allowed_origins': ('https://allowed.example',), 'rate_limit_requests': 100, 'max_request_body_bytes': 1024}
        defaults.update(changes)
        settings = replace(SETTINGS, **defaults)
        test_app = FastAPI()
        test_app.add_middleware(SecurityMiddleware, settings_getter=lambda: settings)
        @test_app.post('/support')
        async def support(): return {'ok': True}
        @test_app.get('/docs-check')
        async def docs_check(): return {'ok': True}
        @test_app.exception_handler(Exception)
        async def safe_error(request, exc): return JSONResponse(status_code=500, content={'detail': 'Internal server error.'})
        @test_app.get('/boom')
        async def boom(): raise RuntimeError('secret diagnostic value')
        return TestClient(test_app, raise_server_exceptions=False)

    def setUp(self): RATE_LIMITER.reset()
    def tearDown(self): RATE_LIMITER.reset()

    def test_security_headers_cache_and_generated_request_id(self):
        response = self.make_client().post('/support', json={'x': 'y'})
        self.assertEqual(response.status_code, 200)
        for name in ('x-content-type-options', 'x-frame-options', 'referrer-policy', 'permissions-policy', 'content-security-policy', 'x-request-id'):
            self.assertIn(name, response.headers)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertNotIn('strict-transport-security', response.headers)

    def test_request_id_validation_and_hsts(self):
        client = self.make_client(app_environment='production', enable_hsts=True, enable_api_docs=False, rate_limit_backend='external')
        valid = client.get('/docs-check', headers={'X-Request-ID': 'safe-id_123'})
        malformed = client.get('/docs-check', headers={'X-Request-ID': 'bad id\t' + 'x' * 100})
        self.assertEqual(valid.headers['x-request-id'], 'safe-id_123')
        self.assertNotEqual(malformed.headers['x-request-id'], 'bad id\t' + 'x' * 100)
        self.assertIn('max-age=', valid.headers['strict-transport-security'])
        self.assertEqual(client.get('/docs').status_code, 404)
        self.assertEqual(client.get('/redoc').status_code, 404)
        self.assertEqual(client.get('/openapi.json').status_code, 404)

    def test_cors_allowed_and_disallowed(self):
        client = self.make_client()
        allowed = client.post('/support', json={}, headers={'Origin': 'https://allowed.example'})
        blocked = client.post('/support', json={}, headers={'Origin': 'https://blocked.example'})
        preflight = client.options('/support', headers={'Origin': 'https://allowed.example'})
        self.assertEqual(allowed.headers['access-control-allow-origin'], 'https://allowed.example')
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(preflight.status_code, 200)

    def test_trusted_host(self):
        client = self.make_client()
        self.assertEqual(client.get('/docs-check').status_code, 200)
        self.assertEqual(client.get('/docs-check', headers={'Host': 'evil.example'}).status_code, 400)

    def test_content_type_and_bounded_body(self):
        client = self.make_client(max_request_body_bytes=1024)
        self.assertEqual(client.post('/support', content=b'{}').status_code, 415)
        self.assertEqual(client.post('/support', content=b'x' * 1025, headers={'Content-Type': 'application/json'}).status_code, 413)
        at_limit = client.post('/support', content=b' ' * 1022 + b'{}', headers={'Content-Type': 'application/json'})
        self.assertNotEqual(at_limit.status_code, 413)
        malformed_length = client.post('/support', content=b'{}', headers={'Content-Type': 'application/json', 'Content-Length': 'invalid'})
        self.assertNotEqual(malformed_length.status_code, 413)

    def test_rate_limit_and_credential_bucket_isolation(self):
        client = self.make_client(rate_limit_requests=1)
        first = client.post('/support', json={}, headers={'Authorization': 'Bearer first'})
        second_identity = client.post('/support', json={}, headers={'Authorization': 'Bearer second'})
        exceeded = client.post('/support', json={}, headers={'Authorization': 'Bearer first'})
        self.assertEqual((first.status_code, second_identity.status_code, exceeded.status_code), (200, 200, 429))
        self.assertGreaterEqual(int(exceeded.headers['retry-after']), 1)
        self.assertNotIn('first', exceeded.text)

    def test_window_reset_with_deterministic_clock(self):
        now = [10.0]
        limiter = MemoryRateLimiter(clock=lambda: now[0])
        self.assertTrue(limiter.allow('a', 1, 5)[0])
        self.assertFalse(limiter.allow('a', 1, 5)[0])
        now[0] = 16.0
        self.assertTrue(limiter.allow('a', 1, 5)[0])

    def test_authenticated_principal_buckets_are_stable_and_isolated(self):
        limiter = MemoryRateLimiter()
        settings = replace(SETTINGS, rate_limit_requests=1)
        def principal(customer_id):
            return AuthenticatedPrincipal(principal_type=PrincipalType.CUSTOMER, subject='token-subject', authentication_method=AuthenticationMethod.FIREBASE_ID_TOKEN, customer_id=customer_id, provider='firebase', customer_status=CustomerStatus.ACTIVE)
        first, second = principal(uuid.uuid4()), principal(uuid.uuid4())
        enforce_principal_rate_limit(first, '/v2/support', settings, limiter)
        enforce_principal_rate_limit(second, '/v2/support', settings, limiter)
        with self.assertRaisesRegex(Exception, '429'):
            enforce_principal_rate_limit(first, '/v2/support', settings, limiter)

    def test_redis_limiter_uses_hashed_key_and_atomic_script_result(self):
        limiter = RedisRateLimiter.__new__(RedisRateLimiter)
        limiter.client = AsyncMock()
        limiter.client.eval.return_value = (2, 17)
        allowed, retry = __import__('asyncio').run(limiter.allow('credential:hashed-value', 1, 60))
        self.assertFalse(allowed)
        self.assertEqual(retry, 17)
        args = limiter.client.eval.await_args.args
        self.assertNotIn('Bearer', ' '.join(map(str, args)))
        self.assertIn('hashed-value', args[2])

    def test_safe_logging_and_redaction(self):
        secret = 'secret diagnostic value'
        with self.assertLogs('app.http', level='INFO') as captured:
            response = self.make_client().get('/boom', headers={'Authorization': 'Bearer do-not-log'})
        self.assertEqual(response.status_code, 500)
        rendered = '\n'.join(captured.output)
        self.assertNotIn(secret, rendered)
        self.assertNotIn('do-not-log', rendered)
        event = json.loads(captured.records[-1].getMessage())
        self.assertEqual(set(event), {'request_id', 'method', 'path', 'status', 'duration_ms'})
        cleaned = redact({'authorization': 'a', 'token': 'b', 'password': 'c', 'database_url': 'postgresql://user:password@host/db', 'safe': 'ok'})
        self.assertEqual(cleaned['safe'], 'ok')
        self.assertTrue(all(cleaned[key] == '[REDACTED]' for key in ('authorization', 'token', 'password', 'database_url')))
