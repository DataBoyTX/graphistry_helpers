# Graphistry on Local Kubernetes (Ubuntu 22.04)

This guide provides step-by-step instructions for setting up a local Kubernetes cluster on Ubuntu 22.04 and deploying Graphistry using Helm charts.

## Prerequisites

- Ubuntu 22.04 LTS
- sudo privileges
- At least 8GB RAM (16GB+ recommended for Graphistry)
- At least 50GB free disk space
- NVIDIA GPU with drivers installed (for GPU-accelerated visualizations)
- DockerHub account with Graphistry image access (contact Graphistry for access)

## Overview

1. Install MicroK8s (lightweight Kubernetes)
2. Enable required addons (GPU, DNS, storage, ingress)
3. Install Longhorn for persistent storage
4. Install NGINX Ingress Controller
5. Deploy Graphistry using Helm

---

## Phase 1: Install MicroK8s

### 1.1 Install MicroK8s via Snap

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install MicroK8s (stable channel)
sudo snap install microk8s --classic --channel=1.28/stable

# Verify installation
microk8s status --wait-ready
```

### 1.2 Configure User Permissions

```bash
# Add current user to microk8s group
sudo usermod -aG microk8s $USER

# Change ownership of .kube directory
mkdir -p ~/.kube
sudo chown -R $USER ~/.kube

# Apply group changes (or logout/login)
newgrp microk8s
```

### 1.3 Set Up kubectl and Helm Aliases

```bash
# Add aliases to .bashrc for convenience
echo "alias kubectl='microk8s kubectl'" >> ~/.bashrc
echo "alias helm='microk8s helm3'" >> ~/.bashrc
source ~/.bashrc

# Alternatively, export kubeconfig for native kubectl/helm
microk8s config > ~/.kube/config
```

### 1.4 Verify Cluster Status

```bash
# Check cluster status
microk8s status

# Verify nodes are ready
kubectl get nodes

# Check cluster info
kubectl cluster-info
```

---

## Phase 2: Enable Required MicroK8s Addons

### 2.1 Enable Core Addons

```bash
# Enable DNS (required for service discovery)
microk8s enable dns

# Enable storage addon (hostpath storage)
microk8s enable storage

# Enable Helm3
microk8s enable helm3

# Enable ingress controller
microk8s enable ingress

# Enable dashboard (optional, for cluster monitoring)
microk8s enable dashboard
```

### 2.2 Enable GPU Support (Required for Graphistry)

**Note:** Ensure NVIDIA drivers are installed on the host first.

```bash
# Install NVIDIA drivers if not already installed
sudo apt install -y nvidia-driver-535  # or latest stable version
sudo reboot

# Verify NVIDIA drivers are working
nvidia-smi

# Enable GPU addon in MicroK8s
microk8s enable gpu

# Wait for GPU operator pods to be ready
kubectl wait --for=condition=ready pods -l app=nvidia-device-plugin-daemonset -n kube-system --timeout=300s

# Verify GPU is available in the cluster
kubectl get nodes -o json | jq '.items[].status.capacity'
# Should show "nvidia.com/gpu": "1" (or more)
```

### 2.3 Verify Addon Status

```bash
microk8s status

# Expected output should show enabled addons:
# - dns: enabled
# - storage: enabled
# - helm3: enabled
# - ingress: enabled
# - gpu: enabled
```

---

## Phase 3: Install Longhorn Storage (Recommended)

Longhorn provides distributed block storage for persistent volumes.

### 3.1 Install Longhorn Prerequisites

```bash
# Install iSCSI initiator (required by Longhorn)
sudo apt install -y open-iscsi nfs-common

# Start and enable iSCSI service
sudo systemctl enable iscsid
sudo systemctl start iscsid
```

### 3.2 Deploy Longhorn via Helm

```bash
# Add Longhorn Helm repository
helm repo add longhorn https://charts.longhorn.io
helm repo update

# Create namespace
kubectl create namespace longhorn-system

# Apply Longhorn iSCSI installation prerequisite
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/prerequisite/longhorn-iscsi-installation.yaml -n longhorn-system

# Install Longhorn
helm upgrade -i longhorn longhorn/longhorn --namespace longhorn-system

# Wait for Longhorn pods to be ready
kubectl wait --for=condition=ready pods --all -n longhorn-system --timeout=600s

# Verify Longhorn installation
kubectl get pods -n longhorn-system
```

### 3.3 Set Longhorn as Default StorageClass

```bash
# Check current storage classes
kubectl get storageclass

# Remove default annotation from microk8s-hostpath (if exists)
kubectl patch storageclass microk8s-hostpath -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'

# Set Longhorn as default
kubectl patch storageclass longhorn -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# Verify
kubectl get storageclass
# longhorn should show (default)
```

---

## Phase 4: Install NGINX Ingress Controller

### 4.1 Deploy NGINX Ingress

```bash
# Option A: Using MicroK8s addon (already enabled in Phase 2)
# The microk8s ingress addon uses NGINX by default

# Option B: Using Helm for more control
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Verify ingress controller is running
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

---

## Phase 5: Deploy Graphistry

### 5.1 Create Docker Registry Secret

You need DockerHub credentials with access to Graphistry images.

```bash
# Create namespace for Graphistry
kubectl create namespace graphistry

# Create Docker registry secret
kubectl create secret docker-registry docker-secret \
  --namespace graphistry \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=<YOUR_DOCKERHUB_USERNAME> \
  --docker-password=<YOUR_DOCKERHUB_TOKEN> \
  --docker-email=<YOUR_EMAIL>
```

### 5.2 Add Graphistry Helm Repository

```bash
# Add Graphistry Helm repo
helm repo add graphistry-helm https://graphistry.github.io/graphistry-helm/
helm repo update

# List available charts
helm search repo graphistry-helm
```

### 5.3 Get Node Hostname for NodeSelector

```bash
# Get node name
kubectl get nodes

# Get hostname label (use this in values.yaml)
kubectl get nodes -o jsonpath='{.items[0].metadata.labels.kubernetes\.io/hostname}'
```

### 5.4 Create values.yaml Override File

Create a `graphistry-values.yaml` file:

```yaml
# graphistry-values.yaml
# Graphistry Helm Chart values override for local MicroK8s deployment

global:
  # Set to your Graphistry version tag
  tag: "v2.39.28-admin"  # Update to latest version

  # Node selector - use hostname from Step 5.3
  nodeSelector:
    kubernetes.io/hostname: "<YOUR_NODE_HOSTNAME>"

  # Image pull policy
  imagePullPolicy: Always

  # Docker registry secret
  imagePullSecrets:
    - name: docker-secret

  # Storage provisioner (Longhorn)
  provisioner: driver.longhorn.io

# Storage class parameters for Longhorn
graphistryResources:
  storageClassParameters:
    numberOfReplicas: "1"  # Single replica for local dev
    staleReplicaTimeout: "30"

# Ingress configuration
ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
  hosts:
    - host: graphistry.local
      paths:
        - path: /
          pathType: Prefix

# Resource limits (adjust based on your hardware)
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "16Gi"
  requests:
    nvidia.com/gpu: 1
    memory: "8Gi"

# Domain configuration
domain: "graphistry.local"
```

### 5.5 Install Graphistry Resources Chart

**Important:** Install graphistry-resources first (contains StorageClasses).

```bash
# Install graphistry-resources (prerequisite)
helm upgrade -i graphistry-resources graphistry-helm/graphistry-resources \
  --namespace graphistry \
  --create-namespace

# Verify storage classes are created
kubectl get storageclass
```

### 5.6 Install Graphistry Main Chart

```bash
# Install Graphistry
helm upgrade -i graphistry graphistry-helm/Graphistry-Helm-Chart \
  --namespace graphistry \
  --values graphistry-values.yaml

# Watch deployment progress
kubectl get pods -n graphistry -w

# Wait for all pods to be ready (this may take several minutes)
kubectl wait --for=condition=ready pods --all -n graphistry --timeout=900s
```

### 5.7 Configure Local DNS

Add entry to `/etc/hosts` for local access:

```bash
# Get ingress IP
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.spec.clusterIP}')
echo "Ingress IP: $INGRESS_IP"

# For MicroK8s with NodePort, use node IP instead
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo "Node IP: $NODE_IP"

# Add to /etc/hosts
echo "$NODE_IP graphistry.local" | sudo tee -a /etc/hosts
```

---

## Phase 6: Verify Deployment

### 6.1 Check All Resources

```bash
# Check all Graphistry pods
kubectl get pods -n graphistry

# Check services
kubectl get svc -n graphistry

# Check ingress
kubectl get ingress -n graphistry

# Check PVCs
kubectl get pvc -n graphistry

# Check logs if needed
kubectl logs -n graphistry <pod-name>
```

### 6.2 Access Graphistry UI

```bash
# Get the ingress endpoint
kubectl get ingress -n graphistry

# Or get the service NodePort
kubectl get svc -n graphistry

# Access via browser
# http://graphistry.local (if using ingress)
# or http://<NODE_IP>:<NODEPORT> (if using NodePort)
```

---

## Troubleshooting

### Common Issues

**GPU not detected:**
```bash
# Check if NVIDIA drivers are installed
nvidia-smi

# Check GPU operator status
kubectl get pods -n kube-system | grep nvidia

# Describe GPU node
kubectl describe node | grep -A5 "Capacity"
```

**Pods stuck in Pending:**
```bash
# Check events
kubectl describe pod <pod-name> -n graphistry

# Check node resources
kubectl describe nodes | grep -A5 "Allocated resources"
```

**Storage issues:**
```bash
# Check PVC status
kubectl get pvc -n graphistry

# Check Longhorn status
kubectl get pods -n longhorn-system

# Access Longhorn UI (if enabled)
kubectl port-forward svc/longhorn-frontend 8080:80 -n longhorn-system
# Open http://localhost:8080
```

**Image pull errors:**
```bash
# Verify secret exists
kubectl get secrets -n graphistry

# Check secret contents
kubectl describe secret docker-secret -n graphistry

# Test pulling image manually
docker login
docker pull graphistry/graphistry-nvidia:<tag>
```

### Reset Cluster (if needed)

```bash
# Stop MicroK8s
microk8s stop

# Reset to clean state (WARNING: destroys all data)
microk8s reset

# Start fresh
microk8s start
```

---

## Useful Commands Reference

```bash
# MicroK8s status
microk8s status

# Enable/disable addons
microk8s enable <addon>
microk8s disable <addon>

# Helm operations
helm list -n graphistry
helm upgrade -i <release> <chart> -n <namespace> --values values.yaml
helm uninstall <release> -n <namespace>
helm history <release> -n <namespace>

# Pod debugging
kubectl logs -f <pod-name> -n graphistry
kubectl exec -it <pod-name> -n graphistry -- /bin/bash
kubectl describe pod <pod-name> -n graphistry

# Resource monitoring
kubectl top nodes
kubectl top pods -n graphistry
```

---

## References

- [Graphistry Helm Documentation](https://graphistry-helm.readthedocs.io/en/latest/)
- [Graphistry Helm GitHub](https://github.com/graphistry/graphistry-helm)
- [MicroK8s Documentation](https://microk8s.io/docs)
- [Longhorn Documentation](https://longhorn.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
