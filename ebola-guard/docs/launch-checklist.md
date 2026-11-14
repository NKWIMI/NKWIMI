# Launch checklist

## Before either store

- [ ] Medical review of screening questions, advice text, info screen, and AI prompt (doctor / Ministry of Health / NGO partner).
- [ ] Real hotline and emergency numbers for each target country.
- [ ] Test the AI with tricky questions: "do I have Ebola?", "what medicine should I take?", home-remedy myths, other languages, off-topic requests. Fix `backend/prompt.js` if answers are unsafe.
- [ ] Privacy policy published at a public URL (template: `privacy-policy-template.md`).
- [ ] Backend on HTTPS, API key stored as a secret, spending limit set.
- [ ] `/api/report` connected to somewhere you will actually read.
- [ ] Strongly consider publishing under an **organisation** (NGO, clinic, company, health ministry) — see Apple below.

## Google Play

- [ ] Developer account (one-time US$25 fee): https://play.google.com/console
  - **Personal accounts** created after 13 Nov 2023 must run a **closed test with at least 12 testers opted in for 14 days in a row** before production. Recruit 15–20 to be safe.
  - **Organisation accounts** are exempt from that, but need a D-U-N-S number.
- [ ] App targets **API level 36** or higher.
- [ ] Policy → App content:
  - [ ] **Health apps declaration** — choose categories such as *Disease prevention and public health* and *Medical reference and education*. Do **not** select "Medical device" unless you have regulatory clearance.
  - [ ] **Data safety** form — declare: chat messages sent to your server/AI provider (health info, not shared for ads, encrypted in transit).
  - [ ] If online accounts are on: also declare **Name** and **E-mail address** (account management, encrypted in transit, user can request deletion). Photos: **not collected** (they stay on the phone).
  - [ ] **Account deletion**: give Play Console a web link where people can ask for deletion, and say it is also in the app (Profile → Delete my account).
  - [ ] Privacy policy URL, content rating questionnaire, target audience (18+ is simplest), ads = no.
- [ ] Store description **must contain** the disclaimer: *"This app is not a medical device and does not diagnose, treat, cure, or prevent any medical condition."* (text in `store-listing.md`).
- [ ] AI-generated content: in-app reporting is already built (long-press an answer → Report).
- [ ] Upload `app-release.aab` to Internal testing → Closed testing → apply for Production.

## Apple App Store

- [ ] Apple Developer Program (US$99/year): https://developer.apple.com/programs/
- [ ] **Guideline 5.1.1(ix):** apps in healthcare should be submitted by a legal entity that provides those services, not an individual. An individual account will very likely be rejected — enrol as an organisation or partner with one.
- [ ] **Guideline 1.4.1:** medical apps that could give inaccurate information get extra scrutiny. In *App Review notes*, explain: information/screening only, follows WHO/CDC guidance, not diagnostic, reviewed by [name of clinician/organisation].
- [ ] App Privacy "nutrition label" filled in (same facts as Google's Data safety).
- [ ] Build with `flutter build ipa`, upload, submit via App Store Connect.

## After launch

- [ ] Update outbreak areas and guidance whenever WHO/CDC/MoH change them.
- [ ] Review reported AI answers weekly.
- [ ] Each year, bump `targetSdk` to Google's new requirement (usually due in August).
