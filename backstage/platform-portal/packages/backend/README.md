# Platform Portal — Backend

Backend Node.js del portal de plataforma. Orquesta todos los plugins de Backstage y sirve como punto de entrada del servidor.

## Plugins registrados

El backend registra los siguientes plugins en `src/index.ts`:

| Plugin | Descripción |
|--------|-------------|
| `app-backend` | Sirve el frontend de React |
| `auth-backend` + guest provider | Autenticación (guest en desarrollo) |
| `catalog-backend` | Catálogo de entidades y componentes |
| `scaffolder-backend` | Motor de ejecución de templates |
| `permission-backend` | Control de permisos (política allow-all) |
| `platform-requests-backend` | Proxy HTTP hacia la Platform Self-Service API |
| `scaffolder-backend-module-platform-requests` | Acción custom `company:platformRequest:create` |
| `kubernetes-backend` | Integración con Kubernetes |
| `notifications-backend` | Sistema de notificaciones |
| `search-backend` | Motor de búsqueda |
| `signals-backend` | Señales en tiempo real |
| `techdocs-backend` | Documentación técnica |

## Desarrollo

```bash
# Desde la raíz del proyecto
yarn install

# Iniciar solo el backend
cd packages/backend
yarn start
# → http://localhost:7007
```

## Configuración

La configuración se lee desde `app-config.yaml` (desarrollo) y `app-config.production.yaml` (producción).

- **Desarrollo:** SQLite in-memory, autenticación guest
- **Producción:** PostgreSQL (variables `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`)

Para sobreescribir configuración localmente, crear `app-config.local.yaml` en la raíz del proyecto.

## Docker

```bash
# Desde la raíz del proyecto
yarn build-image
```

Construye una imagen Docker con el backend compilado usando el `Dockerfile` incluido en este paquete.

Read more about the
[auth-backend](https://github.com/backstage/backstage/blob/master/plugins/auth-backend/README.md)
and
[how to add a new provider](https://github.com/backstage/backstage/blob/master/docs/auth/add-auth-provider.md)

## Documentation

- [Backstage Readme](https://github.com/backstage/backstage/blob/master/README.md)
- [Backstage Documentation](https://backstage.io/docs)
