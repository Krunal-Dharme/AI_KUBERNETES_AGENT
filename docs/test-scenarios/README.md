# Kubernetes Failure Test Scenarios

Deploy these manifests on your GKE cluster to test the AI Kubernetes Agent.

**Namespace:** `ai-agent-test`

```bash
kubectl create namespace ai-agent-test
```

## Scenario 1 — CrashLoopBackOff (missing env var)

```bash
kubectl apply -f 01-crashloop-missing-env.yaml
kubectl get pods -n ai-agent-test -w
```

**Expected diagnosis:** Missing environment variable

**Cleanup:**
```bash
kubectl delete -f 01-crashloop-missing-env.yaml
```

## Scenario 2 — ImagePullBackOff (wrong image tag)

```bash
kubectl apply -f 02-imagepull-wrong-tag.yaml
```

**Expected diagnosis:** Invalid image tag

## Scenario 3 — OOMKilled (low memory limit)

```bash
kubectl apply -f 03-oom-low-memory.yaml
```

**Expected diagnosis:** Container exceeded memory limit

## Scenario 4 — Service Selector Mismatch

```bash
kubectl apply -f 04-service-selector-mismatch.yaml
```

**Expected diagnosis:** Service selector does not match pod labels

## Run Investigation

1. Open the dashboard
2. Select your GKE cluster context
3. Click **Investigate Cluster**
4. Review root cause and suggested fix

## Cleanup All

```bash
kubectl delete namespace ai-agent-test
```
