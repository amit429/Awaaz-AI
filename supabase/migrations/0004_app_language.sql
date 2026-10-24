alter table comm_profiles add column if not exists app_lang text not null default 'en';
comment on column comm_profiles.app_lang is 'Language of the app interface (hi, en, mr, ta, ..., hi-Latn for Hinglish). read_lang is the caption language.';
