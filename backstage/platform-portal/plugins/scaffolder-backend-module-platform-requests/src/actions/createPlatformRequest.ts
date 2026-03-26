import { Config } from '@backstage/config';
import { LoggerService } from '@backstage/backend-plugin-api';
import { createTemplateAction } from '@backstage/plugin-scaffolder-node';

type CreateRequestInput = {
  request_type: string;
  service_name: string;
  team: string;
  environment: string;
  requested_by: string;
  spec: {
    bucket_name: string;
    region: string;
    versioning: boolean;
    encryption: string;
    public_access: boolean;
    tags?: string[];
  };
};

type CreateRequestResponse = {
  request_id: string;
  status: string;
};

class PlatformApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly apiKey?: string,
    private readonly headerName = 'x-api-key',
  ) {}

  static fromConfig(config: Config) {
    const baseUrl = config.getString('platformRequests.baseUrl');
    const apiKey = config.getOptionalString('platformRequests.auth.secret');
    const headerName =
      config.getOptionalString('platformRequests.auth.headerName') ?? 'x-api-key';

    return new PlatformApiClient(baseUrl, apiKey, headerName);
  }

  async createRequest(input: CreateRequestInput): Promise<CreateRequestResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.apiKey) {
      headers[this.headerName] = this.apiKey;
    }

    const response = await fetch(`${this.baseUrl}/api/v1/requests`, {
      method: 'POST',
      headers,
      body: JSON.stringify(input),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Platform API createRequest failed: ${response.status} ${text}`);
    }

    return response.json() as Promise<CreateRequestResponse>;
  }
}

export const createPlatformRequestAction = (deps: {
  config: Config;
  logger: LoggerService;
}) => {
  const client = PlatformApiClient.fromConfig(deps.config);

  return createTemplateAction({
    id: 'company:platformRequest:create',
    description: 'Create a request in the Platform API',
    schema: {
      input: {
        request_type: z => z.string(),
        service_name: z => z.string(),
        team: z => z.string(),
        environment: z => z.enum(['qa', 'stg', 'prod']),
        requested_by: z => z.string(),
        spec: z =>
          z.object({
            bucket_name: z.string(),
            region: z.string(),
            versioning: z.boolean(),
            encryption: z.string(),
            public_access: z.boolean(),
            tags: z.array(z.string()).optional(),
          }),
      },
      output: {
        request_id: z => z.string(),
        status: z => z.string(),
        details_url: z => z.string(),
      },
    },
    async handler(ctx) {
      const autoTags = [
        `service:${ctx.input.service_name}`,
        `team:${ctx.input.team}`,
        `environment:${ctx.input.environment}`,
      ];
      const userTags = ctx.input.spec.tags ?? [];
      const existingPrefixes = new Set(
        userTags.filter(t => t.includes(':')).map(t => t.split(':')[0]),
      );
      const mergedTags = [
        ...autoTags.filter(t => !existingPrefixes.has(t.split(':')[0])),
        ...userTags,
      ];

      const input = {
        ...ctx.input,
        spec: { ...ctx.input.spec, tags: mergedTags },
      };

      deps.logger.info(
        `Creating request for ${ctx.input.service_name} in ${ctx.input.environment}`,
      );

      const result = await client.createRequest(input);

      ctx.output('request_id', result.request_id);
      ctx.output('status', result.status);
      ctx.output('details_url', `/platform/requests/${result.request_id}`);
    },
  });
};