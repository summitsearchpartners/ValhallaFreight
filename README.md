# Valhalla Freight

**Built for the Long Haul. Driven by Honor.**

Valhalla Freight is a Transportation Operating System foundation with LTL-first brokerage execution and multi-mode expansion architecture designed around the complete brokerage lifecycle:

**Quote → Sell → Book → Source → Dispatch → Track → Deliver → Audit → Invoice → Pay → Analyze → Optimize**

This repository contains a Dockerized React/TypeScript frontend, Python FastAPI backend and PostgreSQL data layer. The v0.7 build expands the authenticated Valhalla Freight foundation into modular Customer 360, Carrier 360, Capacity, Visibility, Finance, Claims, Intelligence, Integration Hub and Customer Portal workspaces while preserving: carrier responses are normalized behind a rating layer, customer pricing is rule-driven, shipment data is structured for analytics, and integrations can be replaced without redesigning the operating application.

## What is already in this build

- Professional Valhalla Freight login experience
- JWT authentication and protected operational APIs
- Valhalla Freight logo/brand integration
- Authenticated user session restoration and sign-out
- Valhalla Freight command-center dashboard
- Professional responsive operations UI
- Customer master data

- Carrier 360 with editable carrier master data, compliance, contacts, terminals, modes, service areas, strategic lanes, contracts, documents, pricing relationships, scorecards, claims and activity history
- Capacity Center with digital freight matching/load-board adapter framework
- Visibility Center with delivery-commitment monitoring
- Finance Center with freight-audit variance queue and approve/dispute workflow
- Claims Center with shipment-linked claim records
- Valhalla Freight Intelligence with database-derived operational insights
- Integration Hub covering carrier connectivity, rate intelligence, load boards, visibility, onboarding, accounting, payments, claims and CRM
- Customer Portal administration foundation over the same APIs
- Carrier network and connectivity status
- LTL Quote Studio
- Carrier-independent normalized rate model
- Hierarchical pricing rules with minimum-margin protection
- Quote persistence
- Quote-to-shipment booking API
- Shipment control tower
- Tracking-event API/data model
- Carrier cost vs customer revenue data model
- Billing/invoice data model
- Prospect Analysis CSV/XLSX upload endpoint
- Network analytics workspace
- PostgreSQL persistence
- Seed data for local development
- FastAPI interactive API documentation
- Docker Compose local environment

## Local development login

After the first startup, use:

- Email: `admin@valhallafreight.local`
- Password: `Valhalla123!`

These are local-development credentials only. Change them before any shared or AWS deployment.

## Start Valhalla Freight on Windows / PowerShell

Prerequisites: Docker Desktop, Git, and Visual Studio Code.

```powershell
cd C:\GitHub\ValhallaFreight
docker compose up --build
```

Open:

- Valhalla Freight UI: http://localhost:5173
- Valhalla Freight API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/health

Stop it with:

```powershell
docker compose down
```

Reset the local database completely:

```powershell
docker compose down -v
docker compose up --build
```

## First Git repository push

```powershell
git init
git add .
git commit -m "Initial Valhalla Freight platform foundation"
git branch -M main
git remote add origin YOUR_GIT_REPOSITORY_URL
git push -u origin main
```

## Architecture

```text
React + TypeScript + Vite
          │
          ▼
     FastAPI REST API
          │
   ┌──────┴────────┐
   │               │
Pricing / Rating   Operations Services
Normalization     Quote / Shipment / Track
   │               │
   └──────┬────────┘
          ▼
      PostgreSQL
          │
    Reporting Layer
```

Carrier integrations should implement the normalized Valhalla Freight contract instead of leaking carrier-specific payloads into the rest of the software.

## Recommended build sequence from here

1. Identity, organizations, roles and permissions.
2. Customer contacts, locations, commodities and operating preferences.
3. Production rate-provider adapter interface and first aggregator integration.
4. Direct carrier adapters for highest-volume carriers.
5. Pickup/dispatch workflow, BOL generation and document storage.
6. Tracking normalization and exception management.
7. Freight audit and carrier invoice ingestion.
8. Customer invoice generation and QuickBooks integration.
9. Claims management.
10. Customer self-service portal.
11. Prospect Analysis column-mapping and savings model.
12. Advanced reporting/data warehouse layer.
13. AI intelligence over structured Valhalla Freight data.
14. AWS deployment, secrets, observability, backups and CI/CD.

## Important development note

The local rating service currently uses a **deterministic development carrier connector** so the entire Quote Studio and pricing workflow can run without paid carrier credentials. It is intentionally isolated in `backend/app/services/rating.py`. That adapter is the replacement point for a real LTL aggregator or direct carrier APIs.


## v0.3.0
Authenticated application shell with collapsible navigation, Ctrl+K command search, notifications, profile controls, and responsive Valhalla Freight workspace styling.

## v0.4.0 — Customer 360

Customer 360 is the first Valhalla Freight module built using the new feature/domain architecture. Customer data now has a dedicated backend domain and frontend feature directory rather than being extended inside monolithic shared files.

The workspace includes account KPIs, customer profile data, operating locations, contacts, commercial controls, notes/activity and recent shipment history. New locations, contacts and account notes can be created directly inside Customer 360.

See `docs/MODULAR_ARCHITECTURE.md` and `docs/V0.4.0_CUSTOMER_360.md` for the development standard used going forward.


## v0.4.1 Customer 360 usability
Dedicated Notes, Google Places address autocomplete readiness, system-generated customer codes, consistent phone formatting, and clickable customer/contact communication fields.


## v0.4.4
Quote Studio origin and destination now use shared Google Places address autocomplete and automatically populate City, State, and ZIP.


## v0.5.1
Quote-to-shipment workflow: Quote Bucket, quote detail/approval, rate selection persistence, Command Center quote drill-down, and direct known-carrier shipment creation.


## v0.5.3 — Workspace readability
Quote Studio and Shipment Detail now use full-width operational workspaces with larger typography, controls, financial KPIs, lane data, tracking details, and carrier-rate cards for better use of desktop screens.


## v0.7.0 — Carrier 360 & Carrier Network

Carrier 360 is now a full operational carrier-management domain with editable carrier master records, SCAC/MC/DOT identity, qualification and compliance, contacts, service centers, supported modes, service areas, strategic lanes, target costs, contracts, document vault, pricing-rule relationships, shipment-derived performance scorecards, claims exposure, carrier spend, and activity history.

The Carrier Network provides search/filtering, preferred-carrier strategy, compliance readiness, API/EDI status, on-time performance, claims, spend, and direct navigation into each Carrier 360 record.

## v0.7.1 — Carrier Compliance Document Uploads
Carrier 360 compliance requirements now support persistent PDF/DOC/DOCX/JPG/PNG uploads with View, Download, Replace, file validation, 15 MB default limits, and version-history metadata. Local Docker deployments use the persistent `valhalla_freight_documents` volume; this storage boundary is designed to migrate to S3/object storage for production.

## v0.7.2 — LTL Quote Workflow, Accessorials & Shipping Documents
- Quote Studio now rates ZIP-to-ZIP; full street addresses are confirmed only after quote approval.
- Removed requested pickup date/time from the quote-rate form while retaining an optional customer-required delivery date.
- Added professional Special Services / Accessorial selection grouped by Pickup Services, Delivery Services, and Shipment Characteristics.
- Quote approval now confirms the actual ship-from and ship-to facilities using saved Customer 360 locations or smart address lookup.
- Saved customer location defaults automatically populate appointment, liftgate, residential, and limited-access accessorials into the shipment.
- Shipment creation blocks if the confirmed ZIP differs from the ZIP that was rated, forcing a re-rate to protect pricing accuracy.
- Approved shipments automatically receive a Valhalla BOL number.
- Shipment Control Tower now provides printable Bill of Lading and Shipping Label documents.


## v0.7.3 — Professional Bill of Lading
- Rebuilt the printable BOL using the uploaded Dayton Freight BOL as a structural benchmark while retaining Valhalla Freight branding.
- Automatically populates shipper/consignee addresses, saved-location contact details, carrier/SCAC, BOL, PRO, shipment number, schedule commitments, accessorials, handling-unit details, class, NMFC, hazmat indicator, dimensions, weights, totals, signatures and carrier PRO area.
- Saved Customer 360 location contact/instruction data now travels with the confirmed shipment address so documents can populate it automatically.
- Print view is formatted for US Letter and supports Print / Save PDF.


## v0.7.4 — Shipment BOL Details

Shipment Control Tower now stores editable BOL reference and commodity information: PO number, customer reference, package count/type, commodity description, NMFC, hazmat emergency contact/phone, and declared value. These fields flow automatically into the professional Valhalla Freight BOL. New shipments created from an approved quote receive a Valhalla BOL number automatically.


## v0.7.5 — Shipment Confirmation Address & Immutable Numeric BOL
- Restores/broadens Google Places suggestions during quote-to-shipment confirmation, including rural/route/premise addresses.
- Keeps structured City/State/ZIP autofill after selecting the confirmed shipping facility.
- New Valhalla-created shipments receive a eight-digit numeric BOL (for example `10000042`) at creation.
- BOL numbers are immutable after creation and have been removed from Edit Shipment.


## v0.7.6 — Eight-Digit BOL Numbers
- New Valhalla-created shipments receive an immutable eight-digit numeric BOL at creation (for example `10000042`).
- Existing shipment BOL numbers are preserved and are not renumbered.

## v0.7.8 — Quote Confirmation Address Autocomplete Fix

- Hardened Google Places autocomplete in quote-to-shipment confirmation.
- Added automatic compatibility fallback for Google Places prediction/detail APIs.
- Restored City/State/ZIP/Country autofill after selecting an address.


## v0.8.0 — Carrier Integration Framework & Dayton Freight
- Introduces normalized carrier adapter registry and provider-specific isolation.
- Adds Dayton Freight (DAFG) as the first direct carrier adapter.
- Supports Dayton rating, pickups, tracking/history, BOL/eBOL, document imaging, service eligibility, accessorial/class/terminal metadata.
- Quote Studio automatically switches Dayton from simulated to live API rating when valid Dayton credentials/account are configured.
- Integration Hub adds a Dayton API workbench, safe TESTING pickup workflow, and OpenAPI JSON importer for accelerating future carrier onboarding.
- Dayton secrets are backend-only environment variables and are never exposed to the browser.


## v0.8.1 — Integration Hub Production UX
- Fixed Open adapter / Manage modal visibility.
- Fixed Import OpenAPI interaction and added import results.
- Clarified configured vs live-ready Dayton status.
- Kept Dayton Freight as the quick-access managed carrier adapter.

## v0.8.2 — Secure Carrier API Credentials
- Carrier API usernames/passwords can now be configured directly in Integration Hub.
- Credentials are encrypted server-side before storage and are never returned to the browser.
- Dayton Freight credentials configured in the UI take precedence over legacy `.env` values.
- OpenAPI import discovers server URLs and security schemes and creates a configurable adapter candidate.
- Generic imported adapters can store Basic Auth, API key, bearer token, and client credential profiles while their normalization adapter is developed.

## v0.8.3 — Integration Credential Save & Provider Deletion

- Fixed Dayton credential saves that could report a frontend `querySelector` error after the secure backend save completed.
- Adapter state now refreshes immediately after save and clearly shows masked username/password-saved status.
- Imported OpenAPI provider adapters can be permanently deleted through a typed danger-zone confirmation.
- Built-in Dayton Freight adapter remains protected from accidental deletion.
## v0.8.4 — Requested Pickup Date in Quote Studio

- Replaced the Quote Studio **Required delivery date** field with **Requested pickup date**.
- Quote rating requests now persist the value in `requested_pickup_at` instead of misusing `requested_delivery_at`.
- Quote Detail / Shipment Confirmation displays the requested pickup date and carries it into the shipment as the initial scheduled pickup date.
- Shipment actual pickup and delivery timestamps remain separate operational fields for KPI tracking.



## v0.8.5 — Shipment Confirmation Address + Rated ZIP Location Filtering

- Fixed Google Places structured City/State/ZIP population in shipment confirmation by committing the selected structured address atomically and stabilizing the shared autocomplete lifecycle.
- Saved Ship From and Ship To customer locations are filtered to the exact Origin/Destination ZIP used for the rated quote.
- Confirmation ZIP fields are locked to the rated lane; changing ZIP requires re-rating the quote.

## v0.8.6 — Google Verified Address Autocomplete Repair

- Restores Google-powered street-address suggestions in Quote Bucket shipment confirmation.
- Uses Places API (New) AutocompleteSuggestion directly inside Valhalla Freight instead of relying on the browser-mounted PAC dropdown.
- Selecting a suggestion fills Street, City, and State while preserving the ZIP that was locked by the rated lane.
- Saved customer locations remain filtered to the rated origin/destination ZIP.
- Adds an explicit diagnostic message if the Google Places service cannot initialize.



## v0.8.7 — Quote Record Usability & Simplified Accessorials

- Enlarges Shipment Confirmation and gives it the majority of the Quote Record workspace.
- Keeps Rated Lane, quoted Special Services, and Carrier Options grouped in the left review column.
- Removes the duplicate selected-carrier summary from Shipment Confirmation; the selected rate remains clearly highlighted in Carrier Options.
- Displays Ship From and Ship To confirmation side-by-side on larger screens for faster review and address confirmation.
- Simplifies accessorial selection by consolidating location-specific delivery types such as schools, military/correctional/nuclear sites, hotels/restaurants, farms, mines, mills, self-storage, carnivals/fairs, camps/marinas, utilities, and similar destinations into Limited Access Delivery.
- Preserves backward compatibility by translating older detailed location accessorial codes to the consolidated Limited Access selection when historical quotes are opened.


## v0.8.8 — Rated ZIP Facility Validation

Shipment Confirmation now preserves the ZIP returned by Google Places (or the selected saved customer location) separately from the locked rated-lane ZIP. Approval is blocked if either confirmed facility is outside the ZIP that was originally rated. One-off addresses must be selected from Google suggestions so Valhalla can verify the facility ZIP. The same validation is enforced by the backend before a shipment/BOL can be created.



## v0.9.0 — Automatic Shipment Setup Workflow

- After **Approve, build BOL & create shipment**, Valhalla now routes directly to the new Shipment Control Tower record and automatically opens the shipment setup form.
- Operations can immediately complete PRO, PO/customer references, package details, NMFC, commodity, hazmat contact, declared value, schedule, actuals, and status without manually clicking Edit Shipment.
- The system-assigned BOL remains locked and is already present when the setup form opens.
- Choosing **Finish later** closes the setup form and leaves the user on the newly created shipment; the normal Edit Shipment action remains available afterward.

## v0.8.9 — ZIP+4 & Verified City/State Validation

Shipment approval now accepts valid US ZIP+4 addresses when their first five digits match the rated ZIP and validates that Google-populated City/State remain consistent with the verified address.
