# Ebola Guard — starter project

A cross-platform (Android + iOS) Flutter app that offers:

1. **Symptom & exposure screening** — offline, rule-based checklist following the CDC/WHO logic (exposure in the last 21 days + compatible symptoms → isolate and call for help).
2. **AI health-information assistant** — chat backed by Claude, with strict safety instructions (no diagnosis, always escalates red flags, replies in the user's language, can be reported by the user).
3. **Voice assistant** — speak your question and hear the answer, in the language you choose (uses the phone's free built-in speech engines).
4. **Learn about Ebola** — 7 prevention lessons, facts & myths (offline), plus videos (WHO, Global Health Media, SAWBO) and trusted links.
5. **Emergency contacts** — one-tap call to the hotline / emergency number.

> ⚠️ **Positioning matters.** Present the app as *screening & information*, never "Ebola detection" or "diagnosis". A phone app cannot detect Ebola — only a lab test can — and claiming diagnosis makes the app a regulated **medical device** (needs approval from FDA / EU MDR / your national regulator) and gets it rejected from the stores.

```
ebola-guard/
├── app/        Flutter mobile app (Android + iOS)
│   ├── lib/
│   │   ├── main.dart, config.dart, theme.dart
│   │   ├── screens/   disclaimer, home, screening, result, chat, info
│   │   ├── services/  screening_engine.dart (rules), chat_service.dart (API), phone.dart
│   │   └── widgets/   emergency_banner.dart
│   ├── test/widget_test.dart
│   └── scripts/setup.sh
├── backend/    Node.js API that holds the AI key (never put the key in the app)
│   ├── server.js, prompt.js, server.test.js, Dockerfile, .env.example
└── docs/       privacy policy template, store listing text, launch checklist
```

```
Phone app ──HTTPS──▶ your backend (/api/chat) ──▶ Claude API
   │ offline: screening + info + call buttons work without internet
```

---

## Step 1 — Install the tools (one time)

| Tool | Why | Link |
|---|---|---|
| Flutter SDK (3.27 or newer) | Builds the app | https://docs.flutter.dev/get-started/install |
| Android Studio | Android SDK + emulator | https://developer.android.com/studio |
| Node.js 20+ | Runs the backend | https://nodejs.org |
| Anthropic API key | Powers the chatbot | https://console.anthropic.com |
| Mac + Xcode | **Only** needed for the iOS App Store build | Mac App Store |

Then run `flutter doctor` and fix anything it reports.

## Step 2 — Run the backend locally

```bash
cd backend
npm install
npm test                       # 6 tests should pass
export ANTHROPIC_API_KEY=sk-ant-...   # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
npm start                      # → http://localhost:8080
```

Check: open http://localhost:8080/health → `{"ok":true,"ai":true}`.

## Step 3 — Run the app

```bash
cd app
bash scripts/setup.sh com.yourcompany   # generates android/ & ios/ folders, adds INTERNET permission
flutter test                            # screening rules + home screen tests
flutter run                             # with an emulator running or a phone plugged in
```

The app talks to `http://10.0.2.2:8080` by default (= your computer, seen from the Android emulator). On a real phone, pass your computer's LAN IP:

```bash
flutter run --dart-define=BACKEND_URL=http://192.168.1.20:8080
```

## Step 4 — Customise before release

- **`app/lib/config.dart`** – app name, hotline, emergency number, privacy-policy URL (or pass them with `--dart-define`).
- **`backend/prompt.js`** – the chatbot's rules. Set `HEALTH_HOTLINE` and `EMERGENCY_NUMBER` env vars.
- **`app/lib/services/screening_engine.dart`** – questions and advice. **Have a doctor or your Ministry of Health review this file, `info_screen.dart`, and `prompt.js`.** Update the outbreak areas when the situation changes.
- **Languages** – translate the screens into your users' languages (French, Swahili, Lingala…). The AI already replies in the user's language.
- **App icon** – `flutter pub add dev:flutter_launcher_icons` then follow its README.
- **Package name** – the `--org` you gave setup.sh (e.g. `com.yourcompany.ebola_guard`). It can never change after publishing.

## Step 5 — Deploy the backend (HTTPS)

Any host that runs Docker or Node works. Examples:

- **Google Cloud Run**: `gcloud run deploy ebola-guard-api --source backend --region europe-west1 --allow-unauthenticated --set-env-vars ANTHROPIC_API_KEY=...,HEALTH_HOTLINE=...`
- **Render / Railway / Fly.io**: create a web service from the `backend/` folder, start command `npm start`, add the env vars in the dashboard.

You get an `https://...` URL. Keep the API key only in the host's secret settings, and set a monthly spending limit in the Anthropic Console.

## Step 6 — Build the release app

**Android (Google Play needs an `.aab` bundle):**

```bash
# 1. Create your upload key ONCE and back it up safely — losing it is painful.
keytool -genkey -v -keystore ~/upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```
2. Create `app/android/key.properties` (don't commit it):
```
storePassword=...
keyPassword=...
keyAlias=upload
storeFile=/home/you/upload-keystore.jks
```
3. Wire it into `android/app/build.gradle.kts` → follow https://docs.flutter.dev/deployment/android#configure-signing-in-gradle
4. Confirm `targetSdk` is **36 or higher** (Google Play requirement for new apps since 31 Aug 2026).
5. Build:
```bash
flutter build appbundle --release \
  --dart-define=BACKEND_URL=https://your-backend.example.com \
  --dart-define=HEALTH_HOTLINE=XXXX \
  --dart-define=EMERGENCY_NUMBER=112 \
  --dart-define=PRIVACY_POLICY_URL=https://your-site/privacy
# → build/app/outputs/bundle/release/app-release.aab
```

**iOS (on a Mac):** `flutter build ipa --release --dart-define=...` then upload with Xcode or Transporter. Guide: https://docs.flutter.dev/deployment/ios

## Step 7 — Publish

**Windows step-by-step:** see **`docs/release-guide.md`** (package name, icon, signing key, install on your phone, backend online, Google Play).


See **`docs/launch-checklist.md`** — it covers both stores, including the health-app rules that most often cause rejections.

---

### Notes on the AI

- Model is set by `ANTHROPIC_MODEL` (default `claude-haiku-5-5`, cheap and fast; `claude-sonnet-5-5` for higher quality).
- The backend never logs message content (health data). User reports of bad answers are logged by `/api/report` — connect it to a database or e-mail before launch.
- The in-memory rate limit (15 msgs/min/IP) is fine to start; use Redis or your host's limiter if you grow.

### Voice assistant notes

- Android permissions (microphone, speech/TTS services) are already in `android/app/src/main/AndroidManifest.xml`.
- **Emulator:** to talk to the virtual phone, open the emulator's **⋯ (Extended controls) → Microphone** and turn on **"Virtual microphone uses host audio input"**. A real phone works better.
- Languages available depend on the phone's speech engine (Google). On a real phone: Settings → System → Languages → Speech / On-device recognition to download more languages.
- **iOS** (when you build on a Mac): add to `ios/Runner/Info.plist` inside `<dict>`:
  ```xml
  <key>NSMicrophoneUsageDescription</key>
  <string>The voice assistant uses the microphone to hear your questions.</string>
  <key>NSSpeechRecognitionUsageDescription</key>
  <string>Your speech is converted to text so the assistant can answer.</string>
  ```
- Store listings: declare microphone use in Google Play's Data safety form ("Audio – voice recordings: processed on device / by the speech service, not stored").

### Languages

The app has 6 languages, chosen from the 🌐 button (first screen and home header): English, Français, Lingála, Kikongo (Kikongo ya Leta), Tshiluba, Kiswahili.

- Texts live in `app/lib/l10n/strings_<code>.dart`, one key per text. English is the source.
- **Lingala, Kikongo and Tshiluba are drafts (marked *beta* in the app).** Kikongo and Tshiluba translate all screens, questions, results and chat; the long lessons still show in French. Any missing text falls back to French automatically.
- **Before release**, have native speakers who know health vocabulary (ideally health workers or the Ministry of Health's risk-communication team) review `docs/translations-review.csv`, then copy corrections into the `strings_*.dart` files. When a language is reviewed, set `beta: false` for it in `app/lib/l10n/l10n.dart`.
- The AI assistant is told the chosen language. For Lingala, Kikongo and Tshiluba it falls back to simple French if it cannot answer accurately.
- Voice input in Lingala, Kikongo and Tshiluba depends on the phone's speech engine and is usually not available yet; the app then listens in French and says so.
- `flutter test` checks that every language has all safety-critical texts and keeps placeholders like `{n}`.

### Ebola map (affected areas and treatment centres)

- Home → **Ebola map**. Two views: **Map** (OpenStreetMap, needs internet) and **List** (works offline). An urgent screening result also shows **Find a treatment centre**.
- **Safety rule built in:** every treatment centre shows *Call before you go* with a call button, and *Directions* first asks "Have you called the hotline?". Directions open in Google Maps; the app itself never reads the user's location (nothing to declare for location in the Data safety form).
- **Data:** `backend/data/outbreak-map.json` (served at `/api/outbreak-map`) with a built-in copy in `app/assets/data/outbreak_map.json` for offline use. The app uses the online copy when it can, otherwise the last saved copy, otherwise the built-in copy, and always shows the date.
- **Keep it current (weekly during the outbreak):** update areas from WHO Disease Outbreak News / the WHO Africa situation report / the DRC Ministry of Health, and treatment centres only from official or operator (MSF, ALIMA, WHO) sources. Change `updated`, then redeploy the backend: all phones update on next open. Copy the file to `app/assets/data/outbreak_map.json` before each app release.
- Coordinates are **city level, approximate**. Circles show provinces/countries with cases, not exact borders. Ask the Ministry of Health for an official list of treatment and isolation centres with exact locations.
- **Map tiles:** the free OpenStreetMap tile server is fine for testing and small use, but its usage policy forbids heavy traffic. Before a large public launch, switch `urlTemplate` in `outbreak_map_screen.dart` to a tile provider with a free tier (e.g. MapTiler, Stadia Maps, Thunderforest) or your own server.
