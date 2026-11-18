from decimal import Decimal

from app.models import Carrier, CarrierContract, Customer, EmailOutbox, IntegrationConnection, PricingRule
from test_accounts import account
from test_manufacturer import headers, setup

API = '/api/v1'


def add_user(client, role, company=1):
    response = client.post(
        API + '/admin/users', headers=headers(4),
        json=account(email=f'{role}-{company}@alpha.com', role=role, customer_id=company),
    )
    assert response.status_code == 201, response.text
    return headers(response.json()['id'])


def test_broker_roles_are_scoped_and_cannot_use_super_admin(setup):
    client, _ = setup
    for role in ('broker', 'broker_admin'):
        h = add_user(client, role)
        assert client.get(API + '/auth/me', headers=h).json()['role'] == role
        assert [row['id'] for row in client.get(API + '/quotes', headers=h).json()] == [1]
        assert client.get(API + '/quotes/2', headers=h).status_code == 404
        assert client.get(API + '/quotes', headers={**h, 'X-Company-Id': '2'}).status_code == 403
        assert client.get(API + '/admin/users', headers=h).status_code == 403
        assert client.get(API + '/admin/portal-access/portals', headers=h).status_code == 403
        assert client.post(API + '/admin/users', headers=h, json=account(role='admin')).status_code == 403
        assert client.put(API + '/admin/users/4', headers=h, json=account(role='broker')).status_code == 403
        assert client.get(API + '/portal/me', headers=h).status_code == 403

    for role in ('broker', 'broker_admin'):
        r = client.post(API + '/admin/users', headers=headers(4), json=account(role=role, customer_id=None))
        assert r.status_code == 422
    customer = client.post(API + '/customers', headers=headers(1), json={'name': 'Alpha customer'})
    assert customer.status_code == 201, customer.text
    r = client.post(API + '/admin/users', headers=headers(4),
                    json=account(role='broker_admin', customer_id=customer.json()['id']))
    assert r.status_code == 422


def test_broker_admin_configures_only_own_workspace(setup):
    client, factory = setup
    regular = add_user(client, 'broker')
    manager = add_user(client, 'broker_admin')
    beta = add_user(client, 'broker_admin', 2)
    with factory() as db:
        connection = IntegrationConnection(customer_id=2, provider='Beta Private', category='test')
        db.add(connection)
        db.add(PricingRule(name='Platform default', value=Decimal('15')))
        db.commit()
        beta_connection = connection.id
    assert client.get(API + '/workspace/settings', headers=manager).json()['company_name'] == 'Alpha'
    branding = {'company_name': 'Alpha Brokerage', 'logo_data': ''}
    assert client.patch(API + '/workspace/branding', headers=regular, json=branding).status_code == 403
    assert client.patch(API + '/workspace/branding', headers=manager, json=branding).status_code == 200
    assert client.get(API + '/workspace/settings', headers=regular).json()['company_name'] == 'Alpha Brokerage'
    assert client.get(API + '/workspace/settings', headers=beta).json()['company_name'] == 'Beta'
    assert client.get(API + '/integrations', headers=regular).status_code == 403
    own_connections = client.get(API + '/integrations', headers=manager)
    assert own_connections.status_code == 200, own_connections.text
    assert all(row['customer_id'] == 1 for row in own_connections.json())
    assert client.get(API + f'/integrations/connection/{beta_connection}/manage', headers=manager).status_code == 404
    assert client.get(API + '/pricing-rules', headers=regular).status_code == 403
    rule = client.post(API + '/pricing-rules', headers=manager, json={'name': 'Company rates', 'value': 20})
    assert rule.status_code == 200, rule.text
    assert rule.json()['customer_id'] == 1
    assert client.patch(API + '/workspace/pricing', headers=manager, json={'show_pricing': True}).status_code == 200
    assert [r['name'] for r in client.get(API + '/pricing-rules', headers=regular).json()] == ['Company rates']
    assert client.get(API + '/pricing-rules', headers=beta).json() == []
    assert client.post(API + '/pricing-rules', headers=regular, json={'name': 'No', 'value': 20}).status_code == 403
    assert client.post(API + '/pricing-rules', headers=manager, json={'name': 'No', 'value': 20, 'customer_id': 2}).status_code == 403


def test_broker_capacity_carriers_and_outbox_stay_with_company(setup):
    client, factory = setup
    regular = add_user(client, 'broker')
    manager = add_user(client, 'broker_admin')
    beta = add_user(client, 'broker_admin', 2)
    with factory() as db:
        shared = Carrier(name='Shared carrier', scac='SHRD')
        db.add(shared)
        db.flush()
        db.add(CarrierContract(carrier_id=shared.id, name='Private Valhalla agreement'))
        db.add_all([
            EmailOutbox(customer_id=1, subject='Alpha only', body='A'),
            EmailOutbox(customer_id=2, subject='Beta only', body='B'),
            EmailOutbox(subject='Platform only', body='Platform'),
        ])
        db.commit()
        shared_id = shared.id
    assert [r['subject'] for r in client.get(API + '/finance/email-outbox', headers=regular).json()] == ['Alpha only']
    assert len(client.get(API + '/finance/email-outbox', headers=headers(4)).json()) == 3
    load = client.post(API + '/capacity', headers=regular, json={'origin': {}, 'destination': {}})
    assert load.status_code == 200, load.text
    load_id = load.json()['id']
    assert client.get(API + '/capacity', headers=beta).json() == []
    assert client.get(API + f'/capacity/{load_id}', headers=beta).status_code == 404
    offer = {'carrier_name': 'Broker offer', 'amount': 200}
    assert client.post(API + f'/capacity/{load_id}/offers', headers=beta, json=offer).status_code == 404
    assert client.post(API + f'/capacity/{load_id}/offers', headers=manager, json=offer).status_code == 200
    assert len(client.get(API + f'/capacity/{load_id}', headers=regular).json()['offers']) == 1
    assert client.post(API + '/carrier-360', headers=regular, json={'name': 'No', 'scac': 'NOPE'}).status_code == 403
    created = client.post(API + '/carrier-360', headers=manager, json={'name': 'Alpha carrier', 'scac': 'ALPH'})
    assert created.status_code == 200, created.text
    carrier_id = created.json()['id']
    assert {r['scac'] for r in client.get(API + '/carriers', headers=regular).json()} == {'SHRD', 'ALPH'}
    assert {r['scac'] for r in client.get(API + '/carriers', headers=beta).json()} == {'SHRD'}
    assert client.get(API + f'/carrier-360/{carrier_id}', headers=beta).status_code == 404
    assert client.patch(API + f'/carrier-360/{carrier_id}', headers=regular, json={'name': 'No'}).status_code == 403
    assert client.patch(API + f'/carrier-360/{carrier_id}', headers=manager, json={'name': 'Updated Alpha'}).status_code == 200
    assert client.patch(API + f'/carrier-360/{shared_id}', headers=manager, json={'name': 'No'}).status_code == 403
    detail = client.get(API + f'/carrier-360/{shared_id}', headers=manager).json()
    assert detail['shared_catalog'] and not detail['can_manage'] and detail['contracts'] == []
    assert len(client.get(API + f'/carrier-360/{shared_id}', headers=headers(4)).json()['contracts']) == 1
