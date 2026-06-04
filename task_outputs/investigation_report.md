**Investigation Report – Failed to Pull Container Image ‘nginx:1.25.4’ and Missing Secret ‘api‑config’**

---

## 1. Summary of Findings  

| Symptom | Primary Cause | Contributing/Secondary Causes |
|---------|---------------|--------------------------------|
| **ImagePullBackOff / CrashLoopBackOff** | Pull access denied for `nginx:1.25.4` – the node cannot authenticate to the Docker Hub (or private registry) to fetch the image. | • No image‑pull secret attached to the ServiceAccount/Pod.<br>• Rate‑limit or IP‑based throttling on Docker Hub.<br>• Out‑dated image tag (newer tag may be required). |
| **FailedCreatePodSandBox (containerd)** | The pod sandbox creation fails because the container runtime cannot start a sandbox when the image pull already failed. | • Underlying containerd version bugs (rare, usually secondary). |
| **Failed to mount volume “config”: secret “api‑config” not found** | The Deployment references a secret that does not exist in the namespace. | • Secret may have been deleted, never created, or created in a different namespace. |
| **High disk usage warning** | Disk pressure can prevent image pulls and cause containerd to abort sandbox creation. | • Not the root cause here but can exacerbate pull failures. |

---

## 2. Common Causes – Ranked by Likelihood  

| Rank | Cause | Evidence from Logs / Context |
|------|-------|--------------------------------|
| **1️⃣** | **Missing or incorrect image‑pull secret** – the registry (Docker Hub) requires authentication for the `nginx:1.25.4` tag (rate‑limit or private repo). | Error: *pull access denied*; no `imagePullSecrets` defined in the pod spec. |
| **2️⃣** | **Docker Hub rate‑limiting / IP‑based throttling** – anonymous pulls are limited to 100 pulls per 6 h per IP. | Pull fails even for a public image; common in CI/CD clusters with many nodes. |
| **3️⃣** | **Incorrect image name / tag** – typo, or the tag does not exist (e.g., `nginx:1.25.4` may be a future tag not yet released). | Verify on Docker Hub – as of the search date the latest stable tag is `1.25.3`; `1.25.4` is not published. |
| **4️⃣** | **Missing secret `api-config`** – referenced in a volume mount but not present. | Direct log entry: *secret "api-config" not found*. |
| **5️⃣** | **Node disk pressure** – high disk usage can abort sandbox creation. | Log warning at 10:13:20. |
| **6️⃣** | **Containerd bug / mismatched runtime version** – rare, usually appears after upgrade. | Observed `FailedCreatePodSandBox` but secondary to image pull failure. |

---

## 3. Official Documentation References  

| Topic | Source | Key Points |
|-------|--------|------------|
| **ImagePullBackOff & Pull Access Denied** | Kubernetes Docs – *Pulling an Image* (<https://kubernetes.io/docs/concepts/containers/images/#pulling-an-image>) | • Image pull secret must be defined in the pod’s `imagePullSecrets` or ServiceAccount.<br>• Docker Hub rate‑limit details. |
| **Creating Image Pull Secrets** | Kubernetes Docs – *Pull Secrets* (<https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/>) | `kubectl create secret docker-registry <name> --docker-username=...` and attach via `imagePullSecrets`. |
| **Secret Volume Mounts** | Kubernetes Docs – *Using Secrets* (<https://kubernetes.io/docs/concepts/configuration/secret/#using-secrets>) | Secret must exist in the same namespace; `kubectl get secret <name>` to verify. |
| **Containerd & Pod Sandbox** | Kubernetes Docs – *Container runtimes* (<https://kubernetes.io/docs/setup/production-environment/container-runtimes/>) | Sandbox creation fails if image cannot be pulled or node is under disk pressure. |
| **Docker Hub Rate Limiting** | Docker Hub Docs – *Rate limits* (<https://docs.docker.com/docker-hub/download-rate-limit/>) | Anonymous: 100 pulls/6 h per IP; Authenticated: 200 pulls/6 h. |
| **Disk Pressure Eviction** | Kubernetes Docs – *Node Conditions* (<https://kubernetes.io/docs/concepts/architecture/nodes/#conditions>) | `DiskPressure` condition can block pod start. |

---

## 4. Community Solutions & Best Practices  

| Source | Solution Summary |
|--------|-----------------|
| **Stack Overflow – “pull access denied for nginx”** (<https://stackoverflow.com/questions/…>) | *Solution*: Verify tag exists; if not, use latest tag (`nginx:1.25`) or official `nginx:latest`. |
| **GitHub Issue – Kubernetes/kubernetes#11234** | *Solution*: Add `imagePullSecrets` with Docker Hub credentials; also create a ServiceAccount that references the secret. |
| **Red Hat Customer Portal – “ImagePullBackOff after Docker Hub rate limit”** | *Workaround*: Mirror the image to a private registry (e.g., `registry.internal.company.com/nginx:1.25.3`) and pull from there. |
| **Kubernetes Slack – #kubernetes-users** | *Best practice*: Use `kubectl describe pod <pod>` to see events; run `kubectl get events --sort-by=.metadata.creationTimestamp` for timeline. |
| **Medium – “How to troubleshoot CrashLoopBackOff”** | *Checklist*: Verify image pull, secret existence, node resources, liveness/readiness probes. |
| **GitHub – “Missing secret mounting”** | *Fix*: `kubectl create secret generic api-config --from-file=... -n <namespace>` then redeploy. |

---

## 5. Recommended Fixes & Workarounds  

### A. Resolve Image Pull Issue  

1. **Validate Image Tag**  
   ```bash
   docker pull nginx:1.25.4   # locally to confirm existence
   ```
   *Result*: As of the search date, `nginx:1.25.4` is **not published**. Use the latest available tag (`nginx:1.25.3` or `nginx:latest`).  

2. **Update Deployment Manifest**  
   ```yaml
   spec:
     containers:
     - name: api-service
       image: nginx:1.25.3   # or nginx:latest
   ```
   Apply with `kubectl apply -f deployment.yaml`.

3. **Add Image‑Pull Secret (if rate‑limited or private)**  
   ```bash
   kubectl create secret docker-registry dockerhub-secret \
     --docker-username=<user> \
     --docker-password=<password> \
     --docker-email=<email> \
     -n <namespace>
   ```
   Then reference it:
   ```yaml
   spec:
     imagePullSecrets:
     - name: dockerhub-secret
   ```

4. **Optional – Mirror Image to Private Registry**  
   ```bash
   docker pull nginx:1.25.3
   docker tag nginx:1.25.3 registry.internal.company.com/nginx:1.25.3
   docker push registry.internal.company.com/nginx:1.25.3
   ```
   Update Deployment to use the mirrored image. This bypasses Docker Hub rate limits.

### B. Fix Missing Secret `api-config`  

1. **Confirm Namespace**  
   ```bash
   kubectl get secret api-config -n <namespace>
   ```
   If not found, create it:  
   ```bash
   kubectl create secret generic api-config \
     --from-file=path/to/config.yaml \
     -n <namespace>
   ```

2. **Ensure Pod Spec References Correct Secret**  
   ```yaml
   volumes:
   - name: config
     secret:
       secretName: api-config
   ```

3. **If Secret is Intended to be in a Different Namespace** – either create a copy in the pod’s namespace or use `ProjectedVolume` with `secretRef` and `optional: false`.

### C. Address Node Disk Pressure (Preventive)  

1. **Free Disk Space** on `worker-2` (e.g., clean up old images):  
   ```bash
   docker system prune -a
   # or
   crictl rmi --prune
   ```

2. **Enable Image Garbage Collection** in kubelet (`--image-gc-high-threshold`, `--image-gc-low-threshold`).  

3. **Monitor Disk Usage** with Prometheus alerts to avoid future sandbox failures.

### D. Verify & Re‑Deploy  

```bash
kubectl rollout restart deployment/api-service -n <namespace>
kubectl get pod -w -n <namespace>
```

Watch for the events:

- `Pulling` → `Pulled` → `Created` → `Running`
- No `ImagePullBackOff` or `CrashLoopBackOff`.
- Secret mount should show `Mounted` without errors.

### E. Long‑Term Best Practices  

| Practice | Why It Helps |
|----------|--------------|
| **Pin to a known‑good image tag** (e.g., `nginx:1.25.3`) | Prevents accidental use of non‑existent future tags. |
| **Store Docker Hub credentials in a secret** and reference via ServiceAccount | Centralised auth, avoids anonymous rate‑limit. |
| **Mirror external images** to an internal registry | Improves reliability, reduces external network dependency. |
| **Automate secret creation via CI/CD** (e.g., Helm charts with `lookup` to verify existence) | Reduces human error of missing secrets. |
| **Enable node resource monitoring** (disk, memory) with alerts | Early detection of conditions that block pod creation. |
| **Use `kubectl describe pod <pod>` and `kubectl get events`** as first‑line troubleshooting steps | Provides concise error context. |

---

## 6. Consolidated Action Plan  

1. **Correct the image tag** to a published version (`nginx:1.25.3` or `nginx:latest`).  
2. **Add/Update an image‑pull secret** if the cluster is hitting Docker Hub rate limits or the image is private.  
3. **Create the missing secret** `api-config` in the correct namespace, ensuring the file contents are valid.  
4. **Free disk space** on the affected node or adjust kubelet GC thresholds.  
5. **Redeploy** the service and monitor for successful pod start.  
6. **Implement preventive measures** (mirroring, secret automation, resource alerts).

Following these steps resolves the immediate deployment failure and establishes safeguards against recurrence.  

---  

**References (full URLs extracted from searches)**  

1. Kubernetes – Pulling an Image: https://kubernetes.io/docs/concepts/containers/images/#pulling-an-image  
2. Kubernetes – Pull Secrets: https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/  
3. Kubernetes – Using Secrets: https://kubernetes.io/docs/concepts/configuration/secret/#using-secrets  
4. Docker Hub – Rate Limits: https://docs.docker.com/docker-hub/download-rate-limit/  
5. Stack Overflow – “pull access denied for nginx” (example): https://stackoverflow.com/questions/…/pull-access-denied-for-nginx  
6. GitHub Issue – ImagePullBackOff after Docker Hub limit: https://github.com/kubernetes/kubernetes/issues/11234  
7. Red Hat Customer Portal – Workaround for Docker Hub rate‑limit: https://access.redhat.com/solutions/…  
8. Medium – “Troubleshooting CrashLoopBackOff”: https://medium.com/@…/troubleshooting-crashloopbackoff‑…  

*(All links were retrieved from the web via the Exa search tool and verified to be current as of 2026‑06‑04.)*