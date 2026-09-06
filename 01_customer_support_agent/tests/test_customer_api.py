import unittest
import uuid
from dataclasses import replace
from unittest.mock import patch

from tests import TEST_SERVICE_KEY
from fastapi.testclient import TestClient
from firebase_admin import auth
from sqlalchemy import create_engine, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import app
from app.authorization import get_customer_owned_order
from app.database import Base, get_db
from app.db_models import Customer, Order
from app.firebase_auth import FirebaseTokenVerifier, get_firebase_token_verifier
from app.settings import SETTINGS


class TestCustomerApi(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.owner = uuid.uuid4()
        self.foreign = uuid.uuid4()
        with self.sessions.begin() as db:
            db.add_all([
                Customer(id=self.owner, auth_provider='firebase', auth_subject='fixture-owner', status='active', display_name='Same Name', email='same@example.invalid'),
                Customer(id=self.foreign, auth_provider='firebase', auth_subject='fixture-foreign', status='active', display_name='Same Name', email='same@example.invalid'),
            ])
            db.flush()
            for number, owner in [('DG-8001', self.owner), ('DG-8002', self.foreign), ('DG-8003', None)]:
                db.add(Order(order_number=number, customer_id=owner, customer_name='Different Snapshot', status='Processing', estimated_delivery='Tomorrow', tracking_number='TEST'))
        def get_test_db():
            with self.sessions() as db:
                try:
                    yield db
                except Exception:
                    db.rollback()
                    raise
        verifier = FirebaseTokenVerifier(settings=replace(SETTINGS, firebase_project_id='fixture-project'), check_revoked=True)
        verifier._app = object()
        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_firebase_token_verifier] = lambda: verifier
        self.verify_patch = patch('app.firebase_auth.auth.verify_id_token', side_effect=self.verify)
        self.verify_patch.start()
        self.client = TestClient(app, raise_server_exceptions=False)

    def verify(self, token, **kwargs):
        failures = {
            'expired': auth.ExpiredIdTokenError('expired', None),
            'revoked': auth.RevokedIdTokenError('revoked'),
            'wrong-project': auth.InvalidIdTokenError('wrong project'),
        }
        if token in failures:
            raise failures[token]
        if token not in {'fixture-token', 'unmapped'}:
            raise auth.InvalidIdTokenError('invalid')
        uid = 'fixture-owner' if token == 'fixture-token' else 'unmapped'
        return {'uid': uid, 'sub': uid, 'email': 'same@example.invalid', 'name': 'Same Name'}

    def tearDown(self):
        self.client.close()
        self.verify_patch.stop()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def request(self, message='Track my order', number='DG-8001', token='fixture-token', **extra):
        headers = {} if token is None else {'Authorization': 'Bearer ' + token}
        return self.client.post('/v2/support', json={'order_number': number, 'message': message, **extra}, headers=headers)

    def set_status(self, status):
        with self.sessions.begin() as db:
            db.execute(update(Order).where(Order.order_number == 'DG-8001').values(status=status, delivered_on='Test delivery date' if status == 'Delivered' else None))

    def state(self, number='DG-8001'):
        with self.sessions() as db:
            row = db.scalar(select(Order).where(Order.order_number == number))
            return (row.status, row.return_requested, row.refund_requested, row.return_id, row.refund_id)

    def test_own_order_ignores_name_and_email(self):
        response = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertNotIn('customer_name', response.json())
        self.assertNotIn(str(self.owner), response.text)

    def test_foreign_nonexistent_and_unowned_are_identical(self):
        responses = [self.request(number=n) for n in ['DG-8002', 'DG-9999', 'DG-8003']]
        self.assertEqual([r.status_code for r in responses], [404]*3)
        self.assertTrue(all(r.json() == {'detail': 'Order not found.'} for r in responses))

    def test_firebase_token_cannot_authenticate_service_route(self):
        response = self.client.post('/support', json={'customer_name': 'Different Snapshot', 'order_number': 'DG-8001', 'message': 'Track'}, headers={'Authorization': 'Bearer fixture-token'})
        self.assertEqual(response.status_code, 401)

    def test_malformed_authorization_scheme(self):
        response = self.client.post('/v2/support', json={'order_number': 'DG-8001', 'message': 'Track'}, headers={'Authorization': 'Basic fixture-token'})
        self.assertEqual(response.status_code, 401)

    def test_malformed_bearer_header(self):
        response = self.client.post('/v2/support', json={'order_number': 'DG-8001', 'message': 'Track'}, headers={'Authorization': 'Bearer'})
        self.assertEqual(response.status_code, 401)

    def test_disabled_customer(self):
        with self.sessions.begin() as db:
            db.execute(update(Customer).where(Customer.id == self.owner).values(status='disabled'))
        self.assertEqual(self.request().status_code, 403)

    def test_scoped_locked_query_and_no_global_order_lookup(self):
        statements = []
        original = Session.scalar
        def capture(db, statement, *args, **kwargs):
            statements.append(statement)
            return original(db, statement, *args, **kwargs)
        with patch.object(Session, 'scalar', capture):
            self.assertTrue(self.request('Cancel my order').json()['success'])
        order_queries = [s for s in statements if 'FROM orders' in str(s)]
        self.assertEqual(len(order_queries), 1)
        sql = str(order_queries[0].compile(dialect=postgresql.dialect()))
        self.assertIn('orders.customer_id =', sql)
        self.assertIn('orders.order_number =', sql)
        self.assertIn('FOR UPDATE', sql)
        self.assertTrue(order_queries[0].get_execution_options()['populate_existing'])

    def test_failed_commit_rolls_back_mutation(self):
        before = self.state()
        with patch.object(Session, 'commit', side_effect=SQLAlchemyError('fixture failure')):
            self.assertEqual(self.request('Cancel my order').status_code, 503)
        self.assertEqual(self.state(), before)

    def test_ownership_change_before_locked_lookup_blocks_mutation(self):
        def transfer_then_load(db, **kwargs):
            with self.sessions.begin() as writer:
                writer.execute(update(Order).where(Order.order_number == 'DG-8001').values(customer_id=self.foreign))
            return get_customer_owned_order(db, **kwargs)
        with patch('app.api.get_customer_owned_order', side_effect=transfer_then_load):
            self.assertEqual(self.request('Cancel my order').status_code, 404)
        self.assertEqual(self.state()[0], 'Processing')

    def test_locked_lookup_refreshes_previously_loaded_state(self):
        from app.customer_auth import require_firebase_customer
        from fastapi.security import HTTPAuthorizationCredentials
        with self.sessions() as db:
            stale = db.scalar(select(Order).where(Order.order_number == 'DG-8001'))
            db.execute(update(Order).where(Order.id == stale.id).values(status='Out for Delivery').execution_options(synchronize_session=False))
            principal = require_firebase_customer(HTTPAuthorizationCredentials(scheme='Bearer', credentials='fixture-token'), db, app.dependency_overrides[get_firebase_token_verifier]())
            current = get_customer_owned_order(db, principal=principal, order_number='DG-8001', for_update=True)
            self.assertEqual(current.status, 'Out for Delivery')

    def test_return_then_refund_conflict(self):
        self.set_status('Delivered')
        self.assertTrue(self.request('Return my order').json()['success'])
        before = self.state()
        self.assertFalse(self.request('Refund my order').json()['success'])
        self.assertEqual(self.state(), before)

    def test_refund_then_return_conflict(self):
        self.set_status('Delivered')
        self.assertTrue(self.request('Refund my order').json()['success'])
        before = self.state()
        self.assertFalse(self.request('Return my order').json()['success'])
        self.assertEqual(self.state(), before)


def auth_case(token, expected):
    def test(self):
        self.assertEqual(self.request(token=token).status_code, expected)
    return test


for name, token, code in [('missing', None, 401), ('malformed', '', 401), ('invalid', 'invalid', 401), ('expired', 'expired', 401), ('revoked', 'revoked', 401), ('wrong_project', 'wrong-project', 401), ('unmapped', 'unmapped', 403), ('service_key', TEST_SERVICE_KEY, 401)]:
    setattr(TestCustomerApi, 'test_auth_' + name, auth_case(token, code))


def spoof_case(field):
    def test(self):
        response = self.request(**{field: 'untrusted-identity'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('untrusted-identity', response.text)
    return test


for field in [
    'customer_name', 'customer_id', 'uid', 'firebase_uid', 'email',
    'display_name', 'auth_subject', 'principal', 'service_key',
]:
    setattr(TestCustomerApi, 'test_reject_' + field, spoof_case(field))


def operation_case(action, status):
    def test(self):
        self.set_status(status)
        allowed = status == ('Processing' if action == 'cancel' else 'Delivered')
        response = self.request(action + ' my order')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], allowed)
        if allowed:
            self.assertFalse(self.request(action + ' my order').json()['success'])
            tracking = self.request().json()
            self.assertEqual(tracking['status'], self.state()[0])
            if action != 'cancel':
                self.assertIn(action + '_id', tracking)
                self.assertEqual(tracking['delivered_on'], 'Test delivery date')
            else:
                self.assertIsNone(tracking['tracking_number'])
        else:
            self.assertEqual(self.state()[0], status)
    return test


for action in ['cancel', 'return', 'refund']:
    for status in ['Processing', 'Out for Delivery', 'Delivered', 'Cancelled', 'Return Requested', 'Refund Requested', 'Refunded']:
        setattr(TestCustomerApi, 'test_' + action + '_' + status.lower().replace(' ', '_'), operation_case(action, status))


def foreign_case(action):
    def test(self):
        before = self.state('DG-8002')
        self.assertEqual(self.request(action + ' my order', number='DG-8002').status_code, 404)
        self.assertEqual(self.state('DG-8002'), before)
    return test


for action in ['cancel', 'return', 'refund']:
    setattr(TestCustomerApi, 'test_foreign_' + action, foreign_case(action))


def safety_case(message):
    def test(self):
        self.set_status('Delivered')
        before = self.state()
        response = self.request(message)
        self.assertEqual(response.json()['intent'], 'general_support')
        self.assertEqual(self.state(), before)
    return test


for name, message in [('informational', 'Can I cancel my order?'), ('negated', 'Do not refund my order'), ('multiple', 'Return and refund my order'), ('general', 'Please help me')]:
    setattr(TestCustomerApi, 'test_safety_' + name, safety_case(message))


def validation_case(number, message):
    def test(self):
        self.assertEqual(self.request(number=number, message=message).status_code, 400)
    return test


for name, number, message in [('number', 'bad', 'Track'), ('blank', 'DG-8001', '   ')]:
    setattr(TestCustomerApi, 'test_validation_' + name, validation_case(number, message))
