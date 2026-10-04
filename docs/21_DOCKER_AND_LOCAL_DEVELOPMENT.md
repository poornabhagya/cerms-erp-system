# 21_DOCKER_AND_LOCAL_DEVELOPMENT

## 1. Overview

To ensure absolute environment parity between the developer's local machine and the AWS Cloud production environment, the CERMS platform relies strictly on Docker containerization. This eliminates "it works on my machine" issues prior to cPanel handover.

## 2. Dockerfile Standards (Multi-Stage Build)

The `Dockerfile` must utilize a multi-stage architecture to keep the final production image lightweight, secure, and free of unnecessary development dependencies.

- **Stage 1 (Builder):** Installs OS-level compilation dependencies (e.g., `build-essential`, `libmariadbclient-dev`) and builds Python wheels from `requirements.txt`.
- **Stage 2 (Runtime):** Copies only the compiled binaries and application code from the builder.
- **Security Directive:** The runtime container must execute as an unprivileged non-root user (e.g., `cerms_user`) and expose only the application port (`8000`).

## 3. Docker Compose Configuration

The `docker-compose.yml` file must define the entire monolithic stack within an isolated custom bridge network (`172.28.0.0/16`)[cite: 50].

- **Services:** The file must orchestrate the following interconnected containers: Django, Nginx, MariaDB, Redis, and Celery[cite: 50].
- **Volumes:** Must explicitly map named volumes (e.g., `mariadb_data`, `static_data`, `media_data`) to prevent data loss when containers are destroyed or recreated.
- **Environment Variables:** Containers must load configurations dynamically via the `.env` file at the root level.

## 4. Local Development Commands

Developers and AI agents must use the following standard commands to interact with the containerized environment. Direct local execution of `python manage.py runserver` is prohibited.

- **Build and Start the Stack:**
  `docker compose up --build -d`
- **Stop and Remove Containers:**
  `docker compose down`
- **View Real-Time Logs:**
  `docker compose logs -f web celery`
- **Execute Database Migrations:**
  `docker exec -it cerms_web python manage.py makemigrations`
  `docker exec -it cerms_web python manage.py migrate`
- **Create Admin User:**
  `docker exec -it cerms_web python manage.py createsuperuser`
- **Access Container Shell:**
  `docker exec -it cerms_web /bin/bash`
