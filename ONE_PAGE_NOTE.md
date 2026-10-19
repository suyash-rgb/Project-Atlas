# What I Would Do With One More Week


### Engineering Roadmap & Production Evolution | Project Atlas
---

If granted an additional week of focused engineering time on Project Atlas, I would transition the system from its current **high-performing prototype architecture** to a **globally distributed, enterprise-hardened PaaS deployment**. 

Here are the 5 high-impact initiatives I would execute, organized by technical leverage:

---

### 1. Multi-Turn Conversational Memory & Follow-Up Context Resolution ([GitHub Issue #1](https://github.com/suyash-rgb/Project-Atlas/issues/1))
* **Current State**: 
  - While our CodeIgniter 3 portal records question-answer pairs in MySQL, each FastAPI request is currently evaluated in isolation.
  - Short follow-up queries (such as *"What about 2030?"* or *"Can you explain that scope difference?"*) arrive at the router without the subject, report ID, or topic established in the preceding turn.
* **One-Week Enhancement**:
  - **History-Aware Query Resolution**: Implement a lightweight pre-router step that inspects the last 2–3 turns of trusted session history and rewrites the user's follow-up into a self-contained standalone question (e.g., resolving *"What about 2030?"* into *"What is the projected 2030 market size for smart water meters in report R-101?"*). If the reference is ambiguous, politely prompt the user for clarification.
  - **Raw Security Screening First**: Check the raw user message with the Laya 421M guardrail *before* contextual rewriting, ensuring prompt injections cannot hide inside conversational context.
  - **Re-Routing on the Resolved Question**: Run the Laya intent router on the *resolved* question every turn so the agent can seamlessly switch tools (e.g., pivoting from `factual_lookup` to `calculation`).
  - **Fresh Evidence & Semantic Cache Protection**: Always pull fresh evidence from ChromaDB or the deterministic Python calculator rather than treating previous assistant text as ground truth. In addition, key Redis semantic caches by the resolved question to prevent cross-conversation cache collisions.

---

### 2. High-Accuracy Multi-Modal Visual Chart & Tabular OCR (Nougat / ColPali)
* **Current State**: Multimodal visual elements are extracted via PyMuPDF vector path analysis and converted to Markdown summaries via Gemini/Matplotlib heuristics.
* **One-Week Enhancement**:
  - Deploy an on-premise or quantized **ColPali (Vision-Language Retrieval)** or **Nougat (Academic Document OCR)** microservice container.
  - Index raw graphic bounding boxes as native multi-vector embeddings. This would allow clients to ask: *"Show me the regional breakdown chart on page 12 of R-101"* and have the Copilot render the interactive SVG/ChartJS visualization directly inside the CodeIgniter 3 view canvas.

---

### 3. Dynamic Fine-Grained Role-Based Access Control (RBAC) & Column Masking
* **Current State**: Entitlements are enforced at the report level (`purchased_reports: "R-101, R-103"`). Unpurchased report chunks are filtered out before context assembly.
* **One-Week Enhancement**:
  - Implement **Section- & Metric-Level Entitlements**: allow enterprise clients to purchase granular sections (e.g., *"APAC Regional Chapter Only"* or *"Summary Data Tier"*).
  - Implement **Dynamic Dynamic SQL Column Masking**: integrate MySQL 8.0 row-level security policies or ProxySQL to automatically redact sensitive executive survey commentary for lower-tier corporate subscribers while permitting market aggregate queries.

---

### 4. Active Continuous Fine-Tuning Loop for Guardrails & Routing
* **Current State**: The fine-tuned Laya 421M model operates on pre-quantized weights for sub-40ms routing and perimeter defense, trained on our initial 1,260 curated samples.
* **One-Week Enhancement**:
  - Build an automated **Continuous Hard-Negative Mining Loop**: user feedback (thumbs down) and human escalation tickets stored in the MySQL `feedback` and `escalations` tables will automatically be extracted and labelled.
  - Formulate structured supervised retraining datasets from edge-case client queries that exhibited boundary ambiguity.
  - Trigger a scheduled weekly retraining and ONNX export pipeline, continuously hardening the guardrail router against newly emerging prompt injection and exfiltration patterns with zero downtime.

---

### 5. Native Langfuse Telemetry & Observability Integration in the Admin Portal
* **Current State**: 
  - To gain deep operational visibility, I instrumented the core agent workflow with `@observe` decorators and contextual spans (`report_copilot_pipeline`, `read_only_sql`, `reconcile_report_conflicts`, `extract_calculation_inputs`, `llm_synthesizer`, `entitlement_filtered_retrieval`, and `guardrail_router`).
  - This successfully captured **2,400+ traces**, **4,410+ nested observations**, latency percentiles (p50–p99 across nodes), and cost telemetry ($0.01 across 171.8K tokens) in our Langfuse dashboard.
  - However, because these rich analytics currently reside inside the external Langfuse SaaS cloud, non-technical business stakeholders and platform administrators cannot view them directly within our CodeIgniter 3 web portal.
* **One-Week Enhancement**:
  - **Embedded Stakeholder Analytics Dashboard**: Build a dedicated *Analytics & Model Governance* tab directly inside the CodeIgniter 3 Admin Portal, consuming the Langfuse REST API (`/api/public/traces`, `/api/public/metrics`, `/api/public/sessions`).
  - **Native Real-Time KPI Cards**: Surface live system health metrics directly to executives: average query latency, cost-per-client breakdown, token volume trends, and node-level bottlenecks (e.g., comparing p50 vs p95 generation latency) without requiring external SaaS access.
  - **Automated Score Tracking**: Activate Langfuse automated evaluator scores (currently at 0 in our prototype) to systematically track factual grounding, citation precision, and hallucination rates across all client conversations.
