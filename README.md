# Platform Service

Monorepo que contiene los componentes del sistema de autoservicio de plataforma (Internal Developer Platform). Permite a developers solicitar recursos de infraestructura (ej: buckets S3) de forma autónoma, con validación de reglas de negocio, aprovisionamiento asíncrono y trazabilidad completa.

## Arquitectura General

```
Developer → Backstage UI (formulario) → Scaffolder Template
    → company:platformRequest:create (acción custom)
    → PlatformApiClient → POST /api/v1/requests (Self-Service API)
    → RequestService → Validación → Persistencia (APPROVED/REJECTED) → Audit events

Worker (polling) → claim_next_approved() → Provisioner → Artifact JSON → mark_succeeded()

Developer → Backstage /platform/requests/:id → Plugin proxy → API GET → Detalle completo
```

La solución aplica **Arquitectura Hexagonal (Ports & Adapters)** con inversión de dependencias, Unit of Work y patrón Adapter para el aprovisionamiento.

## Estructura del Repositorio

```
PLATFORM-SERVICE/
├── backstage/
│   └── platform-portal/   # Portal web (Backstage) — UI + plugins + templates
├── self-service/           # Backend API + Worker asíncrono (Python)
└── README.md
```

### `backstage/platform-portal/`

Portal de autoservicio construido sobre [Backstage](https://backstage.io/) (v1.49.1). Proporciona una interfaz web donde los developers llenan formularios para solicitar recursos y consultan el estado de sus solicitudes en tiempo real.

- **Frontend:** React 18, Material-UI 4, rutas `/platform/requests` y `/platform/requests/:id`
- **Plugins propios:** `platform-requests-backend` (proxy HTTP) y `scaffolder-backend-module-platform-requests` (acción custom del Scaffolder)
- **Templates:** `request-storage-bucket` — formulario guiado para solicitar un bucket S3

**Tecnologías:** TypeScript 5.8, React 18, Node.js 22/24, Yarn 4.4.1, Playwright (E2E).

### `self-service/`

Backend de referencia que recibe solicitudes de recursos, valida reglas de negocio, orquesta el aprovisionamiento de forma asíncrona y mantiene un audit trail completo de cada operación.

- **API REST:** 6 endpoints (health, readiness, CRUD de solicitudes, eventos de auditoría)
- **Worker:** Polling loop configurable que procesa solicitudes aprobadas
- **Validación:** 6 reglas de negocio (naming, cifrado, acceso público, región, tags)
- **Observabilidad:** Logging estructurado JSON, Prometheus metrics, Grafana dashboards

**Tecnologías:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, PostgreSQL 16, Docker Compose.

## Inicio Rápido

```bash
# Backend (API + Worker + PostgreSQL + Prometheus + Grafana)
cd self-service
make up                # docker compose up -d --build
# → API:        http://localhost:8000/health
# → Prometheus: http://localhost:9090
# → Grafana:    http://localhost:3001 (admin/admin)

# Portal (Backstage)
cd backstage/platform-portal
yarn install
yarn dev
# → Frontend: http://localhost:3000
# → Backend:  http://localhost:7007
```

## Documentación

- [Self-Service Backend — README](self-service/README.md)
- [Backstage Portal — README](backstage/platform-portal/README.md)
- [Diseño de Solución](self-service/docs/solution-design.md) — Diagramas de integración, ER, máquina de estados, contratos API, arquitectura AWS propuesta