# 14_GIT_AND_VERSION_CONTROL

## 1. Overview

Strict version control practices are required to ensure the GitHub Actions CI/CD pipelines function correctly for the CERMS project. Proper branching and commit standards prevent deployment failures and maintain a clean code history.

## 2. Branch Naming Conventions

To maintain a clean repository and trigger the correct automated workflows, all branches must follow these specific prefixes:

- **`feature/...`**: For developing new modules, screens, or enhancements (e.g., `feature/fleet-management`, `feature/customer-portal`).
- **`fix/...`**: For resolving bugs or critical errors (e.g., `fix/invoice-bug`, `fix/dispatch-date-validation`).
- **`main`**: The core integration and staging branch. Direct commits to `main` are strictly prohibited. Pull Requests merged here automatically trigger the CI/CD pipeline for AWS Staging deployment.
- **Release Tags (`v*`)**: Semantic version tags (e.g., `v1.0.0`) are used to trigger the immutable container promotion pipeline for AWS Production deployment.

## 3. Commit Message Standards (Conventional Commits)

Commit messages must be descriptive and follow the Conventional Commits specification to generate accurate changelogs automatically:

- **`feat:`** A new feature (e.g., `feat: Added quotation generation output in PDF`).
- **`fix:`** A bug fix (e.g., `fix: Resolved date filter issue on the Smart Dashboard`).
- **`docs:`** Documentation changes only (e.g., `docs: Updated deployment runbook for cPanel handover`).
- **`style:`** Changes that do not affect the meaning of the code (e.g., PEP 8 formatting, removing white spaces).
- **`refactor:`** A code change that neither fixes a bug nor adds a feature, but improves code structure.
- **`chore:`** Routine tasks, dependency updates, or CI/CD pipeline tweaks.
