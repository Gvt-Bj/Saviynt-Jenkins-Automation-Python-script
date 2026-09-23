import re
import sys
import time
from pathlib import Path

import requests

WORKSPACE_DIR = Path(r"D:\Github\Saviynt-Jenkins-Automation-Python-script")

ACCOUNT_FILE = WORKSPACE_DIR / "JenkinsAccounts.csv"

ENTITLEMENT_FILE = WORKSPACE_DIR / "JenkinsEntitlements.csv"

# Schema (.sav) file - uploaded to a separate "SAV Files" bucket in Saviynt,
# distinct from the "Data Files" bucket the CSVs go to.
SAV_FILE = WORKSPACE_DIR / "JenkinsAccounts.sav"

ENTITLEMENT_SAV_FILE = WORKSPACE_DIR / "Jenkins_ENTITLEMENT_VALUES.sav"


# JENKINS CONFIGURATION
JENKINS_URL = "http://localhost:8080"
JENKINS_USERNAME = "<jenkins_username>"
JENKINS_API_TOKEN = "<jenkins_username>"
ACCOUNT_JOB = "Accounts_Csv_generate_automation"
ENTITLEMENT_JOB = "Entitlements_csv_auto_gen"

jenkins_session = requests.Session()
jenkins_session.auth = (JENKINS_USERNAME, JENKINS_API_TOKEN)

SAVIYNT_URL = "https:/<org-instance>.saviyntcloud.com"

SAVIYNT_USERNAME = "<saviynt_username>"

# Replace with your current Saviynt password
SAVIYNT_PASSWORD = "<saviynt_password>"
# SAVIYNT API ENDPOINT

# Correct endpoint confirmed from your Postman request
SAVIYNT_LOGIN_ENDPOINT = "/ECM/api/login"

SAVIYNT_UPLOAD_ENDPOINT = "/ECM/api/v5/uploadSchemaFile"

SAVIYNT_RUN_TRIGGER_ENDPOINT = "/ECM/api/v5/runJobTrigger"
# SAVIYNT TRIGG

ACCOUNT_TRIGGER_PAYLOAD = {
    "triggername": "jenkins_account_import",
    "jobgroup": "schema",
    "jobname": "SchemaAccountJob",
}
#these are my jobs i created before running the script you have to create yours
ENTITLEMENT_TRIGGER_PAYLOAD = {
    "triggername": "jenkins_entitlement_import",
    "jobgroup": "schema",
    "jobname": "SchemaEntitlementJob",
}


# JENKINS FUNCTIONS
def trigger_job(job_name):
    url = f"{JENKINS_URL}/job/{job_name}/build"
    response = jenkins_session.post(url, timeout=30)
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to trigger {job_name}: {response.status_code} {response.text}"
        )
    queue_url = response.headers.get("Location")
    if not queue_url:
        raise RuntimeError(f"Jenkins did not return a queue URL for {job_name}")
    print(f"Triggered Jenkins job: {job_name}")
    return queue_url


def wait_for_build_number(queue_url):
    while True:
        response = jenkins_session.get(f"{queue_url}api/json", timeout=30)
        response.raise_for_status()
        data = response.json()
        if "executable" in data:
            build_number = data["executable"]["number"]
            print(f"Build started: #{build_number}")
            return build_number
        if data.get("cancelled"):
            raise RuntimeError("Jenkins queue item was cancelled")
        time.sleep(2)


def wait_for_build(job_name, build_number):
    while True:
        url = f"{JENKINS_URL}/job/{job_name}/{build_number}/api/json"
        response = jenkins_session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data["building"]:
            result = data["result"]
            print(f"{job_name} finished with: {result}")
            if result != "SUCCESS":
                raise RuntimeError(f"{job_name} failed")
            return
        time.sleep(3)


def download_artifact(job_name, build_number, artifact_name):
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/artifact/{artifact_name}"
    response = jenkins_session.get(url, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(
            f"Could not download {artifact_name}: {response.status_code} {response.text}"
        )
    output_path = WORKSPACE_DIR / artifact_name
    output_path.write_bytes(response.content)
    print(f"Saved locally: {output_path}")
    return output_path


def run_export(job_name, artifact_name):
    queue_url = trigger_job(job_name)
    build_number = wait_for_build_number(queue_url)
    wait_for_build(job_name, build_number)
    return download_artifact(job_name, build_number, artifact_name)


def create_sav_files():
    account_sav_content = """SystemName=Jenkins
FileNameStartswith=JenkinsAccounts.csv
Entitlement_type=entitlement,
FILEIMPORTDELIMETER=,
ACCOUNTNAME,endpointname,entitlement,status,
            IGNOREFIRSTLINE=TRUE

DELETEACCOUNTENTITLEMENT=YES

ACCOUNT_NOT_IN_FILE_ACTION=NO
"""
    SAV_FILE.write_text(account_sav_content, encoding="utf-8")
    print(f"Created account SAV file: {SAV_FILE}")

    entitlement_sav_content = """FILE_NAME_STARTS_WITH=JenkinsEntitlements
SKIP_NO_OF_LINES=1
FILE_IMPORT_DELIMETER=,
CREATE_SECURITYSYSTEM_IF_NOT_EXIST=NO
CREATE_ENDPOINT_IF_NOT_EXIST_IN_SECURITYSYSTEM=NO
CREATE_ENTITLEMENTTYPE_IF_NOT_EXIST_IN_ENDPOINT=YES
ENTITLEMENT_VALUES_NOT_IN_FILE_ACTION=NO ACTION
SECURITYSYSTEMS,ENDPOINTS,ENTITLEMENTTYPE,ENTITLEMENT_VALUE,GLOSSARY
"""
    ENTITLEMENT_SAV_FILE.write_text(entitlement_sav_content, encoding="utf-8")
    print(f"Created entitlement SAV file: {ENTITLEMENT_SAV_FILE}")


# SAVIYNT AUTHENTICATI


def saviynt_login():

    url = SAVIYNT_URL + SAVIYNT_LOGIN_ENDPOINT

    payload = {"username": SAVIYNT_USERNAME, "password": SAVIYNT_PASSWORD}

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    print("\nAuthenticating to Saviynt...")
    print(f"URL: {url}")

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=60,
        # Useful while debugging.
        # Prevents an API redirect from silently becoming an HTML login page.
        allow_redirects=False,
    )

    print(f"HTTP Status: {response.status_code}")
    print("Response Content-Type:", response.headers.get("Content-Type"))
    print("Redirect Location:", response.headers.get("Location"))
    # Detect redirec

    if response.status_code in (301, 302, 303, 307, 308):
        raise RuntimeError(
            "\nSaviynt redirected the API login request.\n"
            f"Redirect target: "
            f"{response.headers.get('Location')}\n"
            "The API authentication request did not return a token."
        )
    # HTTP erro

    if response.status_code != 200:
        raise RuntimeError(
            "Saviynt authentication failed.\n"
            f"HTTP Status: {response.status_code}\n"
            f"Response: {response.text[:1000]}"
        )
    # Parse JSON respons

    try:
        data = response.json()

    except ValueError:
        raise RuntimeError(
            "Saviynt returned HTTP 200 but the response "
            "was not JSON.\n"
            f"Content-Type: "
            f"{response.headers.get('Content-Type')}\n"
            f"Response:\n{response.text[:1000]}"
        )
    # Extract access toke

    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Saviynt authentication response did not "
            "contain access_token.\n"
            f"Response: {data}"
        )

    print("\nSaviynt authentication successful.")
    print("Bearer access token obtained.")

    return access_token


# UPLOAD .CSV TO SAVIYNT


def upload_to_saviynt(
    access_token, file_path, path_location, allowed_suffixes, upload_filename=None
):

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Expected a file but received: {file_path}")

    if file_path.suffix.lower() not in allowed_suffixes:
        raise ValueError(
            f"Expected one of {allowed_suffixes}, but received: {file_path.name}"
        )

    url = SAVIYNT_URL + SAVIYNT_UPLOAD_ENDPOINT

    headers = {"Authorization": f"Bearer {access_token}"}

    print()
    print(
        f"Uploading {file_path.name} to Saviynt " f"(pathLocation={path_location})..."
    )

    print(f"Full local file path: " f"{file_path}")

    if upload_filename:
        # Explicit override -- used when the job requires the uploaded
        # data file's name to match its schema (.sav) file's name exactly.
        clean_name = upload_filename
    else:
        # FIX: Saviynt rejects filenames with spaces/special characters
        # ("Invalid file name: file name cannot contain special characters
        # or spaces"). Strip anything that isn't a letter, digit, dot,
        # underscore, or hyphen for the uploaded filename only -- the local
        # file on disk is untouched.
        clean_name = re.sub(r"[^A-Za-z0-9._-]", "", file_path.name)

    if clean_name != file_path.name:
        print(f"Filename for upload: {clean_name} (local file unchanged)")

    content_type = (
        "text/csv" if file_path.suffix.lower() == ".csv" else "application/octet-stream"
    )

    with file_path.open("rb") as data_file:

        files = {"file": (clean_name, data_file, content_type)}

        form_data = {"pathLocation": path_location}

        response = requests.post(
            url, headers=headers, files=files, data=form_data, timeout=120
        )

    print(f"Upload HTTP status: " f"{response.status_code}")

    print(f"Upload response: " f"{response.text}")

    if response.status_code not in (200, 201) or '"errorCode":"1"' in response.text:
        raise RuntimeError(
            f"Saviynt upload failed for "
            f"{file_path.name}\n"
            f"HTTP Status: "
            f"{response.status_code}\n"
            f"Response: "
            f"{response.text}"
        )

    print(f"{file_path.name} " f"uploaded successfully.")


# RUN SAVIYNT IMPORT TRIGG


def run_saviynt_trigger(access_token, trigger_payload):

    url = SAVIYNT_URL + SAVIYNT_RUN_TRIGGER_ENDPOINT

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print()
    print(f"Triggering {trigger_payload['triggername']}...")

    # Import jobs can take a while to acknowledge; give it more room than
    # the earlier 60s (which led to a hang + manual Ctrl+C last run).
    response = requests.post(url, headers=headers, json=trigger_payload, timeout=180)

    print(f"Trigger HTTP status: " f"{response.status_code}")

    print(f"Trigger response: " f"{response.text}")

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Saviynt runJobTrigger request failed for "
            f"{trigger_payload['triggername']}.\n"
            f"HTTP Status: "
            f"{response.status_code}\n"
            f"Response: "
            f"{response.text}"
        )

    print(f"Saviynt {trigger_payload['triggername']} trigger started successfully.")


# ============================================================
# MENU WORKFLOWS
# ============================================================

def run_jenkins_only():

    print()
    print("=" * 60)
    print("JENKINS ONLY")
    print("=" * 60)

    account_file = run_export(
        ACCOUNT_JOB,
        "JenkinsAccounts.csv"
    )

    entitlement_file = run_export(
        ENTITLEMENT_JOB,
        "JenkinsEntitlements.csv"
    )

    print("\nBoth Jenkins exports completed successfully.")

    create_sav_files()

    print()
    print(f"Accounts CSV: {account_file}")
    print(f"Accounts SAV: {SAV_FILE}")
    print(f"Entitlements CSV: {entitlement_file}")
    print(f"Entitlements SAV: {ENTITLEMENT_SAV_FILE}")

    print()
    print("=" * 60)
    print("JENKINS PROCESS COMPLETED")
    print("=" * 60)


def run_saviynt_only():

    account_file = ACCOUNT_FILE
    entitlement_file = ENTITLEMENT_FILE

    print()
    print("=" * 60)
    print("SAVIYNT CSV UPLOAD + IMPORT")
    print("=" * 60)

    print(f"Accounts file: {account_file}")
    print(f"Entitlements file: {entitlement_file}")
    print(f"Schema (.sav) file: {SAV_FILE}")
    print(f"Entitlement schema (.sav) file: {ENTITLEMENT_SAV_FILE}")

    token = saviynt_login()

    upload_to_saviynt(
        token,
        entitlement_file,
        path_location="Datafiles",
        allowed_suffixes=(".csv",),
        upload_filename="JenkinsEntitlements.csv",
    )

    required_csv_name = SAV_FILE.stem + ".csv"

    upload_to_saviynt(
        token,
        account_file,
        path_location="Datafiles",
        allowed_suffixes=(".csv",),
        upload_filename=required_csv_name,
    )

    upload_to_saviynt(
        token,
        SAV_FILE,
        path_location="SAV",
        allowed_suffixes=(".sav",),
        upload_filename="Jenkins_ACCOUNTS.sav",
    )

    upload_to_saviynt(
        token,
        ENTITLEMENT_SAV_FILE,
        path_location="SAV",
        allowed_suffixes=(".sav",),
    )

    run_saviynt_trigger(
        token,
        ENTITLEMENT_TRIGGER_PAYLOAD
    )

    run_saviynt_trigger(
        token,
        ACCOUNT_TRIGGER_PAYLOAD
    )

    print()
    print("=" * 60)
    print("SAVIYNT UPLOAD + TRIGGER COMPLETED")
    print("=" * 60)


def run_full_import():

    print()
    print("=" * 60)
    print("FULL JENKINS -> SAVIYNT IMPORT")
    print("=" * 60)

    account_file = run_export(
        ACCOUNT_JOB,
        "JenkinsAccounts.csv"
    )

    entitlement_file = run_export(
        ENTITLEMENT_JOB,
        "JenkinsEntitlements.csv"
    )

    print("\nBoth Jenkins exports completed successfully.")

    create_sav_files()

    print()
    print(f"Accounts CSV: {account_file}")
    print(f"Accounts SAV: {SAV_FILE}")
    print(f"Entitlements CSV: {entitlement_file}")
    print(f"Entitlements SAV: {ENTITLEMENT_SAV_FILE}")

    token = saviynt_login()

    upload_to_saviynt(
        token,
        entitlement_file,
        path_location="Datafiles",
        allowed_suffixes=(".csv",),
        upload_filename="JenkinsEntitlements.csv",
    )

    required_csv_name = SAV_FILE.stem + ".csv"

    upload_to_saviynt(
        token,
        account_file,
        path_location="Datafiles",
        allowed_suffixes=(".csv",),
        upload_filename=required_csv_name,
    )

    upload_to_saviynt(
        token,
        SAV_FILE,
        path_location="SAV",
        allowed_suffixes=(".sav",),
        upload_filename="Jenkins_ACCOUNTS.sav",
    )

    upload_to_saviynt(
        token,
        ENTITLEMENT_SAV_FILE,
        path_location="SAV",
        allowed_suffixes=(".sav",),
    )

    run_saviynt_trigger(
        token,
        ENTITLEMENT_TRIGGER_PAYLOAD
    )

    run_saviynt_trigger(
        token,
        ACCOUNT_TRIGGER_PAYLOAD
    )

    print()
    print("=" * 60)
    print("END-TO-END AUTOMATION COMPLETED")
    print("=" * 60)


# ============================================================
# MAIN MENU
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("JENKINS + SAVIYNT AUTOMATION MENU")
    print("=" * 60)
    print("1. Full Import Process (Jenkins -> Saviynt Aggregation)")
    print("2. Jenkins Only")
    print("3. Saviynt Only")
    print()

    choice = input(
        "Select an option (1/2/3): "
    ).strip()

    if choice == "1":
        run_full_import()

    elif choice == "2":
        run_jenkins_only()

    elif choice == "3":
        run_saviynt_only()

    else:
        raise SystemExit(
            "Invalid option. Please select 1, 2, or 3."
        )
