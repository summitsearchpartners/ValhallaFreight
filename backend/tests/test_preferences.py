from test_manufacturer import setup, headers
from app.models import UserDisplayPreferences


def test_display_preferences_are_personal_and_persistent(setup):
    c,factory=setup
    defaults=c.get('/api/v1/workspace/preferences',headers=headers(2))
    assert defaults.status_code==200
    assert defaults.json()['theme']=='light'
    payload={**defaults.json(),'theme':'dark','time_format':'24h','timezone':'America/Chicago','date_format':'YYYY-MM-DD','density':'compact','show_seconds':True,'show_clock':False}
    assert c.put('/api/v1/workspace/preferences',headers=headers(2),json=payload).json()==payload
    assert c.get('/api/v1/workspace/preferences',headers=headers(2)).json()==payload
    # Same-company users do not inherit personal display settings.
    assert c.get('/api/v1/workspace/preferences',headers=headers(1)).json()['theme']=='light'
    assert c.get('/api/v1/workspace/preferences',headers=headers(3)).json()['theme']=='light'
    with factory() as db:
        row=db.get(UserDisplayPreferences,2)
        assert row.preferences==payload
    # Normal customer portal accounts can also retain their personal display defaults.
    assert c.put('/api/v1/workspace/preferences',headers=headers(5),json=payload).status_code==200
    assert c.get('/api/v1/workspace/preferences').status_code==401


def test_preference_validation_and_company_context(setup):
    c,_=setup
    for payload in [{'theme':'purple'},{'timezone':'Invalid/NoZone'},{'time_format':'military'},{'user_id':3,'theme':'dark'}]:
        assert c.put('/api/v1/workspace/preferences',headers=headers(2),json=payload).status_code==422
    assert c.put('/api/v1/workspace/preferences',headers={**headers(4),'X-Company-Id':'2'},json={'theme':'dark'}).status_code==200
    assert c.get('/api/v1/workspace/preferences',headers=headers(4)).json()['theme']=='dark'
    assert c.get('/api/v1/workspace/preferences',headers=headers(3)).json()['theme']=='light'


def test_branding_and_pricing_changes_are_independent_and_authorized(setup):
    c,_=setup
    brand={'company_name':'Acme Updated','logo_data':''}
    assert c.patch('/api/v1/workspace/branding',headers=headers(1),json=brand).status_code==200
    assert c.patch('/api/v1/workspace/pricing',headers=headers(1),json={'show_pricing':True}).status_code==200
    settings=c.get('/api/v1/workspace/settings',headers=headers(2)).json()
    assert settings=={**brand,'show_pricing':True}
    brand['company_name']='Acme New Brand'
    updated=c.patch('/api/v1/workspace/branding',headers=headers(1),json=brand)
    assert updated.status_code==200 and updated.json()['show_pricing'] is True
    assert c.patch('/api/v1/workspace/pricing',headers=headers(1),json={'show_pricing':False}).json()['company_name']=='Acme New Brand'
    assert c.get('/api/v1/workspace/settings',headers=headers(3)).json()['company_name']=='Beta'
    for path,data in [('/branding',brand),('/pricing',{'show_pricing':True})]:
        assert c.patch('/api/v1/workspace'+path,headers=headers(2),json=data).status_code==403
        assert c.patch('/api/v1/workspace'+path,headers={**headers(1),'X-Company-Id':'2'},json=data).status_code==403
    assert c.patch('/api/v1/workspace/branding',headers=headers(1),json={**brand,'show_pricing':True}).status_code==422
    assert c.patch('/api/v1/workspace/pricing',headers=headers(1),json={'show_pricing':True,'company_name':'overwrite'}).status_code==422
    assert c.patch('/api/v1/workspace/branding',headers={**headers(4),'X-Company-Id':'2'},json={'company_name':'VF Managed','logo_data':''}).status_code==200
    assert c.get('/api/v1/workspace/settings',headers=headers(3)).json()['company_name']=='VF Managed'
