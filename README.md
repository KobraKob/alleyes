# ALLEYES — Marketing Intelligence Platform

ALLEYES is an autonomous, multi-tenant marketing engine featuring Bayesian Thompson Sampling bandits, deterministic multi-touch attribution, strict regulatory governance (India DPDP Act 2023, TRAI quiet hours, WhatsApp 24-hour messaging window), a 5-agent LLM orchestration system, and Next.js management dashboard.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Ingestion["1. Ingestion & Identity Layer"]
        Webhook["Webhooks / Form Submits / Ad Clicks"] --> IngestAPI["FastAPI Ingestion Endpoint"]
        IngestAPI --> Crypto["Identity Resolution (AES-256-GCM + Tenant HKDF HMAC)"]
        Crypto --> Events["Immutable Partitioned Event Store (PostgreSQL RLS)"]
    end

    subgraph Decision["2. Bandit Decision Engine"]
        Context["Decision Context (Stage, Channel, Attributes)"] --> Thompson["Thompson Sampling (Beta Posteriors)"]
        Thompson --> Explore["Probability Matching (ε = 0.05 Exploration Floor)"]
        Explore --> DecLog["decisions Log (Propensity & Context)"]
    end

    subgraph Agents["3. Multi-Agent Orchestration"]
        LeadAgent["Lead Response Agent (<60s SLA)"]
        PlannerAgent["Planner Agent (Budget & CAC Constraints)"]
        AdsAgent["Ads Agent (Hook/Angle/CTA Generation)"]
        AnalystAgent["Analyst Agent (Zero-Hallucination Verification)"]
        RetentionAgent["Retention Agent (Lifecycle Triggers)"]
    end

    subgraph Governance["4. Governance & Action Pipeline"]
        DecLog & Agents --> PolicyCheck{"Policy Engine\n(6 Safety Rules)"}
        PolicyCheck -->|Pass| Autonomy{"Autonomy Tier\n(L1 / L2 / L3)"}
        PolicyCheck -->|Fail| Rejected["Rejected / Logged"]
        Autonomy -->|Requires Human Approval| ApprovalQueue["Approvals Queue"]
        Autonomy -->|Auto-Approved| Executor["Action Executor"]
        KillSwitch["Emergency Kill Switch (Active)"] -.->|Preempts All| PolicyCheck
        Executor --> Connectors["Connectors (WhatsApp, Meta Ads, Email, GBP)"]
    end

    subgraph Learning["5. Learning & Attribution Loop"]
        Events --> Attribution["Multi-Touch Attribution (Last, First, Position 40/20/40)"]
        Attribution --> RewardCalc["Normalized Reward Calculation [0, 1.0]"]
        RewardCalc --> DeltaUpdater["Batch Posterior Updater (Beta α/β Increments)"]
        DeltaUpdater --> Thompson
        NightlyDiscount["Nightly Discounting (γ = 0.98)"] --> Thompson
    end
```

---

## Core Capabilities

1. **Row-Level Security Multi-Tenancy**: Every database transaction executes with `SET LOCAL app.business_id = :id` to enforce hard cryptographic and operational data boundary isolation across tenants.
2. **Cryptographic Identity & DPDP Compliance**:
   - PII fields (phone, email, name) encrypted with tenant-derived AES-256-GCM.
   - Tenant-isolated deterministic blind indices generated via HKDF-SHA256 (`HMAC(K_tenant, normalize(phone))`).
   - Multilingual consent tracking (`STOP`, `UNSUBSCRIBE`, `ROKO`, `BAND KARO`, `MAT BHEJO`) with 90-day inactive event pruning.
3. **Bayesian Bandit Decision Engine**:
   - Independent Beta posteriors $\text{Beta}(\alpha, \beta)$ per arm.
   - Thompson Sampling with an explicit $\epsilon = 0.05$ probability matching exploration floor to avoid arm starvation.
   - Nightly time discounting ($\gamma = 0.98$) applied to effective sample counts to handle seasonal trend drift.
4. **Deterministic Multi-Touch Attribution**:
   - Configurable models: Last-Touch, First-Touch, and Position-Based (40% first, 40% last, 20% intermediate linear split).
   - Lookback windows: 30 days for ad clicks/messages/forms; 7 days for ad impressions.
   - Mathematical proof: All attributed touch weights sum exactly to 1.0 (`test_hypothesis_attribution_credits_sum_to_one`).
5. **Multi-Agent Orchestration**:
   - **Lead Response Agent**: Intent classification and instant conversational answers within 60-second SLA.
   - **Planner Agent**: Resource planning and budget allocation strictly bound by hard maximum spend and target CAC validation rules.
   - **Ads Agent**: Automated generation of creative hooks, angles, and CTAs, registering new arms into the bandit space.
   - **Analyst Agent**: Performance reporting with strict verification against SQL-computed source of truth to guarantee zero numeric hallucinations.
   - **Retention-Lite Agent**: Lifecycle milestone triggers (trial attendance reminders, 90-day engagement reviews) with frequency cap policing.
6. **Governance & Safety Pipeline**:
   - Emergency kill switch providing immediate pre-emption at tenant, channel, or campaign scope.
   - Autonomy Tiers: L1 (Human review required for all actions), L2 (Auto-executes low-risk messaging within bounds), L3 (Autonomous within daily budget caps).
   - TRAI quiet hours enforcement (21:00 to 09:00 IST), Meta/WhatsApp 24-hour service window verification, and banned regulatory claims blocklist.
7. **Production Dry-Run Default**:
   - `DRY_RUN=true` and `LIVE_SENDS=false` by default. Zero unauthorized network requests are ever emitted in non-production environments.

---

## Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11 | Modern typing, asyncio, robust mathematical libraries. |
| **Type Checking** | Mypy (`--strict`) | Zero implicit `Any`, complete runtime type safety. |
| **API Framework** | FastAPI + Uvicorn | High-throughput asynchronous endpoints with OpenAPI documentation. |
| **Relational Database** | PostgreSQL 16 | Native Row-Level Security (RLS), declarative partitioning, JSONB. |
| **ORM & Migrations** | SQLAlchemy 2.0 + Alembic | Strongly typed async/sync engine, schema evolution. |
| **Background Queue** | Procrastinate | PostgreSQL-backed distributed task queue eliminating Redis overhead. |
| **Bandits & Numerics**| NumPy + SciPy | Vectorized sampling, Beta distributions, bootstrap Monte Carlo OPE. |
| **Cryptography** | `cryptography` (PyCA) | AES-256-GCM authenticated encryption, HKDF key derivation. |
| **Frontend** | Next.js 14 + Tailwind CSS | React Server Components, responsive management interfaces. |

---

## Quickstart & Local Setup

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for dashboard)

### 2. Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```
*(The default keys in `.env.example` are pre-configured for local dry-run development).*

### 3. Start Database Infrastructure
```bash
make up
# Or: docker compose up -d
```

### 4. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 5. Apply Database Migrations
```bash
make migrate
# Or: alembic upgrade head
```

### 6. Seed the Demo Environment (Gym Vertical)
Seeds an organization, sample fitness business ("Iron Fitness Gym"), 3 locations (Indiranagar, Koramangala, HSR Layout), decision points, bandit arms, and default API keys:
```bash
make seed
# Or: python scripts/seed.py
```

### 7. Run the End-to-End Dry-Run Demo
Simulates a complete marketing lifecycle across 7 stages (lead capture, Groq LLM intent classification, bandit decision, lead response agent, governance policy check, conversion ingestion, multi-touch attribution, and bandit posterior update):
```bash
make demo
# Or: python scripts/demo.py
```

### 8. Run the Live Interactive Customer CLI (Groq LLM)
Test arbitrary customer queries interactively with instant intent classification, Thompson sampling arm selection, grounded reply generation, and regulatory policy checks:
```bash
make interactive
# Or: python scripts/interactive.py
# Or with a direct prompt:
python scripts/interactive.py "Can I book a free trial at Indiranagar tomorrow?"
```

### 9. Run the Synthetic Market Simulation
Simulates 20 independent market runs across stationary environments, sudden regime shifts, and adversarially wrong priors:
```bash
make sim
# Or: python scripts/simulate.py
```

---

## Empirical Verification & Simulation Results

The engine was evaluated across 20 synthetic market seeds to measure regret reduction, convergence rate, and offline policy evaluation (OPE) coverage. Results strictly surpass all target thresholds:

| Metric | Target Threshold | Measured Result | Status |
|---|---|---|---|
| **Cumulative Regret Reduction** | $\ge 30\%$ vs Uniform Random | **72.1%** | **PASS** |
| **Best Arm Allocation Share** | $\ge 40\%$ | **71.2%** | **PASS** |
| **Regime Shift Recovery** | $< 10\%$ to collapsed arm within 300 leads | **6.0%** | **PASS** |
| **Wrong Prior Recovery** | Converges to true best within 500 leads | **100% Recovery** | **PASS** |
| **OPE Bootstrap CI Coverage** | $\ge 90\%$ 95% CI coverage | **90.0%** | **PASS** |
| **Deterministic Seed Replay** | Identical stats on identical seeds | **100% Deterministic** | **PASS** |

---

## Testing & Quality Assurance

### Run Unit, Property & Simulation Tests
```bash
make test
# Or: pytest tests/ -v
```

### Run Strict Type Checking
```bash
make typecheck
# Or: mypy src/
```

### Run Linter & Formatter
```bash
make lint
# Or: ruff check src/ tests/ && ruff format --check src/ tests/
```

---

## Extending the Engine

### Adding a New Vertical Pack
Vertical configurations reside in `packs/<vertical>/pack.yaml`. To create a new vertical (e.g., `dental` or `real_estate`):

1. Create directory `packs/<vertical>/` and file `pack.yaml`.
2. Define the schema components:
```yaml
vertical: dental
version: 1.0.0
funnel_stages:
  - key: inquiry
    name: "Consultation Inquiry"
    order: 1
    reward_weight: 1.0
  - key: consultation_attended
    name: "Consultation Attended"
    order: 2
    reward_weight: 10.0
  - key: procedure_scheduled
    name: "Procedure Scheduled"
    order: 3
    reward_weight: 50.0

decision_points:
  - key: offer_selection
    name: "New Patient Offer"
    channel: whatsapp

banned_claims:
  - "(?i)100%\\s+pain\\s*free"
  - "(?i)permanent\\s+cure"

priors:
  offer_selection:
    free_checkup:
      alpha: 2.0
      beta: 18.0
    half_price_cleaning:
      alpha: 3.0
      beta: 17.0
```
3. Load the pack using `seed.py` or the ingestion API.

### Adding an External Connector
Connectors implement the `Connector` protocol defined in [`src/engine/connectors/base.py`](file:///c:/Users/badhu/OneDrive/Desktop/project-hire/alleyes/src/engine/connectors/base.py):

```python
from src.engine.connectors.base import Connector, SendResult, ExternalRef

class CustomSMSConnector(Connector):
    def send_message(self, account: Any, to: str, content: str, template: Any = None) -> SendResult:
        if self.dry_run:
            return SendResult(
                success=True,
                external_message_id=f"dry_custom_{uuid4()}",
                provider="custom_sms",
                delivered=True
            )
        # Implement live API call here
        ...
```

Register the connector in [`src/engine/governance/executor.py`](file:///c:/Users/badhu/OneDrive/Desktop/project-hire/alleyes/src/engine/governance/executor.py) within `_resolve_connector()`.

---

## Repository Structure

```
.
├── alembic/                      # Database migrations (RLS, schema 0001-0003)
├── dashboard/                    # Next.js 14 frontend application
│   ├── src/app/approvals/        # Human-in-the-loop governance queue
│   ├── src/app/performance/      # Multi-touch attribution and revenue dashboard
│   ├── src/app/learning/         # Bandit Beta posteriors and arm distributions
│   └── src/app/control/          # Emergency kill switches and autonomy controls
├── packs/
│   └── gym/                      # Fitness vertical pack (stages, priors, claims)
├── reports/                      # Generated simulation and validation reports
├── scripts/
│   ├── seed.py                   # Multi-tenant organization and arms seeder
│   ├── demo.py                   # 7-stage end-to-end dry-run demonstration
│   └── simulate.py               # 20-seed market simulator
├── src/engine/
│   ├── agents/                   # 5 LLM agents (Lead, Planner, Ads, Analyst, Retention)
│   ├── api/                      # FastAPI routers (Events, Leads, Tracking, Actions, Kill-Switch)
│   ├── attribution/              # Multi-touch attribution computation service
│   ├── connectors/               # Provider connectors (WhatsApp, Meta Ads, Email, GBP, Fake)
│   ├── db/                       # SQLAlchemy models, sessions, partitions, RLS roles
│   ├── domain/                   # Pure mathematical rules (Bandits, Policy, Attribution, Rewards)
│   ├── governance/               # Action executor, approval state machine, kill switch
│   ├── identity/                 # AES-256-GCM encryption, blind indices, consent, contact resolution
│   ├── ingest/                   # High-throughput batch event ingestion service
│   ├── jobs/                     # Background tasks (Procrastinate queue)
│   ├── learning/                 # Bandit decision API, posterior updaters, OPE evaluation
│   └── llm/                      # Anthropic & Fake LLM clients with token tracing
├── tests/
│   ├── unit/                     # Domain algorithms, crypto, governance, agents
│   └── simulation/               # 20-seed Monte Carlo market simulation test
├── pyproject.toml                # Project metadata, dependencies, mypy/ruff settings
├── docker-compose.yml            # PostgreSQL 16 local setup
└── Makefile                      # Automation commands (up, migrate, seed, demo, test, sim)
```

---

## License

Proprietary and Confidential. Built for the Autonomous Marketing Engine project.
