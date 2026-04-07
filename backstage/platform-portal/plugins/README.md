# Plugins

Plugins custom del portal de plataforma que extienden las capacidades de Backstage.

## Plugins incluidos

### `platform-requests-backend/`

Plugin backend que actúa como proxy HTTP entre el portal Backstage y la Platform Self-Service API. Expone endpoints REST para crear solicitudes, consultar estado y obtener eventos de auditoría.

- **ID del plugin:** `platform-requests`
- **Endpoints:** `GET /health`, `POST /requests`, `GET /requests/:id`, `GET /requests/:id/events`
- **Cliente HTTP:** `PlatformApiClient` — configurado desde `app-config.yaml` (`platformRequests.baseUrl`, `platformRequests.auth.secret`)

### `scaffolder-backend-module-platform-requests/`

Módulo del Scaffolder que registra la acción custom `company:platformRequest:create`. Permite que los templates de Backstage creen solicitudes de recursos directamente contra la Platform API.

- **Acción:** `company:platformRequest:create`
- **Validación:** Zod schema en input/output
- **Tags automáticos:** Inyecta `service:`, `team:`, `environment:` con deduplicación por prefijo
- **Output:** `request_id`, `status`, `details_url`

## Desarrollo

```bash
# Iniciar un plugin en modo standalone
cd plugins/<plugin-name>
yarn start

# Crear un nuevo plugin
yarn new   # desde la raíz del proyecto
```
