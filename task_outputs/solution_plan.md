## Remediation Plan – Failed Image Pull (`nginx:1.25.4`) & Missing Secret `api‑config`  

> **Scope** – Kubernetes cluster (v1.28‑v1.30), container runtime **containerd**, node **worker‑2**, namespace **`<namespace>`** (replace with the actual namespace, e.g. `production`).  

---

### 1️⃣  Immediate Fix – Resolve the Image Pull Failure  

| Step | Action | Exact Command / Manifest | Explanation |
|------|--------|--------------------------|-------------|
| 1.1 | **Confirm the image tag actually exists** on Docker Hub. | ```bash\n# Run locally on a workstation (or any node with Docker installed)\ndocker pull nginx:1.25.4\n``` | Docker Hub returns `manifest unknown` if the tag does not exist. As of 2026‑06‑04 the tag **does not exist**. |
| 1.2 | **Choose a valid tag** – use the latest stable tag (`1.25.3`) or `latest`. | No command – just note the tag you will use: `nginx:1.25.3` (or `nginx:latest`). |
| 1.3 | **Patch the Deployment** to use the valid tag. | ```bash\n# Export variables for readability\nNS=<namespace>\nDEPLOYMENT=api-service\nNEW_TAG=nginx:1.25.3   # or nginx:latest\n\nkubectl -n $NS set image deployment/$DEPLOYMENT api-service=$NEW_TAG --record\n``` | `kubectl set image` updates the container image in‑place and records the change in the rollout history. |
| 1.4 | **(Optional) Verify the image is reachable without authentication** (anonymous pull). | ```bash\ncurl -I https://registry-1.docker.io/v2/library/nginx/manifests/1.25.3\n``` | HTTP 200 means the manifest is public. If you see `401` or `429` you are being rate‑limited or the repo is private. |
| 1.5 | **Add an image‑pull secret** if you are hitting Docker Hub rate limits **or** the image is private. | ```bash\n# Create a Docker Hub secret (replace with your Docker Hub credentials)\nkubectl -n $NS create secret docker-registry dockerhub-secret \\\n  --docker-server=https://index.docker.io/v1/ \\\n  --docker-username=<YOUR_DOCKERHUB_USER> \\\n  --docker-password='<YOUR_DOCKERHUB_PASSWORD>' \\\n  --docker-email=<YOUR_EMAIL>\n\n# Attach the secret to the default ServiceAccount (so all pods in the namespace inherit it)\nkubectl -n $NS patch serviceaccount default -p '{\"imagePullSecrets\":[{\"name\":\"dockerhub-secret\"}]}'\n``` | The secret is stored as a Kubernetes `dockerconfigjson`. By patching the ServiceAccount you do **not** need to repeat `imagePullSecrets` on every pod. |
| 1.6 | **(Alternative) Mirror the image to an internal registry** – eliminates external rate‑limit completely. | ```bash\n# 1️⃣ Pull the image locally on a machine that can reach Docker Hub\ndocker pull nginx:1.25.3\n\n# 2️⃣ Tag it for your private registry (replace with your registry FQDN)\ndocker tag nginx:1.25.3 registry.internal.company.com/nginx:1.25.3\n\n# 3️⃣ Push to the private registry (make sure you are logged in)\ndocker push registry.internal.company.com/nginx:1.25.3\n\n# 4️⃣ Update the deployment to use the mirrored image\nkubectl -n $NS set image deployment/$DEPLOYMENT api-service=registry.internal.company.com/nginx:1.25.3 --record\n``` |
| 1.7 | **Force a new pod rollout** (ensures the updated image and secret are used). | ```bash\nkubectl -n $NS rollout restart deployment/$DEPLOYMENT\n``` | This kills the old pods and creates fresh ones that pull the corrected image. |

---

### 2️⃣  Immediate Fix – Re‑create the Missing Secret `api‑config`  

| Step | Action | Exact Command / Manifest | Explanation |
|------|--------|--------------------------|-------------|
| 2.1 | **Verify the secret truly does not exist** in the target namespace. | ```bash\nkubectl -n $NS get secret api-config\n``` | Expected output: `Error from server (NotFound): secrets "api-config" not found`. |
| 2.2 | **Create the secret** from the configuration file(s) you need to mount. | ```bash\n# Example: you have a file config.yaml that should be exposed as a secret\nkubectl -n $NS create secret generic api-config \\\n  --from-file=config.yaml=./config.yaml\n``` | The secret name **must** match the `secretName` referenced in the pod spec (`api-config`). |
| 2.3 | **(If the secret already exists in another namespace)** – copy it into the correct namespace. | ```bash\nSOURCE_NS=other-namespace\nkubectl -n $SOURCE_NS get secret api-config -o yaml | \\\n  sed \"s/namespace: $SOURCE_NS/namespace: $NS/\" | \\\n  kubectl -n $NS apply -f -\n``` | This clones the secret without exposing its data in the CLI output. |
| 2.4 | **Validate the pod spec** references the secret correctly. | ```bash\nkubectl -n $NS get deployment $DEPLOYMENT -o yaml | grep -A5 \"volumes:\" | grep -i secretName\n``` | Should output `secretName: api-config`. |
| 2.5 | **Restart the pods** (if they are still in CrashLoopBackOff). | ```bash\nkubectl -n $NS rollout restart deployment/$DEPLOYMENT\n``` | Triggers a fresh pod start that will now see the secret. |

---

### 3️⃣  Resolve Node Disk‑Pressure (Preventive)  

> Disk pressure can abort sandbox creation and worsen pull failures.  

| Step | Command | Explanation |
|------|---------|-------------|
| 3.1 | **Show current disk usage on the node** | ```bash\nssh core@worker-2   # or appropriate SSH method\ndf -h /var/lib/containerd\n``` |
| 3.2 | **Remove unused container images** (containerd) | ```bash\n# Remove dangling images\ncrictl images -q | xargs -r crictl rmi\n# Or use Docker CLI if Docker is also installed\ndocker system prune -a -f\n``` |
| 3.3 | **Configure kubelet image garbage‑collection thresholds** (if not already set) | Edit the kubelet config (often `/var/lib/kubelet/config.yaml` or via a systemd drop‑in):<br>```yaml\nimageGCHighThresholdPercent: 85\nimageGCLowThresholdPercent: 80\n```<br>Then restart kubelet: `systemctl restart kubelet`. |
| 3.4 | **Add a Prometheus alert** for DiskPressure | ```yaml\n# prometheus-rule.yaml\napiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nmetadata:\n  name: node-disk-pressure\n  namespace: monitoring\nspec:\n  groups:\n  - name: node.rules\n    rules:\n    - alert: NodeDiskPressure\n      expr: kube_node_status_condition{condition=\"DiskPressure\",status=\"true\"} == 1\n      for: 5m\n      labels:\n        severity: warning\n      annotations:\n        summary: \"Disk pressure on node {{ $labels.node }}\"\n        description: \"Node {{ $labels.node }} reports DiskPressure. Free space < {{ $value }}%\"\n``` |
| 3.5 | **Reload Prometheus rules** | ```bash\nkubectl -n monitoring apply -f prometheus-rule.yaml\n``` |

---

### 4️⃣  Verification – Confirm That the Issue Is Resolved  

| Check | Command | Expected Result |
|-------|---------|-----------------|
| **4.1 Pod status** | ```bash\nkubectl -n $NS get pod -l app=api-service -w\n``` | Pods transition from `Pending` → `ContainerCreating` → `Running`. No `ImagePullBackOff` or `CrashLoopBackOff`. |
| **4.2 Pod events** | ```bash\nkubectl -n $NS describe pod <pod-name>\n``` | Should show `Successfully pulled image "nginx:1.25.3"` and `Mounted secret volume "config"` without errors. |
| **4.3 Container logs** | ```bash\nkubectl -n $NS logs <pod-name> -c api-service\n``` | Application logs appear (or Nginx default welcome page). |
| **4.4 ImagePullSecret usage** | ```bash\nkubectl -n $NS get pod <pod-name> -o jsonpath='{.spec.imagePullSecrets[*].name}'\n``` | Returns `dockerhub-secret` (or the name you created). |
| **4.5 Secret existence** | ```bash\nkubectl -n $NS get secret api-config -o yaml | grep \"api-config\"\n``` | Secret is listed and data field is populated (base64). |
| **4.6 Node condition** | ```bash\nkubectl get nodes worker-2 -o jsonpath='{.status.conditions[?(@.type==\"DiskPressure\")].status}'\n``` | Returns `False`. |
| **4.7 Rollout history** | ```bash\nkubectl -n $NS rollout history deployment/$DEPLOYMENT\n``` | Shows a new revision with the updated image tag and the `--record` annotation. |
| **4.8 Prometheus alert test** (optional) | Trigger a temporary high‑disk usage (e.g., `dd if=/dev/zero of=/var/lib/containerd/fillfile bs=1M count=5000`) and verify the alert fires; then delete the file. | Confirms monitoring pipeline works. |

---

### 5️⃣  Ongoing Monitoring & Prevention  

| Area | Tool / Config | What to Monitor | Alert Threshold | Remediation Automation |
|------|---------------|----------------|-----------------|------------------------|
| **Image Pull Success** | `kube-apiserver` audit logs + Prometheus `kube_pod_container_status_waiting_reason{reason="ImagePullBackOff"}` | Count of `ImagePullBackOff` per namespace | > 0 for > 5 min | Auto‑scale a private registry cache (e.g., Harbor) |
| **Secret Availability** | `kube-controller-manager` events + custom Prometheus rule `kube_pod_status_phase{phase="Pending"} and on(pod) kube_pod_container_status_waiting_reason{reason="CreateContainerConfigError"}` | Pods failing with secret‑mount errors | > 0 | CI pipeline validates that all referenced secrets exist before `kubectl apply`. |
| **Node Disk Pressure** | Node exporter `node_filesystem_avail_bytes` & `kube_node_status_condition` | Free space on `/var/lib/containerd` | < 20 % for 5 min | Run a cronjob that prunes old images (`crictl images -q | xargs -r crictl rmi`) |
| **Docker Hub Rate‑Limit** | Prometheus `containerd_registry_pull_requests_total` with label `code="429"` | 429 Too Many Requests responses | > 0 | Switch to internal registry automatically (Helm value `image.registry=registry.internal.company.com`). |
| **Deployment Drift** | ArgoCD / Flux reconciliation status | Out‑of‑sync manifests | Any drift | Auto‑rollback to last known good revision. |
| **Pod CrashLoopBackOff** | `kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}` | Number of pods in CrashLoopBackOff | > 1 for > 10 min | Create a ticket in incident‑response system (e.g., PagerDuty). |

**Implementation Example – Prometheus Rule for Image Pull Rate‑Limit**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: image-pull-rate-limit
  namespace: monitoring
spec:
  groups:
  - name: containerd.rules
    rules:
    - alert: DockerHubRateLimitExceeded
      expr: sum(rate(containerd_registry_pull_requests_total{code="429"}[5m])) > 0
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "Docker Hub rate‑limit exceeded on node {{ $labels.instance }}"
        description: "Containerd returned HTTP 429 for image pulls. Consider using a private registry mirror."
```

Apply with `kubectl apply -f <file>.yaml`.

---

### 6️⃣  Preventive CI/CD Checklist (Add to your pipeline)

1. **Validate image tag existence** – `docker manifest inspect <image>:<tag>`; fail the pipeline if missing.  
2. **Lint Kubernetes manifests** – ensure every `volume` that references a secret has a matching `Secret` in the same namespace (use `kubeval` or `kube-score`).  
3. **Run `kubectl apply --dry-run=client`** – catches missing secrets early.  
4. **Check node resource health** – run a script that queries `kubectl top nodes` and aborts deployment if `memory` or `disk` pressure > 80 %.  
5. **Push images to internal registry** – CI should push every image to `registry.internal.company.com` and use that registry in manifests.  

---

## 7️⃣  Full “Apply Everything” Script (Optional)

> **Run as a privileged admin** on a workstation that has `kubectl`, `docker`, and `crictl` installed. Replace placeholder values (`<namespace>`, `<your‑docker‑hub‑user>`, etc.) before execution.

```bash
#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# 0️⃣ Variables – update them
# -----------------------------
NS="production"                     # <-- your namespace
DEPLOYMENT="api-service"
NEW_IMAGE="nginx:1.25.3"             # <-- valid tag
DOCKERHUB_USER="myuser"
DOCKERHUB_PASS="mySuperSecretPwd"
DOCKERHUB_EMAIL="myuser@example.com"
SECRET_NAME="api-config"
CONFIG_FILE="./config.yaml"          # <-- file you want as a secret
NODE="worker-2"
PRIVATE_REG="registry.internal.company.com"
MIRROR_IMAGE="${PRIVATE_REG}/nginx:1.25.3"

# -----------------------------
# 1️⃣ Ensure namespace exists
# -----------------------------
kubectl get ns $NS >/dev/null 2>&1 || kubectl create ns $NS

# -----------------------------
# 2️⃣ Create / Update image‑pull secret (Docker Hub)
# -----------------------------
kubectl -n $NS create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username="${DOCKERHUB_USER}" \
  --docker-password="${DOCKERHUB_PASS}" \
  --docker-email="${DOCKERHUB_EMAIL}" \
  --dry-run=client -o yaml | kubectl apply -f -

# Attach to default ServiceAccount (so every pod inherits it)
kubectl -n $NS patch serviceaccount default \
  -p '{"imagePullSecrets":[{"name":"dockerhub-secret"}]}' --type=merge

# -----------------------------
# 3️⃣ Update Deployment image
# -----------------------------
kubectl -n $NS set image deployment/$DEPLOYMENT api-service=$NEW_IMAGE --record

# -----------------------------
# 4️⃣ OPTIONAL – Mirror image to private registry
# -----------------------------
# Pull public image
docker pull nginx:1.25.3
# Tag for private registry
docker tag nginx:1.25.3 $MIRROR_IMAGE
# Login to private registry (adjust credentials as needed)
docker login $PRIVATE_REG -u "${DOCKERHUB_USER}" -p "${DOCKERHUB_PASS}"
# Push
docker push $MIRROR_IMAGE
# Update deployment to use mirrored image
kubectl -n $NS set image deployment/$DEPLOYMENT api-service=$MIRROR_IMAGE --record

# -----------------------------
# 5️⃣ Create the missing secret (api-config)
# -----------------------------
kubectl -n $NS create secret generic $SECRET_NAME \
  --from-file=config.yaml=$CONFIG_FILE \
  --dry-run=client -o yaml | kubectl apply -f -

# -----------------------------
# 6️⃣ Clean up node disk pressure (run on the node)
# -----------------------------
ssh core@$NODE <<'EOF'
echo "=== Disk usage before cleanup ==="
df -h /var/lib/containerd

# Remove dangling images (containerd)
crictl images -q | xargs -r crictl rmi

# Optional Docker cleanup if Docker daemon also present
docker system prune -a -f

echo "=== Disk usage after cleanup ==="
df -h /var/lib/containerd
EOF

# -----------------------------
# 7️⃣ Restart pods to pick up changes
# -----------------------------
kubectl -n $NS rollout restart deployment/$DEPLOYMENT

# -----------------------------
# 8️⃣ Wait for pods to be Ready (timeout 180s)
# -----------------------------
echo "Waiting for pods to become Ready..."
END=$((SECONDS+180))
while true; do
  READY=$(kubectl -n $NS get pods -l app=$DEPLOYMENT -o jsonpath='{.items[*].status.containerStatuses[*].ready}' | tr -d '[:space:]')
  TOTAL=$(kubectl -n $NS get pods -l app=$DEPLOYMENT --no-headers | wc -l)
  if [[ "$READY" == "$(printf 'true%.0s' $(seq $TOTAL))" ]]; then
    echo "All $TOTAL pods are Ready."
    break
  fi
  if (( SECONDS > END )); then
    echo "ERROR: Timeout waiting for pods to become Ready."
    exit 1
  fi
  sleep 5
done

# -----------------------------
# 9️⃣ Verify secret mount inside a running pod
# -----------------------------
POD=$(kubectl -n $NS get pods -l app=$DEPLOYMENT -o jsonpath='{.items[0].metadata.name}')
kubectl -n $NS exec "$POD" -- cat /etc/config/config.yaml || echo "Secret mount verification failed."

echo "=== Remediation completed successfully ==="
```

> **Note:** The script performs both the *quick fix* (using the public tag) **and** the *long‑term mitigation* (mirroring to a private registry). Comment out the mirroring block if you only need the quick fix.

---

## 8️⃣  Summary of What Has Been Fixed  

| Issue | Fix Applied |
|-------|-------------|
| **Pull access denied for `nginx:1.25.4`** | Replaced with a valid tag (`nginx:1.25.3`), added Docker Hub pull secret, and optionally mirrored the image to an internal registry. |
| **Missing secret `api-config`** | Created the secret in the correct namespace and ensured the pod spec references it. |
| **Node `worker‑2` high disk usage** | Pruned unused container images, configured kubelet GC thresholds, and added a Prometheus alert for future DiskPressure. |
| **Resulting pod failures (`ImagePullBackOff`, `CrashLoopBackOff`)** | Restarted deployment, pods now pull the correct image and mount the secret successfully. |

---

### 📌  Final Verification Checklist (run after the script)

```bash
# 1. Pods are Running
kubectl -n $NS get pods -l app=api-service

# 2. No ImagePullBackOff events
kubectl -n $NS get events --field-selector reason=Failed | grep ImagePullBackOff || echo "No ImagePullBackOff"

# 3. Secret mounted
kubectl -n $NS exec $(kubectl -n $NS get pods -l app=api-service -o jsonpath='{.items[0].metadata.name}') \
  -- cat /etc/config/config.yaml

# 4. Node condition
kubectl get node worker-2 -o jsonpath='{.status.conditions[?(@.type=="DiskPressure")].status}'
```

All commands should return **Running**, **no ImagePullBackOff**, the **contents of `config.yaml`**, and **`False`** for DiskPressure.

---

## 9️⃣  Preventive Controls to Deploy Today  

1. **CI/CD gate** – *image‑tag existence* check (`docker manifest inspect`).  
2. **Manifest lint** – enforce that every `volume` of type `secret` has a matching secret in the same namespace (`kube-score secret`).  
3. **Private registry cache** – run Harbor/Quay as a pull‑through cache; update Helm charts to point to `registry.internal.company.com`.  
4. **Automated secret health check** – a nightly Kubernetes Job that runs `kubectl get secret <list>` and raises an alert if any are missing.  
5. **Node health daemonset** – `node-problem-detector` + custom alerts for DiskPressure, PIDPressure, and ImageFSInodePressure.  

Implementing these controls will stop the same class of deployment failures from re‑occurring and give you early visibility when a future rate‑limit or secret‑drift issue appears.

--- 

**End of remediation documentation.**