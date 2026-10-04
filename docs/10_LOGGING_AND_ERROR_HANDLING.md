# 10_LOGGING_AND_ERROR_HANDLING

## 1. The Strict Logging Rule (No Print Statements)

In an enterprise application, standard `print()` statements are completely useless for debugging deployed applications and are strictly prohibited. All output, state tracking, and error recording MUST be executed using Python's standard `logging` module.

```python
import logging
logger = logging.getLogger(__name__)
2. Environment-Aware Log Routing
The logging configuration inside the settings/ directory must be dynamic to accommodate both infrastructure environments:

AWS CloudWatch (Docker/Cloud): In settings/aws.py, logs must be streamed to the console (StreamHandler -> stdout/stderr). The Docker daemon will automatically capture these and forward them to AWS CloudWatch.

cPanel (Shared Hosting): In settings/cpanel.py, logs must be configured to use RotatingFileHandler, writing to a local file (e.g., logs/django_error.log). This allows the client to read logs directly via the cPanel File Manager without needing terminal access.

3. Log Levels and Usage Standards
To prevent "log noise" and ensure critical issues are visible, AI must categorize logs using the correct severity level:

logger.debug(): For detailed development/troubleshooting insights (e.g., variable states, API payload dumps). Disabled in production.

logger.info(): For successful execution of significant business workflows (e.g., "Quotation #Q-1002 approved", "Equipment EX-05 dispatched").

logger.warning(): For recoverable issues, unexpected behaviors, or security flags (e.g., "Failed login attempt", "File upload exceeded size limit").

logger.error(): For handled exceptions and failed operations that affect a user but don't crash the system (e.g., "Failed to generate PDF invoice", "Email dispatch failed").

logger.critical(): For catastrophic system failures (e.g., "Database connection timeout", "Redis cache unreachable").

4. Exception Handling Best Practices
Never swallow exceptions silently with a bare except: block. Always catch specific exceptions (e.g., ObjectDoesNotExist, ValidationError).

When an unexpected error occurs, you MUST use logger.exception() inside the except block. This automatically captures and formats the full stack trace, which is invaluable for AWS CloudWatch and cPanel error_log debugging.

Python
try:
    # Complex business logic
    contract.generate_invoice()
except CustomBusinessError as e:
    logger.warning(f"Business rule violation: {e}")
except Exception as e:
    logger.exception(f"Critical failure during invoice generation for Contract {contract.id}")
    # Return a generic safe HTTP 500 response to the user
```
