# Packages

Contiene las aplicaciones principales del portal de plataforma.

## Estructura

| Paquete | Descripción |
|---------|-------------|
| `app/` | Frontend React 18 con Material-UI. Incluye las páginas de solicitudes de plataforma (`PlatformRequestsHomePage`, `PlatformRequestDetailsPage`), navegación personalizada y tests E2E con Playwright. |
| `backend/` | Backend Node.js que registra y orquesta todos los plugins de Backstage: catálogo, scaffolder, autenticación, permisos, y los plugins custom (`platform-requests-backend`, `scaffolder-backend-module-platform-requests`). |

## Desarrollo

```bash
# Desde la raíz del proyecto
yarn start        # Inicia ambos paquetes (frontend :3000, backend :7007)
yarn build:all    # Compila todos los paquetes
yarn test         # Tests unitarios
yarn test:e2e     # Tests E2E con Playwright
```
