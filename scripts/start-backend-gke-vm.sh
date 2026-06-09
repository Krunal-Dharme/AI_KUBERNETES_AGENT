#!/usr/bin/env bash
# Run on GCP VM pipeline-demo where kubectl already works.
set -euo pipefail

cd "$(dirname "$0")/../backend"

export KUBECONFIG_PATH="${KUBECONFIG_PATH:-/home/kunudharme/.kube/config}"

if [ ! -f "$KUBECONFIG_PATH" ]; then
  echo "Kubeconfig not found at: $KUBECONFIG_PATH"
  exit 1
fi

echo "Using kubeconfig: $KUBECONFIG_PATH"
kubectl config get-contexts

python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
