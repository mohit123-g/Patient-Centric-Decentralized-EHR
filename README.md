# Patient-Centric Decentralized EHR — Solidity Version

This is a Solidity/Ethereum version of the original Python blockchain project.

## Architecture

- Solidity smart contract: immutable record fingerprints + access grant/revoke + authorization.
- Python Flask/Web3: uploads, encryption, SQLite metadata, and blockchain transaction submission.
- AES-256-CBC: encrypts the actual medical file off-chain.
- SHA-256: fingerprints the original medical file; the fingerprint is stored on-chain.
- Streamlit: patient/doctor UI.

> Solidity should NOT store the medical file, AES key, or large PDF/image data. Putting sensitive medical documents directly on a public blockchain is inappropriate and expensive. This hybrid design is the practical way to convert your existing project to Solidity.

## Requirements

1. Node.js + npm
2. Python 3.11/3.12 recommended
3. A fresh virtual environment

## Setup

### 1. Install Node packages

Open terminal in this project folder:

```bash
npm install
```

### 2. Compile Solidity

```bash
npm run compile
```

### 3. Start local Ethereum blockchain

Terminal 1:

```bash
npm run node
```

Hardhat will print test accounts and private keys. Use the private key of Account #0 only for this local demo.

### 4. Deploy contract

Terminal 2:

```bash
npm run deploy
```

This creates `deployment.json`.

### 5. Create Python environment

Terminal 2 or 3:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

### 6. Create `.env`

Copy `.env.example` to `.env`.

Put the Account #0 private key from `npm run node` into `ETH_PRIVATE_KEY`.

Put the contract address from `deployment.json` into `CONTRACT_ADDRESS`.

Never publish `.env` or a real private key.

### 7. Start Flask

Terminal 3:

```bash
.venv\Scripts\activate
python backend\app.py
```

### 8. Start Streamlit

Terminal 4:

```bash
.venv\Scripts\activate
streamlit run frontend\streamlit_app.py
```

## Test order

1. Doctor Upload: create `REC-104`.
2. Patient Portal: grant `PAT-001` → `DOC-05` access to `REC-104`.
3. Doctor Consultation: use the same three IDs.
4. Confirm `AUTHORIZED`, `DECRYPTION SUCCESS`, and `INTEGRITY VERIFIED`.
5. Blockchain Explorer: confirm the record fingerprint is on-chain.
6. Revoke access and retry Doctor Consultation; it should return `ACCESS DENIED`.
7. Optional tamper test: alter the encrypted file in `storage/REC-104.enc`; decryption/integrity protection should detect the problem.

## Important local-demo behavior

The Hardhat chain is local and in-memory. If you stop `npm run node`, the local blockchain state disappears. Deploy the contract again and create fresh records after restarting it.

The Solidity contract currently restricts writes to the deployer/backend owner. This keeps the Streamlit demo simple. For a production/decentralized version, replace the backend-owner model with wallet-based patient/doctor addresses and have users sign transactions from MetaMask or another wallet.
