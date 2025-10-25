## EliteX V7 Agentic Workflow (Single Diagram)

flowchart TD

%% =============================================================
%% STYLES
%% =============================================================
classDef source fill:#e2e8f0,stroke:#64748b,color:#0f172a,stroke-width:2
classDef core fill:#0ea5e9,stroke:#0284c7,color:#ffffff,stroke-width:2
classDef combined fill:#f59e0b,stroke:#d97706,color:#111827,stroke-width:2
classDef sme fill:#10b981,stroke:#059669,color:#052e29,stroke-width:2
classDef final fill:#6366f1,stroke:#4f46e5,color:#eef2ff,stroke-width:2
classDef out fill:#ef4444,stroke:#dc2626,color:#fff,stroke-width:2
classDef note fill:#fff7ed,stroke:#fdba74,color:#7c2d12,stroke-dasharray: 3 3

%% =============================================================
%% DATA SOURCES (READ-ONLY)
%% =============================================================
subgraph DS[Data Sources]
direction TB
  DB[(PostgreSQL Database:<br/>Client profiles, transactions, investments,<br/>risk definitions, engagement history,<br/>banking products, insurance policies)]:::source
  XLSX[(Excel Files:<br/>Market data, economic indicators,<br/>risk scenarios, credit products)]:::source
  APP[(Application Data:<br/>Upsell opportunities and<br/>product recommendations)]:::source
end

%% =============================================================
%% CORE AGENTS (FOUNDATION CONTEXT)
%% =============================================================
subgraph CORE[Core Context Builders]
direction TB
  MGR["Manager Agent<br/><br/>Consumes: Client profile, spending patterns, banking balances,<br/>engagement history, communication logs, upsell opportunities<br/><br/>Delivers: Comprehensive client overview with behavioral insights,<br/>wallet share analysis, and engagement summary"]:::core
  RSK["Risk & Compliance Agent<br/><br/>Consumes: Client risk profile, credit bureau alerts,<br/>compliance flags, transaction patterns<br/><br/>Delivers: Risk assessment, compliance status,<br/>and regulatory considerations"]:::core
  ALLOC["Asset Allocation Agent<br/><br/>Consumes: Current portfolio holdings, client risk appetite,<br/>strategic asset allocation benchmarks<br/><br/>Delivers: Portfolio analysis showing current vs target allocation,<br/>deviations, and rebalancing recommendations"]:::core
  MI["Market Intelligence Agent<br/><br/>Consumes: Current market data, economic indicators,<br/>risk scenarios and forecasts<br/><br/>Delivers: Market outlook, economic context,<br/>and scenario-based investment implications"]:::core
end

%% DATA FLOWS INTO CORE AGENTS
DB --> MGR
APP --> MGR
DB --> RSK
DB --> ALLOC
XLSX --> MI

%% =============================================================
%% COMBINED CONTEXT
%% =============================================================
CC["Combined Context<br/><br/>Aggregates insights from all 4 core agents into a unified context<br/>containing client overview, risk profile, portfolio status, and market outlook<br/><br/>This context is shared with all specialist agents below"]:::combined
MGR --> CC
RSK --> CC
ALLOC --> CC
MI --> CC

%% =============================================================
%% SME / SPECIALIST AGENTS (CONSUME COMBINED CONTEXT)
%% =============================================================
subgraph SME[Specialist Execution Agents]
direction TB
  INV["Investment Agent<br/><br/>Consumes: Combined context + investment portfolio,<br/>product catalogs, funds/bonds/stocks data<br/><br/>Delivers: Investment recommendations, product opportunities,<br/>portfolio optimization suggestions aligned with risk profile"]:::sme
  LOAN["Loan & Credit Agent<br/><br/>Consumes: Combined context + credit bureau data,<br/>existing loans, eligible loan products<br/><br/>Delivers: Lending capacity analysis, credit opportunities,<br/>suitable loan products based on creditworthiness"]:::sme
  BANK["Banking/CASA Agent<br/><br/>Consumes: Combined context + account balances,<br/>transaction patterns, banking products<br/><br/>Delivers: Banking relationship analysis, CASA opportunities,<br/>account optimization recommendations"]:::sme
  BANCA["Bancassurance Agent<br/><br/>Consumes: Combined context + insurance holdings,<br/>life events, protection gaps<br/><br/>Delivers: Insurance needs analysis, lifecycle-based triggers,<br/>protection gap recommendations and suitable policies"]:::sme
end

%% COMBINED CONTEXT TO ALL SME AGENTS
CC --> INV
CC --> LOAN
CC --> BANK
CC --> BANCA

%% =============================================================
%% FINAL SYNTHESIS & OUTPUTS
%% =============================================================
RM["RM Strategy Agent - Final Synthesis<br/><br/>Consumes: All outputs from Manager, Risk, Asset Allocation,<br/>Market Intelligence, Investment, Loan, Banking, and Bancassurance agents<br/><br/>Delivers: Unified relationship management strategy with prioritized<br/>action items, cross-sell opportunities, and next-best-actions"]:::final
INV --> RM
LOAN --> RM
BANK --> RM
BANCA --> RM
MGR --> RM
RSK --> RM
ALLOC --> RM
MI --> RM

subgraph OUTS[Final Deliverables]
direction TB
  OA[Consolidated JSON Report:<br/>All agent insights combined<br/>for system integration]:::out
  RPT[Executive Report:<br/>Human-readable analysis<br/>for relationship managers]:::out
  IND[Individual Agent Reports:<br/>Detailed outputs per agent<br/>for audit and traceability]:::out
end
RM --> OA
RM --> RPT
RM --> IND

%% =============================================================
%% EXPLANATORY NOTES (LEGEND)
%% =============================================================
NOTE1["WORKFLOW SUMMARY:<br/><br/>1. Core agents build foundation context from data sources<br/>2. Outputs combine into shared context for all specialists<br/>3. Specialist agents add domain expertise using combined context<br/>4. RM Strategy synthesizes everything into actionable strategy<br/>5. Final reports generated for systems and relationship managers<br/><br/>Color Legend: Blue=Core | Amber=Combined | Green=Specialists | Purple=Final | Red=Outputs | Grey=Data"]:::note
NOTE1 --- CORE
NOTE1 --- CC
NOTE1 --- SME
NOTE1 --- RM
NOTE1 --- OUTS


