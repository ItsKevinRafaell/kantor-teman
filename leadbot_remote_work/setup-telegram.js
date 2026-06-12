const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

async function getUpdates() {
  if (!BOT_TOKEN) {
    console.error('Set TELEGRAM_BOT_TOKEN dulu. Contoh: TELEGRAM_BOT_TOKEN=xxx node setup-telegram.js');
    process.exit(1);
  }

  const response = await fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/getUpdates');
  const data = await response.json();
  if (!data.ok) {
    console.log('Error:', data.description);
    return;
  }

  console.log('Kirim pesan ke bot Telegram, lalu run script ini lagi.');
  if (data.result.length > 0) {
    const chat = data.result[0].message.chat;
    console.log('Chat ID:', chat.id);
    console.log('Username:', chat.username || '-');
    console.log('Tambahkan ke .env: ADMIN_TELEGRAM_ID=' + chat.id);
  }
}

getUpdates().catch((error) => {
  console.error('Error:', error.message);
  process.exit(1);
});
