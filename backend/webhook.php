<?php
/**
 * Webhook for auto-deploy
 * Usage: https://kantorteman.my.id/backend/webhook.php?key=YOUR_SECRET
 */

// Set your secret key here
$secret = 'change-me-to-random-string';

// Check key
$key = $_GET['key'] ?? '';
if ($key !== $secret) {
    http_response_code(403);
    echo 'Forbidden';
    exit;
}

// Run deploy script
$output = [];
$code = 0;
exec('cd ' . __DIR__ . ' && bash deploy.sh 2>&1', $output, $code);

// Log the deploy
$log = date('Y-m-d H:i:s') . ' - ' . ($code === 0 ? 'OK' : 'FAIL') . "\n";
@file_put_contents('/tmp/deploy.log', $log, FILE_APPEND);

echo $code === 0 ? 'OK' : 'FAIL: ' . implode("\n", $output);