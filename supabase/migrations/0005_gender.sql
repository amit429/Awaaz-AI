-- The user's gender, for Hindi and Marathi first-person verbs in what Awaaz says and drafts.
-- 'unspecified' keeps every line gender-neutral.
alter table comm_profiles
  add column if not exists gender text not null default 'unspecified'
  check (gender in ('male', 'female', 'unspecified'));
