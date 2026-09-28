# Zero-Trust Dynamic Access Control for Distributed API Gateways

M.Tech Distributed Computing project based on the supplied proposal.

## Project goal

Compare three API-gateway configurations:

1. No Access Control (No-AC)
2. Static Role-Based Access Control (RBAC)
3. Dynamic Attribute-Based Access Control (ABAC)

The system measures:

- p50 latency
- p95 latency
- p99 latency
- throughput (requests/second)
- total blocked requests
- contextual-attack blocking rate

The implementation uses separate HTTP microservices so that the experiment reflects distributed communication rather than a single Python function.

## Architecture

Client / Benchmark
        |
        v
   API Gateway :8000
      |       \
      |        \--- Policy Engine :8002  (ABAC)
      |
      +-----------> Resource Service :8003

Authentication Service :8001
      |
      +--- issues RS256 JWTs

The gateway verifies JWT signatures using the public RSA key.

## Project structure

- `services/auth_service.py` - creates signed JWTs
- `services/gateway.py` - three gateway modes
- `services/policy_service.py` - dynamic ABAC policy evaluation
- `services/resource_service.py` - protected backend resource
- `benchmark/run_benchmark.py` - concurrent workload generator
- `benchmark/plot_results.py` - graphs
- `scripts/generate_keys.py` - creates RSA key pair
- `docker-compose.yml` - distributed deployment
- `PROJECT_EXPLANATION.md` - detailed viva/project explanation

## Prerequisites

- Python 3.10+
- Docker Desktop / Docker Engine + Compose
- 4 GB RAM recommended

## 1. Generate RSA keys

```bash
python scripts/generate_keys.py
```

This creates:

- `keys/private.pem`
- `keys/public.pem`

Do not publish the private key in a real deployment.

## 2. Install Python dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Start the distributed services

```bash
docker compose up --build
```

The services are:

- Gateway: http://localhost:8000
- Auth: http://localhost:8001
- Policy: http://localhost:8002
- Resource: http://localhost:8003

## 4. Get a JWT

```bash
curl -X POST http://localhost:8001/token ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"u001\",\"role\":\"admin\",\"device_trust\":0.95}"
```

On Linux/macOS use:

```bash
curl -X POST http://localhost:8001/token \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","role":"admin","device_trust":0.95}'
```

Copy the returned token.

## 5. Test the three gateway modes

### RBAC

```bash
curl "http://localhost:8000/api/data?mode=rbac" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Dynamic ABAC

```bash
curl "http://localhost:8000/api/data?mode=abac" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Geo-Country: IN" \
  -H "X-Device-Trust: 0.95"
```

### No access control

```bash
curl "http://localhost:8000/api/data?mode=noac"
```

## 6. Run the benchmark

Inside another terminal:

```bash
python benchmark/run_benchmark.py --requests 10000 --concurrency 100
```

For the proposal's larger experiment:

```bash
python benchmark/run_benchmark.py --requests 100000 --concurrency 200
```

The benchmark creates a mixed workload:

- 70% valid requests
- 15% role mismatch attacks
- 15% contextual mismatch attacks

The benchmark writes CSV results under `results/`.

## 7. Plot results

```bash
python benchmark/plot_results.py
```

Graphs are written under `results/plots/`.

## Suggested final experiment matrix

Run the benchmark multiple times, not just once:

- users: 50, 100, 250, 500, 1000
- resources/endpoints: 10, 50, 100, 250, 500
- requests: 10,000 and 100,000
- modes: No-AC, RBAC, ABAC
- repetitions: at least 5 runs per configuration

For a research paper, report mean/median and variation across runs instead of relying on one execution.

## Important interpretation

This project is an experimental simulation/prototype, not a production security gateway. The benchmark is designed to test the research questions in the supplied proposal.

The hypothesis in the proposal is that dynamic ABAC can block context-sensitive attacks with less than 15% latency overhead relative to RBAC. The benchmark should test this; do not claim the hypothesis is proven until your measured data supports it.

## Extension for a stronger IEEE/Springer-style implementation

The current project is already containerized. A further upgrade would add:

- Mininet network emulation
- a Docker/Mininet topology
- Open Policy Agent (OPA)
- realistic service-to-service traffic
- DDoS or privilege-escalation attack traffic
- repeated statistically analyzed experiments
- confidence intervals / significance testing
