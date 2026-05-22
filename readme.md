# 🚀 Telegram Offer Filter & Forwarder Userbot

An advanced, asynchronous Telegram Userbot developed in **Python 3.10+** utilizing the **Telethon** library.

This bot is engineered to automatically monitor real-time deal streams from third-party channels, sanitize multi-channel affiliate spam, break down bundled messages into atomic offers, compute mathematically accurate discounts, and forward high-yield matches into a centralized channel.

---

## 📌 Table of Contents

- [🔍 What it is?](#-what-it-is)
- [🎯 What's the purpose?](#-whats-the-purpose)
- [⚙️ How do I install it?](#️-how-do-i-install-it)
- [🔧 How do I set it up?](#-how-do-i-set-it-up)
- [☁️ Where do I run it 24/7?](#️-where-do-i-run-it-247)
- [🏃 How do I run it?](#-how-do-i-run-it)
- [🏗️ How does it do it? (Architecture & Patterns)](#️-how-does-it-do-it-architecture--patterns)

---

# 🔍 What it is?

This project is a smart, automated Telegram **Userbot** designed to act as an automated curator for deal hunters and affiliate marketers.

It listens to incoming messages from selected channels or groups, strips out invalid formatting or hidden tracking layers, unpacks macro-messages (messages containing multiple aggregated offers), evaluates them against strict customized criteria, and publishes only the best deals to your target destination.

---

# 🎯 What's the purpose?

- **Noise Reduction:** Automatically discards generic spam, out-of-stock items, and uninteresting stores by enforcing a domain whitelist (`Amazon`, `Zalando`, etc.).
- **Smart Aggregation:** Splits clustered multi-offer text block notifications into individual, clean, readable micro-posts.
- **Automated ROI Validation:** Calculates exact discount percentages based on text parsing or price mathematical comparisons, ignoring low-value drops.
- **Instant Scalability:** Forwards high-discount anomalies ("Super Offers") or specific premium brands straight to your conversion channels instantly.

---

# ⚙️ How do I install it?

## 1. Clone the repository

```bash
git clone https://github.com/viandanteS/telgram_offer_filter.git
cd telgram_offer_filter
```

## 2. Set up a virtual environment (Recommended)

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

### Windows

```powershell
venv\Scripts\activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔧 How do I set it up?

## 1. Get Telegram API Credentials

Go to `my.telegram.org`, log in, create an application, and retrieve your:

- `API_ID`
- `API_HASH`

---

## 2. Generate a String Session

Telethon requires a session persistence layer.

To avoid re-authenticating every time the bot restarts, run the session generator script:

```bash
python genera_sessione.py
```

Follow the terminal instructions:

- Input your phone number
- Insert the Telegram verification code
- Insert the 2FA password (if enabled)

At the end, copy the generated session string and go to the next step.

---

## 3. Configure the Environment Variables

Create a `.env` file in the project root:

```env
API_ID=12345678
API_HASH=your_api_hash_here
SESSION_STRING=your_generated_string_session_here

# Target chat/channel ID or username
# Example: -100xxxxxxxxx or 'me'
DESTINATION_GROUP=me

# Filtering configuration
# Comma-separated lists
KEYWORDS=offerta,sconto,promo,amazon
PREMIUM_BRANDS=columbia,the north face,stussy
BLACK_LIST=terminato,esaurito,errore di prezzo esaurito
```

---

# ☁️ Where do I run it 24/7?

Because this bot runs asynchronously via an active connection loop, it needs to stay online permanently.

You can deploy it to:

- **Linux VPS**
  - DigitalOcean
  - Linode
  - AWS EC2
  - Hetzner

- **PaaS Providers**
  - Render
  - Railway
  - AlwaysData

- **Docker Containers**
  - Lightweight Python Alpine container

Recommended process managers:

- `pm2`
- `systemd`

---

# 🏃 How do I run it?

Start the bot with:

```bash
python main.py
```

---

# 🎮 Commands

While running, you can interact with your userbot live from Telegram.

Send the following message in any chat where the userbot is present:

```text
activate n0w -superoffers
```

When enabled:

- Any offer with a discount `>= SUPEROFFERS_PERCDISC` (all percentage can be modified in the code)
- Bypasses standard keyword restrictions
- Gets forwarded immediately

---

# 🏗️ How does it do it? (Architecture & Patterns)

## 🌀 1. Asynchronous Producer-Consumer Architecture

The system employs an `asyncio.Queue` inside `main.py`.

### Workflow

- Incoming Telegram events act as **Producers**
- Raw message chunks are pushed into the queue
- A dedicated `message_worker` acts as the **Consumer**
- Messages are processed sequentially without blocking the Telegram polling engine

---

## ⛓️ 2. Chain of Responsibility Pattern (CoR)

Inside `filters.py`, execution logic is decoupled into atomic handlers:

### Handlers

- **ExtractorHandler**
  - Parses metadata
  - Extracts discount information

- **KeywordHandler**
  - Matches keywords
  - Detects premium brands

- **EvaluationHandler**
  - Applies mathematical thresholds
  - Example:
    - Standard offers require `>= 50%`
    - Premium brands require `>= 60%`

- **BlacklistHandler**
  - Final safety validation
  - Removes out-of-stock or forbidden offers

---

## 🎯 3. Strategy Pattern for Discount Extraction

Discount values can appear in multiple formats on Telegram.

The project uses an `ExtractorStrategy` interface to dynamically switch parsing algorithms at runtime.

### Strategies

#### ExplicitPercentageExtractor

Targets explicit discount patterns such as:

```text
-30%
Sconto 50%
```

Features:

- Context-aware parsing
- Ignores false positives inside URLs

---

#### MathPriceExtractor

Activated when multiple price formats are detected.

Example:

```text
~~120€~~ 45€
```

The real discount is calculated mathematically:

\[
\text{Discount \%} =
\frac{\text{Old Price} - \text{Current Price}}
{\text{Old Price}}
\times 100
\]

---

## 🛠️ 4. Rich Entity Re-hydration

Telegram often hides URLs behind rich text hyperlinks (`MessageEntityTextUrl`).

The userbot:

1. Scans message metadata entities
2. Reconstructs hidden URLs
3. Injects links back into their original text location
4. Validates them against `ALLOWED_DOMAINS`

before continuing the filtering pipeline.

---

# 📊 Processing Flow

```text
[Telegram Message]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ 1. Hyperlink Expansion (Metadata → Raw Text)          │
├────────────────────────────────────────────────────────┤
│ 2. Multi-Offer Splitting (Smart Buffer Parser)        │
├────────────────────────────────────────────────────────┤
│ 3. Store Whitelist Filtering                          │
│    (Amazon / Zalando / Domain Exclusions)             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
                (Push to Async Queue)
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Async Message Worker                               │
│    (Producer → Consumer Processing)                   │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
                 (Chain of Responsibility)
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. ExtractorHandler                                   │
│    (Discount Extraction Strategy)                     │
├────────────────────────────────────────────────────────┤
│ 6. KeywordHandler                                     │
│    (Niche / Premium Brand Validation)                 │
├────────────────────────────────────────────────────────┤
│ 7. EvaluationHandler                                  │
│    (Mathematical Threshold Validation)                │
├────────────────────────────────────────────────────────┤
│ 8. BlacklistHandler                                   │
│    (Final Forbidden Word Validation)                  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
                   [Forward / Drop]
```

---


## ✅ Core Design Goals

- Fully asynchronous
- High-throughput processing
- Non-blocking Telegram event handling
- Modular filtering architecture
- Easily extensible parsing strategies
- Runtime-configurable filtering logic

---