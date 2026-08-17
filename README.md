# FreightForge

**Transportation Intelligence. Forged for LTL.**

FreightForge is an LTL-first Transportation Management System foundation designed around the complete brokerage lifecycle:

**Quote → Book → Dispatch → Track → Deliver → Audit → Invoice → Analyze**

This repository contains a Dockerized React/TypeScript frontend, Python FastAPI backend and PostgreSQL data layer. The current build is intentionally structured as a production-oriented foundation rather than a throwaway prototype: carrier responses are normalized behind a rating layer, customer pricing is rule-driven, shipment data is structured for analytics, and integrations can be replaced without redesigning the operating application.

## What is already in this build

- FreightForge command-center dashboard
- Professional responsive operations UI
- Customer master data
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

## Start FreightForge on Windows / PowerShell

Prerequisites: Docker Desktop, Git, and Visual Studio Code.

```powershell
cd C:\Path\To\FreightForge
docker compose up --build
```

Open:

- FreightForge UI: http://localhost:5173
- FreightForge API: http://localhost:8000
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
git commit -m "Initial FreightForge platform foundation"
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

Carrier integrations should implement the normalized FreightForge contract instead of leaking carrier-specific payloads into the rest of the software.

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
13. AI intelligence over structured FreightForge data.
14. AWS deployment, secrets, observability, backups and CI/CD.

## Important development note

The local rating service currently uses a **deterministic development carrier connector** so the entire Quote Studio and pricing workflow can run without paid carrier credentials. It is intentionally isolated in `backend/app/services/rating.py`. That adapter is the replacement point for a real LTL aggregator or direct carrier APIs.
