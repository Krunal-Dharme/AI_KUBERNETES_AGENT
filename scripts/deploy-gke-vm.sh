#!/usr/bin/env bash
# Deploy on GCP VM pipeline-demo (where kubectl already works).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

KUBECONFIG_PATH="${KUBECONFIG_PATH:-/home/kunudharme/.kube/config}"

if [ ! -f "$KUBECONFIG_PATH" ]; then
  echo "ERROR: kubeconfig not found at $KUBECONFIG_PATH"
  exit 1
fi

echo "Kubeconfig: $KUBECONFIG_PATH"
kubectl config get-contexts

echo "Starting stack with GKE volume mounts..."
docker compose -f docker-compose.yml -f docker-compose.gke.yml up --build -d

echo ""
echo "Backend:  http://$(curl -s -H Metadata-Flavor:Google http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || hostname -I | awk '{print $1}'):8000/health"
echo "Frontend: http://$(curl -s -H Metadata-Flavor:Google http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || hostname -I | awk '{print $1}'):3000"
echo "Clusters: curl -s http://localhost:8000/clusters | jq"
