# scaffolder-backend-module-platform-requests

Módulo del Scaffolder de Backstage que registra la acción custom `company:platformRequest:create`. Permite que los templates de Backstage creen solicitudes de recursos de infraestructura directamente contra la Platform Self-Service API.

## Acción: `company:platformRequest:create`

### Input

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `request_type` | string | Sí | Tipo de recurso (ej: `storage_bucket`) |
| `service_name` | string | Sí | Nombre del servicio solicitante |
| `team` | string | Sí | Equipo responsable |
| `environment` | `qa` \| `stg` \| `prod` | Sí | Ambiente destino |
| `requested_by` | string | Sí | Usuario solicitante |
| `spec` | object | Sí | Especificación del recurso (`bucket_name`, `region`, `versioning`, `encryption`, `public_access`, `tags`) |

### Output

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `request_id` | string | UUID de la solicitud creada |
| `status` | string | Estado de la solicitud (`APPROVED` o `REJECTED`) |
| `details_url` | string | URL del detalle: `/platform/requests/{id}` |

### Comportamiento

1. Valida input/output con Zod schemas
2. Inyecta automáticamente los tags `service:{name}`, `team:{team}` y `environment:{env}` (sin duplicar si el usuario ya los proporcionó)
3. Llama a `PlatformApiClient.createRequest()` contra la Self-Service API
4. Expone los resultados como outputs del paso del Scaffolder

## Estructura

```
src/
├── module.ts                            # Registro del módulo en el Scaffolder
└── actions/
    └── createPlatformRequest.ts         # Implementación de la acción
```

## Uso en templates

```yaml
steps:
  - id: create-request
    name: Solicitar recurso
    action: company:platformRequest:create
    input:
      request_type: storage_bucket
      service_name: ${{ parameters.service_name }}
      team: ${{ parameters.team }}
      environment: ${{ parameters.environment }}
      requested_by: ${{ user.entity.metadata.name }}
      spec:
        bucket_name: ${{ parameters.bucket_name }}
        region: ${{ parameters.region }}
        versioning: ${{ parameters.versioning }}
        encryption: ${{ parameters.encryption }}
        public_access: ${{ parameters.public_access }}
        tags: ${{ parameters.tags }}
```

## Configuración

Reutiliza la configuración de `platformRequests` en `app-config.yaml`:

```yaml
platformRequests:
  baseUrl: http://localhost:8000
  auth:
    headerName: x-api-key
    secret: change-me
```

## Instalación

```bash
yarn --cwd packages/backend add @internal/backstage-plugin-scaffolder-backend-module-platform-requests
```

Registrar en `packages/backend/src/index.ts`:

```ts
backend.add(import('@internal/backstage-plugin-scaffolder-backend-module-platform-requests'));
```
