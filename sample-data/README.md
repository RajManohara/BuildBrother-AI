# Safe synthetic data

The idempotent generator lives in `backend/app/demo.py` and runs on API startup when DEMO_MODE is enabled. It creates `demo/payments-api`, 12 builds, 2 services, a verified demo deployment, a fictitious dependency finding, and 2 runtime incidents. No real vulnerability, credential, or compromise is represented.

`runtime-event.json` is an ingestion example for the seeded service. Replace its source_event_id when creating a new event and set the timestamp relative to a stored deployment if you want it correlated. Reusing an identical event is idempotent.
