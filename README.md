# EduScraper — 🏫 Education Institute Contact Finder

A powerful, automated tool to search for educational institutions (schools, colleges, universities, and coaching centers) using Google and extract verified email addresses and phone numbers directly from their websites.

![EduScraper UI](https://raw.githubusercontent.com/msubham193/edu-scraper/main/static/screenshot.png) (Add screenshot here later)

## ✨ Features

- **🎯 Smart Filtering**: Filter by State, City, Pincode, and Institute Type.
- **📚 Category Support**: Pre-configured categories for JEE/NEET, IAS, Schools (CBSE/ICSE), Engineering, MBA, Law, and more.
- **⚡ Live Scraping**: Real-time progress tracking with a smooth Web UI.
- **📄 Excel Export**: Download results in a beautifully formatted `.xlsx` file with contact details and institute tags.
- **🤖 Playwright Integrated**: Uses headless Chromium to bypass anti-bot measures and handle modern JavaScript websites.

## 🚀 Deployment (Docker/Render)

This project is cloud-ready with **Docker**.

1. Connect this repo to **Render.com**.
2. Select **Docker** as the Runtime.
3. Add the `PORT` environment variable (set to `5000` by default).
4. Deploy!

## 🛠️ Local Setup

1. **Clone & Install**:
   ```bash
   git clone https://github.com/msubham193/edu-scraper.git
   cd edu-scraper
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. **Run Server**:
   ```bash
   python -X utf8 server.py
   ```
   Open `http://localhost:5000` in your browser.

## 📁 Project Structure

- `server.py`: Flask backend API & SSE streaming.
- `google_search.py`: Playwright-based search engine.
- `scraper.py`: Website fetcher & sub-page discovery.
- `extractor.py`: Regex & phone/email extraction logic.
- `exporter.py`: Excel generation using openpyxl.
- `static/`: HTML/JS/CSS frontend.
- `Dockerfile`: Deployment configuration.

---
Created with ❤️ by Antigravity
