-- Receipt tracker: transactions table
create table if not exists public.transactions (
  id uuid primary key default gen_random_uuid(),
  date date not null,
  "user" text not null,
  category text not null,
  amount numeric not null,
  note text default '',
  receipt_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Index for common filters (month + user)
create index if not exists idx_transactions_date_user on public.transactions (date, "user");

-- Optional: trigger to keep updated_at in sync
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_transactions_updated_at on public.transactions;
create trigger set_transactions_updated_at
  before update on public.transactions
  for each row execute function public.set_updated_at();

-- Allow service role / anon to read/write (restrict via RLS in production if needed)
alter table public.transactions enable row level security;

create policy "Allow all for authenticated and anon"
  on public.transactions
  for all
  using (true)
  with check (true);
