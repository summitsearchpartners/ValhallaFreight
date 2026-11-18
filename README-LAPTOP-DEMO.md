# Transfer your actual Valhalla Freight demo to your laptop

This transfer kit contains the application you uploaded (v0.18.5) and export/restore tools. **This downloaded kit does not yet contain your desktop PostgreSQL database.** The original project ZIP had no database backup. Run the exporter on the desktop to create the complete transfer ZIP.

## 1. On the desktop where your accounts and shipments currently work

1. Start Docker Desktop and the existing Valhalla Freight application. Check that your usual accounts and data are visible.
2. Extract this kit. Copy `Export-Demo.ps1`, `Restore-Demo.ps1`, `Demo-Transfer.Common.ps1`, `README-LAPTOP-DEMO.md`, and `docs/demo_restore_documents.py` into the matching locations in your **existing working ValhallaFreight project folder**. Keep your existing `.env` and application files.
3. Open PowerShell in that existing project folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Export-Demo.ps1
```

The exporter briefly pauses the backend while it snapshots PostgreSQL and uploaded documents, then resumes it. Saving images and making the ZIP can take several minutes and require several GB of free disk space. All database tables are dumped, including users, password hashes, companies, quotes, shipments, settings, integrations and activity. It also saves documents, application files, local `.env`, effective runtime keys and Docker images.

The final message prints the NEW file location, normally:
`Downloads\ValhallaFreight-Demo-YYYYMMDD-HHMMSS.zip`

**Copy that newly created ZIP to the laptop**, not this original transfer kit. The exporter prints users/company/quote/shipment row counts for comparison after restore.

If you would rather keep the kit extracted separately, point it at the actual working source folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Export-Demo.ps1 -SourceProject "C:\path\to\your\working\ValhallaFreight"
```

If your existing installation was launched using `docker compose -p CUSTOMNAME`, also pass `-SourceComposeProject CUSTOMNAME`. The script refuses to export if it cannot find the running original backend and database.

## 2. On the laptop

Docker Desktop must be installed, running, and set to Linux containers. Desktop/laptop CPU architecture must be compatible with the saved images (normally Windows Intel/AMD with Docker Desktop). The default export bundles images, so image downloads and package installs should not be needed on the laptop. Google address search and live carrier services still need internet; manual addresses and existing data work without them.

1. Copy and extract the NEW `ValhallaFreight-Demo-TIMESTAMP.zip` into a local folder. Avoid OneDrive while Docker is running.
2. Open PowerShell in its `ValhallaFreight` folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Restore-Demo.ps1
```

3. Open **http://localhost:5173** and sign in with the **same accounts/passwords you use on the desktop**. Check companies, quotes, shipment/BOL and uploaded files before the demo.

The restore checks SHA-256 hashes, imports the entire database and document volume, compares row counts, and starts the application. It uses the separate Compose project `valhalla-laptop-demo`. Existing databases are not overwritten. If another local app already uses ports 5432, 8000 or 5173, stop that app's containers first without deleting their volumes.

## Start or stop the laptop demo later

Do not rerun the restore after a successful import. From the extracted folder, use:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.json -p valhalla-laptop-demo up -d
```

To stop it while keeping the imported data:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.json -p valhalla-laptop-demo stop
```

Use the same files and project name to inspect logs:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.json -p valhalla-laptop-demo logs --tail 100 backend frontend db
```

Do not run reset scripts or delete Docker volumes. Keep the full extracted demo folder and `docker-compose.demo.json`; the latter preserves encryption/authentication keys and image references.

## If restoration is interrupted

The script does not delete existing tables or overwrite a populated database. If database import succeeded but a later step failed, don't rerun into that database. Use the logs above. For document-only recovery after a successful DB import, with an EMPTY target document volume:

```powershell
Get-Content -Raw .\docs\demo_restore_documents.py | docker compose -f docker-compose.yml -f docker-compose.demo.json -p valhalla-laptop-demo run --rm -T --no-deps --entrypoint python --volume "${PWD}\demo-backup:/demo-backup:ro" backend -
```

Then use the Start command. To make a separate fresh restore without deleting anything, use `Restore-Demo.ps1 -ProjectName valhalla-demo2` after stopping containers that occupy the app ports. Subsequent Start/Stop/Logs commands must use that same name.

## Optional smaller export

Use `Export-Demo.ps1 -SkipImages` only if the laptop will have internet to pull PostgreSQL and build the app. The database/documents/settings are still included, but this is not an offline image bundle.

## Privacy and validation

The generated ZIP contains private account data, password hashes, uploaded credit applications, and integration/authentication secrets. Keep it on your own devices. It does not need to be uploaded here.

The scripts have been parsed and exercised with a simulated Docker command interface, including archive integrity, restore refusal and failure cleanup. Document extraction is tested against valid and unsafe archives. An actual Docker/PostgreSQL transfer cannot be run from this workspace because your desktop Docker volume is not connected here. The on-machine exporter and restore checks perform the real validation.
