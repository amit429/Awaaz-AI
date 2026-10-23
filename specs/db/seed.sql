-- Awaaz seed (fictional). Run after 001_init.sql.
-- Stock voices: replace provider_voice_id with real ids from Cartesia / Sarvam dashboards.
insert into voices (kind, provider, provider_voice_id, label, languages) values
  ('stock', 'cartesia', 'REPLACE_ME', 'Calm, man, 50s', '{hi,en,mr}'),
  ('stock', 'cartesia', 'REPLACE_ME', 'Warm, woman, 30s', '{hi,en,mr}'),
  ('stock', 'sarvam', 'REPLACE_ME', 'Bulbul, woman', '{hi,mr,bn,ta,te,kn,ml,gu,pa,or}'),
  ('stock', 'kalpa', 'REPLACE_ME', 'Clear voice, slow', '{hi,en}');

-- Shared outbound number for the demo
insert into awaaz_numbers (number_e164, provider, purpose) values ('+910000000000', 'plivo', 'shared_outbound');

-- Demo users: create in Supabase Auth, then insert profiles / comm_profiles via the app onboarding.
