import express from 'express';
import Router from 'express-promise-router';
import { LoggerService } from '@backstage/backend-plugin-api';
import { PlatformApiClient } from '../services/PlatformApiClient';

export async function createRequestsRouter(options: {
  logger: LoggerService;
  client: PlatformApiClient;
}) {
  const { logger, client } = options;
  const router = Router();

  router.use(express.json());

  router.get('/health', async (_req, res) => {
    res.json({ status: 'ok' });
  });

  router.post('/requests', async (req, res) => {
    logger.info('Creating platform request through Backstage backend');

    const result = await client.createRequest(req.body, {
      apiKey: req.header('x-api-key') ?? undefined,
      idempotencyKey: req.header('Idempotency-Key') ?? undefined,
    });

    res.status(201).json(result);
  });

  router.get('/requests/:id', async (req, res) => {
    const result = await client.getRequest(req.params.id, {
      apiKey: req.header('x-api-key') ?? undefined,
    });
    res.json(result);
  });

  router.get('/requests/:id/events', async (req, res) => {
    const result = await client.getRequestEvents(req.params.id, {
      apiKey: req.header('x-api-key') ?? undefined,
    });
    res.json(result);
  });

  return router;
}