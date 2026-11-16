<h1 align="center">Hi, I'm Grevi Nkwimi Bilangoma 👋</h1>
<h3 align="center">Software Developer · M.S. in Applied Artificial Intelligence (Hanyang University ERICA)</h3>

<p align="center">
  <a href="https://www.linkedin.com/in/nkwimi-grevi-b64510351"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn"/></a>
  <a href="https://orcid.org/0009-0008-9836-5863"><img src="https://img.shields.io/badge/ORCID-A6CE39?style=for-the-badge&logo=orcid&logoColor=white" alt="ORCID"/></a>
  <a href="mailto:grevi91nkwimi@gmail.com"><img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email"/></a>
  <img src="https://img.shields.io/badge/Based%20in-South%20Korea-blue?style=for-the-badge" alt="Location"/>
</p>

---

### 🧑‍💻 About me

- 🌍 Software developer from the **DR Congo**, now based in **South Korea**
- 🎓 **M.S. in Applied Artificial Intelligence** (Digital Innovation), Hanyang University ERICA — **GPA 4.00/4.00**, KOICA full scholarship
- 💼 Web application developer at **PROCLADE Congo** since 2021 (Python / Django)
- 📄 Co-author of **10 research papers** in computer vision, predictive modelling and explainable AI (XAI)
- 👨‍🏫 University teaching assistant in programming, software engineering and databases since 2017
- 🔭 Open to **software developer / AI engineer** roles in Korea
- 🤖 I build **AI applications end to end**: a tomato quality-inspection web app with a CNN I trained, and a health app whose assistant answers from official WHO/CDC documents (**RAG**) with cited sources
- 🌱 Currently learning: running AI in production at scale (monitoring, CI/CD) and publishing apps on Google Play
- 🗣️ French (native) · English (professional) · Korean (basic)

---

### 🚀 Featured projects

#### 🩺 [Ebola Guard](https://github.com/NKWIMI/NKWIMI/tree/main/ebola-guard) — Health app with a RAG AI assistant (Android)
*Mobile health project · 2026*

An Android app that helps people in the DR Congo **check symptoms and exposure, learn prevention, and find the nearest treatment centre**. It is a screening and information tool, not a diagnostic device.

- **Flutter / Dart** app with a guided risk check that gives clear next steps (urgent cases are sent to the hotline and treatment centres)
- **AI assistant with RAG**: before answering, a **Node.js / Express** backend searches 6 official **WHO/CDC** documents with **hybrid search** (BM25 keywords + multilingual embeddings), then the **Claude API** answers from those passages with **clickable citations**
- Text and **voice chat** (speech-to-text and text-to-speech), plus rule-based **danger-sign alerts**
- **Measured results** on 40 test questions in 4 languages: right source in the top 5 for **100%**, ranked first for **94%**; all danger signs flagged with **no false alarms** ([details](https://github.com/NKWIMI/NKWIMI/tree/main/ebola-guard#results--how-well-the-assistant-finds-the-right-source))
- **6 languages**: French, English, Swahili, **Lingala, Kikongo and Tshiluba**
- **Outbreak map** (OpenStreetMap), lessons, myth-vs-fact quiz and trusted videos
- 47 automated tests; backend deployed with **Docker** on Render; Android APK v1.2

#### 🍅 [TomatoGrade](https://github.com/NKWIMI/tomatograde) — Tomato quality inspection with AI
*Computer vision project · 2026*

A web app that grades tomatoes as **fresh or rotten** from a photo and **shows why**, building on my research on tomato quality grading.

- **PyTorch**: fine-tuned a **MobileNetV3** CNN by transfer learning on **1,986 real tomato photos** (Google Colab GPU)
- **FastAPI** web app: single and batch grading, **Grad-CAM** heatmaps explaining each decision, a "needs review" flag when the model is unsure
- Inspection history in **SQLite** with CSV export, and a quality dashboard
- Packaged with **Docker**; automated tests with **pytest**

#### ⛓️ [BlockLand](https://github.com/NKWIMI/NKWIMI/tree/main/blockland) — Blockchain-Based Land Registration System
*Master's thesis · Hanyang University ERICA · 2025–2026 · built alone*

A web application that keeps land records **transparent and tamper-resistant**, to help reduce land ownership conflicts in the DR Congo.

- Designed and built end to end, from requirements analysis to a working prototype
- **Django (Python)** backend and web interface: parcel registration, ownership transfers, admin dashboard, block explorer
- **Solidity** smart contract (`LandRegistry.sol`) compiled and deployed with **Hardhat**, connected through **Web3.py** to a local Ethereum blockchain (**Ganache**)
- Documents stored on **IPFS** (Pinata) with file hashes recorded on-chain; metadata in **CouchDB**
- AI-assisted document checks (**TensorFlow**, **OpenCV**, Tesseract OCR)
- 📘 [Setup guide](https://github.com/NKWIMI/NKWIMI/blob/main/blockland/SETUP.md)

---

### 🛠️ Tech stack

**Languages**
<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/C%23-512BD4?style=flat-square&logo=dotnet&logoColor=white"/>
  <img src="https://img.shields.io/badge/Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white"/>
  <img src="https://img.shields.io/badge/VB.NET-5C2D91?style=flat-square&logo=dotnet&logoColor=white"/>
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black"/>
  <img src="https://img.shields.io/badge/Dart-0175C2?style=flat-square&logo=dart&logoColor=white"/>
  <img src="https://img.shields.io/badge/Solidity-363636?style=flat-square&logo=solidity&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQL-4479A1?style=flat-square&logo=databricks&logoColor=white"/>
</p>

**Mobile**
<p>
  <img src="https://img.shields.io/badge/Flutter-02569B?style=flat-square&logo=flutter&logoColor=white"/>
  <img src="https://img.shields.io/badge/Android-3DDC84?style=flat-square&logo=android&logoColor=white"/>
</p>

**Web**
<p>
  <img src="https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white"/>
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white"/>
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white"/>
  <img src="https://img.shields.io/badge/Node.js-339933?style=flat-square&logo=nodedotjs&logoColor=white"/>
  <img src="https://img.shields.io/badge/Express-000000?style=flat-square&logo=express&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
</p>

**Data & AI**
<p>
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white"/>
  <img src="https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white"/>
  <img src="https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white"/>
  <img src="https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white"/>
  <img src="https://img.shields.io/badge/Matplotlib-11557C?style=flat-square"/>
  <img src="https://img.shields.io/badge/Seaborn-4C72B0?style=flat-square"/>
  <img src="https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white"/>
  <img src="https://img.shields.io/badge/Power%20BI-F2C811?style=flat-square&logo=powerbi&logoColor=black"/>
  <img src="https://img.shields.io/badge/Claude%20API-D97757?style=flat-square&logo=anthropic&logoColor=white"/>
  <img src="https://img.shields.io/badge/Hugging%20Face-FFD21E?style=flat-square&logo=huggingface&logoColor=black"/>
  <img src="https://img.shields.io/badge/RAG-6E40C9?style=flat-square"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white"/>
</p>

**Databases**
<p>
  <img src="https://img.shields.io/badge/SQL%20Server-CC2927?style=flat-square&logo=microsoftsqlserver&logoColor=white"/>
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white"/>
  <img src="https://img.shields.io/badge/CouchDB-E42528?style=flat-square&logo=apachecouchdb&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white"/>
</p>

**Blockchain**
<p>
  <img src="https://img.shields.io/badge/Ethereum-3C3C3D?style=flat-square&logo=ethereum&logoColor=white"/>
  <img src="https://img.shields.io/badge/Web3.py-F16822?style=flat-square&logo=web3dotjs&logoColor=white"/>
  <img src="https://img.shields.io/badge/Ganache-E4A663?style=flat-square"/>
  <img src="https://img.shields.io/badge/Hardhat-FFF100?style=flat-square&logo=hardhat&logoColor=black"/>
  <img src="https://img.shields.io/badge/IPFS-65C2CB?style=flat-square&logo=ipfs&logoColor=white"/>
</p>

**Modelling & analysis:** StarUML · JMerise · SmartPLS

---

### 📚 Research (co-author)

- **An Explainable Hybrid GraphRAG Framework for Diabetes Risk Stratification** — *accepted at IEEE WiMob 2026*
- Explainable AI (XAI) for Obesity Prediction: An Optimized MLP Approach with SHAP Interpretability
- Deep Learning-Enhanced Automatic License Plate Recognition: A CNN-Based Framework for Real-Time Traffic Management
- Enhancing the Robustness of Computer Vision Models to Adversarial Perturbations Using Multi-Scale Attention Mechanisms
- A Cost-Aware Comparative Study of Deep Learning Models for Industrial Tomato Quality Grading
- AI-Generated Sneaker Detection: Leveraging GANs and CNNs for Image Classification
- Multi-Model Optimization for Telecom Churn Prediction
- A Hybrid Approach to Vehicle Price Prediction: Combining PCA and Supervised Learning
- Contrasting Classical and Symbolic Approaches to Classification in Data Warehousing Systems
- Strengthening Electoral Trust in the DRC: A Multimodal Biometric and RFID Voting Prototype

📖 Full list on [ORCID](https://orcid.org/0009-0008-9836-5863)

---

### 🏅 Certificates

| Certificate | Issuer | Date |
|---|---|---|
| Smart Contract Engineer | Udemy | Jan 2025 |
| AI Engineer | Udemy | May 2025 |
| Data Science and Machine Learning | Udemy | May 2025 |
| Advanced Django Web Development | Udemy | Jul 2025 |

---

### 📊 GitHub stats

<p align="center">
  <img height="165" src="https://github-readme-stats.vercel.app/api?username=NKWIMI&show_icons=true&hide_border=true&count_private=true" alt="GitHub stats"/>
  <img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username=NKWIMI&layout=compact&hide_border=true" alt="Top languages"/>
</p>

---

<p align="center"><i>"Building software that solves real problems — from Kinshasa to Seoul."</i></p>
