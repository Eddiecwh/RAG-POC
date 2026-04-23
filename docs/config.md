## appointment_sync_enabled

Controls whether appointment sync jobs run during the ETL pipeline.

- staging: true
- production: true
- dev: false (disabled to avoid noise during local development)

This flag is checked in AppointmentSyncJob.java at startup.
If false, the sync loop is skipped entirely and no appointments are processed.

## max_retry_attempts

Number of times a failed sync job will retry before marking the record as errored.

- staging: 3
- production: 5
- dev: 1

Configured in RetryConfig.java. Applies to all EHR integrations including Epic, Athena, and ECW.

## ehr_timeout_seconds

HTTP timeout in seconds for outbound EHR API calls.

- staging: 30
- production: 60
- dev: 10

If exceeded, the request is logged as a timeout error and retry logic kicks in.
Relevant for Veradigm and Athena integrations which can be slow under load.