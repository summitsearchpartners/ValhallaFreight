import pytest
from pydantic import ValidationError
from app.api.routes.truckload import Stop

@pytest.mark.parametrize('state,expected',[('Kansas','KS'),(' ohio ','OH'),('ks','KS'),('New York','NY'),('District of Columbia','DC')])
def test_full_state_names_are_normalized(state,expected):
    stop=Stop(kind='pickup',name='Test warehouse',address1='100 Main St',city='Olathe',state=state,postal_code='66061',appointment_at='2026-12-01T10:00')
    assert stop.state==expected

def test_invalid_state_identifies_field():
    with pytest.raises(ValidationError) as error:
        Stop(kind='pickup',name='Test warehouse',address1='100 Main St',city='Olathe',state='Not a state',postal_code='66061',appointment_at='2026-12-01T10:00')
    assert error.value.errors()[0]['loc']==('state',)
    assert 'Choose a US state' in str(error.value)
