## New client onboarding checklist

Steps to onboard a new client onto the platform.

1. Create client record in the admin console with the correct EHR type (Epic, Athena, ECW, Veradigm)
2. Set environment config values for staging — confirm appointment_sync_enabled is true
3. Run the constants sync job to pull provider and location data from the EHR
4. Validate provider ID mapping in the provider_map table
5. Trigger a test appointment sync and verify records appear in the dashboard
6. Confirm with the implementation team before flipping to production

## Common onboarding issues

- Provider IDs not mapping correctly: check the provider_map table for nulls, often caused by a mismatch between the EHR's provider NPI and our internal ID
- Constants sync returning empty: usually an auth token issue, verify the client's API credentials in the secrets config
- Appointments not syncing: check appointment_sync_enabled is true for the environment, and check the ETL logs for timeout errors