# 20_NOTIFICATIONS_AND_INTEGRATIONS

## 1. Centralized Notification Architecture

To prevent notification logic (Email, SMS, WhatsApp) from being scattered across views, models, and forms, all outbound communications MUST be routed through a centralized service module.

- **Module Location:** `intelligence/services/notifications.py`
- **Purpose:** This acts as a single interface. If the client decides to switch their SMS provider or SMTP gateway in the future, developers only need to update this single file rather than hunting through hundreds of views.

## 2. Environment-Aware Background Processing (Celery)

Connecting to external SMTP servers or SMS APIs takes time and can block the main HTTP thread, causing slow page loads for the user.

- **AWS Cloud (`USE_CELERY=True`):** The `notifications.py` service must dispatch the sending process as a background task via Celery and Redis. The main thread will return an immediate HTTP response while the Celery worker sends the email.
- **cPanel Fallback (`USE_CELERY=False`):** To comply with the strict environment rule, if Celery is disabled, the system must gracefully fall back to sending the notification synchronously or queuing it in the database for a cPanel Cron Job to process.

## 3. Standard Coding Pattern

Developers must **never** use Django's native `send_mail()` directly inside `views.py`. AI tools must strictly adhere to the following task delegation pattern:

```python
# PROHIBITED (Do not write this in views):
# send_mail('Contract Created', 'Message...', 'info@cerms.com', ['client@email.com'])

# MANDATORY PATTERN (Use the Central Service):
from intelligence.tasks import dispatch_system_notification

# Inside your view or service layer:
dispatch_system_notification.delay(
    recipient_email=customer.email,
    notification_type="CONTRACT_ACTIVATION",
    context={"contract_no": contract.contract_no, "date": str(contract.created_at)}
)
4. Third-Party Integrations (SMS & WhatsApp API)The system is scoped for future integrations with accounting software, SMS gateways, and WhatsApp.   Adapter Pattern: External integrations must be written using the Adapter Pattern. Create a base interface (e.g., BaseSMSProvider) and implement specific providers (e.g., TwilioProvider, LocalSMSProvider).Environment Driven: The active provider must be determined dynamically based on keys defined in the .env file (e.g., ACTIVE_SMS_PROVIDER=TWILIO).Error Handling: API rate limits or connection timeouts from external providers must be caught and logged as logger.error(), preventing the main CERMS application from crashing.
```
