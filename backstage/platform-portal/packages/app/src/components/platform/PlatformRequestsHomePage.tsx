import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Content,
  Header,
  InfoCard,
  Page,
} from '@backstage/core-components';
import { Button, Grid, TextField } from '@material-ui/core';

export const PlatformRequestsHomePage = () => {
  const [requestId, setRequestId] = React.useState('');
  const navigate = useNavigate();

  const onOpenDetails = () => {
    const trimmed = requestId.trim();
    if (!trimmed) return;
    navigate(`/platform/requests/${trimmed}`);
  };

  return (
    <Page themeId="tool">
      <Header
        title="Platform Requests"
        subtitle="Autoservicio y seguimiento de solicitudes"
      />
      <Content>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <InfoCard title="Create request">
              <p>
                En la siguiente fase conectaremos esta capacidad con Scaffolder
                en <strong>/create</strong>.
              </p>
              <Button
                variant="contained"
                color="primary"
                href="/create"
              >
                Open create
              </Button>
            </InfoCard>
          </Grid>

          <Grid item xs={12} md={6}>
            <InfoCard title="Open request details">
              <TextField
                fullWidth
                label="Request ID"
                value={requestId}
                onChange={e => setRequestId(e.target.value)}
                margin="normal"
              />
              <Button
                variant="contained"
                color="primary"
                onClick={onOpenDetails}
              >
                View details
              </Button>
            </InfoCard>
          </Grid>
        </Grid>
      </Content>
    </Page>
  );
};