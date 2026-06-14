const config = require('../config');
const conversationService = require('./conversationService');
const fonnteService = require('./fonnteService');

class TelegramPolling {
  constructor() {
    this.botToken = config.telegram.botToken;
    this.adminId = String(config.admin.telegramId || '');
    this.offset = 0;
    this.running = false;
  }

  async start() {
    if (!this.botToken) {
      console.log('[Telegram] Bot token not configured');
      return;
    }
    this.running = true;
    console.log('[Telegram] Polling started');
    this.poll();
  }

  async poll() {
    while (this.running) {
      try {
        const response = await fetch('https://api.telegram.org/bot' + this.botToken + '/getUpdates?offset=' + this.offset + '&timeout=10');
        const data = await response.json();
        if (data.ok && data.result.length > 0) {
          for (const update of data.result) {
            await this.handleUpdate(update);
            this.offset = update.update_id + 1;
          }
        }
      } catch (error) {
        console.error('[Telegram] Poll error:', error.message);
        await this.sleep(5000);
      }
    }
  }

  isAdmin(chatId) {
    return this.adminId && String(chatId) === this.adminId;
  }

  async handleUpdate(update) {
    if (!update.message) return;
    const chatId = update.message.chat.id;
    const text = update.message.text || '';

    if (!this.isAdmin(chatId)) {
      console.log('[Telegram] Ignored non-admin chat:', chatId);
      await this.sendMessage(chatId, 'Akses ditolak. Bot ini hanya untuk admin LeadBot.');
      return;
    }

    if (text === '/start') {
      await this.sendMessage(chatId, 'LeadBot Admin\n\n/stats - statistik\n/conversations - percakapan aktif\n/reply <phone> <message> - balas WA\n/help - bantuan');
    } else if (text === '/stats') {
      const stats = await conversationService.getDashboardStats();
      await this.sendMessage(chatId, 'Statistik\n\nTotal: ' + stats.total + '\nAktif: ' + stats.active + '\nEskalasi: ' + stats.escalated + '\nPesan hari ini: ' + stats.messagesToday);
    } else if (text === '/conversations') {
      const convs = await conversationService.getActiveConversations();
      if (convs.length === 0) return this.sendMessage(chatId, 'Belum ada percakapan aktif');
      const list = convs.slice(0, 10).map((c, i) => (i + 1) + '. ' + c.phone + ' - ' + c.status + ' - ' + (c.last_message || '-')).join('\n');
      await this.sendMessage(chatId, 'Percakapan Aktif\n\n' + list);
    } else if (text === '/help') {
      await this.sendMessage(chatId, 'Command:\n/start\n/stats\n/conversations\n/reply <phone> <message>');
    } else if (text.startsWith('/reply ')) {
      const parts = text.slice(7).split(' ');
      const phone = parts[0];
      const message = parts.slice(1).join(' ');
      if (!phone || !message) return this.sendMessage(chatId, 'Format: /reply <phone> <message>');
      const conversation = await conversationService.getOrCreateConversation(phone, 'Telegram Admin');
      await conversationService.addMessage(conversation.id, 'outbound', message, { responder: 'admin_telegram' });
      const sent = await fonnteService.sendMessage(phone, message);
      await conversationService.markHumanReply(conversation.id);
      await this.sendMessage(chatId, sent.success ? 'Terkirim ke ' + phone : 'Gagal: ' + sent.error);
    } else {
      await this.sendMessage(chatId, 'Command tidak dikenal. Ketik /help');
    }
  }

  async sendMessage(chatId, text) {
    try {
      await fetch('https://api.telegram.org/bot' + this.botToken + '/sendMessage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text }),
      });
    } catch (error) {
      console.error('[Telegram] Send error:', error.message);
    }
  }

  sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
  stop() { this.running = false; }
}

module.exports = new TelegramPolling();
