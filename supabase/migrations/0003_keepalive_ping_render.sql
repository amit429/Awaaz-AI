create extension if not exists pg_net with schema extensions;
create extension if not exists pg_cron;

-- Render's free plan sleeps after 15 minutes without traffic: ping the API every 10 minutes.
select cron.unschedule('awaaz-keepalive') where exists (select 1 from cron.job where jobname = 'awaaz-keepalive');
select cron.schedule(
  'awaaz-keepalive',
  '*/10 * * * *',
  $$select net.http_get(url := 'https://awaaz-api-jv6d.onrender.com/v1/health')$$
);
