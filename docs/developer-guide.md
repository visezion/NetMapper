# Developer Guide

## How to Understand the Repository

If you are new to the codebase, read it in this order:

1. `netmapper/__init__.py`
   Plugin registration, default settings, asset sync.
2. `netmapper/models.py`
   Core data model.
3. `netmapper/views.py`
   Main UI behavior.
4. `netmapper/forms.py`
   User input and filter handling.
5. `netmapper/tasks.py`
   Main discovery execution flow.
6. `netmapper/utils.py`
   Shared helpers.
7. `netmapper/dictionaries.py`
   Discovery mode definitions and behavior maps.
8. `netmapper/discoverers/`
   Per-platform collection logic.
9. `netmapper/ingestors/`
   Per-command data ingestion logic.
10. `netmapper/jobs/netmapper_jobs.py`
    NetBox script jobs for operators.

Mental model:

- discoverers collect
- logs store
- ingestors interpret
- models persist
- views or forms present and trigger workflows

## How to Add or Extend Functionality

### Add a new discovery mode

1. Add the mode definition to `DiscoveryModeChoices.MODES` in `netmapper/dictionaries.py`.
2. Create a matching discoverer in `netmapper/discoverers/`.
3. Add platform-specific command logic.
4. Add matching ingestors in `netmapper/ingestors/` for supported outputs.
5. Test that `tasks.discovery()` can reach the discoverer and ingest the results.

### Add a new parsed command ingestor

1. Identify the command template name used by the discoverer.
2. Add a module under `netmapper/ingestors/`.
3. Implement ingestion logic that maps parsed output into NetBox models.
4. Verify that `utils.log_ingest()` can resolve and run the ingestor.

### Add a new scan inference rule

1. Update `infer_discovery_mode()` in `netmapper/network_discovery.py`.
2. Add or extend tests in `netmapper/tests/test_network_discovery.py`.
3. Validate with dry-run or queued scan history.

### Add a new UI page

1. Create or update a view in `netmapper/views.py`.
2. Add forms and filters in `netmapper/forms.py` if needed.
3. Add tables in `netmapper/tables.py` if needed.
4. Add routes in `netmapper/urls.py`.
5. Add menu items in `netmapper/navigation.py`.
6. Add templates under `netmapper/templates/netmapper/`.

### Add a new model

1. Add the model to `netmapper/models.py`.
2. Create a migration in `netmapper/migrations/`.
3. Add views, forms, filtersets, and tables if the object needs UI support.
4. Add tests and validate startup and migration flow.
