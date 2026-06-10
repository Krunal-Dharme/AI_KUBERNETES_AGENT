"""Resource-type-specific kubectl commands — never hallucinate unsupported verbs."""


def pod_commands(name: str, namespace: str) -> list[str]:
    return [
        f"kubectl describe pod {name} -n {namespace}",
        f"kubectl get events -n {namespace} --sort-by=.lastTimestamp",
        f"kubectl logs {name} -n {namespace}",
        f"kubectl get pod {name} -n {namespace} -o yaml",
    ]


def deployment_commands(name: str, namespace: str) -> list[str]:
    return [
        f"kubectl describe deployment {name} -n {namespace}",
        f"kubectl rollout status deployment/{name} -n {namespace}",
        f"kubectl get pods -n {namespace} -l app={name}",
        f"kubectl get deployment {name} -n {namespace} -o yaml",
    ]


def replicaset_commands(name: str, namespace: str) -> list[str]:
    return [
        f"kubectl describe replicaset {name} -n {namespace}",
        f"kubectl get pods -n {namespace} --show-labels",
        f"kubectl get replicaset {name} -n {namespace} -o yaml",
    ]


def service_commands(name: str, namespace: str) -> list[str]:
    return [
        f"kubectl describe service {name} -n {namespace}",
        f"kubectl get endpoints {name} -n {namespace}",
        f"kubectl get pods -n {namespace} --show-labels",
    ]


def ingress_commands(name: str, namespace: str) -> list[str]:
    return [
        f"kubectl describe ingress {name} -n {namespace}",
        f"kubectl get ingress {name} -n {namespace} -o yaml",
    ]


def node_commands(name: str) -> list[str]:
    return [
        f"kubectl describe node {name}",
        f"kubectl get pods -A --field-selector spec.nodeName={name}",
    ]
