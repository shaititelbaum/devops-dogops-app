# 🐾 DogOps - Core Application Repository

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.11-blue.svg) ![Docker](https://img.shields.io/badge/docker-ready-blue) ![Helm](https://img.shields.io/badge/helm-packaged-informational) ![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-orange) ![AWS](https://img.shields.io/badge/AWS-S3-yellow)

Welcome to the **DogOps Application Repository**. This is the heart of the DogOps ecosystem—a state-of-the-art, highly observable, and secure microservice designed specifically for professional dog trainers. 

This repository contains the complete source code for the Backend API, the Frontend UI, and the Kubernetes Helm packaging required to deploy the system into any cloud native environment.

---

## 📚 Self-Documenting Architecture
This codebase is engineered to be presentation-ready. Throughout the critical source files (e.g., `app.py`, `charts/backend/values.yaml`, `.github/workflows/app-ci.yaml`), you will find large **Architectural Block Comments** (marked with `=======`) detailing the "Why" and "How" behind major design decisions such as OpenTelemetry tracing, HPA auto-scaling, and GitOps CI/CD flows.

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
* **📊 OpenTelemetry Distributed Tracing**: Fully instrumented Python backend using OpenTelemetry to automatically generate detailed waterfall traces for Flask requests, SQLAlchemy database queries, and external API requests. Traces are exported to Grafana Tempo for deep observability.

---

## 🏗 System Architecture

DogOps is built using modern cloud-native principles:

1. **Backend (Python / Flask)**: Provides a lightning-fast RESTful API. It utilizes `SQLAlchemy` as the ORM, seamlessly supporting both SQLite (for local dev) and PostgreSQL (for production).
2. **Frontend (Vanilla HTML/CSS/JS)**: A single-page application (SPA) featuring stunning **Glassmorphism** aesthetics. It includes responsive design, RTL (Right-to-Left) Hebrew support, and highly dynamic UI transitions.
3. **Containerization**: A highly optimized, multi-stage `Dockerfile` running Python 3.11-slim, ensuring minimal image size and attack surface.
4. **Kubernetes Native (Helm)**: The application is packaged into a unified **Umbrella Chart** (`dogops-umbrella`) which manages the `backend`, `frontend`, and `postgres` sub-charts, allowing for atomic, cohesive deployments via GitOps.

---

## 📈 Dual-Engine Autoscaling Architecture

DogOps features a highly modular autoscaling design built directly into its Helm charts, allowing cluster administrators to seamlessly toggle between two powerful scaling engines depending on the environment's specific needs:

1. **Standard Autoscaling (HPA)**: 
   * **What it is:** The native Kubernetes Horizontal Pod Autoscaler.
   * **Why/When we use it:** This is the **default, primary strategy**. It watches pure CPU and Memory consumption. It is incredibly stable, requires zero overhead, and is the perfect baseline for normal HTTP web traffic bursts.
2. **Event-Driven Autoscaling (KEDA)**:
   * **What it is:** Kubernetes Event-driven Autoscaling, an enterprise CNCF project.
   * **Why/When we use it:** This is included as an advanced **"Show Off" / Toggle option**. KEDA replaces the standard HPA with a `ScaledObject` that can do things HPA cannot: **Scale to Zero**.
   * **How it works:** We configured KEDA to use a `Cron` scaler. In a staging environment, KEDA can scale the entire application down to zero pods at night to save cloud costs, and wake it up automatically the next morning.

**How to Toggle:** Administrators can simply flip `autoscaling.enabled=false` and `keda.enabled=true` in the `values.yaml` file, and GitOps handles the rest!

---

## 🌳 Complete Repository Tree

```text
📦 devops-dogops-app
 ┣ 📂 .github
 ┃ ┗ 📂 workflows
 ┃ ┃ ┗ 📜 app-ci.yaml
 ┣ 📂 charts
 ┃ ┣ 📂 backend
 ┃ ┣ 📂 frontend
 ┃ ┗ 📂 postgres
 ┣ 📂 frontend
 ┃ ┣ 📂 assets
 ┃ ┃ ┣ 🎵 dog-clicker.mp3
 ┃ ┃ ┣ 🎵 oops.mp3
 ┃ ┃ ┗ 🖼️ dogsmailpic.png
 ┃ ┣ 📜 Dockerfile
 ┃ ┣ 📜 index.html
 ┃ ┗ 📜 style.css
 ┣ 📜 Dockerfile
 ┣ 📜 README.md
 ┣ 📜 antigravity.md
 ┣ 📜 app.py
 ┣ 📜 docker-compose.yaml
 ┣ 📜 git-clean.sh
 ┗ 📜 requirements.txt
```

---

## 🔍 Deep-Dive Technical Specification

The following is an exhaustive file-by-file breakdown of the core systems that power DogOps.

### 🐍 `app.py` - The Monolithic Core (946 Lines of Code)
The backend is a robust Python 3.11 Flask application that consolidates multiple complex systems:

#### 🗄️ Relational Data Models (SQLAlchemy)
* **`User` Table**: Stores core identity. Includes critical security columns like `reset_code_expiry`, `last_password_change`, and `auth_provider` (`local`, `google`, `linkedin`, `microsoft`).
* **`PasswordHistory` Table**: A security table mapping `user_id` to `password_hash` to ensure users cannot recycle their last 3 passwords.
* **`DogProfile` Table**: Captures detailed canine metrics (`breed`, `dob`, `gender`, `status`, `chip`, `allergies`) along with the AWS S3 `image_url`.
* **`Todo` Table**: Represents the core "behavior log" allowing trainers to document specific events (Good/Bad), prioritize them (קל, בינוני, חשוב), and attach GPS links.
* **`Vaccine` Table**: Medical tracking for 6 primary vaccine types (משושה, כלבת, תולעת הפארק, etc.) including `expiry_date`.
* **`Summary` Table**: Stores AI-generated daily summaries (`is_auto=True`) of the dog's performance.

#### 🔐 SSO Authentication Flows
* **Google SSO**: Validates `Credential` tokens locally against the Google OAuth library (`id_token.verify_oauth2_token`).
* **LinkedIn & Microsoft**: Uses a robust redirect-and-callback flow. It requests an `authorization_code`, exchanges it for an `access_token` via `requests.post`, and pulls profile data dynamically from OpenID endpoints (`graph.microsoft.com` or `api.linkedin.com`).

#### ☁️ AWS S3 Garbage Collection
The `/api/profile/image` route uses `boto3`. Before uploading a new profile picture, the code uses `s3_client.list_objects_v2` with the `Prefix=user_{id}_profile` to discover old profile images and explicitly runs `delete_objects` to prevent storage bloat.

### 🎨 `frontend/index.html` & `style.css` - The UI Experience (2,182 Lines of Code)
The frontend is a colossal Single Page Application utilizing cutting-edge web APIs.

* **Audio Context API**: Preloads `dog-clicker.mp3` and `oops.mp3` utilizing `<audio preload="auto">` to provide instantaneous auditory feedback when a trainer logs a "Good Dog" or "Oops" event.
* **Glassmorphism Design (`style.css`)**: Built entirely without frameworks. Uses highly specific CSS properties (`backdrop-filter: blur(10px)`, `background: rgba(255,255,255,0.1)`, `box-shadow`) to create stunning, frosted-glass modals layered over a dynamic gradient background.
* **Dynamic Modals & DOM Manipulation**: The 2000+ line `index.html` orchestrates seamless tab switching (`dashboard`, `weather`, `mydog`, `history`, `vaccines`, `summaries`, `settings`) dynamically hiding and showing divs without a single page reload.
* **Complex Deletion Logic**: Features a highly guarded "Account Deletion" mechanism in the `settings-section`, requiring the user to re-enter their password and pass through two distinct, red-colored warning steps before executing the permanent `DELETE /api/account` call.

### ⚙️ `.github/workflows/app-ci.yaml` - The CI/CD Pipeline
This is not a simple build script. It is an advanced, dual-image, GitOps-triggering pipeline using **Reusable Composite Actions**.

* **GitHub Composite Action (`deploy-ecr-gitops`)**: To keep the pipeline strictly DRY, all Docker build, ECR push, and GitOps YAML patching logic is encapsulated in a reusable custom action.
* **Dual Parallel Builds**: The pipeline simultaneously processes the `backend` and `frontend` using the reusable action.
* **Umbrella Chart GitOps**: The pipeline dynamically builds images based on branch tags (e.g. `test-`, `staging-`) and uses `yq` to precisely patch the image tags within the `dogops-umbrella` values file in the GitOps repository. This securely delegates the actual deployment phase to ArgoCD.

---

## 📊 Observability: Custom Prometheus Metrics

This application doesn't just log—it provides deep mathematical insights into its operation using `prometheus_flask_exporter`. The `/metrics` endpoint exposes several custom business metrics:

* 🟢 **`dogops_active_profiles` (Gauge)**: Tracks the real-time number of dog profiles registered in the system.
* 📈 **`dogops_behavior_events_total` (Counter)**: Tracks behavioral reports logged by trainers.
* ⏱️ **`dogops_ai_response_seconds` (Histogram)**: Measures the exact latency of the Gemini AI model (`buckets=(0.5, 1.0, 2.0, 3.0, 5.0, inf)`) to ensure trainers aren't waiting too long for advice.
* ⏱️ **`dogops_s3_upload_seconds` (Histogram)**: Tracks the network latency when uploading profile pictures to AWS S3.
* 🚨 **`dogops_login_failures_total` (Counter)**: Security metric that tracks failed authentication attempts to trigger automated brute-force alerts in Grafana.

---

## 🚀 Local Development Guide

Want to run DogOps locally? Follow these steps:

### Prerequisites
* Python 3.11+
* Docker Desktop & Docker Compose (`docker-compose.yaml` handles local orchestration)
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

### Running via Docker Compose

To simulate the exact production environment locally:

```bash
docker-compose up --build -d
```

---
*Built with ❤️ and best-in-class DevOps practices for DogOps.*