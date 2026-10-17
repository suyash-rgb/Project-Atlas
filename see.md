````mermaid
flowchart TD
    A[Incoming Request: client_id + question] --> B[Input Guardrail & Intent Router]
    
    B -->|Out of Scope / Politics| C[Polite Refusal Node]
    B -->|Direct Prompt Attack e.g. 'List all emails'| D[Security Refusal & Log Injection]
    B -->|Aggregate Query e.g. 'Which sector has most reports?'| E[Read-Only MySQL SQL Tool]
    B -->|Market Research / Projections| F[Entitlement-Aware Retriever]
    
    F -->|Document Has Trap Footnote| G[Data Sanitizer / Isolation Layer]
    G --> H{Requires Math / Projections?}
    H -->|Yes e.g. 2030 APAC Market| I[Deterministic Calculator Tool]
    H -->|No| J[Draft Synthesis Node]
    I --> J
    
    J --> K[Critic & Conflict Detector Node]
    K -->|Confidence < Threshold OR Missing Citation| L[Escalation Node: Insert Ticket in MySQL]
    K -->|Passes Fact Check| M[Final Response Formatter]
    
    L --> N[Structured JSON Response]
    M --> N
    C --> N
    D --> N
    E --> N
````