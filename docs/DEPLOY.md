# Deployment

| Part | Where | Notes |
|---|---|---|
| API | Render **free** web service `awaaz-api`, Singapore | `cd apps/api && pip install uv && uv sync --frozen --no-dev`; start `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`; `PYTHON_VERSION=3.14.8`; one instance (sessions are in memory) |
| Web | Vercel hobby, project `awaaz-web` (team Amit-Personal-Projects) | project **Root Directory is `apps/web`**; every push to `main` builds on Vercel from GitHub; routing in `apps/web/vercel.json` |
| Database and auth | Supabase project `awaaz` (ap-south-1) | migrations in `supabase/migrations`; Google and email sign-in; redirect URLs include the Vercel address |
| Keep-alive | Supabase `pg_cron` job `awaaz-keepalive` | pings `/v1/health` every 10 minutes so Render's free plan does not sleep (migration 0003) |
| Phone calls | Bolna | production custom model `awaaz-relay-prod` and a production relay agent whose webhook and LLM point at the Render address; set `BOLNA_RELAY_AGENT_ID` on Render |

## Environment (API, set on Render)
`APP_ENV=production`, `MOCK_PROVIDERS=false`, `PUBLIC_BASE_URL`, `WEBHOOK_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWKS_URL`, `SARVAM_API_KEY`, `BOLNA_API_KEY`, `BOLNA_RELAY_AGENT_ID`, `LLM_*`, `MAX_CALL_MINUTES`, `DAILY_MINUTES_PER_USER`, `PYTHON_VERSION`. Not set in production: `DEV_JWT_SECRET` (the dev-only token, console and WhatsApp dev endpoints answer 404).

## Environment (web, set on Vercel as build variables)
`VITE_API_BASE`, `VITE_WS_BASE`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`. No `VITE_DEV_LOGIN`.

## Redeploy
- API: push to `main` (auto deploy), or change an environment variable.
- Web: push to `main` (Vercel builds from GitHub). By hand: run `vercel deploy --prod --yes --scope amit-personal-projects` from the **repo root**, not from `apps/web`, because the project's Root Directory is already `apps/web` (running it inside `apps/web` would look for `apps/web/apps/web` and fail).
- Bolna agent after the API address changes: `PUBLIC_BASE_URL=... WEBHOOK_SECRET=... RELAY_MODEL=awaaz-relay-prod PRINT_ONLY=1 uv run python scripts/bolna_spike.py register` then `relay-agent`.

## Free-plan limits to remember
A deploy or restart ends calls in progress. Render's free plan allows about 750 instance hours a month, enough for one always-on service.

## Google sign-in sends people to localhost
Symptom: after choosing a Google account on the live site, the browser lands on `http://localhost:3000`. Cause: the app asks Supabase to return to the site's own address (`redirectTo = window.location.origin`), and Supabase only honours addresses on its allow-list; anything else falls back to the project's **Site URL**, which defaults to `http://localhost:3000`.
Fix, in the Supabase dashboard (Authentication, URL Configuration):
- **Site URL:** `https://awaaz-web-sigma.vercel.app`
- **Redirect URLs:** `https://awaaz-web-sigma.vercel.app/**` and, for local work, `http://localhost:5173/**`
The Google provider's own redirect (`https://<project>.supabase.co/auth/v1/callback`) stays as it is in Google Cloud Console.
Google's own permission screen is configured in Google Cloud Console (APIs and Services, OAuth consent screen): app name, support email, and the scopes email and profile. While its publishing status is "Testing", only listed test users can sign in. Awaaz additionally shows its own "Before you start" screen once per account; the consent is stored in the `consents` table (kind `terms`, with a version).
