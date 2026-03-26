# Diseño de la Solución — Platform Self Service

## 1. Contexto y Problema

Un developer necesita solicitar la habilitación de recursos técnicos (ej: bucket S3) sin depender de intervención manual del equipo de plataforma. La solución debe recibir solicitudes, validar reglas, orquestar aprovisionamiento, registrar evidencia y devolver un estado consumible por otros sistemas o una interfaz interna.

## 2. Visión General

La solución se compone de dos sistemas:

- **Self Service API** (Python/FastAPI): backend que recibe, valida, persiste y aprovisiona solicitudes de forma asíncrona.
- **Platform Portal** (TypeScript/Backstage): portal web que actúa como interfaz para developers, consumiendo la API mediante plugins propios.

```mermaid
graph LR
    DEV[Developer] -->|Formulario| BST[Backstage Portal :3000]
    DEV -->|curl / SDK| API[Self Service API :8000]
    BST -->|HTTP proxy| PLG[Plugin platform-requests :7007]
    PLG -->|REST| API
    API -->|Persiste| DB[(PostgreSQL)]
    API -->|Publica evento| EVT[Audit Events]
    WRK[Worker] -->|Poll| DB
    WRK -->|Ejecuta| PROV[Provisioner]
    PROV -->|Escribe| ART[Artifact JSON]
    WRK -->|Actualiza estado| DB
```

## 3. Diseño de Integración

### 3.1 Flujo completo de una solicitud

```mermaid
sequenceDiagram
    participant D as Developer
    participant B as Backstage
    participant S as Scaffolder Action
    participant A as Self Service API
    participant DB as PostgreSQL
    participant W as Worker
    participant P as Provisioner

    D->>B: Llena formulario (template)
    B->>S: Ejecuta company:platformRequest:create
    S->>S: Inyecta tags automáticos (service, team, environment)
    S->>A: POST /api/v1/requests
    A->>A: Valida API Key + Idempotency-Key
    A->>A: RequestService.create()
    A->>A: Inyecta auto-tags (service, team, environment)
    A->>A: RequestValidator.validate()
    alt Validación exitosa
        A->>DB: INSERT request (status=APPROVED)
        A->>DB: INSERT events (RECEIVED, VALIDATION_*, APPROVED)
        A-->>S: 202 {request_id, status: APPROVED}
    else Validación fallida
        A->>DB: INSERT request (status=REJECTED)
        A->>DB: INSERT events (RECEIVED, VALIDATION_*, REJECTED)
        A-->>S: 202 {request_id, status: REJECTED}
    end
    S-->>B: Output (request_id, status, details_url)
    B-->>D: Muestra resultado

    loop Cada 2 segundos
        W->>DB: claim_next_approved() [APPROVED→PROVISIONING]
        alt Hay solicitud pendiente
            W->>DB: INSERT event (PROVISIONING_STARTED)
            W->>P: provision_bucket(request_id, spec)
            P->>P: Genera artifact JSON
            P-->>W: {resource_id, metadata}
            W->>DB: mark_succeeded() + INSERT resource
            W->>DB: INSERT events (PROVISIONING_FINISHED, REQUEST_COMPLETED)
        end
    end

    D->>B: Consulta detalle
    B->>A: GET /api/v1/requests/{id}
    A->>DB: SELECT request + resource
    A-->>B: {status: SUCCEEDED, result: {...}}
    B-->>D: Muestra resultado de provisioning
```

### 3.2 Integración Backstage ↔ Self Service API

```mermaid
graph TB
    subgraph "Backstage Portal (:3000 / :7007)"
        UI[React Frontend]
        SCF[Scaffolder Engine]
        PLG[platform-requests-backend plugin]
        ACT[company:platformRequest:create action]
        
        UI -->|"GET /api/platform-requests/requests/:id"| PLG
        UI -->|"GET /api/platform-requests/requests/:id/events"| PLG
        SCF -->|Ejecuta acción| ACT
        ACT -->|Usa| CLIENT[PlatformApiClient]
    end

    subgraph "Self Service API (:8000)"
        EP[FastAPI Endpoints]
        SVC[RequestService]
        VAL[RequestValidator]
        REPO[SqlAlchemyRepository]
    end

    PLG -->|"HTTP GET/POST"| EP
    CLIENT -->|"POST /api/v1/requests"| EP
    EP --> SVC
    SVC --> VAL
    SVC --> REPO
```

**Contrato de autenticación:**

| Componente | Header | Valor |
|------------|--------|-------|
| Backstage → API | `x-api-key` | Configurado en `platformRequests.auth.secret` |
| Backstage → API | `Idempotency-Key` | Opcional, enviado por el router |
| Backstage → API | `X-Correlation-Id` | Generado automáticamente si ausente |

### 3.3 Configuración de integración (`app-config.yaml`)

```yaml
platformRequests:
  baseUrl: http://localhost:8000      # URL del Self Service API
  auth:
    headerName: x-api-key             # Nombre del header de autenticación
    secret: change-me                 # API key compartida
```

## 4. Diseño de Estructuras de Datos

### 4.1 Modelo Entidad-Relación

```mermaid
erDiagram
    SERVICE_REQUESTS {
        string request_id PK "UUID (36 chars)"
        string request_type "storage_bucket"
        string service_name "3-120 chars"
        string team "2-120 chars"
        string environment "qa | stg | prod"
        string requested_by "3-120 chars"
        json spec_json "BucketSpec serializado"
        enum status "PENDING..FAILED"
        text status_reason "nullable"
        string idempotency_key UK "nullable, 255 chars"
        datetime created_at "timezone-aware"
        datetime updated_at "timezone-aware, auto"
    }

    REQUEST_EVENTS {
        string event_id PK "UUID (36 chars)"
        string request_id FK "→ service_requests"
        string event_type "80 chars"
        json event_payload "default {}"
        string correlation_id "nullable, 100 chars"
        datetime created_at "timezone-aware"
    }

    PROVISIONED_RESOURCES {
        string resource_id PK "bucket/{name}, 120 chars"
        string request_id FK "→ service_requests"
        string resource_type "storage_bucket, 50 chars"
        string resource_name "bucket name, 255 chars"
        json resource_metadata "resultado completo"
        datetime created_at "timezone-aware"
    }

    SERVICE_REQUESTS ||--o{ REQUEST_EVENTS : "genera"
    SERVICE_REQUESTS ||--o| PROVISIONED_RESOURCES : "produce"
```

### 4.2 Estados y transiciones

```mermaid
stateDiagram-v2
    [*] --> APPROVED: Validación exitosa
    [*] --> REJECTED: Validación fallida
    REJECTED --> [*]
    APPROVED --> PROVISIONING: Worker toma solicitud
    PROVISIONING --> SUCCEEDED: Provisioning OK
    PROVISIONING --> FAILED: Provisioning error
    SUCCEEDED --> [*]
    FAILED --> [*]
```

| Estado | Descripción | Siguiente |
|--------|-------------|-----------|
| `APPROVED` | Validación exitosa, pendiente de provisioning | `PROVISIONING` |
| `REJECTED` | Validación fallida (estado terminal) | — |
| `PROVISIONING` | Worker en proceso de creación del recurso | `SUCCEEDED` / `FAILED` |
| `SUCCEEDED` | Recurso creado exitosamente (estado terminal) | — |
| `FAILED` | Error en provisioning (estado terminal) | — |

### 4.3 Eventos de auditoría

Cada solicitud genera una secuencia de eventos que constituye un trail de auditoría completo:

| Evento | Payload | Momento |
|--------|---------|---------|
| `REQUEST_RECEIVED` | `{request_type, service_name}` | Al recibir la solicitud |
| `VALIDATION_STARTED` | `{request_type}` | Antes de validar |
| `VALIDATION_FINISHED` | `{is_valid, errors}` | Resultado de validación |
| `REQUEST_APPROVED` | `{next_status: "APPROVED"}` | Si validación exitosa |
| `REQUEST_REJECTED` | `{reason: [...]}` | Si validación fallida |
| `PROVISIONING_STARTED` | `{request_type}` | Worker inicia provisioning |
| `PROVISIONING_FINISHED` | `{resource_id, provisioner}` | Provisioning exitoso |
| `PROVISIONING_FAILED` | `{error}` | Error en provisioning |
| `REQUEST_COMPLETED` | `{final_status}` | Estado terminal alcanzado |

### 4.4 Esquema del payload de solicitud (`BucketSpec`)

```json
{
  "request_type": "storage_bucket",
  "service_name": "payments-api",
  "team": "platform-payments",
  "environment": "qa",
  "requested_by": "johan.gomez",
  "spec": {
    "bucket_name": "payments-api-qa-artifacts",
    "region": "us-east-1",
    "versioning": true,
    "encryption": "AES256",
    "public_access": false,
    "tags": [
      "team:platform-payments",
      "data_classification:internal"
    ]
  }
}
```

### 4.5 Esquema del artefacto de provisioning

El provisioner genera un archivo JSON en `artifacts/{request_id}.json`:

```json
{
  "resource_id": "bucket/payments-api-qa-artifacts",
  "bucket_name": "payments-api-qa-artifacts",
  "region": "us-east-1",
  "versioning": true,
  "encryption": "AES256",
  "public_access": false,
  "tags": ["service:payments-api", "team:platform-payments", "environment:qa"],
  "provisioned_at": "2026-03-25T00:00:00+00:00",
  "provisioner": "mock"
}
```

## 5. Diseño de API REST

### 5.1 Endpoints

```
                    ┌──────────────────────────────────────────┐
                    │          Self Service API :8000           │
                    ├──────────────────────────────────────────┤
                    │                                          │
  Health ──────────►│  GET  /health              → 200         │
  Readiness ──────►│  GET  /ready               → 200         │
                    │                                          │
  Crear ──────────►│  POST /api/v1/requests     → 202 / 200   │
  Listar ─────────►│  GET  /api/v1/requests     → 200         │
  Detalle ────────►│  GET  /api/v1/requests/:id → 200 / 404   │
  Auditoría ──────►│  GET  /api/v1/requests/:id/events → 200  │
                    │                                          │
                    └──────────────────────────────────────────┘
```

### 5.2 Contrato de respuestas

**POST /api/v1/requests → 202 (nueva) / 200 (idempotente)**
```json
{
  "request_id": "uuid",
  "status": "APPROVED",
  "message": "Request accepted and approved for provisioning"
}
```

**GET /api/v1/requests → 200**
```json
{
  "items": [
    {
      "request_id": "uuid",
      "request_type": "storage_bucket",
      "service_name": "payments-api",
      "team": "platform-payments",
      "environment": "qa",
      "requested_by": "johan.gomez",
      "status": "SUCCEEDED",
      "status_reason": null,
      "spec": { "..." },
      "resource_id": "bucket/payments-api-qa-artifacts",
      "result": { "..." },
      "created_at": "2026-03-25T00:00:00Z",
      "updated_at": "2026-03-25T00:00:10Z"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

**GET /api/v1/requests/:id/events → 200**
```json
{
  "items": [
    {
      "event_id": "uuid",
      "event_type": "REQUEST_RECEIVED",
      "event_payload": {"request_type": "storage_bucket"},
      "correlation_id": "corr-abc",
      "created_at": "2026-03-25T00:00:00Z"
    }
  ],
  "total": 6,
  "limit": 50,
  "offset": 0
}
```

## 6. Diseño de Arquitectura por Capas

```mermaid
graph TB
    subgraph "Application Layer"
        API["API (FastAPI)"]
        WRK["Worker (polling loop)"]
    end

    subgraph "Domain Layer"
        SVC[RequestService]
        VAL[RequestValidator]
        ENT["Entities<br>(ServiceRequest, RequestEvent,<br>ProvisionedResource)"]
        PRT["Ports<br>(RepositoryPort, ProvisionerPort,<br>UnitOfWorkPort)"]
    end

    subgraph "Infrastructure Layer"
        REPO[SqlAlchemyRepository]
        UOW[SqlAlchemyUnitOfWork]
        ORM[ORM Models]
        PROV[MockProvisioner]
        LOG[JsonFormatter Logging]
        DB[(PostgreSQL / SQLite)]
    end

    subgraph "Shared"
        SCH[Pydantic Schemas]
        CFG[Settings / Config]
    end

    API --> SVC
    API --> SCH
    WRK --> PRT
    WRK --> PROV
    SVC --> VAL
    SVC --> PRT
    PRT -.->|implementado por| REPO
    PRT -.->|implementado por| PROV
    PRT -.->|implementado por| UOW
    REPO --> ORM
    UOW --> ORM
    ORM --> DB
    API --> LOG
    WRK --> LOG
    API --> CFG
    WRK --> CFG
```

**Principios aplicados:**

| Principio | Implementación |
|-----------|----------------|
| Separación de responsabilidades | Domain no depende de infraestructura; usa puertos abstractos |
| Dependency Inversion | `RepositoryPort` y `ProvisionerPort` son interfaces abstractas |
| Unit of Work | Transacciones explícitas con commit/rollback |
| Adapter Pattern | `MockProvisioner` implementa `ProvisionerPort`, reemplazable por Terraform/SDK |
| Idempotencia | `Idempotency-Key` con constraint único en BD |
| Vertical Slice | Un caso completo (storage_bucket) end-to-end |

## 7. Reglas de Validación

```mermaid
flowchart TD
    REQ[Solicitud recibida] --> R1{bucket_name<br>regex válido?}
    R1 -->|No| ERR[Acumula error]
    R1 -->|Sí| R2{Prefijo<br>service-env-?}
    R2 -->|No| ERR
    R2 -->|Sí| R3{public_access<br>== false?}
    R3 -->|No| ERR
    R3 -->|Sí| R4{encryption<br>AES256 o aws:kms?}
    R4 -->|No| ERR
    R4 -->|Sí| R5{Cada tag<br>tiene ':'?}
    R5 -->|No| ERR
    R5 -->|Sí| R6{prod →<br>us-east-1?}
    R6 -->|No| ERR
    R6 -->|Sí| OK[APPROVED]
    ERR --> REJECT[REJECTED con motivos]
```

## 8. Diseño de Despliegue

```mermaid
graph TB
    subgraph "Docker Compose"
        DB["PostgreSQL 16<br>:5432<br>platform/platform"]
        API["API Container<br>uvicorn :8000<br>API_KEY=change-me"]
        WRK["Worker Container<br>python -m application.worker.main<br>POLL_INTERVAL=2s"]
    end

    subgraph "Backstage"
        BST["Node.js<br>Frontend :3000<br>Backend :7007"]
    end

    API -->|"postgresql+psycopg2"| DB
    WRK -->|"postgresql+psycopg2"| DB
    BST -->|"HTTP :8000"| API

    style DB fill:#336791,color:#fff
    style API fill:#009688,color:#fff
    style WRK fill:#FF9800,color:#fff
    style BST fill:#6C47FF,color:#fff
```

## 9. Seguridad

| Control | Implementación |
|---------|----------------|
| Autenticación | API Key vía header `x-api-key` (configurable) |
| Validación de entrada | Pydantic con constraints de tipo, largo y formato |
| Idempotencia | Header `Idempotency-Key` con constraint único en BD |
| Cifrado obligatorio | `encryption` debe ser `AES256` o `aws:kms` |
| Acceso público bloqueado | `public_access=false` enforced por validación |
| No secrets en código | Variables de entorno + `python-dotenv` |
| Trazabilidad | `X-Correlation-Id` propagado en toda la cadena |
| Restricción regional | `prod` solo permite `us-east-1` |

## 10. Observabilidad

| Componente | Implementación |
|------------|----------------|
| Logging estructurado | JSON con campos: `timestamp`, `level`, `message`, `request_id`, `correlation_id`, `stage`, `status` |
| Correlation ID | Generado automáticamente o recibido vía header, propagado a eventos |
| Health check | `GET /health` — liveness probe |
| Readiness check | `GET /ready` — valida conexión a BD |
| Audit trail | Tabla `request_events` con cada transición de estado consultable vía API |
| Artefactos | JSON en `artifacts/{request_id}.json` como evidencia del provisioning |