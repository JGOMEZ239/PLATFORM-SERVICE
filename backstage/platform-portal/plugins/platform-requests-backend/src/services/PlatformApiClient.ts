import { Config } from '@backstage/config';

export type CreateRequestInput = {
  request_type: string;
  service_name: string;
  team: string;
  environment: string;
  requested_by: string;
  spec: Record<string, unknown>;
};

export type PlatformRequest = {
  request_id: string;
  request_type: string;
  service_name: string;
  team: string;
  environment: string;
  requested_by: string;
  status: string;
  status_reason?: string;
  created_at?: string;
  updated_at?: string;
  result?: Record<string, unknown>;
};

export type PlatformEvent = {
  event_id: string;
  request_id: string;
  event_type: string;
  event_payload?: Record<string, unknown>;
  correlation_id?: string;
  created_at: string;
};

type RequestOptions = {
  apiKey?: string;
  idempotencyKey?: string;
};

export class PlatformApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly defaultApiKey?: string,
    private readonly headerName = 'x-api-key',
  ) {}

  static fromConfig(config: Config) {
    const baseUrl = config.getString('platformRequests.baseUrl');
    const apiKey = config.getOptionalString('platformRequests.auth.secret');
    const headerName =
      config.getOptionalString('platformRequests.auth.headerName') ?? 'x-api-key';

    return new PlatformApiClient(baseUrl, apiKey, headerName);
  }

  private async doFetch<T>(
    path: string,
    init?: RequestInit,
    options?: RequestOptions,
  ): Promise<T> {
    const headers = new Headers(init?.headers ?? {});

    if (!headers.has('Content-Type') && init?.method && init.method !== 'GET') {
      headers.set('Content-Type', 'application/json');
    }

    const effectiveApiKey = options?.apiKey ?? this.defaultApiKey;

    if (effectiveApiKey) {
      headers.set(this.headerName, effectiveApiKey);
    }

    if (options?.idempotencyKey) {
      headers.set('Idempotency-Key', options.idempotencyKey);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Platform API error: ${response.status} ${text}`);
    }

    return response.json() as Promise<T>;
  }

  async createRequest(
    input: CreateRequestInput,
    options?: RequestOptions,
  ): Promise<{ request_id: string; status: string }> {
    return this.doFetch(
      '/api/v1/requests',
      {
        method: 'POST',
        body: JSON.stringify(input),
      },
      options,
    );
  }

  async getRequest(id: string, options?: RequestOptions): Promise<PlatformRequest> {
    return this.doFetch(`/api/v1/requests/${id}`, { method: 'GET' }, options);
  }

  async getRequestEvents(id: string, options?: RequestOptions): Promise<PlatformEvent[]> {
    return this.doFetch(`/api/v1/requests/${id}/events`, { method: 'GET' }, options);
  }
}