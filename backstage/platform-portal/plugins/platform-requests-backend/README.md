# platform-requests-backend

Plugin backend de Backstage que actúa como proxy HTTP entre el portal y la Platform Self-Service API. Permite al frontend consultar y crear solicitudes de recursos de infraestructura sin exponer directamente la API interna.

## Arquitectura

```
Backstage Frontend → platform-requests-backend (Express router) → PlatformApiClient → Platform API (:8000)
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/platform-requests/health` | Health check del plugin |
| `POST` | `/api/platform-requests/requests` | Crear solicitud (proxy a `POST /api/v1/requests`) |
| `GET` | `/api/platform-requests/requests/:id` | Consultar solicitud por ID |
| `GET` | `/api/platform-requests/requests/:id/events` | Obtener eventos de auditoría |

### Headers soportados en `POST`

| Header | Descripción |
|--------|-------------|
| `x-api-key` | Autenticación contra la Platform API |
| `Idempotency-Key` | Previene creación duplicada (se reenvía al backend) |

## Estructura

```
src/
├── plugin.ts                    # Definición del plugin (ID: platform-requests)
├── routes/
│   └── requestsRouter.ts       # Express router con los 4 endpoints
└── services/
    └── PlatformApiClient.ts     # Cliente HTTP hacia la Platform API
```

## Configuración

El plugin lee su configuración desde `app-config.yaml`:

```yaml
platformRequests:
  baseUrl: http://localhost:8000       # URL de la Platform Self-Service API
  auth:
    headerName: x-api-key             # Header de autenticación
    secret: change-me                  # API key
```

## Instalación

```bash
# Desde la raíz del proyecto
yarn --cwd packages/backend add @internal/backstage-plugin-platform-requests-backend
```

Registrar en `packages/backend/src/index.ts`:

```ts
const backend = createBackend();
// ...
backend.add(import('@internal/backstage-plugin-platform-requests-backend'));
```

## Desarrollo

```bash
cd plugins/platform-requests-backend
yarn start    # Inicia el plugin en modo standalone
```
