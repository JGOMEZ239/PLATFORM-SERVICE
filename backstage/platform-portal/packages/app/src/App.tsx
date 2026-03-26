import { Route } from 'react-router-dom';
import { FlatRoutes } from '@backstage/core-app-api';
import { createApp } from '@backstage/frontend-defaults';
import { convertLegacyAppRoot } from '@backstage/core-compat-api';

import catalogPlugin from '@backstage/plugin-catalog/alpha';
import { navModule } from './modules/nav';

import { PlatformRequestsHomePage } from './components/platform/PlatformRequestsHomePage';
import { PlatformRequestDetailsPage } from './components/platform/PlatformRequestDetailsPage';

const convertedRootFeatures = convertLegacyAppRoot(
  <FlatRoutes>
    <Route path="/platform/requests" element={<PlatformRequestsHomePage />} />
    <Route
      path="/platform/requests/:id"
      element={<PlatformRequestDetailsPage />}
    />
  </FlatRoutes>,
);

const app = createApp({
  features: [catalogPlugin, navModule, ...convertedRootFeatures],
});

export default app;
