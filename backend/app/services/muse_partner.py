"""Muse partner access is a Super Admin designated company, never a branding check."""
from sqlalchemy import select, func
from app.models import Customer, User, MusePartnerCompany


def has_access(db, user):
    if user.role == "admin":return True
    if user.role not in {"broker_admin","muse_admin"} or not user.customer_id:return False
    company=db.get(MusePartnerCompany,1)
    return bool(company and company.company_id==user.customer_id)


def initialize(db):
    """One-time upgrade for an existing unambiguous Muse Freight company.

    Once initialized, including an empty designation, company renames never
    change permission. Subsequent assignments require Super Admin.
    """
    if db.get(MusePartnerCompany,1) is not None:return
    candidates=db.query(Customer.id).filter(
        Customer.manufacturer_id.is_(None),
        func.lower(func.trim(Customer.name))=="muse freight",
        Customer.id.in_(select(User.customer_id).where(User.role.in_(["broker_admin","muse_admin"])))
    ).all()
    db.add(MusePartnerCompany(id=1,company_id=candidates[0][0] if len(candidates)==1 else None))
    db.commit()
