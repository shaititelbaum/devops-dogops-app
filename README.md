# 🐾 DogOps - Application Repository

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.9+-blue.svg) ![Docker](https://img.shields.io/badge/docker-ready-blue) ![Helm](https://img.shields.io/badge/helm-packaged-informational)

Welcome to the **DogOps Application**! This is the core microservice repository containing the backend API, the frontend UI, and the Kubernetes Helm charts used to deploy the application.

## 🏗 Architecture
* **Backend**: Python-based API handling core business logic, SSO authentication (Google, LinkedIn), and S3 profile image uploads.
* **Frontend**: Modern, responsive UI featuring Glassmorphism design principles, dynamic transitions, and RTL (Right-to-Left) rendering support for emails.
* **Database**: Integrates with PostgreSQL.
* **Secrets**: Integrates with AWS Secrets Manager via External Secrets Operator (ESO) for API keys, SMTP, and DB credentials.

## 📁 Repository Structure
* `/app.py`: Main application entrypoint.
* `/frontend/`: Contains all HTML, CSS, and UI assets.
* `/Dockerfile`: Multi-stage, optimized container build.
* `/charts/`: Helm charts for packaging the application.
* `/requirements.txt`: Python dependencies.

## 🚀 Local Development
1. **Prerequisites**:
   - Docker Desktop with Kubernetes enabled.
   - Helm CLI.
   - AWS CLI configured with ECR permissions.

2. **Running Locally**:
   ```bash
   docker build -t dogops-app:local .
   docker run -p 8080:8080 dogops-app:local
   ```

3. **Helm Validation**:
   ```bash
   helm lint ./charts/devops-dogops-backend-chart
   ```

## 🔄 Deployment Pipeline
This application is strictly deployed using GitOps. **Never use the `latest` image tag.**
1. Code pushed to `master` triggers a GitHub Action.
2. The Action builds a new Docker image, tags it with the Git SHA, and pushes to AWS ECR.
3. The pipeline automatically makes a `[skip ci]` commit to the `devops-dogops-gitops` repository to trigger ArgoCD.