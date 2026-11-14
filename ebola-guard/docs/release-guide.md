# Release guide: from your computer to your phone and Google Play (Windows)

Do the steps in order. Run all commands in **cmd** from `C:\projects\ebola-guard\app` unless the step says otherwise.
If `flutter` is "not recognized", first run: `set PATH=%PATH%;C:\src\flutter\bin`

| Step | What | Time |
|---|---|---|
| 1 | Choose your package name | 5 min |
| 2 | Generate the app icon and splash screen | 5 min |
| 3 | Create your upload key (signing) | 10 min |
| 4 | Install on your own phone (testing) | 20 min |
| 5 | Put the chatbot backend online (HTTPS) | 30–60 min |
| 6 | Publish your privacy policy | 20 min |
| 7 | Build the release files | 10 min |
| 8 | Google Play Console: listing, forms, testing, production | 1 day of work + 14 days of testing |

---

## 1. Choose your package name (once, forever)

The package name identifies your app on Google Play and **can never change after you publish**.
Format: `com.<your name or organisation>.<app>`, lowercase, no spaces or dashes. Example: `com.grevi.ebolaguard`.

```cmd
node tools\prepare-release.js com.grevi.ebolaguard
```

This sets the package name, moves `MainActivity.kt`, adds release signing, and creates
`android\key.properties` and `config\release.json`.

## 2. App icon and splash screen

```cmd
flutter pub get
dart run flutter_launcher_icons
dart run flutter_native_splash:create
```

To change the design, replace the PNGs in `assets\icon\` and run the two commands again.

## 3. Create your upload key

Google Play uses this key to know updates really come from you. **Back up the .jks file and the
passwords (e.g. on a USB stick and in a password manager). If you lose them, you need Google support to reset.**

```cmd
"C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" -genkey -v -keystore C:\Users\user\upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

It asks for a password (type it twice; nothing shows while you type), then your name, organisation, city and country code (e.g. `CD`, `KR`), then `y` to confirm.

Now put the password in `key.properties`:
```cmd
notepad android\key.properties
```
Replace both `CHANGE_ME` with your password, save, and close. Keep `storeFile=C:/Users/user/upload-keystore.jks` (forward slashes).

## 4. Install on your own phone (testing)

**On the phone:**
1. Settings → About phone → tap **Build number** 7 times, so "You are now a developer" appears.
2. Settings → System → Developer options → turn on **USB debugging**.
3. Connect the phone with a USB cable → tap **Allow** on the phone ("Allow USB debugging?").

**On the computer:**
```cmd
flutter devices
```
Your phone should be listed (e.g. `SM A155F (mobile)`).

### 4a. Debug install with your local backend (quick test)
Phone and computer on the **same Wi-Fi**. Find your computer's IP:
```cmd
ipconfig
```
Look for `IPv4 Address` (e.g. `192.168.0.15`). Start the backend in another window (`npm start` in `backend`), then:
```cmd
flutter run --dart-define=BACKEND_URL=http://192.168.0.15:8080
```
If Windows asks to allow Node.js through the firewall, click **Allow** (private networks).
The app stays on the phone after you unplug, but the chat only works while your computer's backend is running.

### 4b. Release install (after step 5, works anywhere)
```cmd
flutter build apk --release --dart-define-from-file=config/release.json
flutter install --release
```

## 5. Put the backend online

The phone app needs an **HTTPS** address that works anywhere. A simple, beginner-friendly option is **Render**:

1. Create a free account at https://github.com → **New repository** → name `ebola-guard-backend`, **Private** → Create.
2. On the repo page click **uploading an existing file** and drag in these files from `C:\projects\ebola-guard\backend`:
   `server.js`, `prompt.js`, `package.json`, `package-lock.json`, `Dockerfile`, `server.test.js`
   (**not** `node_modules`, **never** a `.env` file) → **Commit changes**.
3. Create an account at https://render.com (sign in with GitHub) → **New → Web Service** → pick the repo.
4. Settings: Runtime **Node**, Build command `npm install`, Start command `npm start`.
5. **Environment variables**: `ANTHROPIC_API_KEY` = your key, `HEALTH_HOTLINE` = your hotline, `EMERGENCY_NUMBER` = e.g. `112`.
6. **Create Web Service**. After the build, Render shows a URL like `https://ebola-guard-backend.onrender.com`.
7. Test it in your browser: `https://…onrender.com/health` should show `{"ok":true,"ai":true}`.
8. Put that URL into `config\release.json`:
   ```cmd
   notepad config\release.json
   ```

Notes: free hosting may "sleep" when unused, so the first message can take up to a minute; a paid plan keeps it awake.
Set a monthly **spending limit** at https://console.anthropic.com → Billing.

## 6. Privacy policy (required)

Fill in `docs\privacy-policy-template.md` (your name/organisation, e-mail, country) and publish it at a public web address, e.g.:
- **Google Sites** (free): https://sites.google.com → Blank site → paste the text → **Publish** → copy the link.

Put the link in `config\release.json` as `PRIVACY_POLICY_URL`.

## 7. Build the release files

1. Update the version in `pubspec.yaml` for every new upload: `version: 1.0.0+1` → `1.0.1+2` (the number after `+` must always go up).
2. Build:
```cmd
flutter build appbundle --release --dart-define-from-file=config/release.json
```
Result: `build\app\outputs\bundle\release\app-release.aab`. This is the file you upload to Google Play.

## 8. Google Play Console

1. **Create a developer account**: https://play.google.com/console (one-time US$25, ID verification).
   - *Personal* account → you must run a **closed test with at least 12 testers for 14 days in a row** before production.
   - *Organisation* account (NGO/company, needs a D-U-N-S number) → no 12-tester rule.
2. **Create app** → name "Ebola Guard – Symptom Check & Info", App, Free.
3. **Store listing** (Grow → Store presence → Main store listing):
   - Short and full description: copy from `docs\store-listing.md` (keep the "not a medical device" sentence).
   - App icon: `store-assets\play-icon-512.png`
   - Feature graphic: `store-assets\play-feature-graphic-1024x500.png`
   - Phone screenshots (2–8): on the emulator click the 📷 camera icon in the side toolbar, or on your phone press Power + Volume down. Take: home, check, result, chat, voice, learn.
4. **App content** (Policy → App content), complete every item:
   - Privacy policy URL
   - Ads: **No**
   - App access: all features available without login
   - Content rating questionnaire (category: Reference/Health; answer honestly)
   - Target audience: **18+**
   - **Health apps**: tick *Disease prevention and public health* and *Medical reference and education*. **Not** "Medical device".
   - **Data safety**: collects *Health info* (chat messages and screening summary you send), *Audio* only if your speech engine sends audio (Google's does, processed by Google), *Crash/diagnostics: no*. Data is encrypted in transit, not sold, not used for ads, and you can say users can't request deletion because nothing is stored (adjust if you add storage).
   - Government app: No. Financial features: No.
5. **Testing → Closed testing** → Create track → upload `app-release.aab` → add testers (Google account e-mails, or a Google Group) → send them the opt-in link. Keep **12+ testers opted in for 14 days**; recruit 15–20 to be safe.
6. After 14 days → **Apply for production** → answer the questions → when approved, **Production → Create release** → upload the latest `.aab` → **Review and roll out**.

Review usually takes a few days. Health apps can get extra checks. Make sure the disclaimer is visible in the description and in the app.

---

### Updating the app later
1. Change the code, bump `version:` in `pubspec.yaml` (e.g. `1.0.1+2`).
2. `flutter build appbundle --release --dart-define-from-file=config/release.json`
3. Play Console → your track → Create release → upload the new `.aab`.
