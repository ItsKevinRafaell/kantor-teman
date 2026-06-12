const db = require('../db');

class KantorTemanService {
  constructor() {
    this.apiBase = process.env.KANTORTEMAN_API_URL || 'https://api.kantorteman.com';
    this.apiKey = process.env.KANTORTEMAN_API_KEY;
  }

  async fetchLeads() {
    if (!this.apiKey) {
      console.log('[KantorTeman] API key not configured');
      return [];
    }

    try {
      const response = await fetch(this.apiBase + '/leads', {
        headers: {
          'Authorization': 'Bearer ' + this.apiKey,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('API error: ' + response.status);
      }

      return await response.json();
    } catch (error) {
      console.error('[KantorTeman] Error fetching leads:', error.message);
      return [];
    }
  }

  async syncLeads() {
    const leads = await this.fetchLeads();
    let synced = 0;

    for (const lead of leads) {
      try {
        await db.query(
          'INSERT INTO conversations (phone, contact_name, source) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING',
          [lead.phone, lead.name, 'kantorteman']
        );
        synced++;
      } catch (error) {
        console.error('[KantorTeman] Error syncing lead:', error.message);
      }
    }

    console.log('[KantorTeman] Synced ' + synced + ' leads');
    return synced;
  }

  async createCampaign(name, message) {
    if (!this.apiKey) {
      return { success: false, error: 'API key not configured' };
    }

    try {
      const response = await fetch(this.apiBase + '/campaigns', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + this.apiKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, message })
      });

      return await response.json();
    } catch (error) {
      console.error('[KantorTeman] Error creating campaign:', error.message);
      return { success: false, error: error.message };
    }
  }

  async getCampaignStats(campaignId) {
    if (!this.apiKey) {
      return null;
    }

    try {
      const response = await fetch(this.apiBase + '/campaigns/' + campaignId + '/stats', {
        headers: {
          'Authorization': 'Bearer ' + this.apiKey
        }
      });

      return await response.json();
    } catch (error) {
      console.error('[KantorTeman] Error fetching stats:', error.message);
      return null;
    }
  }
}

module.exports = new KantorTemanService();
