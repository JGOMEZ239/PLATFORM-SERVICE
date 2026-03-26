import { coreServices, createBackendModule } from '@backstage/backend-plugin-api';
import {
  scaffolderActionsExtensionPoint,
} from '@backstage/plugin-scaffolder-node';
import { createPlatformRequestAction } from './actions/createPlatformRequest';

const scaffolderPlatformRequestsModule = createBackendModule({
  pluginId: 'scaffolder',
  moduleId: 'platform-requests',
  register(env) {
    env.registerInit({
      deps: {
        scaffolder: scaffolderActionsExtensionPoint,
        config: coreServices.rootConfig,
        logger: coreServices.logger,
      },
      async init({ scaffolder, config, logger }) {
        scaffolder.addActions(
          createPlatformRequestAction({ config, logger }),
        );
      },
    });
  },
});

export default scaffolderPlatformRequestsModule;