# Detailed Project Explanation

## 1. Project title

**Zero-Trust Dynamic Access Control for Distributed API Gateways**

This is a security research project for Distributed Computing. The main idea is to compare a traditional static access-control method with a dynamic method that checks runtime context.

## 2. What problem are you solving?

In a traditional RBAC system, a user is given a role such as:

- admin
- doctor
- employee
- user

The role decides which resources can be accessed.

The limitation is that the same role may remain valid even when the request context becomes unsafe. For example:

- an admin account is used from an unexpected country
- the request occurs outside the allowed time window
- a device has a low trust score
- a valid credential is reused during a suspicious situation

Dynamic ABAC adds contextual attributes to the decision.

A simplified ABAC decision can be written as:

`ALLOW = role_permission AND location_allowed AND time_allowed AND device_trusted`

Therefore, the research question is not simply "how to implement authentication". The research question is:

**How much security improvement is obtained from dynamic context evaluation, and what latency overhead does that introduce in a distributed API gateway?**

## 3. Why this is a Distributed Computing project

The implementation separates the system into networked services:

1. Authentication Service
2. API Gateway
3. Policy Service
4. Resource Service

The services communicate using HTTP. This introduces network communication and service-to-service latency.

This is closer to a distributed microservice environment than implementing every security function in one Python file.

## 4. Three experimental configurations

### Configuration A: No Access Control

The gateway forwards requests directly to the resource service.

Purpose:

- provides a lower-bound performance baseline
- shows the cost of adding security mechanisms

Expected behavior:

- very low security processing overhead
- unauthorized traffic is not blocked by the gateway

### Configuration B: Static RBAC

The gateway:

1. verifies the JWT
2. reads the user role
3. checks a static permission table
4. forwards or blocks the request

Example:

`admin -> /api/data -> allowed`

`guest -> /api/admin -> denied`

RBAC does not make a new decision from location, time, and device context.

### Configuration C: Dynamic ABAC

The gateway:

1. verifies the JWT
2. collects request attributes
3. sends the authorization request to the policy service
4. the policy service evaluates the attributes
5. the gateway forwards or blocks the request

Example:

A user may have a valid admin role, but:

`role = admin`
`country = US`
`allowed countries = IN`
`device trust = 0.95`

Result:

`DENY`

The identity is valid, but the context is not.

## 5. Authentication mechanism

The project uses JSON Web Tokens signed with RSA (RS256).

The authentication service signs a token using the private RSA key.

The gateway verifies the token using the public RSA key.

This demonstrates stateless token verification.

Important token fields include:

- subject / user ID
- role
- issued-at time
- expiry time
- device trust score

## 6. ABAC attributes

The prototype evaluates:

- role
- requested endpoint
- request time
- geographic country
- device trust score

An example policy is:

- `admin` can access `/api/data`
- country must be `IN`
- request hour must be between 06:00 and 22:00
- device trust must be at least 0.70

These values are intentionally configurable so you can change the experiment.

## 7. Attack scenarios

### Role mismatch

The attacker has a valid JWT but attempts an endpoint not allowed for that role.

Expected:

- RBAC: blocked
- ABAC: blocked
- No-AC: allowed

### Context mismatch

The attacker has a valid role and a valid endpoint but uses a bad context.

Examples:

- wrong country
- low-trust device
- outside allowed time

Expected:

- RBAC: may be allowed because role/endpoint match
- ABAC: blocked
- No-AC: allowed

This is the main experiment showing why dynamic authorization is useful.

## 8. Workload

The proposal uses:

- 70% valid
- 15% role mismatch
- 15% context mismatch

This gives the benchmark three request classes.

For each gateway mode, the benchmark records:

- response latency
- status code
- allowed or blocked decision
- request type
- throughput

## 9. Why p95 and p99 matter

An average latency can hide slow requests.

Suppose 99 requests take 10 ms and one request takes 1000 ms.

The mean becomes misleading for user experience.

Tail metrics show the slower end:

- p50: typical middle request
- p95: 95% of requests are at or below this latency
- p99: 99% are at or below this latency

The proposal specifically asks for p50, p95, and p99.

## 10. Research questions

### RQ1

How effectively does dynamic ABAC block contextual attacks that pass static RBAC checks?

The experiment compares contextual mismatch results under RBAC and ABAC.

### RQ2

What is the latency penalty of dynamic attribute evaluation under concurrent traffic?

This is answered by comparing p95 and p99 latency.

## 11. Hypothesis

The proposal states:

**Dynamic ABAC will block 100% of context-sensitive attacks with less than 15% latency overhead compared to static RBAC.**

This is a hypothesis, not a guaranteed result.

Your final report should show measured data and then state whether the hypothesis was supported or not supported.

## 12. What to show in your demo

A good 5-10 minute demonstration is:

1. Start Docker containers.
2. Generate an admin JWT.
3. Show a normal request through RBAC.
4. Send a context-invalid request through RBAC.
5. Show that RBAC can accept it when role and endpoint are valid.
6. Send the same request through ABAC.
7. Show ABAC denying it.
8. Run the benchmark.
9. Open the CSV.
10. Show p50/p95/p99 and blocking rates.
11. Display the generated graphs.

## 13. Suggested report chapters

### Chapter 1 - Introduction
- Distributed APIs
- security problem
- RBAC limitation
- motivation for dynamic ABAC

### Chapter 2 - Literature Review
- ABAC
- zero trust
- microservice/API gateway security
- policy engine overhead
- tail latency

### Chapter 3 - Proposed System
- architecture
- JWT
- RBAC
- ABAC
- attack scenarios

### Chapter 4 - Implementation
- Python
- FastAPI
- Docker
- HTTP communication
- benchmark implementation

### Chapter 5 - Experimental Setup
- users
- requests
- concurrency
- traffic mix
- hardware/software
- repetitions

### Chapter 6 - Results
- p50/p95/p99
- throughput
- blocking rate
- attack-specific blocking
- graphs
- discussion

### Chapter 7 - Conclusion and Future Work
- findings
- limitations
- Mininet/OPA/real-world extension

## 14. How to explain the project in viva

A simple explanation is:

> "My project studies the security-performance trade-off in a distributed API gateway. I compare three configurations: no access control, static RBAC, and dynamic ABAC. RBAC checks the role, while ABAC also evaluates runtime context such as location, request time, and device trust. I use separate microservices for authentication, gateway, policy evaluation, and the protected resource. I generate concurrent workloads containing valid, role-mismatch, and context-mismatch requests. I measure p50, p95, p99 latency, throughput, and blocking rate. The main purpose is to determine how much extra latency dynamic security enforcement introduces while measuring how well it blocks contextual attacks."

## 15. What would make the project stronger later?

The supplied proposal is a strong experimental prototype, but for a stronger research paper you can extend it with:

- Mininet network topology
- Open Policy Agent
- containerized microservices with realistic service-to-service traffic
- controlled DDoS or privilege-escalation scenarios
- 5+ repetitions per configuration
- confidence intervals
- statistical significance testing
- larger request volumes
