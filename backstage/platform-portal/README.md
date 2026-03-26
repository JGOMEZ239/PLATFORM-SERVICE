# Platform Portal (Backstage)

Portal de autoservicio para solicitar y dar seguimiento a recursos de plataforma, construido sobre [Backstage](https://backstage.io) v1.49.1.

## Requisitos

- Node.js 22 o 24
- Yarn 4 (4.4.1)
- Platform API corriendo en `http://localhost:8000` (ver `app-config.yaml`)
- Variable de entorno `GITHUB_TOKEN` para la integración con GitHub

## Inicio rápido

```sh
yarn install
yarn start
```

Esto levanta el frontend en `http://localhost:3000` y el backend en `http://localhost:7007`.

## Estructura del proyecto

```
platform-portal/
├── packages/
│   ├── app/                          # Frontend (React 18 + Material-UI)
│   │   └── src/
│   │       ├── App.tsx               # Rutas principales (/platform/requests)
│   │       ├── App.test.tsx          # Test de renderizado
│   │       ├── components/platform/
│   │       │   ├── PlatformRequestsHomePage.tsx   # Página principal de solicitudes
│   │       │   └── PlatformRequestDetailsPage.tsx # Detalle y auditoría de solicitud
│   │       └── modules/nav/          # Sidebar, logos y navegación
│   │   └── e2e-tests/
│   │       └── app.test.ts           # Test E2E con Playwright
│   └── backend/                      # Backend (Node.js)
│       └── src/index.ts              # Registro de plugins y módulos
├── plugins/
│   ├── platform-requests-backend/    # Plugin: proxy a la Platform API
│   │   └── src/
│   │       ├── plugin.ts             # Definición del plugin (ID: platform-requests)
│   │       ├── routes/
│   │       │   └── requestsRouter.ts # Endpoints GET/POST /requests
│   │       └── services/
│   │           └── PlatformApiClient.ts # Cliente HTTP hacia la Platform API
│   └── scaffolder-backend-module-platform-requests/
│       └── src/
│           ├── module.ts             # Módulo scaffolder
│           └── actions/
│               └── createPlatformRequest.ts # Acción company:platformRequest:create
├── templates/
│   └── request-storage-bucket/       # Template de solicitud de bucket S3
│       └── template.yaml
├── examples/                         # Entidades y datos de ejemplo para el catálogo
├── app-config.yaml                   # Configuración de desarrollo
├── app-config.production.yaml        # Configuración de producción (PostgreSQL)
├── catalog-info.yaml                 # Registro del componente en el catálogo
└── playwright.config.ts              # Configuración de tests E2E
```

## Plugins propios

### platform-requests-backend

Expone endpoints que actúan como proxy hacia la Platform API. Usa `PlatformApiClient` para comunicarse con el backend de self-service.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/platform-requests/health` | Health check del plugin |
| POST | `/api/platform-requests/requests` | Crear solicitud (proxy a Platform API) |
| GET | `/api/platform-requests/requests/:id` | Consultar solicitud por ID |
| GET | `/api/platform-requests/requests/:id/events` | Auditoría de eventos |

Headers soportados en `POST`: `x-api-key`, `Idempotency-Key`.

### scaffolder-backend-module-platform-requests

Registra la acción `company:platformRequest:create` en el Scaffolder para que los templates puedan crear solicitudes contra la Platform API.

**Input de la acción:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `request_type` | string | Tipo de recurso (ej: `storage_bucket`) |
| `service_name` | string | Nombre del servicio |
| `team` | string | Equipo responsable |
| `environment` | `qa` \| `stg` \| `prod` | Ambiente |
| `requested_by` | string | Solicitante |
| `spec` | object | Especificación del recurso (bucket_name, region, etc.) |

**Output de la acción:**

| Campo | Descripción |
|-------|-------------|
| `request_id` | ID de la solicitud creada |
| `status` | Estado de la solicitud |
| `details_url` | URL para ver el detalle (`/platform/requests/{id}`) |

**Tags automáticos:** la acción inyecta automáticamente los tags `service:{name}`, `team:{team}` y `environment:{env}` antes de enviar la solicitud al API. No se duplican si el usuario ya los proporcionó.

## Páginas del frontend

| Ruta | Componente | Descripción |
|------|------------|-------------|
| `/platform/requests` | `PlatformRequestsHomePage` | Dashboard con acceso a crear solicitudes y consultar por ID |
| `/platform/requests/:id` | `PlatformRequestDetailsPage` | Detalle de solicitud, resultado de provisioning y trail de auditoría |
| `/create` | Scaffolder | Selección y ejecución de templates |

## Templates

### request-storage-bucket

Template del Scaffolder para solicitar la creación de un bucket S3 seguro.

**Parámetros:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `service_name` | string | Sí | — | Nombre del servicio |
| `team` | string | Sí | — | Equipo responsable |
| `environment` | enum | Sí | — | `qa`, `stg`, `prod` |
| `bucket_name` | string | Sí | — | Sufijo del bucket (nombre final: `{service}-{env}-{suffix}`) |
| `region` | enum | Sí | — | `us-east-1`, `us-east-2` |
| `versioning` | boolean | No | `true` | Habilitar versionamiento |
| `encryption` | enum | No | `AES256` | `AES256` o `aws:kms` |
| `public_access` | boolean | No | `false` | Acceso público |
| `tags` | array | No | `[]` | Tags adicionales en formato `key:value`. Tags de service, team y environment se agregan automáticamente |

## Plugins de Backstage registrados

El backend registra los siguientes plugins y módulos en [packages/backend/src/index.ts](packages/backend/src/index.ts):

- **app-backend** — Sirve el frontend
- **auth-backend** + guest provider — Autenticación
- **catalog-backend** — Catálogo de entidades
- **scaffolder-backend** — Motor de templates
- **permission-backend** — Permisos (política allow-all)
- **platform-requests-backend** — Plugin custom de solicitudes
- **scaffolder-backend-module-platform-requests** — Acción custom del scaffolder

## Scripts disponibles

| Comando | Descripción |
|---------|-------------|
| `yarn start` | Inicia frontend y backend en modo desarrollo |
| `yarn build:backend` | Compila el backend |
| `yarn build:all` | Compila todos los paquetes |
| `yarn build-image` | Construye imagen Docker desde packages/backend/Dockerfile |
| `yarn tsc` | Verificación de tipos TypeScript |
| `yarn test` | Ejecuta tests unitarios |
| `yarn test:all` | Tests con cobertura |
| `yarn test:e2e` | Tests end-to-end (Playwright) |
| `yarn lint` | Linter (cambios desde origin/main) |
| `yarn lint:all` | Linter completo |
| `yarn prettier:check` | Verificación de formato |
| `yarn clean` | Limpia artefactos de build |
| `yarn new` | Scaffoldear nuevo plugin o paquete |

## Configuración

La configuración se gestiona en `app-config.yaml` (desarrollo) y `app-config.production.yaml` (producción).

### Desarrollo

| Clave | Default | Descripción |
|-------|---------|-------------|
| `app.baseUrl` | `http://localhost:3000` | URL del frontend |
| `backend.baseUrl` | `http://localhost:7007` | URL del backend |
| `backend.database.client` | `better-sqlite3` | Base de datos (in-memory) |
| `platformRequests.baseUrl` | `http://localhost:8000` | URL de la Platform API |
| `platformRequests.auth.headerName` | `x-api-key` | Nombre del header de autenticación |
| `platformRequests.auth.secret` | `change-me` | API key para la Platform API |
| `integrations.github.token` | `${GITHUB_TOKEN}` | Token de GitHub |
| `auth.providers.guest` | habilitado | Autenticación guest para desarrollo |

### Producción

| Variable de entorno | Descripción |
|---------------------|-------------|
| `POSTGRES_HOST` | Hostname de PostgreSQL |
| `POSTGRES_PORT` | Puerto de PostgreSQL |
| `POSTGRES_USER` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL |
| `GITHUB_TOKEN` | Token de integración con GitHub |

## Tests

- **Unitarios**: `yarn test` — Verificación de renderizado del App y tests de plugins
- **E2E**: `yarn test:e2e` — Playwright levanta automáticamente frontend (3000) y backend (7007), con timeout de 60s por test y screenshots en caso de falla
