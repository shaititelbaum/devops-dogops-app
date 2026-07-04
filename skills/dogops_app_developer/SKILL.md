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
   - **Review First**: ALWAYS present the code changes to the user for review before committing or pushing.
   - **Manual Push Trigger**: DO NOT automatically push. Only push when the user explicitly commands you to push.
   - **Pre-Push Sync**: Always run `git pull` on the branch before pushing to avoid conflicts.
   - **Post-Push Action**: Do nothing after pushing.
   - **Cleanup**: When the user informs you a PR is merged, execute `~/github-projects/devops-dogops-app/git-clean.sh` to safely prune branches.
5. **Documentation Lifecycle**:
   - Automatically update `README.md` when proposing new features.
   - Always ask for user approval on documentation changes before committing.
