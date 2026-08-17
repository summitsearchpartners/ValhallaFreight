# Valhalla Freight Modular Architecture Standard

Valhalla Freight is organized by feature/domain so individual parts of the TMS can be changed without hunting through monolithic files.

## Backend standard

Each substantial business domain should live under `backend/app/domains/<domain>/` and separate:

1. **models.py** — persistent data structures unique to that domain.
2. **schemas.py** — API request and response contracts.
3. **service.py** — business rules, validation, calculations and orchestration.
4. **routes.py** — thin HTTP layer that delegates to services.
5. Additional files such as `repository.py`, `integrations/`, or `events.py` when the domain becomes large enough to justify them.

Cross-cutting infrastructure remains under `core`, `db`, `api/deps`, and shared `services`.

## Frontend standard

Each substantial UI domain should live under `frontend/src/features/<feature>/` and separate:

1. **types.ts** — feature contracts.
2. **api.ts** — API integration.
3. **hooks/** or feature hooks — state and data orchestration.
4. **components/** — focused UI components.
5. Page entry components that compose the feature.

Generic design-system pieces stay under `components/`. Global authentication stays under `context/` until it becomes its own domain.

## Size rule

A file should not become the catch-all for a feature. When a component, service, model collection or route set becomes difficult to scan, split it by responsibility before adding more behavior.

## Planned domains

- customers
- carriers
- pricing
- quoting
- shipments
- tracking
- documents
- billing
- claims
- analytics
- prospect intelligence
- users / RBAC
- integrations

Customer 360 in v0.4.0 is the reference implementation for this structure.
