# Valhalla Freight password recovery — v0.19.17

The login screen now includes a working **Forgot password?** form and a **Reset password** page. Reset links expire after 20 minutes and become invalid after a successful reset. The endpoint responds identically for existing and nonexistent users. Passwords are hashed with the existing bcrypt implementation.

## Production setup required before email recovery works

Configure a real transactional SMTP account in `/opt/valhalla-freight/.env.production` on the AWS host (do **not** add credentials to Git or this ZIP):

```env
SMTP_HOST=your-smtp-server
SMTP_PORT=587
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=notifications@valhallatms.com
SMTP_USE_TLS=true
PASSWORD_RESET_BASE_URL=https://valhallatms.com
```

The sending address must be authorized by your email provider (SPF/DKIM as required). The AWS EC2 instance must be able to reach the SMTP host/port. Without SMTP, requests are accepted without revealing account existence, but **no email is sent**. SMTP delivery failures are logged server-side without exposing reset links to the client.

**Important:** Existing seeded admin login `admin@valhallafreight.local` is not a deliverable email address. Sign in as admin and update that account to a real, accessible email address in User Management before testing email recovery. If User Management does not allow changing the email, use a controlled admin procedure; do not rely on a `.local` address for password recovery.

## Deploying

1. Back up database and application. Copy the updated source into the repository.
2. Set the production environment values above.
3. `docker compose --env-file .env.production -f compose.production.yml up -d --build backend frontend`
4. Test with a real email account and verify that the link is delivered, expires, and cannot be reused.

**Security:** This version uses short-lived signed JWTs bound to the current password hash. For a high-traffic public service, add durable per-IP and per-account rate limits at the edge and API, plus security monitoring.
