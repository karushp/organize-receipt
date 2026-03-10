-- Create public storage bucket for receipt images
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'receipts',
  'receipts',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp', 'image/heic']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Allow read for everyone (public bucket), upload/update/delete for all (tighten in production)
create policy "Public read"
  on storage.objects for select
  using (bucket_id = 'receipts');

create policy "Allow insert"
  on storage.objects for insert
  with check (bucket_id = 'receipts');

create policy "Allow update"
  on storage.objects for update
  using (bucket_id = 'receipts');

create policy "Allow delete"
  on storage.objects for delete
  using (bucket_id = 'receipts');
