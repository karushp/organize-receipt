# Receipt Capture & Expense Tracker – Project Plan

## Overview
A lightweight receipt tracking application designed for **two users** to capture receipts from mobile devices, store them reliably, and export the data to Google Sheets for reporting and tax purposes.

The system uses **Supabase as the primary backend** and **Google Sheets as a secondary reporting layer**.

---

# System Architecture

User (iPhone / Browser)
│
▼
Streamlit Web App
│
▼
Supabase
├── PostgreSQL Database (transactions)
├── Storage Bucket (receipt images)
└── API
│
▼
Python Sync Script
│
▼
Google Sheets (per user)

---

# Core Features

### Receipt Capture
- Upload receipt photo (camera or file)
- Manual entry of:
  - date
  - category
  - amount
  - note
  - user

### Image Storage
- Receipts stored in **Supabase Storage**

Structure:

receipts/
user-1/
user-2/

### Transaction Database
All transaction data stored in **Supabase PostgreSQL**.

---

# Database Design

## Table: `transactions`

| Column | Type | Description |
|------|------|-------------|
| id | uuid | Primary key |
| date | date | Transaction date |
| user | text | user-1 or user-2 (from USERS) |
| category | text | Expense category |
| amount | numeric | Transaction amount |
| note | text | Optional notes |
| receipt_url | text | Storage URL of receipt |
| created_at | timestamp | Record creation time |
| updated_at | timestamp | Last update |

---

# Supabase Setup

## 1 Create Project
Create a project in Supabase.

## 2 Create Table
Create the `transactions` table.

## 3 Create Storage Bucket

receipts

Set bucket visibility to **public**.

---

# Application (Streamlit)

## Main Pages

### 1 Upload Receipt
Fields:

- User selector
- Date
- Category dropdown
- Amount
- Notes
- Image upload

Actions:

Upload image → Supabase Storage
Get public URL
Insert row → transactions table

---

### 2 Transaction Editor
User can:

- view transactions
- edit details
- delete records

---

### 3 Monthly Report

User selects:

- month
- user

Display:

- transactions list
- receipt thumbnails
- totals

Option to **print multiple receipts per page**.

---

# Google Sheets Sync

Supabase is the **primary database**.

Google Sheets is used for:

- review
- tax reporting
- manual editing if necessary

---

## Sync Script

Python script will:

1. fetch transactions from Supabase
2. filter by user
3. update Google Sheets

Example structure:

scripts/
sync_to_sheets.py

---

## Google Sheets Structure

Spreadsheet:

expenses
├── user-1
└── user-2

Each tab contains:

| date | category | amount | note | receipt_url |

---

# Sync Process

Supabase
↓
Python script
↓
Google Sheets

Options:

### Manual
Run script manually.

python sync_to_sheets.py

### Scheduled
Run monthly using cron.

Example:

0 2 1 * * python sync_to_sheets.py

Runs on the **1st day of every month**.

---

# Repository Structure

receipt-tracker
│
├── app
│   ├── streamlit_app.py
│   ├── upload_receipt.py
│   ├── transactions.py
│   └── supabase_client.py
│
├── scripts
│   └── sync_to_sheets.py
│
├── utils
│   ├── image_processing.py
│   ├── export_statement.py
│   └── export_receipt.py
│
├── config
│   └── categories.json
│
├── requirements.txt
│
└── PROJECT_PLAN.md

---

# Dependencies

streamlit
supabase
pandas
gspread
google-auth
pillow

---

# Estimated Data Volume

Expected usage:

50 receipts per month
≈ 600 receipts per year

Supabase free tier is sufficient.

---

# Planned Phases

### Phase: PDF Print streamline
- **Statement in table** – Print transaction list (statement) in table form in the PDF.
- **Receipts in table** – Option to include receipt images in the same table (e.g. one row per transaction with thumbnail or image cell).
- **No receipt** – Option to generate PDF with statement/table only, without embedding receipt images.

### Phase: Capture enhancement
- **Auto crop with receipt edges** – Detect receipt boundaries in the captured/uploaded image and auto-crop to the receipt edges (e.g. document scanning style) before saving or displaying.

---

# Future Improvements

### AI Receipt Parsing
Automatically extract:

- merchant
- date
- amount

### Category Suggestions
Automatically categorize expenses.

### Dashboard
Add charts:

- monthly spending
- category breakdown
- user comparison

### PDF Reports
Generate downloadable reports for accounting.

---

# Advantages of This Architecture

- No Google Drive permission issues
- Simple backend
- Reliable image storage
- Easy export to Google Sheets
- Scalable if usage grows

---

# Development Steps

1. Create Supabase project
2. Create database table
3. Create storage bucket
4. Build Streamlit receipt upload page
5. Store transactions in Supabase
6. Build transaction viewer/editor
7. Implement Google Sheets sync script
8. Add monthly reporting view
9. Deploy application

---

# Deployment

Recommended hosting:

Render
or
Streamlit Cloud

Environment variables required:

SUPABASE_URL
SUPABASE_KEY
GOOGLE_SERVICE_ACCOUNT_JSON

---

# Summary

The system uses **Supabase as the reliable backend** and **Google Sheets for reporting**, allowing simple receipt capture from mobile devices while maintaining easy access to financial data for tax and accounting purposes.
