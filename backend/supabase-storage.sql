-- Run in Supabase SQL Editor. Files stay private; only backend-generated signed
-- URLs allow review / temporary Instagram fetches. No anon INSERT/SELECT policy.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('videos', 'videos', false, 52428800, array['video/mp4'])
on conflict (id) do update set public = false,
    file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;
-- App tables are created and have RLS enabled by backend startup.
