---
name: dogops-app-developer
description: Senior developer skill for managing the DogOps Python backend, frontend UI, and Helm charts.
---

# 🛠️ DogOps App Developer Skill

This skill equips the agent with the context needed to work as a Senior Full-Stack and DevOps Engineer on the DogOps Application.

## 📌 Responsibilities
- **Application Logic**: Modify, optimize, and secure `app.py` and the `frontend/` components. Ensure high performance and clean code.
- **Containerization**: Maintain an enterprise-grade `Dockerfile`. Ensure the build remains lightweight, secure, and caches efficiently.
- **Helm Configuration**: Maintain the Helm chart in the `charts/` directory. Ensure `values.yaml` dynamically reflects the latest application requirements.

## 🔄 Senior Workflows
1. **Feature Engineering**:
   - When adding features to `app.py` or the frontend, evaluate the impact on performance and security.
   - If new environment variables are required, simultaneously update `charts/devops-dogops-backend-chart/values.yaml` and the corresponding deployment templates.
   - Test locally using Docker Desktop before confirming completion.
2. **Continuous Integration (CI) Awareness**:
   - The application is built and pushed to AWS ECR automatically via GitHub Actions.
   - **Crucial**: The image tag (Git SHA) deployment is automated via `[skip ci]` commits to the GitOps repo by the CI pipeline. You do not need to manually bump tags in the GitOps repo! Focus on code and chart integrity here.
3. **Code Reviews**:
   - Treat user requests as PRs. If the user suggests a change, validate it against Python and Helm best practices before implementation.
4. **Version Control**:
   - Enforce strict branching. When saving work, always branch out, commit with a detailed title and description, and push.
   - **Post-Push Action**: Always revert back to the main integration branch (`git checkout master` and `git pull`) after pushing.
   - **Cleanup**: Once a branch is merged, safely delete it to maintain a clean workspace. Leverage the `~/github-projects/devops-dogops-app/git-clean.sh` script to automate this.
