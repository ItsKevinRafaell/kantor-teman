module.exports = {
  apps: [{
    name: 'leadbot',
    script: 'src/app.js',
    cwd: '/opt/leadbot',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production'
    },
    error_file: '/var/log/leadbot-error.log',
    out_file: '/var/log/leadbot-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
