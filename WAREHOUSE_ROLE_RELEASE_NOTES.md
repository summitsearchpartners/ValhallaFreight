# Valhalla Freight v0.19.19 — Warehouse role (candidate build)

This is a development/test candidate, **not yet validated for production deployment**.

- Warehouse role has independent login credentials and a manufacturer assignment.
- Manufacturer Admins and Super Admins can manage warehouse accounts under **Warehouse Users**. Super Admin can also select the role in Users & Company Access.
- Server checks the stored role on each request and blocks warehouse accounts from all non-Safe Load APIs (except authentication self-check/logout).
- Safe Load queue, events, and shipment endpoints filter/authorize warehouse access to the assigned manufacturer and its child companies.
- Warehouse users cannot enable or invite Safe Load assignments, approve assignments, edit broker contacts, export custody evidence, or authorize broker overrides.
- Manufacturer web portal blocks warehouse accounts after login.

## Required validation before AWS deployment

1. Install backend and frontend dependencies and build both Docker images.
2. Run existing backend tests and mobile tests.
3. Run authorization integration tests with real sample manufacturer A/B accounts and shipments; verify 403/404 cross-tenant and forbidden API calls, and verify intended 200 calls.
4. Confirm Manufacturer Admin can create, disable and reset only its own Warehouse accounts, and Super Admin can administer any assigned manufacturer.
5. Verify Safe Load app login and the complete arrival photo/scan/release workflow with test shipments.
6. Verify existing Manufacturer/Broker/Super Admin workflows remain unchanged.

**Do not deploy this candidate to AWS before these tests pass.**
