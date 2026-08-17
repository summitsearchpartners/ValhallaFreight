# Valhalla Freight Architecture Blueprint

## Product domains

### Commercial
Customer accounts, pricing agreements, contracts, credit, sales ownership, prospect analysis and margin strategy.

### Rating
Carrier request adapters, normalization, pricing-rule resolution, quote expiration, quote comparison and customer-facing rates.

### Execution
Shipment booking, pickup requests, BOL/labels, PRO assignment, dispatch, status events, delivery and proof-of-delivery.

### Financial
Expected carrier cost, final carrier invoice, accessorial variance, customer revenue, gross profit, invoice status, payment and accounting sync.

### Intelligence
Shipment facts, lane metrics, carrier scorecards, cost trends, accessorial analysis, claims, on-time performance, customer savings and natural-language analysis.

## Core normalized shipment grain

Customer → Origin → Destination → ZIP → Carrier → Terminal → Handling Unit → Weight → Dimensions → Class → NMFC → Accessorial → Quote → Carrier Cost → Customer Revenue → Margin → Pickup → Tracking → Delivery → Audit → Invoice → Claim

## Integration strategy

Carrier integrations should be adapters behind a Valhalla Freight interface. V1 can use an aggregator. High-volume carriers can migrate to direct API/EDI integrations individually without changing quote, shipment, finance or analytics screens.

## Multi-tenant path

The current starter is a single operating company instance. Before offering Valhalla Freight as SaaS, introduce `organization_id` as a tenant boundary across operational tables and enforce it in repository/service access. This preserves the path to running both the brokerage and a separate TMS SaaS business from the same platform family.

## Production controls still required before public deployment

Authentication/authorization, secrets management, Alembic migrations, background jobs, idempotency, API retries, audit trails, structured logging, monitoring, object storage, document security, database backup strategy, WAF/rate limiting, dependency scanning, CI/CD, automated tests and disaster recovery.
