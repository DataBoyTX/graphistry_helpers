# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository contains documentation and tooling for deploying Graphistry on local Kubernetes (MicroK8s) with Ubuntu 22.04. It includes deployment guides, subagent configurations, and operational runbooks.

## Key Commands

### Kubernetes Operations (MicroK8s)

```bash
# Cluster management
microk8s status
microk8s start / microk8s stop
microk8s reset  # WARNING: destroys all data

# Use kubectl and helm aliases (or configure ~/.kube/config)
alias kubectl='microk8s kubectl'
alias helm='microk8s helm3'
```

### Graphistry Deployment

```bash
# Deploy Graphistry resources (required first)
helm upgrade -i graphistry-resources graphistry-helm/graphistry-resources \
  --namespace graphistry --create-namespace

# Deploy Graphistry
helm upgrade -i graphistry graphistry-helm/Graphistry-Helm-Chart \
  --namespace graphistry --values graphistry-values.yaml

# Monitor deployment
kubectl get pods -n graphistry -w
kubectl wait --for=condition=ready pods --all -n graphistry --timeout=900s
```

### Troubleshooting

```bash
# Check GPU availability
nvidia-smi
kubectl get nodes -o json | jq '.items[].status.capacity'

# Check storage
kubectl get pvc -n graphistry
kubectl get pods -n longhorn-system

# View pod logs
kubectl logs -f <pod-name> -n graphistry
kubectl describe pod <pod-name> -n graphistry
```

## Architecture

### Deployment Stack

- **Kubernetes**: MicroK8s 1.28 (lightweight single-node)
- **Storage**: Longhorn distributed block storage
- **Ingress**: NGINX Ingress Controller
- **GPU**: NVIDIA GPU Operator for CUDA workloads
- **Application**: Graphistry visualization platform (Helm charts)

### Required MicroK8s Addons

- `dns` - Service discovery
- `storage` - Hostpath storage fallback
- `helm3` - Helm package manager
- `ingress` - NGINX ingress
- `gpu` - NVIDIA GPU support

## Subagents

The `subagents/` directory contains specialized agent configurations:

- **build-validator.md** - Node.js build validation pipeline (clean, install, lint, test, build)
- **code-architect.md** - Architectural review checklist for PRs
- **code-simplifier.md** - Code refactoring guidelines without behavior changes
- **oncall-guide.md** - Incident response framework (SEV1-4 classification, runbooks)
- **verify-app.md** - End-to-end application verification workflow

## MCP Servers

Configured in `.mcp.json`:
- `memory` - Persistent memory across sessions
- `fetch` - Web content and API fetching
- `github` - GitHub repository interaction (requires GITHUB_TOKEN)

## External References

- [Graphistry Helm Charts](https://github.com/graphistry/graphistry-helm)
- [Graphistry Helm Docs](https://graphistry-helm.readthedocs.io/en/latest/)
- [MicroK8s Docs](https://microk8s.io/docs)
- [Longhorn Docs](https://longhorn.io/docs/)
