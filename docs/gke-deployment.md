# GKE Deployment (pipeline-demo VM)

## Root cause

Cluster discovery failed because:

1. **Docker Compose override bug** — `docker-compose.yml` set `KUBECONFIG_PATH=${KUBECONFIG_PATH:-}`, which overwrote `backend/.env` with an **empty string** when the host shell did not define `KUBECONFIG_PATH`.
2. **Architecture mismatch** — The kubeconfig lives on the GCP VM at `/home/kunudharme/.kube/config`. A backend running on Windows (or in Docker on Windows) cannot read that Linux path unless the file is mounted or kubectl runs on the VM.

## Recommended: run on pipeline-demo

On the VM where `kubectl get pods -A` already works:

```bash
git clone <repo> && cd AI_KUBERNETES_AGENT
cp backend/.env.example backend/.env   # add OPENROUTER_API_KEY
chmod +x scripts/deploy-gke-vm.sh
./scripts/deploy-gke-vm.sh
```

Or manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.gke.yml up --build
```

This mounts:

- `/home/kunudharme/.kube/config` → `/kube/config`
- `/home/kunudharme/.config/gcloud` → `/root/.config/gcloud` (for `gcloud` + `gke-gcloud-auth-plugin`)

The GKE image installs `google-cloud-cli`, `kubectl`, and `gke-gcloud-auth-plugin`.
Startup fails fast if `gcloud auth list` or `kubectl get nodes` does not succeed.

Verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/clusters
```

Open the UI at `http://34.47.189.50:3000`.

## Windows development (optional)

If you run the backend locally on Windows, set in `backend/.env`:

```env
KUBECTL_SSH_HOST=kunudharme@34.47.189.50
KUBECTL_SSH_KUBECONFIG=/home/kunudharme/.kube/config
```

Requires SSH key access to the VM. Without keys, run the backend on the VM instead.

## Native backend on VM (no Docker)

```bash
./scripts/start-backend-gke-vm.sh
```

Point the frontend at `http://34.47.189.50:8000` via `NEXT_PUBLIC_API_BASE_URL`.
