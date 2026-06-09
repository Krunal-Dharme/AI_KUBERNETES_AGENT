from kubernetes.executor import KubectlResult, summarize_stderr


def friendly_kubectl_error(result: KubectlResult) -> str:
    message = summarize_stderr(result.stderr)

    if "not found" in message.lower() and "kubectl" in message.lower():
        return (
            "kubectl is not installed or not in PATH. "
            "Install kubectl on the backend server."
        )

    if "gke-gcloud-auth-plugin" in message.lower() or "exec" in message.lower():
        return (
            "GKE authentication failed. Please verify:\n"
            "- gcloud is logged in (gcloud auth login)\n"
            "- gke-gcloud-auth-plugin is installed\n"
            "- kubeconfig is valid"
        )

    if "connection refused" in message.lower() or "unable to connect" in message.lower():
        return (
            "Unable to connect to the Kubernetes cluster.\n\n"
            "Please verify:\n"
            "- KUBECONFIG_PATH points to the correct file\n"
            "- The cluster is running and reachable\n"
            "- gke-gcloud-auth-plugin is installed\n"
            "- You selected the correct cluster context"
        )

    if "forbidden" in message.lower() or "unauthorized" in message.lower():
        return (
            "Kubernetes authorization failed.\n\n"
            "Your account does not have permission to access this cluster. "
            "Check RBAC roles and GKE IAM permissions."
        )

    if "permission denied (publickey)" in message.lower():
        return (
            "SSH authentication to the GCP VM failed.\n\n"
            "Either:\n"
            "1) Run the backend on pipeline-demo (recommended):\n"
            "   docker compose -f docker-compose.yml -f docker-compose.gke.yml up --build\n"
            "2) Configure SSH key access from this machine to kunudharme@34.47.189.50"
        )

    if "no such file" in message.lower() or "kubeconfig" in message.lower():
        return (
            "Kubeconfig file not found.\n\n"
            "Set KUBECONFIG_PATH in backend/.env to your kubeconfig file, "
            "e.g. /home/kunudharme/.kube/config"
        )

    if "timed out" in message.lower():
        return (
            "Connection to the Kubernetes cluster timed out.\n\n"
            "The cluster may be unreachable or overloaded. Try again shortly."
        )

    return message or "Kubernetes command failed. Check backend logs for details."


def missing_kubeconfig_message() -> str:
    return (
        "Kubeconfig is not configured.\n\n"
        "Set KUBECONFIG_PATH in backend/.env, for example:\n"
        "KUBECONFIG_PATH=/home/kunudharme/.kube/config"
    )
