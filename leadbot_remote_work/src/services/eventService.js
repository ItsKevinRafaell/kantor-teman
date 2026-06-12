const clients = new Set();

function writeEvent(client, type, payload) {
  client.res.write('event: ' + type + '\n');
  client.res.write('data: ' + JSON.stringify({ type, payload, timestamp: new Date().toISOString() }) + '\n\n');
}

function stream(req, res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const client = { id: Date.now() + ':' + Math.random(), res };
  clients.add(client);
  writeEvent(client, 'connected', { clients: clients.size });

  const heartbeat = setInterval(() => writeEvent(client, 'heartbeat', {}), 25000);

  req.on('close', () => {
    clearInterval(heartbeat);
    clients.delete(client);
  });
}

function emit(type, payload = {}) {
  for (const client of clients) {
    try {
      writeEvent(client, type, payload);
    } catch (error) {
      clients.delete(client);
    }
  }
}

module.exports = {
  stream,
  emit,
  getClientCount: () => clients.size,
};
