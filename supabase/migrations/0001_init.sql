-- Awaaz: initial schema for Supabase Postgres
-- Users read their own rows (RLS on user_id = auth.uid()). Settings tables (comm_profiles, contacts, phrases)
-- may also be written by the user directly. Everything else is written by the API with the service role.

create extension if not exists pgcrypto;

-- ---------- Enums ----------
create type talk_mode as enum ('voice', 'type', 'replies', 'help', 'clarity', 'sign');
create type hear_mode as enum ('captions', 'clear', 'audio', 'summary', 'vibe', 'translate');
create type call_kind as enum ('relay', 'task', 'face', 'wa_relay');
create type call_direction as enum ('outbound', 'inbound');
create type call_status as enum ('created', 'ringing', 'connected', 'ended', 'failed', 'no_answer', 'busy');
create type turn_speaker as enum ('other', 'user', 'system');
create type turn_source as enum ('stt', 'typed', 'reply', 'phrase', 'draft', 'voice', 'clarity', 'keeper', 'disclosure', 'ask_repeat', 'dtmf');
create type task_status as enum ('draft', 'calling', 'waiting_approval', 'done', 'partial', 'failed', 'cancelled');
create type approval_status as enum ('pending', 'approved', 'declined', 'expired');
create type voice_kind as enum ('stock', 'clone');
create type job_status as enum ('queued', 'running', 'done', 'failed', 'cancelled');

create or replace function set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

-- ---------- Users and settings ----------
create table profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  phone_e164 text,
  disability_phrase text,               -- how the disclosure describes them, e.g. 'cannot speak', 'is deaf'
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger profiles_updated before update on profiles for each row execute function set_updated_at();

create table voices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,  -- null for stock voices
  kind voice_kind not null,
  provider text not null,               -- 'cartesia' | 'sarvam' | 'kalpa'
  provider_voice_id text not null,
  label text not null,                  -- 'My own voice', 'Calm, man, 50s'
  languages text[] not null default '{}',
  consent_text text,
  consent_at timestamptz,
  created_at timestamptz not null default now()
);

create table comm_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  preset text,                          -- 'mute' | 'deafspeak' | 'deaftype' | 'hoh' | 'speech' | 'lowread' | null (custom)
  talk_modes talk_mode[] not null default '{type,replies,help}',   -- ordered; first is default
  hear_modes hear_mode[] not null default '{audio,summary}',
  read_lang text not null default 'hi',
  type_lang text not null default 'hi-Latn',                        -- romanised Hindi
  voice_id uuid references voices(id),
  speech_rate numeric(3,2) not null default 0.75 check (speech_rate between 0.5 and 1.2),
  easy_font boolean not null default false,
  share_with_family boolean not null default false,
  updated_at timestamptz not null default now()
);
create trigger comm_profiles_updated before update on comm_profiles for each row execute function set_updated_at();

create table contacts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  phone_e164 text not null,
  call_lang text,                       -- language they speak, e.g. 'hi', 'mr'
  notes text,                           -- facts Awaaz may use on calls and tasks
  talk_override talk_mode[],
  hear_override hear_mode[],
  favourite boolean not null default false,
  created_at timestamptz not null default now(),
  unique (user_id, phone_e164)
);

create table phrases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  contact_id uuid references contacts(id) on delete cascade,
  label text not null,
  text text not null,
  group_name text,
  use_count int not null default 0,
  created_at timestamptz not null default now()
);

create table awaaz_numbers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  number_e164 text not null unique,
  provider text not null,               -- 'exotel' | 'plivo'
  purpose text not null default 'personal',  -- 'personal' | 'shared_outbound'
  created_at timestamptz not null default now()
);

create table wa_users (
  wa_id text primary key,               -- WhatsApp phone id (E.164 without +)
  user_id uuid references auth.users(id) on delete set null,
  window_expires_at timestamptz,        -- 24-hour service window
  active_call_id uuid,
  created_at timestamptz not null default now()
);

create table family_links (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  relation text,
  phone_e164 text not null,
  can_edit_contacts boolean not null default true,
  receives_summaries boolean not null default false,
  consent_at timestamptz,
  created_at timestamptz not null default now()
);

create table consents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check (kind in ('voice_clone', 'family_share', 'recording', 'terms')),
  text text not null,
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- ---------- Calls ----------
create table calls (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  contact_id uuid references contacts(id) on delete set null,
  kind call_kind not null,
  direction call_direction not null default 'outbound',
  other_number text,
  call_lang text,
  talk_modes talk_mode[] not null,
  hear_modes hear_mode[] not null,
  status call_status not null default 'created',
  provider text,                        -- 'plivo' | 'bolna' | 'callee_sim' | 'mock'
  provider_call_id text,
  from_number text,
  started_at timestamptz,
  ended_at timestamptz,
  duration_s int,
  saved boolean not null default false, -- user chose to keep beyond retention
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index calls_user_time on calls (user_id, created_at desc);
create trigger calls_updated before update on calls for each row execute function set_updated_at();

create table turns (
  id bigint generated always as identity primary key,
  call_id uuid not null references calls(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  seq int not null,
  speaker turn_speaker not null,
  source turn_source not null,
  text text not null,
  text_translated text,
  lang text,
  confidence numeric(3,2),
  entities jsonb not null default '[]'::jsonb,
  t_ms int not null,                    -- ms from call start
  created_at timestamptz not null default now(),
  unique (call_id, seq)
);

create table summaries (
  call_id uuid primary key references calls(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  summary jsonb not null,               -- specs/schemas/call_summary.schema.json
  voice_note_path text,
  created_at timestamptz not null default now()
);

create table scam_events (
  id uuid primary key default gen_random_uuid(),
  call_id uuid not null references calls(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  turn_seq int,
  reason text not null,                 -- 'otp_request' | 'pin_request' | 'cvv_request' | 'remote_app' | 'upi_pin' | 'other'
  action text not null,                 -- 'warned' | 'blocked_digits' | 'user_ended'
  created_at timestamptz not null default now()
);

-- ---------- Call for me ----------
create table tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  template text not null,               -- specs/data/task_templates.json ids
  contact_id uuid references contacts(id) on delete set null,
  number_e164 text not null,
  call_lang text not null default 'hi',
  facts jsonb not null default '{}'::jsonb,
  limits jsonb not null default '{}'::jsonb,
  status task_status not null default 'draft',
  call_id uuid references calls(id),
  bolna_execution_id text unique,
  result jsonb,                         -- specs/schemas/task_result.schema.json
  source text not null default 'app' check (source in ('app', 'whatsapp')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger tasks_updated before update on tasks for each row execute function set_updated_at();

create table approvals (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references tasks(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  question text not null,
  options jsonb not null default '["approve","decline"]'::jsonb,
  amount_inr numeric,
  status approval_status not null default 'pending',
  answer text,
  answered_via text check (answered_via in ('app', 'whatsapp')),
  created_at timestamptz not null default now(),
  answered_at timestamptz
);

-- ---------- Infrastructure ----------
create table jobs (
  id bigint generated always as identity primary key,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  run_at timestamptz not null default now(),
  status job_status not null default 'queued',
  attempts int not null default 0,
  last_error text,
  locked_at timestamptz,
  dedupe_key text unique,
  created_at timestamptz not null default now()
);
create index jobs_due on jobs (status, run_at);

create or replace function claim_jobs(n int) returns setof jobs language sql as $$
  update jobs set status = 'running', locked_at = now(), attempts = attempts + 1
  where id in (select id from jobs where status = 'queued' and run_at <= now() order by run_at limit n for update skip locked)
  returning *;
$$;

create table audit_log (
  id bigint generated always as identity primary key,
  user_id uuid,
  actor text not null,
  action text not null,
  entity text not null,
  entity_id text,
  data jsonb not null default '{}'::jsonb,
  at timestamptz not null default now()
);

-- Retention helper: delete unsaved turns older than 30 days (schedule daily via pg_cron or the job poller)
create or replace function purge_old_turns() returns int language sql as $$
  with d as (
    delete from turns t using calls c
    where t.call_id = c.id and c.saved = false and t.created_at < now() - interval '30 days'
    returning 1
  ) select count(*)::int from d;
$$;

-- ---------- RLS ----------
alter table profiles enable row level security;
alter table voices enable row level security;
alter table comm_profiles enable row level security;
alter table contacts enable row level security;
alter table phrases enable row level security;
alter table awaaz_numbers enable row level security;
alter table wa_users enable row level security;
alter table family_links enable row level security;
alter table consents enable row level security;
alter table calls enable row level security;
alter table turns enable row level security;
alter table summaries enable row level security;
alter table scam_events enable row level security;
alter table tasks enable row level security;
alter table approvals enable row level security;
alter table jobs enable row level security;
alter table audit_log enable row level security;

-- read own rows
create policy own_read on profiles for select to authenticated using (user_id = auth.uid());
create policy own_read on comm_profiles for select to authenticated using (user_id = auth.uid());
create policy own_read on contacts for select to authenticated using (user_id = auth.uid());
create policy own_read on phrases for select to authenticated using (user_id = auth.uid());
create policy own_read on awaaz_numbers for select to authenticated using (user_id = auth.uid());
create policy own_read on family_links for select to authenticated using (user_id = auth.uid());
create policy own_read on consents for select to authenticated using (user_id = auth.uid());
create policy own_read on calls for select to authenticated using (user_id = auth.uid());
create policy own_read on turns for select to authenticated using (user_id = auth.uid());
create policy own_read on summaries for select to authenticated using (user_id = auth.uid());
create policy own_read on scam_events for select to authenticated using (user_id = auth.uid());
create policy own_read on tasks for select to authenticated using (user_id = auth.uid());
create policy own_read on approvals for select to authenticated using (user_id = auth.uid());
create policy voices_read on voices for select to authenticated using (user_id is null or user_id = auth.uid());

-- users may edit their own settings directly
create policy own_write on profiles for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy own_write on comm_profiles for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy own_write on contacts for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy own_write on phrases for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
-- wa_users, jobs, audit_log: backend only

-- ---------- Realtime ----------
alter publication supabase_realtime add table calls, turns, tasks, approvals, summaries;

-- ---------- Storage ----------
insert into storage.buckets (id, name, public) values
  ('voice-samples', 'voice-samples', false),
  ('voice-notes', 'voice-notes', false),
  ('wa-media', 'wa-media', false)
on conflict (id) do nothing;
