# Blockland – how to run it

Blockchain land registration system (Django + Ethereum smart contract + CouchDB + IPFS).
These steps are for **Windows 10/11**.

## What you need

| Tool | Version | Install (in cmd) | Used for |
|---|---|---|---|
| Python | **3.13** | `winget install -e --id Python.Python.3.13` | the Django web app |
| Node.js | 20 LTS or newer | `winget install -e --id OpenJS.NodeJS.LTS` | Hardhat (compile and deploy the contract) |
| Git | any | `winget install -e --id Git.Git` | one Python package is installed from GitHub |
| Ganache | 7 (desktop app) | https://archive.trufflesuite.com/ganache/ | local Ethereum test network on port **7545** |
| Apache CouchDB | 3.x | https://couchdb.apache.org/#download | metadata database on port **5984** |
| Tesseract OCR | 5.x | `winget install -e --id UB-Mannheim.TesseractOCR` | reading text from uploaded documents (AI checks) |
| Redis *(optional)* | – | `winget install -e --id Redis.Redis` | only if live notifications are set to use Redis |

Python packages are listed in `requirements.txt`. Node packages are in `blockchain/package.json`.

After installing, **close cmd and open a new one** so Windows finds the new tools.

## Setup (first time)

1. **Download the project**, for example with GitHub Desktop, then open cmd in the `blockland` folder.
2. **Run the setup script.** It creates `venv`, installs all packages, compiles the contract, creates `.env` from the template, and builds the database:
   ```
   setup.bat
   ```
3. **Start CouchDB.** It runs as a Windows service after install. Open http://127.0.0.1:5984/_utils and log in with the admin name and password you chose during install.
4. **Start Ganache.** Click **Quickstart**, and make sure the RPC server is `HTTP://127.0.0.1:7545`.
5. **Fill in `.env`** (`notepad .env`):
   - `COUCHDB_USERNAME` / `COUCHDB_PASSWORD`: from step 3
   - `ETHEREUM_PRIVATE_KEY` and `FUNDER_PRIVATE_KEY`: in Ganache, click the 🔑 key icon next to the **first** account and copy the private key
   - `SECRET_KEY`: make one with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `IPFS_API_KEY` / `IPFS_API_SECRET`: from https://app.pinata.cloud → API Keys, or set `REQUIRE_IPFS=False`

   Put the same Ganache private key in `blockchain\.env` as `PRIVATE_KEY=`.
6. **Deploy the smart contract to Ganache:**
   ```
   cd blockchain
   npx hardhat run scripts/deploy.js --network ganache
   cd ..
   ```
   If Hardhat says the network is unknown, open `blockchain\hardhat.config.js` and use the name written under `networks:` (for example `localhost`).
   Copy the **contract address** it prints into `.env` as `CONTRACT_ADDRESS=`.
7. **Prepare CouchDB and an admin account:**
   ```
   venv\Scripts\activate
   python manage.py init_couchdb
   python manage.py createsuperuser
   ```

## Run

```
run.bat
```
Open **http://127.0.0.1:8000**. Ganache and CouchDB must be running.

## Useful commands

| Command | What it does |
|---|---|
| `python manage.py assign_wallets` | gives every user a Ganache wallet |
| `python manage.py fund_users` | sends test ETH to users |
| `python manage.py sync_blockchain_data` | re-reads data from the blockchain |
| `python manage.py check_blockchain_state` | checks the connection to the contract |

> Ganache starts a **new, empty blockchain** each time you use Quickstart. To keep your data, use **New Workspace** in Ganache and save it. Otherwise redo step 6 and `assign_wallets` after each restart.

## Troubleshooting

- **`did not find executable at ...python.exe`**: the `venv` was made on another computer. Delete the `venv` folder and run `setup.bat` again.
- **YouTube videos show "Error 153"**: `settings.py` must contain `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"` (already included).
- **Connection refused 7545**: Ganache isn't running.
- **Connection refused 5984**: CouchDB isn't running, or the password in `.env` is wrong.
- **`TesseractNotFoundError`**: install Tesseract OCR (see the table above).

## Security

`.env`, `blockchain\.env`, `db.sqlite3`, `media/`, `identity_proofs/` and the contract folders with uploaded documents are **never** uploaded to GitHub (see `.gitignore`). Ganache keys are test keys only. Never put a real wallet key in this project.
