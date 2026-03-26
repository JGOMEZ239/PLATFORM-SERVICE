import {
  coreServices,
  createBackendPlugin,
} from '@backstage/backend-plugin-api';
import { createRequestsRouter } from './routes/requestsRouter';
import { PlatformApiClient } from './services/PlatformApiClient';

const platformRequestsBackendPlugin = createBackendPlugin({
  pluginId: 'platform-requests',
  register(env) {
    env.registerInit({
      deps: {
        logger: coreServices.logger,
        httpRouter: coreServices.httpRouter,
        config: coreServices.rootConfig,
      },
      async init({ logger, httpRouter, config }) {
        const client = PlatformApiClient.fromConfig(config);
        const router = await createRequestsRouter({
          logger,
          client,
        });

        httpRouter.use(router);

        httpRouter.addAuthPolicy({
          path: '/health',
          allow: 'unauthenticated',
        });

        httpRouter.addAuthPolicy({
          path: '/requests',
          allow: 'unauthenticated',
        });

        httpRouter.addAuthPolicy({
          path: '/requests/:id',
          allow: 'unauthenticated',
        });

        httpRouter.addAuthPolicy({
          path: '/requests/:id/events',
          allow: 'unauthenticated',
        });

        logger.info('Platform requests backend plugin initialized');
      },
    });
  },
});

export default platformRequestsBackendPlugin;