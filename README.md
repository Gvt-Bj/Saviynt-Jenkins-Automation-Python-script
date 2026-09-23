# Jenkins to Saviynt Automation using Python

## Overview

This project demonstrates an end-to-end automation flow where Jenkins generates account and entitlement data, stores the generated files on the local system, and a Python automation script uploads those files to Saviynt and triggers the required import jobs.

This setup does **not** use SFTPGo or any SFTP server.

## High-Level Flow

```text
Jenkins
   ↓
Generate Accounts CSV
Generate Entitlements CSV
   ↓
Local System
   ↓
Generate/Store SAV Mapping Files
   ↓
Python Automation Script
   ↓
Authenticate to Saviynt
   ↓
Upload CSV files to Datafiles
Upload SAV files to SAV
   ↓
Trigger Entitlement Import Job
   ↓
Trigger Account Import Job
   ↓
Accounts + Entitlements Aggregated in Saviynt
```

## Components

- Jenkins
- Jenkins Role-Based Authorization Strategy plugin
- Python
- Saviynt Enterprise Identity Cloud
- Saviynt REST APIs
- Local Windows file system

## Jenkins Jobs

### Accounts Export Job

Job name:

```text
Accounts_Csv_generate_automation
```

Purpose:

- Reads Jenkins users and their assigned roles.
- Generates the account data required by Saviynt.
- Creates `JenkinsAccounts.csv`.

Example fields:

```text
ACCOUNTNAME
endpointname
entitlement
status
```

### Entitlements Export Job

Job name:

```text
Entitlements_csv_auto_gen
```

Purpose:

- Reads the Jenkins global roles.
- Generates the entitlement inventory required by Saviynt.
- Creates `JenkinsEntitlements.csv`.

Example fields:

```text
Security System
Endpoint
Entitlement Type
Entitlement Value
Glossary
```

## Local Working Directory

All generated files are stored in:

```text
D:\Github\Saviynt-Jenkins-Automation-Python-script
```

Expected files:

```text
JenkinsAccounts.csv
JenkinsEntitlements.csv
JenkinsAccounts.sav
Jenkins_ENTITLEMENT_VALUES.sav
```

## SAV Mapping Files

### Accounts SAV

File:

```text
JenkinsAccounts.sav
```

Purpose:

- Identifies the Jenkins security system.
- Identifies the Jenkins accounts CSV.
- Defines the account import fields.
- Controls account and account-entitlement reconciliation behavior.

### Entitlements SAV

File:

```text
Jenkins_ENTITLEMENT_VALUES.sav
```

Purpose:

- Identifies the Jenkins entitlement CSV.
- Defines entitlement-related fields.
- Controls entitlement creation and reconciliation behavior.

## Python Automation Flow

1. Trigger the Jenkins Accounts pipeline.
2. Wait for the Jenkins build to complete successfully.
3. Download `JenkinsAccounts.csv`.
4. Trigger the Jenkins Entitlements pipeline.
5. Wait for the Jenkins build to complete successfully.
6. Download `JenkinsEntitlements.csv`.
7. Create or use the corresponding `.sav` mapping files.
8. Authenticate to Saviynt.
9. Retrieve a Bearer access token.
10. Upload CSV files to Saviynt `Datafiles`.
11. Upload SAV files to Saviynt `SAV`.
12. Trigger the entitlement import job.
13. Trigger the account import job.
14. Verify Jenkins accounts and entitlements in Saviynt.

## Saviynt API Endpoints

### Authentication

```text
POST /ECM/api/login
```

Purpose:

- Authenticate to Saviynt.
- Return an access token.

### File Upload

```text
POST /ECM/api/v5/uploadSchemaFile
```

Used for:

```text
CSV files → Datafiles
SAV files → SAV
```

### Run Import Job

```text
POST /ECM/api/v5/runJobTrigger
```

Used to trigger the Saviynt file-based import jobs.

## Saviynt Import Jobs

### Entitlement Import

Trigger:

```text
jenkins_entitlement_import
```

Job group:

```text
schema
```

Job:

```text
SchemaEntitlementJob
```

Purpose:

- Import Jenkins roles as Saviynt entitlements.

### Account Import

Trigger:

```text
jenkins_account_import
```

Job group:

```text
schema
```

Job:

```text
SchemaAccountJob
```

Purpose:

- Import Jenkins accounts.
- Associate accounts with the Jenkins endpoint.
- Reconcile account-to-entitlement relationships.

## File Upload Mapping

| File | Saviynt Location | Purpose |
|---|---|---|
| `JenkinsAccounts.csv` | `Datafiles` | Jenkins account data |
| `JenkinsEntitlements.csv` | `Datafiles` | Jenkins entitlement data |
| `JenkinsAccounts.sav` | `SAV` | Account import mapping |
| `Jenkins_ENTITLEMENT_VALUES.sav` | `SAV` | Entitlement import mapping |

## Recommended Import Order

```text
Upload files
   ↓
SchemaEntitlementJob
   ↓
Entitlements created/updated
   ↓
SchemaAccountJob
   ↓
Accounts imported
   ↓
Account-entitlement relationships reconciled
```

## Complete End-to-End Process

```text
Jenkins Users + Roles
        ↓
Accounts_Csv_generate_automation
        ↓
JenkinsAccounts.csv

Jenkins Roles
        ↓
Entitlements_csv_auto_gen
        ↓
JenkinsEntitlements.csv

        ↓

Local Windows Directory

        ↓

JenkinsAccounts.sav
Jenkins_ENTITLEMENT_VALUES.sav

        ↓

Python Automation

        ↓

Saviynt Authentication

        ↓

CSV → Datafiles
SAV → SAV

        ↓

jenkins_entitlement_import
SchemaEntitlementJob

        ↓

jenkins_account_import
SchemaAccountJob

        ↓

Jenkins Accounts + Entitlements
Aggregated in Saviynt
```

## Verification in Saviynt

After the jobs complete, verify:

- Jenkins accounts are visible in the Identity Repository.
- Jenkins entitlements are visible under the Jenkins endpoint.
- Account status is correct.
- Entitlement assignments are linked to the correct accounts.
- The Jenkins security system and endpoint contain the expected imported data.

## Summary

```text
Jenkins
   ↓
Local Files
   ↓
Python
   ↓
Saviynt REST API
   ↓
Schema Import Jobs
   ↓
Aggregation
```
