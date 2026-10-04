# ==============================================================================
# Construction Equipment Rental Management System (CERMS)
# Automated Route Scanning & Smoke Testing Harness
# Reference: docs/05_DEVOPS_AND_CLOUD.md, docs/22_ENTERPRISE_CLOUD_ROADMAP.md
# ==============================================================================

import os
import sys
import json
import traceback
import django
from django.urls import get_resolver
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cerms_project.settings.aws')
django.setup()

def get_all_urls(urlpatterns, prefix=''):
    routes = []
    for pattern in urlpatterns:
        if hasattr(pattern, 'url_patterns'):
            routes.extend(get_all_urls(pattern.url_patterns, prefix + str(pattern.pattern)))
        else:
            routes.append(prefix + str(pattern.pattern))
    return routes

resolver = get_resolver()
all_urls = get_all_urls(resolver.url_patterns)

# Filter static routes (endpoints without regex or dynamic path parameters)
static_urls = []
for u in all_urls:
    if not any(char in u for char in ['<', '>', '(', ')', '^', '$', '?']):
        clean_url = '/' + u.lstrip('/')
        if clean_url not in static_urls:
            static_urls.append(clean_url)

print(f"\n[+] Total CERMS static routes identified: {len(static_urls)}")

client = Client()
errors = []
success_count = 0
protected_count = 0

for url in static_urls:
    try:
        res = client.get(url)
        if res.status_code == 500:
            print(f"[-] CRASH 500: {url}")
            errors.append({
                "url": url,
                "status_code": 500,
                "error": "Internal Server Error (HTTP 500)"
            })
        elif res.status_code in [301, 302, 401, 403]:
            protected_count += 1
        else:
            success_count += 1
    except Exception as e:
        err_msg = str(e)
        stack = traceback.format_exc().splitlines()[-3:]
        print(f"[-] EXCEPTION on {url}: {err_msg}")
        errors.append({
            "url": url,
            "status_code": "EXCEPTION",
            "error": err_msg,
            "trace": " | ".join(stack)
        })

total_tested = len(static_urls)
crash_count = len(errors)

print("\n" + "=" * 50)
print("CERMS AUTOMATED SMOKE TEST AUDIT REPORT")
print("=" * 50)
print(f"Total Routes Tested : {total_tested}")
print(f"Accessible (200/Other): {success_count}")
print(f"RBAC Protected (Redirect/Forbidden): {protected_count}")
print(f"Crashes / 500 Errors : {crash_count}")
print("=" * 50)

# Export summary JSON for GitHub Actions step summaries & alerts
summary_data = {
    "total_tested": total_tested,
    "success_count": success_count,
    "protected_count": protected_count,
    "crashes": crash_count,
    "failed_routes": errors,
    "status": "PASSED" if crash_count == 0 else "FAILED"
}

with open("smoke_test_summary.json", "w") as f:
    json.dump(summary_data, f, indent=2)

if crash_count == 0:
    print("[SUCCESS] All CERMS endpoints verified with 0 crashes!")
    sys.exit(0)
else:
    print(f"[FAIL] {crash_count} endpoints encountered errors.")
    for err in errors:
        print(f"  ::error title=Smoke Test Failure on {err['url']}::{err.get('error')} ({err.get('status_code')})")
    sys.exit(1)
