import React from 'react';
import { useParams } from 'react-router-dom';
import {
  Content,
  Header,
  InfoCard,
  Page,
  Progress,
  ResponseErrorPanel,
} from '@backstage/core-components';
import { useApi, discoveryApiRef } from '@backstage/core-plugin-api';
import { Grid, List, ListItem, ListItemText, Chip } from '@material-ui/core';

type PlatformRequest = {
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

type PlatformEvent = {
  event_id: string;
  event_type: string;
  event_payload?: Record<string, unknown>;
  correlation_id?: string | null;
  created_at: string;
};

export const PlatformRequestDetailsPage = () => {
  const { id = '' } = useParams<{ id: string }>();
  const discoveryApi = useApi(discoveryApiRef);

  const [request, setRequest] = React.useState<PlatformRequest | null>(null);
  const [events, setEvents] = React.useState<PlatformEvent[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const baseUrl = await discoveryApi.getBaseUrl('platform-requests');

        const [requestRes, eventsRes] = await Promise.all([
          fetch(`${baseUrl}/requests/${id}`),
          fetch(`${baseUrl}/requests/${id}/events`),
        ]);

        if (!requestRes.ok) {
          throw new Error(`Failed to fetch request: ${requestRes.status}`);
        }

        if (!eventsRes.ok) {
          throw new Error(`Failed to fetch events: ${eventsRes.status}`);
        }

        const requestContentType = requestRes.headers.get('content-type') ?? '';
        const eventsContentType = eventsRes.headers.get('content-type') ?? '';

        if (!requestContentType.includes('application/json')) {
          throw new Error(`Request endpoint did not return JSON. Content-Type: ${requestContentType}`);
        }

        if (!eventsContentType.includes('application/json')) {
          throw new Error(`Events endpoint did not return JSON. Content-Type: ${eventsContentType}`);
        }

        const requestJson = (await requestRes.json()) as PlatformRequest;
        const eventsJson = (await eventsRes.json()) as { items: PlatformEvent[] };

        setRequest(requestJson);
        setEvents(eventsJson.items);
      } catch (e) {
        setError(e as Error);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [id]);

  if (loading) {
    return <Progress />;
  }

  if (error) {
    return <ResponseErrorPanel error={error} />;
  }

  if (!request) {
    return <ResponseErrorPanel error={new Error('Request not found')} />;
  }

  return (
    <Page themeId="tool">
      <Header
        title={`Request ${request.request_id}`}
        subtitle={`${request.service_name} • ${request.environment}`}
      />
      <Content>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <InfoCard title="Summary">
              <p><strong>Status:</strong> <Chip size="small" label={request.status} /></p>
              <p><strong>Type:</strong> {request.request_type}</p>
              <p><strong>Service:</strong> {request.service_name}</p>
              <p><strong>Team:</strong> {request.team}</p>
              <p><strong>Environment:</strong> {request.environment}</p>
              <p><strong>Requested by:</strong> {request.requested_by}</p>
              <p><strong>Created at:</strong> {request.created_at ?? '-'}</p>
              <p><strong>Updated at:</strong> {request.updated_at ?? '-'}</p>
              <p><strong>Status reason:</strong> {request.status_reason ?? '-'}</p>
            </InfoCard>
          </Grid>

          <Grid item xs={12} md={6}>
            <InfoCard title="Provisioning result">
              <pre style={{ whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(request.result ?? {}, null, 2)}
              </pre>
            </InfoCard>
          </Grid>

          <Grid item xs={12}>
            <InfoCard title="Audit trail">
              <List>
                {events.map(event => (
                  <ListItem key={event.event_id} divider alignItems="flex-start">
                    <ListItemText
                      primary={`${event.event_type} • ${event.created_at}`}
                      secondary={
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(event.event_payload ?? {}, null, 2)}
                        </pre>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </InfoCard>
          </Grid>
        </Grid>
      </Content>
    </Page>
  );
};