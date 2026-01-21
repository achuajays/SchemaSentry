# 🛡️ SchemaSentry - Smart API Contract Guardian

**Detect breaking API changes before clients do.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![smolagents](https://img.shields.io/badge/smolagents-1.0+-purple.svg)](https://huggingface.co/docs/smolagents)
[![Groq](https://img.shields.io/badge/Groq-LLM-orange.svg)](https://groq.com/)

---

## 📸 Dashboard Preview

![SchemaSentry Dashboard](docs/dashboard.png)

*Premium dark-mode dashboard with glassmorphism design, real-time health monitoring, and contract issue visualization.*

---

## 🎯 What Problem Does It Solve?

In real backend systems:
- 📉 APIs drift from OpenAPI specs over time
- 🔒 Fields silently become required or optional
- 🔄 Response shapes change without documentation
- 💥 **Clients break after deployment**

SchemaSentry continuously observes real traffic, compares it against declared contracts, and flags breaking or risky changes **before they reach production**.

> *This is not a toy. Platform teams pay for this.*

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph Input["📥 Input Sources"]
        A["🌐 API Gateway Logs"]
        B["⚡ FastAPI Middleware"]
        C["📄 OpenAPI Spec"]
        D["📊 Client Usage Data"]
    end

    subgraph AgentSystem["🤖 Multi-Agent System"]
        subgraph Agent1["Agent 1: Traffic Observer"]
            E1["Sample Traffic"]
            E2["Extract Fields"]
            E3["Build Schema"]
        end
        
        subgraph Agent2["Agent 2: Contract Analyzer"]
            F1["Parse OpenAPI"]
            F2["Compare Schemas"]
            F3["Detect Breaking Changes"]
            F4["Classify Risk"]
        end
        
        subgraph Agent3["Agent 3: Impact Assessor"]
            G1["Map Client Usage"]
            G2["Calculate Blast Radius"]
            G3["Generate Recommendations"]
        end
    end

    subgraph Output["📤 Outputs"]
        H["🚨 Alerts"]
        I["📋 Reports"]
        J["🎨 Dashboard"]
    end

    A --> E1
    B --> E1
    E1 --> E2 --> E3
    E3 -->|Observed Schema| F1
    C --> F1
    F1 --> F2 --> F3 --> F4
    F4 -->|Contract Issues| G1
    D --> G1
    G1 --> G2 --> G3
    G3 --> H
    G3 --> I
    G3 --> J

    style Agent1 fill:#6366f1,color:#fff
    style Agent2 fill:#8b5cf6,color:#fff
    style Agent3 fill:#a855f7,color:#fff
```

---

## 🔄 Agent Workflow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Orch as Orchestrator
    participant T as Traffic Observer
    participant C as Contract Analyzer
    participant I as Impact Assessor
    participant LLM as Groq LLM

    User->>API: POST /api/report
    API->>Orch: Run Full Analysis
    
    rect rgb(99, 102, 241)
        Note over T: Agent 1: Traffic Observer
        Orch->>T: observe(traffic_data)
        T->>LLM: Execute code with tools
        LLM-->>T: Observed Schema
        T-->>Orch: Schema JSON
    end
    
    rect rgb(139, 92, 246)
        Note over C: Agent 2: Contract Analyzer
        Orch->>C: analyze(schema, spec)
        C->>LLM: Execute code with tools
        LLM-->>C: Contract Issues
        C-->>Orch: Issues JSON
    end
    
    rect rgb(168, 85, 247)
        Note over I: Agent 3: Impact Assessor
        Orch->>I: assess(issues, clients)
        I->>LLM: Execute code with tools
        LLM-->>I: Recommendations
        I-->>Orch: Impact Report
    end
    
    Orch-->>API: Analysis Report
    API-->>User: JSON Response
```

---

## 🛠️ Tool Architecture

```mermaid
graph LR
    subgraph TrafficTools["🔍 Traffic Tools"]
        T1["sample_traffic"]
        T2["extract_field_info"]
        T3["build_observed_schema"]
    end

    subgraph ContractTools["📋 Contract Tools"]
        C1["parse_openapi_spec"]
        C2["compare_schemas"]
        C3["detect_breaking_changes"]
        C4["classify_risk"]
    end

    subgraph ImpactTools["💥 Impact Tools"]
        I1["map_client_usage"]
        I2["identify_critical_clients"]
        I3["calculate_blast_radius"]
        I4["generate_recommendations"]
    end

    T1 --> T2 --> T3
    T3 -.->|Observed Schema| C1
    C1 --> C2 --> C3 --> C4
    C4 -.->|Issues| I1
    I1 --> I2
    I1 --> I3
    I3 --> I4

    style TrafficTools fill:#10b981,color:#fff
    style ContractTools fill:#3b82f6,color:#fff
    style ImpactTools fill:#ef4444,color:#fff
```

---

## 📊 Data Flow

```mermaid
flowchart LR
    subgraph Input
        RAW["Raw Traffic<br/>Records"]
        SPEC["OpenAPI<br/>Spec"]
        LOGS["Client<br/>Logs"]
    end

    subgraph Processing
        SAMPLE["Sampled &<br/>Masked Traffic"]
        OBSERVED["Observed<br/>Schema"]
        PARSED["Parsed<br/>Contract"]
        ISSUES["Contract<br/>Issues"]
        IMPACT["Impact<br/>Assessment"]
    end

    subgraph Output
        REPORT["Analysis<br/>Report"]
        ALERT["Alerts &<br/>Notifications"]
        DASH["Dashboard<br/>Metrics"]
    end

    RAW -->|sample_traffic| SAMPLE
    SAMPLE -->|build_observed_schema| OBSERVED
    SPEC -->|parse_openapi_spec| PARSED
    OBSERVED -->|compare_schemas| ISSUES
    PARSED -->|compare_schemas| ISSUES
    ISSUES -->|classify_risk| ISSUES
    ISSUES -->|calculate_blast_radius| IMPACT
    LOGS -->|map_client_usage| IMPACT
    IMPACT -->|generate_recommendations| REPORT
    REPORT --> ALERT
    REPORT --> DASH
```

---

## 🤖 The Three Agents

### Agent 1: Traffic Observer 🔍

**Responsibility**: Observe real API traffic and build observed contracts.

| Tool | Purpose |
|------|---------|
| `sample_traffic` | Sample at configurable rate with PII masking |
| `extract_field_info` | Extract types, nullability from payloads |
| `build_observed_schema` | Aggregate into schema with presence rates |

**Output Example:**
```json
{
  "endpoint": "POST /patients",
  "observed_fields": {
    "id": {"type": "string", "presence_rate": 1.0},
    "insurance": {"type": "object", "presence_rate": 0.42, "nullable": true}
  }
}
```

### Agent 2: Contract Analyzer 📋

**Responsibility**: Compare observed schema vs OpenAPI spec.

| Tool | Purpose |
|------|---------|
| `parse_openapi_spec` | Parse YAML/JSON OpenAPI specs |
| `compare_schemas` | Detect drifts between observed/declared |
| `detect_breaking_changes` | Filter critical breaking issues |
| `classify_risk` | LLM-enhanced risk explanations |

**Output Example:**
```json
{
  "issue_type": "BREAKING_CHANGE",
  "endpoint": "GET /eligibility",
  "detail": "Field 'coverage_status' missing in 37% of responses",
  "risk": "CRITICAL"
}
```

### Agent 3: Impact Assessor 💥

**Responsibility**: Answer "Who will break if this ships?"

| Tool | Purpose |
|------|---------|
| `map_client_usage` | Map endpoints to consuming clients |
| `identify_critical_clients` | Score client priority |
| `calculate_blast_radius` | Count affected clients |
| `generate_recommendations` | Create actionable suggestions |

**Output Example:**
```json
{
  "affected_clients": ["billing-service", "frontend-app"],
  "confidence": 0.82,
  "blast_radius": 3,
  "recommended_action": "STOP DEPLOYMENT. Fix breaking changes."
}
```

---

## 🚀 Quick Start

### 1. Clone and Install

```bash
cd SchemaSentry
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure

```bash
copy .env.example .env
# Edit .env and add your Groq API key
# Get one at: https://console.groq.com/keys
```

**Example `.env`:**
```bash
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=groq/llama-3.3-70b-versatile
```

### 3. Run

```bash
python main.py
```

**Access:**
- 🎨 **Dashboard**: http://localhost:8000/
- 📖 **API Docs**: http://localhost:8000/docs

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/observe` | POST | Submit traffic for observation |
| `/api/analyze` | POST | Analyze contract drift |
| `/api/assess` | POST | Assess client impact |
| `/api/report` | POST | Generate full analysis report |
| `/api/issues` | GET | List detected issues |
| `/api/dashboard-data` | GET | Dashboard metrics |

---

## 📁 Project Structure

```
SchemaSentry/
├── 📄 main.py                    # Entry point
├── 📄 sample_api.py              # Test API with drifts
├── 📄 requirements.txt           # Dependencies
├── 📁 api/
│   └── main.py                   # FastAPI application
├── 📁 src/
│   ├── config.py                 # Configuration
│   ├── 📁 agents/                # AI Agents
│   │   ├── traffic_observer.py
│   │   ├── contract_analyzer.py
│   │   ├── impact_assessor.py
│   │   └── orchestrator.py
│   ├── 📁 tools/                 # Agent Tools
│   │   ├── traffic_tools.py
│   │   ├── contract_tools.py
│   │   └── impact_tools.py
│   ├── 📁 models/                # Pydantic Schemas
│   └── 📁 utils/                 # Utilities
├── 📁 ui/                        # Dashboard UI
├── 📁 docs/                      # Documentation
└── 📁 tests/                     # Test Data
```

---

## 🧪 Testing

A sample Patient API with **intentional contract drifts** is included:

```bash
# Terminal 1: Run the test API (port 8001)
python sample_api.py

# Terminal 2: Run SchemaSentry (port 8000)
python main.py
```

The sample API has these drifts for testing:
- `coverage_status` sometimes missing (40%)
- `insurance` sometimes null unexpectedly
- `internal_score` undocumented field appears

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | [smolagents](https://huggingface.co/docs/smolagents) |
| LLM Provider | [Groq](https://groq.com/) (llama-3.3-70b-versatile) |
| Backend | FastAPI + Uvicorn |
| Data Models | Pydantic v2 |
| Frontend | Vanilla HTML/CSS/JS |

---

## 🔮 Future Roadmap

- [ ] Webhook notifications (Slack, Teams, Discord)
- [ ] GitHub PR comments
- [ ] Historical trend analysis
- [ ] Multi-environment support
- [ ] OpenTelemetry integration
- [ ] CI/CD pipeline integration

---

## 📄 License

MIT License - Feel free to use in your projects!

---

<p align="center">
  <b>Built with 🤖 smolagents + ⚡ Groq</b>
</p>
