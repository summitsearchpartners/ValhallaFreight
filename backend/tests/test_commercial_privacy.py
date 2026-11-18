from test_manufacturer import setup, headers
from app.services.commercial_privacy import public_payload


def test_recursive_commercial_redaction():
    private={'customer_price':'150','carrier_cost':'100','gross_profit':'50','margin_pct':33,
             'options':[{'carrierCost':100,'gp':50,'fuel':10,'base_charge':90,'accessorials':0}],
             'accessorials':['liftgate'],'default_markup_pct':15}
    assert public_payload(private)=={'customer_price':'150','options':[{}],'accessorials':['liftgate']}


def test_manufacturer_cannot_override_buy_pricing(setup):
    client,_=setup
    for uid in (1,2):
        assert client.get('/api/v1/pricing-rules',headers=headers(uid)).status_code==403
        assert client.get('/api/v1/finance/payables',headers=headers(uid)).status_code in (403,404)
        assert client.get('/api/v1/finance/customer-invoices',headers=headers(uid)).status_code==200
        payload={'customer_id':1,'origin':{'postal_code':'66061','address1':'','city':'','state':''},'destination':{'postal_code':'45414','address1':'','city':'','state':''},
                 'handling_units':[{'quantity':1,'weight_lbs':500,'length_in':48,'width_in':40,'height_in':48,'freight_class':'70'}],
                 'quote_pricing_mode':'flat','quote_pricing_value':0}
        result=client.post('/api/v1/quotes/rate',headers=headers(uid),json=payload)
        assert result.status_code==403,result.text
    assert client.get('/api/v1/pricing-rules',headers=headers(4)).status_code==200
