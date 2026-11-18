"""Role keys stored on user accounts."""
BROKER_ROLES = frozenset({'broker', 'broker_admin'})
MANUFACTURER_ROLES = frozenset({'manufacturer', 'manufacturer_admin'})
COMPANY_ROLES = BROKER_ROLES | MANUFACTURER_ROLES
COMPANY_ADMIN_ROLES = frozenset({'broker_admin', 'manufacturer_admin'})
