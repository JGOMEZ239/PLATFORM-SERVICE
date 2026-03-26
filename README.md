# Platform Service

Monorepo que contiene los componentes del sistema de autoservicio de plataforma. Permite a developers solicitar recursos de infraestructura (ej: buckets S3) de forma autónoma, con validación de reglas de negocio, aprovisionamiento asíncrono y trazabilidad completa.

## Estructura del Repositorio

```
PLATFORM-SERVICE/
├── backstage/          # Portal web (Backstage)
├── self-service/       # Backend API + Worker asíncrono
└── README.md
```

### `backstage/platform-portal/`

Portal de autoservicio construido sobre [Backstage](https://backstage.io/) (v1.49.1). Proporciona una interfaz web donde los developers llenan formularios para solicitar recursos y consultan el estado de sus solicitudes en tiempo real.

**Tecnologías:** TypeScript 5.8, React 18, Node.js 22, Yarn 4, Playwright (E2E).

### `self-service/`

Backend de referencia que recibe solicitudes de recursos, valida reglas de negocio, orquesta el aprovisionamiento de forma asíncrona y mantiene un audit trail completo de cada operación.


**Tecnologías:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, PostgreSQL 16, Docker Compose.

## Inicio Rápido

```bash
# Backend (API + Worker + PostgreSQL)
cd self-service
make up                # docker compose up -d --build
# → http://localhost:8000/health

# Portal (Backstage)
cd backstage/platform-portal
yarn install
yarn dev
# → http://localhost:3000
```