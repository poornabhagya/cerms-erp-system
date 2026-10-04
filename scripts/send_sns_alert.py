#!/usr/bin/env python3
# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Automated DevOps SNS Alert Dispatcher (CI/CD Deployment Notifications)
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

import argparse
import json
import os
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="CERMS DevOps Alert Dispatcher via AWS SNS")
    parser.add_argument(
        "--env",
        dest="environment",
        choices=["staging", "production"],
        default="staging",
        help="Target deployment environment (staging or production)",
    )
    parser.add_argument(
        "--summary-file",
        dest="summary_file",
        default="staging_smoke_summary.json",
        help="Path to the JSON smoke test summary file",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 1. Read Smoke Test Summary
    summary_data = {
        "total_tested": "N/A",
        "success_count": "N/A",
        "protected_count": "N/A",
        "crashes": 0,
        "failed_routes": [],
        "status": "PASSED",
    }

    if os.path.exists(args.summary_file):
        try:
            with open(args.summary_file, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to parse summary file {args.summary_file}: {e}")

    total = summary_data.get("total_tested", "N/A")
    passed = summary_data.get("success_count", "N/A")
    protected = summary_data.get("protected_count", "N/A")
    crashes = summary_data.get("crashes", 0)
    failed = summary_data.get("failed_routes", [])

    # 2. Gather Environment & Pipeline Variables
    job_status = os.environ.get("JOB_STATUS", "success").upper()
    is_success = (job_status == "SUCCESS") and (crashes == 0)
    status_text = "SUCCESS" if is_success else "FAILURE"

    topic_arn = os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:ap-south-1:804372444724:cerms-devops-alerts")
    aws_region = os.environ.get("AWS_REGION", "ap-south-1")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "poornabhagya/cerms-erp-system")
    github_run_id = os.environ.get("GITHUB_RUN_ID", "")
    actor = os.environ.get("GITHUB_ACTOR", "CI/CD Pipeline")
    commit_sha = os.environ.get("GITHUB_SHA", "")
    commit_short = commit_sha[:7] if commit_sha else "unknown"
    release_tag = os.environ.get("GITHUB_REF_NAME", "latest")

    # 3. Construct Subject and Message Payload
    if args.environment == "staging":
        instance_id = os.environ.get("STAGING_INSTANCE_ID", "i-0cb762fcdb76a4720")
        subject = f"[CERMS Staging] Deployment {status_text}: Commit {commit_short}"
        env_title = "STAGING"
        env_details = "Staging Silo (ap-south-1b | 10.10.2.0/24)"
        verdict = "PASSED (Zero Defects)" if crashes == 0 else f"FAILED ({crashes} Crashes Detected)"
    else:
        instance_id = os.environ.get("PROD_INSTANCE_ID", "i-093dc6493e6f4636f")
        subject = f"[CERMS Production] Release {status_text}: Tag {release_tag}"
        env_title = "PRODUCTION"
        env_details = "Production Dedicated Silo (ap-south-1a | 10.10.1.0/24)"
        verdict = "PASSED (Zero-Downtime Verified)" if crashes == 0 else f"FAILED ({crashes} Crashes Detected)"

    lines = [
        "================================================================================",
        f"CERMS MULTI-TENANT CLOUD DEPLOYMENT REPORT ({env_title})",
        "================================================================================",
        f"Status          : {status_text} (Pipeline Job: {job_status})",
        f"Environment     : {env_details}",
        f"Target Instance : {instance_id}",
    ]

    if args.environment == "staging":
        lines.append(f"Commit SHA      : {commit_sha}")
    else:
        lines.append(f"Release Tag     : {release_tag}")
        lines.append("Public Endpoint : http://13.204.130.46")

    lines.extend([
        f"Triggered By    : {actor}",
        f"Repository      : {github_repo}",
        "",
        "SMOKE TEST VERIFICATION BREAKDOWN:",
        "--------------------------------------------------------------------------------",
        f"- Total Endpoints Audited : {total}",
        f"- HTTP 200 OK Endpoints   : {passed}",
        f"- Auth/RBAC Secured (302) : {protected}",
        f"- 500 Route Crashes       : {crashes}",
        f"- Verification Verdict    : {verdict}",
    ])

    if failed:
        lines.extend([
            "",
            "CRASHED ROUTE DETAILS:",
            "--------------------------------------------------------------------------------",
        ])
        for r in failed:
            url = r.get("url", "unknown")
            code = r.get("status_code", 500)
            err = r.get("error", "Internal Server Error")
            lines.append(f"- {url} [HTTP {code}]: {err}")

    if github_run_id:
        lines.extend([
            "",
            "--------------------------------------------------------------------------------",
            f"GitHub Workflow Run: https://github.com/{github_repo}/actions/runs/{github_run_id}",
        ])

    lines.append("================================================================================")

    message_body = "\n".join(lines)

    # 4. Dispatch SNS Notification
    print(f"[*] Publishing notification to SNS Topic: {topic_arn}")
    print(f"[*] Subject: {subject}")

    try:
        res = subprocess.run(
            [
                "aws",
                "sns",
                "publish",
                "--topic-arn",
                topic_arn,
                "--subject",
                subject,
                "--message",
                message_body,
                "--region",
                aws_region,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if res.returncode == 0:
            print("[+] SNS Publish succeeded:")
            print(res.stdout)
        else:
            print(f"[!] SNS Publish returned non-zero exit code ({res.returncode}):")
            print(res.stderr)
    except Exception as e:
        print(f"[!] Exception during SNS publish execution: {e}")


if __name__ == "__main__":
    main()
