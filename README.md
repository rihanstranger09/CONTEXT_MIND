# Scalable Microservice Deployment using Docker, Kubernetes and Helm

A complete, classroom-ready deployment project: a **Streamlit task board** talks to a **Flask REST API**, which stores tasks in **PostgreSQL**. Docker Compose runs the stack locally; raw Kubernetes manifests and a parameterized Helm chart deploy the same services to a cluster.

> **Demo project, not a production database setup.** Change the example database password before deploying. For real environments use managed PostgreSQL, externally managed secrets, TLS/Ingress, backups, and image tags pinned to immutable digests.

## Architecture

```text
Browser ──> Streamlit frontend (8501)
                 │ API_URL
                 ▼
         Flask backend (5000) ──> PostgreSQL (5432)
                 │                     │
            ClusterIP service      PVC / Compose volume
```

- **Frontend:** Streamlit UI to add, list, complete, and delete tasks.
- **Backend:** Flask JSON API with database-aware readiness and process liveness endpoints.
- **Database:** PostgreSQL 16, persistent storage in Compose and Kubernetes.
- **Containers:** separate, slim Python images; application processes run as non-root.
- **Kubernetes:** frontend NodePort, backend/database ClusterIP, health probes and CPU/memory requests and limits.
- **Helm:** replica counts, images, resource sizing, storage, service ports and DB settings are configurable in `scalable-app-chart/values.yaml`.

## Repository layout

```text
backend/                 Flask API and Dockerfile
frontend/                Streamlit UI and Dockerfile
docker-compose.yml       Local three-container stack
k8s/                     Direct Kubernetes manifests
scalable-app-chart/      Helm chart (templates + values)
tests/                   Lightweight API validation tests
```

## Run locally with Docker Compose

Requirements: Docker Engine and the Docker Compose plugin.

```bash
docker compose up --build
```

Open **http://localhost:8501**. Compose waits for PostgreSQL and the API health checks before starting dependent services. Stop with `Ctrl+C`; remove containers with `docker compose down`. Data remains in the named `postgres_data` volume. To start with a clean database, run `docker compose down -v` (this permanently deletes local task data).

Optional local overrides can be placed in a root `.env` file (not committed):

```dotenv
POSTGRES_DB=tasks
POSTGRES_USER=appuser
POSTGRES_PASSWORD=replace-with-a-long-random-value
FRONTEND_PORT=8501
```

The compose file's default credential is intentionally convenient for a local demonstration only. Never reuse it outside a disposable local environment.

## REST API

The API is reachable from the Compose network at `http://backend:5000` and inside a cluster via the backend Service. Routes:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check (process is responding) |
| `GET` | `/ready` | Readiness check (PostgreSQL is reachable) |
| `GET` | `/api/tasks` | List tasks |
| `POST` | `/api/tasks` | Create task: `{"title":"Ship it","description":"Optional"}` |
| `PATCH` | `/api/tasks/{id}` | Set completion: `{"completed":true}` |
| `DELETE` | `/api/tasks/{id}` | Delete task |

Example:

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Deploy the app","description":"Try the Helm chart"}'
```

Compose publishes the API at `http://localhost:5000` for local development; the database port remains private to the Compose network.

## Build and run the containers separately

```bash
docker build -t scalable-app-backend:latest ./backend
docker build -t scalable-app-frontend:latest ./frontend
```

The frontend expects `API_URL` (default `http://localhost:5000`); when containers run together, set it to the backend's reachable service name. The backend accepts either `DATABASE_URL` or `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`.

## Kubernetes: raw manifests

Requirements: `kubectl`, a running Kubernetes cluster, and a default StorageClass (or edit `k8s/01-postgres.yaml` for your environment). Build and make images available to the cluster first.

For **Kind**, load images after building:

```bash
docker build -t scalable-app-backend:latest ./backend
docker build -t scalable-app-frontend:latest ./frontend
kind load docker-image scalable-app-backend:latest scalable-app-frontend:latest
```

For **Minikube**, instead build directly in its Docker daemon before applying:

```bash
eval "$(minikube docker-env)"
docker build -t scalable-app-backend:latest ./backend
docker build -t scalable-app-frontend:latest ./frontend
```

Change `POSTGRES_PASSWORD` in `k8s/00-config.yaml` before applying. The raw manifests use an illustrative string in the Secret; Kubernetes Secret values are base64-encoded at rest by default, not encrypted automatically.

```bash
kubectl apply -f k8s/
kubectl get pods,svc,pvc
kubectl rollout status deployment/backend
kubectl rollout status deployment/frontend
```

Visit the NodePort on a cluster node at `http://<node-ip>:30080`. For Minikube, run `minikube service frontend --url`. Or use a portable port-forward:

```bash
kubectl port-forward service/frontend 8501:8501
```

Then open http://localhost:8501. For direct API access, use `kubectl port-forward service/backend 5000:5000` in another terminal and call `http://localhost:5000`.

Remove the resources with `kubectl delete -f k8s/`. The PVC and its data may remain depending on the cluster and reclaim policy; inspect before deleting storage.

## Kubernetes: Helm chart (recommended)

Install Helm 3 and ensure the app images are available to your cluster as above. Replace the demo password with a strong value (or use an existing secret):

```bash
helm lint ./scalable-app-chart
helm template task-demo ./scalable-app-chart
helm install task-demo ./scalable-app-chart \
  --set postgresql.password='replace-with-a-long-random-value'
```

Open the frontend using the NodePort at `http://<node-ip>:30080`, `minikube service task-demo-scalable-app-chart-frontend --url`, or:

```bash
kubectl port-forward service/task-demo-scalable-app-chart-frontend 8501:8501
```

Useful lifecycle commands:

```bash
helm status task-demo
kubectl get pods,svc,pvc
helm upgrade task-demo ./scalable-app-chart --set backend.replicaCount=3
helm uninstall task-demo
```

To use a secret managed outside Helm, create it in the release namespace and set `postgresql.existingSecret` to its name. The secret must contain the key configured by `postgresql.existingSecretKey` (default `POSTGRES_PASSWORD`). Avoid putting credentials on a shared shell command line or committing them in a values file; use your deployment platform's secret manager. The chart's simple single-instance PostgreSQL workload is for learning, not a highly available database architecture.

### Common configuration

```yaml
backend:
  replicaCount: 2
  image: { repository: scalable-app-backend, tag: "1.0.0", pullPolicy: IfNotPresent }
frontend:
  replicaCount: 2
  service: { type: NodePort, port: 8501, nodePort: 30080 }
postgresql:
  database: tasks
  persistence: { enabled: true, size: 2Gi, accessMode: ReadWriteOnce }
```

Provide overrides with `-f my-values.yaml`. Most clusters dynamically provision a PVC using their default StorageClass. Set `postgresql.persistence.storageClass` explicitly if your cluster requires a named class.

## Tests

The request-validation tests do not require a running database. Install the backend dependencies and test dependency, then run:

```bash
python -m pip install -r backend/requirements.txt -r requirements-dev.txt
python -m pytest -q
```

For an end-to-end smoke test, start Compose and check `http://localhost:8501` and `http://localhost:5000/ready`.

## Troubleshooting

- **`ImagePullBackOff`:** build and load both app images into the local cluster, or publish them to a registry and update both image repositories/tags. Local images should use `IfNotPresent`.
- **PVC `Pending`:** inspect `kubectl describe pvc`; install/enable a StorageClass or set `postgresql.persistence.storageClass` to a provisioned class.
- **API restarting / readiness failing:** `kubectl logs deployment/<release>-scalable-app-chart-backend`; verify database Pod, Service, username/password, and Secret key. The API retries database initialization during startup.
- **NodePort not reachable:** try `kubectl port-forward service/<release>-scalable-app-chart-frontend 8501:8501`; some desktop clusters do not expose node IPs directly.
- **Resource pressure:** lower requests/limits in values; the configured limits are conservative teaching defaults, not workload benchmarks.
