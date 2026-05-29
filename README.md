# 📄 Custom PDF Text Redactor & Watermark Remover

A fast, lightweight, and completely free web-based utility designed to permanently strip unwanted text, promotional watermarks, and telegram links from your PDF files. 

Built specifically with students in mind to clean up cluttered study materials (like heavily watermarked JEE prep files) and improve readability.

🚀 **[Click Here to Use the Live Web Application](https://pdfcleaner007.streamlit.app/)**

---

## ✨ Features
* **Bulk Processing:** Upload and clean multiple PDF files simultaneously.
* **Smart Defaults:** Comes pre-configured to look for common promotional strings (e.g., `Rankers  Academy  JEE`).
* **Fully Customizable:** Easily add, edit, or remove target phrases line-by-line via the interactive sidebar.
* **True Redaction:** This app doesn't just put a white box over the text—it permanently strips the target characters from the underlying PDF data layer, making it completely unsearchable and uncopyable.
* **Privacy Focused:** Your files are processed entirely in memory and are never stored on any server.

---

## 🛠️ How It Works

1. **Paste Targets:** Type or paste the phrases you want to get rid of into the sidebar (one phrase per line).
2. **Upload:** Drag and drop your PDFs into the main window.
3. **Download:** The application instantly processes the files and generates a customized download button for your cleaned PDFs.

---

## 💻 Local Installation & Setup

If you want to run this application locally on your machine instead of using the cloud version, follow these steps:

### Prerequisites
Make sure you have Python installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/ostrich2635/pdf_cleaner
cd pdf_cleaner
