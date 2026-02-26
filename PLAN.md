# Project Plan - Receipt Organization App

## Overview
A Streamlit application for recording and organizing expenses with receipt images. Users can capture receipt details (date, item, category, amount), which are saved to Google Sheets with associated images stored in Google Drive.

---

## Phase 1: Receipt Capture & Storage

### Step 1: Core Services Setup
- [ ] Implement `auth_service.py` - Google OAuth authentication
- [ ] Implement `sheets_service.py` - Google Sheets API integration
- [ ] Implement `drive_service.py` - Google Drive API integration
- [ ] Implement `pdf_service.py` - PDF/image processing utilities

### Step 2: Utility Functions
- [ ] Implement `date_utils.py` - Date parsing and formatting
- [ ] Implement `id_utils.py` - Generate unique IDs for receipts
- [ ] Implement `image_utils.py` - Image processing and validation

### Step 3: UI Components
- [ ] Implement `capture_form.py` - Form for capturing receipt details (date, item, category, amount, image upload)
- [ ] Implement `transactions_table.py` - Table display of all transactions with edit/delete options
- [ ] Implement `print_section.py` - Basic UI layout for Phase 2

### Step 4: Main Application
- [ ] Implement `app.py` - Main Streamlit app with:
  - User selection dropdown
  - Receipt capture form
  - Transactions table display
  - Delete functionality

### Step 5: Data Flow Implementation
- [ ] Upload receipt image to Google Drive
- [ ] Extract image file ID and store in Google Sheets row
- [ ] Link transactions in Sheets to receipt images in Drive
- [ ] Implement delete functionality (remove from Sheets AND Drive)

### Step 6: Testing & Configuration
- [ ] Set up `requirements.txt` with all dependencies
- [ ] Configure `streamlit/secrets.toml` with Google API credentials
- [ ] Test complete flow: capture → upload → display → delete

---

## Phase 2: Report Printing

### Step 1: Filtering UI
- [ ] Add month selector/filter in `print_section.py`
- [ ] Add "view all" option

### Step 2: Report Generation
- [ ] Fetch transactions from Sheets based on filter
- [ ] Generate printable report layout

### Step 3: Report Display
- [ ] Display report with all relevant transaction details
- [ ] Add print/export to PDF functionality
- [ ] Include receipt images in report

---

## Progress Tracking

**Current Status:** Planning phase
**Phase 1 Completion:** 0%
**Phase 2 Completion:** 0%

> Update this section as work progresses
