# DevOps Todo Application

This repository contains the multi-tier DevOps Todo application and its deployment configurations.

## Local Deployment & Validation (Step 3)

The Helm chart has been successfully validated and deployed locally inside a Kubernetes cluster using Docker Desktop.

### Prerequisites
* Docker Desktop with Kubernetes enabled
* Helm CLI installed
* AWS CLI configured with active permissions to ECR

### Deployment Steps

1. **Create the ECR Image Pull Secret**
   Since the backend image is hosted in a private AWS ECR repository, we inject a temporary authentication token into the cluster so Kubernetes can pull the container:
   ```bash
   kubectl create secret docker-registry ecr-registry-secret \
     --docker-server=480891637713.dkr.ecr.us-east-1.amazonaws.com \
     --docker-username=AWS \
     --docker-password=$(aws ecr get-login-password --region us-east-1)

2. **Deploy the Application via Helm**
   To avoid using the latest tag (which is bad practice in Production) and maintain immutability, we dynamically inject the specific Git Commit SHA tag during deployment using the --set flag:
   ```bash
     helm install devops-todo-backend ./devops-todo-backend-chart --set image.tag="6f68088d2e50695cf267217aedeb872d5fecbee4"

3. **Verify Deployment Status**
   Check that the Pod has successfully pulled the image and transitioned into a Running state:
   ```bash
     kubectl get pods