#!/usr/bin/env node

const baseUrl = (
  process.env.AUTOLEAD_BRIDGE_URL
  || process.env.KANTORTEMAN_BRIDGE_URL
  || `http://127.0.0.1:${process.env.PORT || 3000}`
).replace(/\/+$/, '');

const token = process.env.KANTORTEMAN_BRIDGE_TOKEN || process.env.KANTORTEMAN_API_KEY || '';
const shouldSend = String(process.env.AUTOLEAD_SMOKE_SEND || '').toLowerCase() === 'true';
const target = process.env.AUTOLEAD_SMOKE_TARGET || '';
const message = process.env.AUTOLEAD_SMOKE_MESSAGE || 'Smoke test AutoLead demo bridge from KantorTeman integration.';

function join(path) {
  return `${baseUrl}/${String(path).replace(/^\/+/, '')}`;
}

async function request(path, options = {}) {
  const response = await fetch(join(path), {
    ...options,
    headers: {
      Accept: 'application/json',
      'X-KantorTeman-Key': token,
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let body = text;
  try {
    body = text ? JSON.parse(text) : {};
  } catch (error) {}
  if (!response.ok) {
    const error = typeof body === 'object' ? (body.error || body.message || JSON.stringify(body)) : body;
    throw new Error(`${response.status} ${error}`);
  }
  return body;
}

async function main() {
  if (!token) {
    throw new Error('KANTORTEMAN_BRIDGE_TOKEN or KANTORTEMAN_API_KEY is required');
  }

  const health = await request('/api/integrations/kantorteman/health');
  console.log(JSON.stringify({
    step: 'health',
    status: health.status,
    demo: health.demo,
    bridgeTokenConfigured: health.bridgeTokenConfigured,
    wahaConfigured: Boolean(health.waha?.configured),
  }, null, 2));

  if (!shouldSend) {
    console.log('AUTOLEAD_SMOKE_SEND is not true; skipping demo send.');
    return;
  }

  if (!target) {
    throw new Error('AUTOLEAD_SMOKE_TARGET is required when AUTOLEAD_SMOKE_SEND=true');
  }

  const result = await request('/api/integrations/kantorteman/whatsapp/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target,
      message,
      dry_run: true,
      request_id: `smoke-${Date.now()}`,
      business_name: 'AutoLead Smoke Test',
    }),
  });

  console.log(JSON.stringify({
    step: 'demo_send',
    success: result.success,
    action: result.action,
    dryRun: result.dryRun,
    provider: result.provider,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
