# Platform Self Service API

Implementación de referencia para el caso de prueba de Platform Team. La solución expone una capacidad de autoservicio para que un developer solicite la habilitación de un recurso técnico sin depender de ejecución manual del equipo de plataforma.

## Qué resuelve

- Recibe una solicitud de autoservicio
- Valida reglas mínimas de negocio y seguridad
- Orquesta el aprovisionamiento de un recurso
- Registra evidencia del proceso y del resultado (auditoría completa)
- Devuelve un estado consumible por otras plataformas o una UI interna

## Caso implementado

Se implementa un caso vertical completo para `storage_bucket`.

### Flujo

1. El developer envía una solicitud a `POST /api/v1/requests`
2. La API valida el payload y las políticas mínimas
3. Si pasa validación, la solicitud queda en estado `APPROVED`; si no, queda en `REJECTED` con motivos
4. Un worker independiente toma las solicitudes aprobadas
5. El worker ejecuta un provisioner simulado y genera un artefacto JSON en `artifacts/`
6. El resultado queda persistido con eventos de auditoría y estado final `SUCCEEDED`

## Arquitectura

- **FastAPI**: mecanismo de entrada (API REST)
- **SQLAlchemy + PostgreSQL**: persistencia de solicitudes, eventos y recursos provisionados
- **Worker separado**: procesamiento asíncrono con polling configurable
- **Mock Provisioner**: simulación del aprovisionamiento, reemplazable por Terraform/SDK cloud (patrón Adapter)
- **Unit of Work**: transacciones explícitas con commit/rollback
- **Logging estructurado**: JSON con `request_id`, `correlation_id`, `stage`, `status`
- **Artifacts directory**: evidencia del resultado para la demo local

Más detalle en [`docs/solution-design.md`](docs/solution-design.md).

## Estructura del repositorio

```text
self-service/
├── application/
│   ├── api/
│   │   └── main.py                  # FastAPI app, endpoints, middleware
│   └── worker/
│       └── main.py                  # Worker polling loop
├── domain/
│   ├── models/
│   │   └── entities.py              # ServiceRequest, RequestEvent, ProvisionedResource
│   ├── policies/
│   │   └── validation.py            # Reglas de validación de negocio
│   ├── ports/
│   │   └── repository.py            # Puertos abstractos (Repository, UoW, Provisioner)
│   └── services/
│       └── request_service.py       # Lógica de creación y eventos de ciclo de vida
├── infrastructure/
│   ├── observability/
│   │   └── logging.py               # JsonFormatter con correlation_id
│   ├── persistence/
│   │   ├── database.py              # Engine y SessionLocal
│   │   ├── orm_models.py            # Modelos SQLAlchemy
│   │   ├── sqlalchemy_repository.py # Implementación del puerto de repositorio
│   │   └── unit_of_work.py          # SqlAlchemyUnitOfWork
│   └── provisioners/
│       └── mock_provisioner.py      # Provisioner simulado (genera artefacto JSON)
├── shared/
│   ├── config.py                    # Variables de entorno y configuración
│   └── schemas.py                   # Schemas Pydantic (request/response)
├── tests/
│   ├── conftest.py                  # Fixtures (in-memory SQLite, TestClient)
│   ├── test_api.py                  # Tests de endpoints (13 tests)
│   ├── test_request_service.py      # Tests de servicio de dominio (4 tests)
│   └── test_validation.py           # Tests de reglas de validación (8 tests, sin I/O)
├── docs/
│   ├── solution-design.md           # Diseño de solución (integración, datos, diagramas)
├── artifacts/                       # Artefactos generados por el provisioner
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```

## Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/health` | No | Liveness probe |
| `GET` | `/ready` | No | Readiness probe (valida conexión a BD) |
| `POST` | `/api/v1/requests` | `x-api-key` | Crear solicitud (202 nueva, 200 idempotente) |
| `GET` | `/api/v1/requests` | `x-api-key` | Listar solicitudes (filtros: `status`, `team`, `environment`, `limit`, `offset`) |
| `GET` | `/api/v1/requests/{request_id}` | `x-api-key` | Consultar solicitud por ID |
| `GET` | `/api/v1/requests/{request_id}/events` | `x-api-key` | Eventos de auditoría paginados (`limit`, `offset`, `total`) |

### Headers soportados en `POST`

| Header | Requerido | Descripción |
|--------|-----------|-------------|
| `x-api-key` | Sí (si `API_KEY` está configurado) | Autenticación |
| `Idempotency-Key` | No | Previene creación duplicada |
| `X-Correlation-Id` | No | Traza distribuida (se genera automáticamente si no se envía) |

Documentación detallada en [`docs/solution-design.md`](docs/solution-design.md).

## Ejemplo de solicitud

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

## Reglas de validación

| Regla | Detalle |
|-------|---------|
| Naming convention | El `bucket_name` debe iniciar con `{service_name}-{environment}-` |
| Formato de nombre | Solo caracteres alfanuméricos, guiones y puntos (3-63 caracteres) |
| Acceso público | `public_access` debe ser `false` |
| Cifrado obligatorio | `encryption` debe ser `AES256` o `aws:kms` |
| Tags requeridos | Cada tag debe seguir el formato `key:value` |
| Tags automáticos | `service:{name}`, `team:{team}` y `environment:{env}` se inyectan automáticamente |
| Restricción regional | En `prod` solo se permite `us-east-1` |
| Idempotencia | Se soporta `Idempotency-Key` para evitar creaciones duplicadas |

## Configuración

| Variable de entorno | Default | Descripción |
|---------------------|---------|-------------|
| `APP_NAME` | `platform-self-service` | Nombre de la aplicación |
| `DATABASE_URL` | `sqlite+pysqlite:///./platform_self_service.db` | Cadena de conexión SQLAlchemy |
| `API_KEY` | _(deshabilitado)_ | API key para autenticación |
| `POLL_INTERVAL_SECONDS` | `2` | Intervalo de polling del worker (segundos) |
| `ARTIFACTS_DIR` | `./artifacts` | Directorio de artefactos de provisioning |

Soporta archivos `.env` vía `python-dotenv`.

## Ejecución rápida con Docker

```bash
make up
```

Esto levanta 3 servicios con Docker Compose:
- **db**: PostgreSQL 16 en puerto 5432
- **api**: FastAPI en puerto 8000 (`API_KEY=change-me`)
- **worker**: Polling loop con intervalo de 2 segundos

API disponible en `http://localhost:8000`.

Para detener:

```bash
make down
```

## Ejecución local sin Docker

```bash
make install
source .venv/bin/activate
export DATABASE_URL=sqlite+pysqlite:///./platform_self_service.db
make run-api
```

En otra terminal:

```bash
source .venv/bin/activate
export DATABASE_URL=sqlite+pysqlite:///./platform_self_service.db
PYTHONPATH=. python -m application.worker.main
```

## Demo rápida con curl

### Crear solicitud

```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: change-me' \
  -H 'Idempotency-Key: demo-001' \
  -d '{
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
  }'
```

### Consultar estado

```bash
curl http://localhost:8000/api/v1/requests/<request_id> -H 'x-api-key: change-me'
```

### Listar solicitudes

```bash
curl 'http://localhost:8000/api/v1/requests?team=platform-payments&limit=10' \
  -H 'x-api-key: change-me'
```

### Consultar auditoría

```bash
curl http://localhost:8000/api/v1/requests/<request_id>/events -H 'x-api-key: change-me'
```

## Pruebas

```bash
PYTHONPATH=. pytest -q
```

25 tests cubriendo:
- **API** (13 tests): health, ready, creación válida/inválida, idempotencia, correlation ID, consulta, listado con filtros, eventos paginados
- **Servicio** (4 tests): flujo completo de creación, validación, idempotencia, eventos de ciclo de vida
- **Validación** (8 tests): cada regla de negocio con caso positivo y negativo

## Comandos disponibles (Makefile)

| Comando | Descripción |
|---------|-------------|
| `make install` | Crea virtualenv e instala dependencias |
| `make run-api` | Levanta la API con uvicorn (hot reload, puerto 8000) |
| `make run-worker` | Ejecuta el worker de procesamiento |
| `make test` | Ejecuta los tests con pytest |
| `make up` | Levanta todos los servicios con Docker Compose |
| `make down` | Detiene y limpia los contenedores |
| `make logs` | Muestra los logs de Docker Compose |

## Dependencias principales

| Paquete | Versión |
|---------|---------|
| FastAPI | 0.115.8 |
| Uvicorn | 0.34.0 |
| SQLAlchemy | 2.0.38 |
| Pydantic | 2.10.6 |
| psycopg2-binary | 2.9.10 |
| httpx | 0.28.1 |
| pytest | 8.3.4 |
| python-dotenv | 1.0.1 |


## Documentación adicional

- [Diseño de solución](docs/solution-design.md) — Diagramas de integración, estructuras de datos, arquitectura, despliegue y seguridad
