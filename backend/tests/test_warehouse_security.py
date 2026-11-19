"""Warehouse role isolation regression checks (v0.19.26)."""
import pytest
from test_manufacturer import setup, headers
from app.models import Customer, User, Shipment, SafeLoadCase
from app.services.auth import hash_password

@pytest.fixture
def warehouse_setup(setup):
    client, factory = setup
    with factory() as db:
        db.add(Customer(id=3, code='A-CHILD', name='Alpha child', manufacturer_id=1))
        for uid, cid in [(20, 1), (21, 2), (22, None)]:
            db.add(User(id=uid, email=f'warehouse{uid}@test.local', full_name=f'Warehouse {uid}',
                        role='warehouse', customer_id=cid, active=True,
                        password_hash=hash_password('WarehouseTest123!')))
        for sid, cid in [(101, 1), (102, 2), (103, 3)]:
            db.add(Shipment(id=sid, shipment_number=f'WH-{sid}', customer_id=cid,
                            origin={}, destination={}, handling_units=[]))
            db.add(SafeLoadCase(shipment_id=sid, customer_id=cid,
                                status='awaiting_assignment', revision=0))
        db.commit()
    return client, factory


def test_warehouse_queue_is_manufacturer_scoped(warehouse_setup):
    client, _ = warehouse_setup
    for uid, expected in [(20, {101, 103}), (21, {102})]:
        response = client.get('/api/v1/safe-load', headers=headers(uid))
        assert response.status_code == 200, response.text
        assert {item['shipment_id'] for item in response.json()} == expected
    assert client.get('/api/v1/safe-load', headers=headers(22)).status_code == 403


@pytest.mark.parametrize('suffix,method,payload', [
    ('photo', 'get', None),
    ('photo-data', 'get', None),
    ('custody', 'get', None),
    ('attempts', 'get', None),
    ('attempts/1/license', 'get', None),
    ('attempts/1/license/photo-data', 'get', None),
    ('attempts/1/extraction', 'get', None),
    ('custody/1/dispatcher-photo', 'get', None),
    ('scan', 'post', {'revision': 0, 'license_barcode': 'unreadable', 'vin_barcode': '1HGCM82633A004352'}),
    ('release', 'post', {'revision': 0}),
    ('reject-arrival', 'post', {'revision': 0}),
    ('capture-event', 'post', {'revision': 0, 'kind': 'vin', 'captured_at': '2026-11-18T12:00:00'}),
])
def test_warehouse_cannot_read_or_modify_other_manufacturer(warehouse_setup, suffix, method, payload):
    client, _ = warehouse_setup
    path = f'/api/v1/safe-load/shipments/102/{suffix}'
    response = getattr(client, method)(path, headers=headers(20), **({'json': payload} if payload is not None else {}))
    assert response.status_code == 404, (path, response.status_code, response.text)


@pytest.mark.parametrize('suffix,method,payload', [
    ('enable', 'post', None),
    ('invite', 'post', None),
    ('approve-assignment', 'post', {'revision': 0, 'reason': 'Confirmed independently'}),
    ('broker-contact', 'put', {'phone': '5555555555'}),
    ('broker-release', 'post', {'revision': 0}),
    ('custody/export', 'get', None),
    ('custody/1/dispatcher-photo', 'get', None),
    ('attempts/1/extraction', 'get', None),
])
def test_warehouse_cannot_perform_broker_or_export_actions(warehouse_setup, suffix, method, payload):
    client, _ = warehouse_setup
    path = f'/api/v1/safe-load/shipments/101/{suffix}'
    response = getattr(client, method)(path, headers=headers(20), **({'json': payload} if payload is not None else {}))
    assert response.status_code == 403, (path, response.status_code, response.text)


@pytest.mark.parametrize('path', [
    '/api/v1/admin/users', '/api/v1/quotes', '/api/v1/shipments',
    '/api/v1/truckload', '/api/v1/customers', '/api/v1/warehouse/users',
    '/api/v1/notifications', '/api/v1/workspace/settings',
])
def test_warehouse_is_not_a_tms_or_admin_account(warehouse_setup, path):
    client, _ = warehouse_setup
    assert client.get(path, headers=headers(20)).status_code == 403


def test_warehouse_cannot_select_company_context(warehouse_setup):
    client, _ = warehouse_setup
    h = {**headers(20), 'X-Company-Id': '2'}
    assert client.get('/api/v1/safe-load', headers=h).status_code == 403


def test_warehouse_role_and_deactivation_apply_to_existing_token(warehouse_setup):
    client, factory = warehouse_setup
    token_headers = headers(20)
    assert client.get('/api/v1/safe-load', headers=token_headers).status_code == 200
    with factory() as db:
        user = db.get(User, 20)
        user.customer_id = 2
        db.commit()
    result = client.get('/api/v1/safe-load', headers=token_headers)
    assert result.status_code == 200
    assert {item['shipment_id'] for item in result.json()} == {102}
    with factory() as db:
        db.get(User, 20).active = False
        db.commit()
    assert client.get('/api/v1/safe-load', headers=token_headers).status_code == 401


def test_manufacturer_admin_cannot_manage_other_manufacturer_warehouse(warehouse_setup):
    client, _ = warehouse_setup
    assert client.get('/api/v1/warehouse/users', headers=headers(1)).status_code == 200
    assert client.get('/api/v1/warehouse/users?customer_id=2', headers=headers(1)).status_code == 403
    assert client.put('/api/v1/warehouse/users/21', headers=headers(1), json={}).status_code in {403, 422}
