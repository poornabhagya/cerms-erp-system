# 11_SECURITY_AND_AUTHENTICATION

## 1. Authentication Strategy

- **Web Interface:** Use standard Django Session Authentication for all web-based portals (Dashboard, cPanel deployment).
- **Mobile / API:** Use Token Authentication (DRF Tokens or SimpleJWT) for the Field Operations mobile app to ensure stateless and secure API communication.

## 2. Vulnerability Prevention (OWASP Standards)

- **CSRF (Cross-Site Request Forgery):**
  - Must include `{% csrf_token %}` in all HTML `<form>` submissions.
  - All AJAX POST/PUT/DELETE requests must pass the `X-CSRFToken` header.
- **XSS (Cross-Site Scripting):**
  - Strictly rely on Django template auto-escaping.
  - Never use the `|safe` filter on user-generated content without prior strict sanitization.
- **SQL Injection:**
  - Strictly use the Django ORM for all database interactions.
  - The use of raw SQL (`.raw()`, `cursor.execute()`) is explicitly prohibited.

## 3. Secrets and `.env` Management

- **No Hardcoded Secrets:** Passwords, Database Credentials, AWS Keys, and the `SECRET_KEY` must never be hardcoded in the codebase.
- **Environment Variables:** Always fetch sensitive data using `os.getenv()` or `python-decouple`.
- **Git Ignore:** The `.env` file must be strictly listed in `.gitignore` to prevent accidental exposure to version control.

## 4. User Data Encryption

- **Passwords:** Must be hashed using Django's default PBKDF2 password hasher. Plain text passwords are strictly forbidden.
- **Sensitive Files:** Database backups pushed to S3 must remain GPG AES-256 encrypted as defined in the DevOps pipeline.
