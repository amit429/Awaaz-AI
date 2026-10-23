alter function public.set_updated_at() set search_path = public;
alter function public.claim_jobs(int) set search_path = public;
alter function public.purge_old_turns() set search_path = public;
