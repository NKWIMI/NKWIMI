# Accounts: how to switch on online sign-up (optional, free)

The app works **without this**. Until you do these steps, "Create account"
saves the name, e-mail and photo **on the phone only**.

When you want real online accounts (log in on another phone, reset a
forgotten password), use a free **Supabase** project. No credit card is needed.

## 1. Create the project (10 minutes, in your browser)
1. Go to https://supabase.com, click **Start your project**, sign in with GitHub or e-mail.
2. Click **New project**. Name: `ebola-guard`. Choose a strong database password (save it). Region: the one closest to Kinshasa (e.g. *West EU* or *South Africa* if offered). Click **Create**.
3. Wait ~2 minutes until the project is ready.

## 2. Allow account deletion (Google Play requires it)
1. In the left menu click **SQL Editor** → **New query**.
2. Paste this, then click **Run**:

```sql
create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null then
    raise exception 'not signed in';
  end if;
  delete from auth.users where id = auth.uid();
end;
$$;

revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;
```

You should see "Success. No rows returned".

## 3. E-mail confirmation (choose one)
**Authentication → Sign In / Providers → Email**:
- **Confirm email ON** (safer): people get an e-mail and must click the link before they can log in. The free plan only sends a few e-mails per hour, which is enough for a small test.
- **Confirm email OFF** (easiest for your test): accounts work at once.

## 4. Put the keys in the app
1. **Project Settings → API** (or **Data API**). Copy the **Project URL** and the **anon public** key.
   The anon key is meant to be inside apps, so this is safe. **Never** copy the `service_role` key into the app.
2. Open `C:\projects\ebola-guard\app\config\release.json` in Notepad and fill in:

```json
  "SUPABASE_URL": "https://abcdefgh.supabase.co",
  "SUPABASE_ANON_KEY": "eyJhbGciOi..."
```

(If you have no `release.json` yet, copy `release.example.json` and rename the copy.)

3. Build the APK again with `tools\build-apk.bat`. For testing with `run-app.bat`, run instead:
   `flutter run --dart-define-from-file=config/release.json`

## Note
Free Supabase projects **pause after 7 days without use**. Open the
Supabase dashboard and click **Restore** if sign-up stops working.

## What is stored where
| Data | Where |
|---|---|
| First name, e-mail, password (scrambled) | Supabase (only with online accounts) |
| Profile picture | On the phone only, never uploaded |
| Check answers | Never stored. Only a count of checks done, on the phone |
