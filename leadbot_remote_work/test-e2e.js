const BASE_URL = process.env.TEST_URL || 'http://localhost:3000';
let passed = 0;
let failed = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log('  ✅ ' + name);
    passed++;
  } catch (error) {
    console.log('  ❌ ' + name + ': ' + error.message);
    failed++;
  }
}

async function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(message + ' - Expected: ' + expected + ', Got: ' + actual);
  }
}

async function run() {
  console.log('\n📋 LeadBot E2E Tests\n' + '='.repeat(40));

  // Health check
  await test('Health endpoint returns ok', async () => {
    const res = await fetch(BASE_URL + '/api/health');
    const data = await res.json();
    await assertEqual(data.status, 'ok', 'Health status');
  });

  // API info
  await test('API info endpoint works', async () => {
    const res = await fetch(BASE_URL + '/api');
    const data = await res.json();
    await assertEqual(data.name, 'LeadBot API', 'API name');
    await assertEqual(data.status, 'running', 'API status');
  });

  // Dashboard stats
  await test('Dashboard stats returns valid data', async () => {
    const res = await fetch(BASE_URL + '/api/dashboard/stats');
    const data = await res.json();
    if (typeof data.total !== 'number') throw new Error('total not a number');
    if (typeof data.active !== 'number') throw new Error('active not a number');
  });

  // Keywords
  await test('Get keywords returns array', async () => {
    const res = await fetch(BASE_URL + '/api/dashboard/keywords');
    const data = await res.json();
    if (!Array.isArray(data)) throw new Error('Keywords not array');
  });

  // Conversations
  await test('Get conversations returns array', async () => {
    const res = await fetch(BASE_URL + '/api/dashboard/conversations');
    const data = await res.json();
    if (!Array.isArray(data)) throw new Error('Conversations not array');
  });

  // Webhook - keyword trigger
  await test('Webhook triggers keyword response', async () => {
    const testPhone = '62812345678' + Date.now().toString().slice(-4);
    const res = await fetch(BASE_URL + '/api/webhook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sender: testPhone,
        message: 'halo',
        name: 'E2E Test'
      })
    });
    const data = await res.json();
    await assertEqual(data.success, true, 'Webhook success');
    await assertEqual(data.autoReply, true, 'Auto reply triggered');
  });

  // Dashboard UI
  await test('Dashboard HTML loads', async () => {
    const res = await fetch(BASE_URL + '/');
    const ct = res.headers.get('content-type');
    if (!ct.includes('html')) throw new Error('Not HTML: ' + ct);
  });

  // Verify stats updated
  await test('Stats reflect new data', async () => {
    const res = await fetch(BASE_URL + '/api/dashboard/stats');
    const data = await res.json();
    if (data.messagesToday < 1) throw new Error('No messages today');
  });

  console.log('\n' + '='.repeat(40));
  console.log('📊 Results: ' + passed + ' passed, ' + failed + ' failed\n');

  process.exit(failed > 0 ? 1 : 0);
}

run().catch(err => {
  console.error('Test error:', err);
  process.exit(1);
});
