# TelcoLane Architectural Specification (architecture.md)

**System:** TelcoLane Subscriber & Plan Lifecycle Operations Platform  
**Document Version:** 1.0.0  
**Architectural Discipline:** Strict Layer Isolation · Domain Driven Design · Invariant Safety  

---

## 1. System Overview & C4 Context Diagram
TelcoLane coordinates retail subscribers, retail dealers, customer service representatives (CSRs), and telecom administrators with external provisioning stubs and national clearinghouses.

```mermaid
flowchart TD
    subgraph External_Users [External & Internal Actors]
        Sub["Subscriber (Self-Service)"]
        Dealer["Authorized Dealer (POS)"]
        CSR["Customer Service Rep (CSR)"]
        Admin["Telecom Administrator"]
    end

    subgraph TelcoLane_Platform [TelcoLane Operations Substrate]
        Web["React Operations Portal (Vite / Responsive UI)"]
        API["FastAPI / APIController Gateway (HTTP REST)"]
        ServiceLayer["Service Orchestration Layer (Subscription, Reporting)"]
        RepoLayer["Append-Only Repositories (Subscribers, Plans, Audits, Billing)"]
        DomainCore["Pure Domain Layer (State Machine, Pro-Rata Engine, Policies)"]
    end

    subgraph External_Stubs [External Upstream / Regulatory Stubs]
        KYCStub["National KYC Registry Stub"]
        MNPStub["MNP Clearinghouse Stub"]
        ProvStub["Network HSS / OCS Provisioning Stub"]
    end

    Sub -->|Register / Change Plan / Suspend / Port-Out| Web
    Dealer -->|Activate Subscriber| Web
    CSR -->|Manual Overrides / Audit Inspection| Web
    Admin -->|Catalog Config / Operational BI| Web

    Web -->|JSON over HTTP / X-Correlation-ID| API
    API --> ServiceLayer
    ServiceLayer --> RepoLayer
    ServiceLayer --> DomainCore
    DomainCore --> KYCStub
    DomainCore --> MNPStub
    DomainCore --> ProvStub
```

---

## 2. Layered Architecture Structure
The codebase strictly adheres to directional dependencies:  
`Controllers` $\to$ `Services` $\to$ `Repositories` $\to$ `Domain`.  
The `Domain` layer contains zero framework imports and zero outer-layer references, enforced by automated architecture tests and `.claude/hooks/architecture-layering-check.sh`.

```mermaid
flowchart LR
    subgraph Layer1 [1. Controller Layer]
        C1["APIController"]
        C2["FastAPI Main Routes"]
        C3["Correlation & PII Masking Filters"]
    end

    subgraph Layer2 [2. Service Layer]
        S1["SubscriptionService"]
        S2["ReportingService"]
        S3["Audit Logger Coordinator"]
    end

    subgraph Layer3 [3. Repository Layer]
        R1["SubscriberRepository"]
        R2["PlanRepository (Versioned)"]
        R3["AuditRepository (Append-Only)"]
        R4["BillingRepository"]
    end

    subgraph Layer4 [4. Pure Domain Core]
        D1["Models & Exceptions"]
        D2["StateMachineValidator"]
        D3["ProRataCalculator (Decimal)"]
        D4["ActivationPolicy"]
        D5["PlanChangePolicy"]
        D6["PortOutPolicy"]
        D7["SuspensionPolicy"]
        D8["CSROverridePolicy"]
    end

    Layer1 --> Layer2
    Layer2 --> Layer3
    Layer2 --> Layer4
    Layer3 --> Layer4
```

---

## 3. End-to-End Sequence: Activation to Port-Out Lifecycle
This sequence illustrates the complete lifecycle path of a subscriber from registration through activation, plan migration with pro-rata billing, and 7-day port-out cooling period management.

```mermaid
sequenceDiagram
    autonumber
    actor Sub as Subscriber
    actor Dealer as Dealer
    participant API as API Controller
    participant Srv as Subscription Service
    participant Dom as Domain Policies / State Machine
    participant Repo as Repositories

    Note over Sub, Repo: Phase 1: Self-Registration (AC-01)
    Sub->>API: POST /subscribers/register (Mobile, ID Proof, PREPAID)
    API->>Srv: register_subscriber()
    Srv->>Repo: save(Subscriber state=PENDING_KYC)
    Srv-->>API: Subscriber (Masked PII)
    API-->>Sub: 200 OK (SUB-ID, XXXXXX1234, [REDACTED])

    Note over Dealer, Repo: Phase 2: Dealer Activation (AC-08)
    Dealer->>API: POST /subscribers/activate (SUB-ID, DEALER_001, KYC=VERIFIED, MNP=APPROVED)
    API->>Srv: activate_subscriber()
    Srv->>Dom: StateMachineValidator.validate(PENDING_KYC -> ACTIVE)
    Srv->>Dom: ActivationPolicy.validate()
    Srv->>Repo: save(Subscriber state=ACTIVE, current_plan)
    Srv->>Repo: append(AuditLog: SUBSCRIBER_ACTIVATED)
    API-->>Dealer: 200 OK (ACTIVE)

    Note over Sub, Repo: Phase 3: Mid-Cycle Plan Change (AC-04, AC-05)
    Sub->>API: POST /subscribers/change-plan (New Plan, Day 10 of 30)
    API->>Srv: change_plan()
    Srv->>Dom: ProRataCalculator.calculate(old_rent, new_rent, 10, 30)
    Dom-->>Srv: Total Pro-Rata Charge (Decimal 83.33)
    Srv->>Repo: append(BillingRecord)
    Srv->>Repo: append(AuditLog: PLAN_CHANGE)
    API-->>Sub: 200 OK (Pro-rata: $83.33)

    Note over Sub, Repo: Phase 4: Port-Out & Cooling Period (AC-07)
    Sub->>API: POST /subscribers/port-out (Recipient Operator)
    API->>Srv: initiate_port_out()
    Srv->>Dom: PortOutPolicy.validate_initiation()
    Srv->>Repo: save(Subscriber state=PORT_OUT_REQUESTED, timestamp=now)
    API-->>Sub: 200 OK (7-Day Cooling Period Active)

    opt Subscriber Cancels Within 7 Days
        Sub->>API: POST /subscribers/port-out/cancel
        API->>Srv: cancel_port_out()
        Srv->>Dom: PortOutPolicy.validate_cancellation(elapsed < 7 days)
        Srv->>Repo: save(Subscriber state=ACTIVE)
        API-->>Sub: 200 OK (Cancelled, Restored to ACTIVE)
    end
```

---

## 4. Architectural Invariants Enforced by Tests
1. **Layer Dependency Direction**: Domain never imports from controllers, services, repositories, or external frameworks (`tests/architecture/test_layering.py`).
2. **Financial Precision**: Floating-point casts (`float()`) are strictly forbidden across domain calculations (NFR-01).
3. **Plan Immutability**: Published plan records (`is_published=True`) cannot be updated in place (NFR-02).
4. **Duplicate Active Mobile Number Guard**: An identical mobile number cannot hold more than one ACTIVE subscription concurrently (NFR-08).
5. **PII Masking**: Mobile numbers and identity proof references are masked across logs and public payloads (NFR-03).
