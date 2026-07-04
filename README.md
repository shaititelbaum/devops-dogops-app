# 🐾 DogOps - Core Application Repository

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.11-blue.svg) ![Docker](https://img.shields.io/badge/docker-ready-blue) ![Helm](https://img.shields.io/badge/helm-packaged-informational) ![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-orange) ![AWS](https://img.shields.io/badge/AWS-S3-yellow)

Welcome to the **DogOps Application Repository**. This is the heart of the DogOps ecosystem—a state-of-the-art, highly observable, and secure microservice designed specifically for professional dog trainers. 

This repository contains the complete source code for the Backend API, the Frontend UI, and the Kubernetes Helm packaging required to deploy the system into any cloud native environment.

---

## 🌟 Core Features & Business Logic

The DogOps application is packed with advanced functionalities tailored for canine behavior tracking and trainer productivity:

* **🧠 Gemini AI Integration**: A built-in AI assistant trained to act as an expert dog behaviorist. It answers complex training questions on the fly via the `/api/chat` route.
* **☁️ Advanced SSO (Single Sign-On)**: Seamless OAuth2 authentication supporting **Google**, **LinkedIn**, and **Microsoft**. The system automatically generates placeholder dog profiles upon initial SSO registration.
* **🐕 Comprehensive Profile Management**: Users can track their dog's breed, city, date of birth, weight, chip number, and allergies. 
* **📸 AWS S3 Image Uploads**: Direct integration with `boto3` to securely upload, store, and manage high-resolution dog profile pictures in an AWS S3 bucket, including automatic garbage collection of old images to save storage costs.
* **🌦️ Smart Weather Training Integration**: Connects to the Open-Meteo API to pull live weather data, intelligently analyzing temperature and wind to warn trainers about asphalt heat, rain, or storms before field sessions.
* **✉️ Automated SMTP Emailing**: A robust email engine that sends beautifully branded HTML emails (with inline DogOps logos) for registrations, password resets, and account deletions.
* **🛡️ Security & Rate Limiting**: Employs `flask-limiter` to protect AI routes (5 requests/minute) and tracks login failures to prevent brute force attacks. Implements a strict 90-day password rotation policy and prevents recycling the last 3 passwords.

---

## 🏗 System Architecture

DogOps is built using modern cloud-native principles:

1. **Backend (Python / Flask)**: Provides a lightning-fast RESTful API. It utilizes `SQLAlchemy` as the ORM, seamlessly supporting both SQLite (for local dev) and PostgreSQL (for production).
2. **Frontend (Vanilla HTML/CSS/JS)**: A single-page application (SPA) featuring stunning **Glassmorphism** aesthetics. It includes responsive design, RTL (Right-to-Left) Hebrew support, and highly dynamic UI transitions.
3. **Containerization**: A highly optimized, multi-stage `Dockerfile` running Python 3.11-slim, ensuring minimal image size and attack surface.
4. **Kubernetes Native (Helm)**: The application is split into three independent Helm charts (`backend`, `frontend`, `postgres`) allowing for granular scaling and lifecycle management via GitOps.

---

## 📁 Repository Structure & Deep Dive

Here is a breakdown of the critical files and directories inside this repository:

### 1. `app.py`
The monolithic API entrypoint. It handles everything from database connections (`SQLAlchemy`), JWT token generation (`flask_jwt_extended`), AI model prompting (`google.generativeai`), to exposing Prometheus metrics.

### 2. `/frontend/`
Contains the entire UI stack. 
* `index.html`: The main dashboard featuring dynamic modals, weather widgets, and the AI chat interface.
* `style.css`: Implements the premium Glassmorphism design system, including frosted glass panels, modern gradients, and smooth hover animations.
* `assets/`: Contains critical brand assets like `dogsmailpic.png` used for inline email branding.

### 3. `/charts/`
The Kubernetes packaging directory.
* `backend/`: Helm chart containing Deployments, Services, and Ingress routes for the Python API.
* `frontend/`: Helm chart for serving the UI.
* `postgres/`: Helm chart for deploying the persistent database layer with StatefulSets and PVCs.

### 4. `.github/workflows/app-ci.yaml`
The backbone of our automated CI/CD pipeline. 
* **Build & Push**: Triggers on every push to `master`. It builds the multi-stage Docker image and pushes it to an AWS ECR registry, tagged with the exact Git SHA.
* **GitOps Trigger**: Automatically connects to the `devops-dogops-gitops` repository and makes a `[skip ci]` commit to update the Helm `values.yaml` with the new image tag, triggering an ArgoCD sync.

---

## 📊 Observability: Custom Prometheus Metrics

This application doesn't just log—it provides deep mathematical insights into its operation using `prometheus_flask_exporter`. The `/metrics` endpoint exposes several custom business metrics:

* 🟢 **`dogops_active_profiles` (Gauge)**: Tracks the real-time number of dog profiles registered in the system.
* 📈 **`dogops_behavior_events_total` (Counter)**: Tracks behavioral reports logged by trainers.
* ⏱️ **`dogops_ai_response_seconds` (Histogram)**: Measures the exact latency of the Gemini AI model to ensure trainers aren't waiting too long for advice.
* ⏱️ **`dogops_s3_upload_seconds` (Histogram)**: Tracks the network latency when uploading profile pictures to AWS S3.
* 🚨 **`dogops_login_failures_total` (Counter)**: Security metric that tracks failed authentication attempts to trigger automated brute-force alerts in Grafana.

---

## 🚀 Local Development Guide

Want to run DogOps locally? Follow these steps:

### Prerequisites
* Python 3.11+
* Docker Desktop
* AWS CLI (configured with appropriate S3 permissions)
* API Keys for Google (SSO), Microsoft (SSO), LinkedIn (SSO), and Gemini AI.

### Running Python Locally

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Export Environment Variables**:
   ```bash
   export FLASK_APP=app.py
   export GOOGLE_API_KEY="your_gemini_key"
   export JWT_SECRET_KEY="local-dev-secret"
   ```
3. **Run the Server**:
   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

### Running via Docker

To simulate the exact production environment locally:

```bash
docker build -t dogops-app:latest .
docker run -p 5000:5000 \
  -e AWS_REGION=us-east-1 \
  -e GOOGLE_API_KEY="your_gemini_key" \
  dogops-app:latest
```

---
*Built with ❤️ and best-in-class DevOps practices for DogOps.*