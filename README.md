# S2-mini Supabase Dashboard (Streamlit)

A simple Streamlit app to view your 4S LiFePO₄ logs stored in Supabase.

## 1) SQL (table & policies)

```sql
create table if not exists public.cell_logs (
  device_id   text        not null,
  ts          timestamptz not null,
  n1          real, n2 real, n3 real, n4 real,
  c1          real, c2 real, c3 real, c4 real,
  pack_v      real,
  spread_mv   integer,
  status      text,
  note        text,
  primary key (device_id, ts)
);

alter table public.cell_logs enable row level security;

create policy if not exists ingest_from_s2mini
on public.cell_logs for insert to anon
with check (device_id = 'pack-4s2p-reza-s2mini');

create policy if not exists read_logs_device
on public.cell_logs for select to anon
using (device_id = 'pack-4s2p-reza-s2mini');

create index if not exists idx_cell_logs_ts_desc
  on public.cell_logs using btree (device_id, ts desc);
```

## 2) Secrets

Set env vars or create `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_ANON_KEY = "YOUR-ANON-KEY"
DEVICE_ID = "pack-4s2p-reza-s2mini"
LOCAL_TZ = "Asia/Jakarta"
```

## 3) Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL (usually http://localhost:8501).
