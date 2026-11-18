from test_manufacturer import setup, headers


def test_unified_profile_saves_name_and_branding(setup):
    c,_=setup
    payload={'full_name':'Updated Admin','branding':{'company_name':'Company Brand','logo_data':''}}
    result=c.put('/api/v1/workspace/profile-page',headers=headers(1),json=payload)
    assert result.status_code==200,result.text
    assert result.json()['user']['full_name']=='Updated Admin'
    assert result.json()['workspace']['company_name']=='Company Brand'
    assert c.get('/api/v1/auth/me',headers=headers(1)).json()['full_name']=='Updated Admin'
    assert c.get('/api/v1/workspace/settings',headers=headers(2)).json()['company_name']=='Company Brand'
    # A normal manufacturer can save personal information without shared branding.
    assert c.put('/api/v1/workspace/profile-page',headers=headers(2),json={'full_name':'Manufacturer User'}).status_code==200


def test_profile_page_rejects_unauthorized_or_invalid_edits_without_partial_save(setup):
    c,_=setup
    unauthorized={'full_name':'Must Not Save','branding':{'company_name':'Cannot Edit','logo_data':''}}
    assert c.put('/api/v1/workspace/profile-page',headers=headers(2),json=unauthorized).status_code==403
    assert c.get('/api/v1/auth/me',headers=headers(2)).json()['full_name']=='User 2'
    invalid={'full_name':'Must Not Save','branding':{'company_name':'Invalid','logo_data':'data:image/png;base64,bm90aW1hZ2U='}}
    assert c.put('/api/v1/workspace/profile-page',headers=headers(1),json=invalid).status_code==422
    assert c.get('/api/v1/auth/me',headers=headers(1)).json()['full_name']=='User 1'


def test_unified_settings_saves_preferences_and_company_visibility(setup):
    c,_=setup
    preferences=c.get('/api/v1/workspace/preferences',headers=headers(1)).json()
    preferences.update(theme='dark',time_format='24h',timezone='America/Chicago')
    result=c.put('/api/v1/workspace/settings-page',headers=headers(1),json={'preferences':preferences,'pricing':{'show_pricing':True}})
    assert result.status_code==200,result.text
    assert result.json()['preferences']==preferences
    assert result.json()['workspace']['show_pricing'] is True
    assert c.get('/api/v1/workspace/preferences',headers=headers(1)).json()==preferences
    assert c.get('/api/v1/workspace/settings',headers=headers(2)).json()['show_pricing'] is True
    assert c.get('/api/v1/workspace/preferences',headers=headers(2)).json()['theme']=='light'
    assert c.get('/api/v1/workspace/settings',headers=headers(3)).json()['show_pricing'] is False


def test_settings_page_rejects_company_edit_without_saving_personal_changes(setup):
    c,_=setup
    assert c.put('/api/v1/workspace/settings-page',headers=headers(2),json={'preferences':{'theme':'dark'},'pricing':{'show_pricing':True}}).status_code==403
    assert c.get('/api/v1/workspace/preferences',headers=headers(2)).json()['theme']=='light'
    assert c.put('/api/v1/workspace/settings-page',headers=headers(2),json={'preferences':{'theme':'dark'}}).status_code==200
    assert c.get('/api/v1/workspace/preferences',headers=headers(2)).json()['theme']=='dark'
    assert c.put('/api/v1/workspace/settings-page',headers=headers(1),json={'preferences':{'theme':'invalid'},'pricing':{'show_pricing':True}}).status_code==422
    assert c.get('/api/v1/workspace/settings',headers=headers(1)).json()['show_pricing'] is False


def test_super_user_company_context_keeps_personal_changes_on_superuser(setup):
    c,_=setup
    context={**headers(4),'X-Company-Id':'2'}
    payload={'full_name':'Valhalla Super User','branding':{'company_name':'Beta Branding','logo_data':''}}
    assert c.put('/api/v1/workspace/profile-page',headers=context,json=payload).status_code==200
    assert c.get('/api/v1/auth/me',headers=headers(4)).json()['full_name']=='Valhalla Super User'
    assert c.get('/api/v1/auth/me',headers=headers(3)).json()['full_name']=='User 3'
    assert c.get('/api/v1/workspace/settings',headers=headers(3)).json()['company_name']=='Beta Branding'
    assert c.put('/api/v1/workspace/settings-page',headers=context,json={'preferences':{'theme':'dark'},'pricing':{'show_pricing':True}}).status_code==200
    assert c.get('/api/v1/workspace/preferences',headers=headers(4)).json()['theme']=='dark'
    assert c.get('/api/v1/workspace/preferences',headers=headers(3)).json()['theme']=='light'
    assert c.get('/api/v1/workspace/settings',headers=headers(3)).json()['show_pricing'] is True
