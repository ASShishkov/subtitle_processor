# 🎬 Video-to-Anki Subtitle Processor

### 🛠 Automated ETL Tool for Language Learning
**Role:** Developer & QA Engineer
**Stack:** Python 3, **PyQt5** (GUI), **SQLite**, **NLP (pymorphy3)**, `pysrt`, Threading.

## 🎥 Demos

### Subtitle Processor (Extraction Logic)
![Subtitle Extractor Demo](img/demo_animation(subtitle_extractor).gif)

## 🚀 Project Overview
This desktop application automates the creation of high-quality Anki flashcards from video content. It acts as an **ETL (Extract, Transform, Load)** pipeline that parses raw subtitles, synchronizes them with learning lists using morphological analysis, and extracts precise media clips.

**Key Engineering Challenges Solved:**
* **Concurrency:** Implemented `QThread` to perform heavy NLP parsing operations without freezing the UI.
* **Data Integrity:** "Smart Matching" algorithm using **Levenshtein distance** (`difflib`) and Lemmatization (`pymorphy3`) to match phrases regardless of word forms.
* **Algorithmic Precision:** Custom logic to interpolate sub-sentence timestamps based on word density distribution.
* **Persistence:** SQLite integration to save session state (ACID compliant).

## ⚙️ Key Features
1.  **NLP-Driven Parsing:** Normalizes words to their base forms (lemmas) to find matches even if the tense or case differs.
2.  **Manual Override Mode:** Context menus and "Find Manually" feature allows users to patch missing data via external editor integration (Notepad).
3.  **Timestamp Interpolation:** Calculates the exact start/end time of a specific phrase *within* a long subtitle line (`calculate_exact_timestamps`).
4.  **Logging & Error Handling:** Comprehensive logging of parsing failures and I/O operations.

## 🛠 Installation & Usage

### Prerequisites
* Python 3.10+
* FFmpeg (must be added to PATH)

### Setup
Since this tool is part of the **AnkiForge** suite, ensure you have installed the project dependencies:

```bash
# Navigate to the tool directory
cd tools/subtitle_extractor

# Install dependencies
pip install -r requirements.txt
```

### Running the App
```bash
python app.py
```
Developed to demonstrate skills in Desktop App Testing, Automation, and Python Development.

## 📖 User Guide

### 1. Input Configuration
The interface requires three input files to begin the ETL process:
* **Subtitle Path (SRT):** The source subtitles from the movie/series.
* **English Phrases (TXT):** A list of target phrases you want to learn (one per line).
* **Russian Phrases (TXT):** The corresponding translations (one per line).
* **Output Folder:** Where the generated artifacts will be saved.

### 2. Analysis Workflow
1. **Find Matches:** Click this button to start the NLP engine. It runs in a background thread.
   * *Result:* The table will populate with "Full Matches" (green) and "Partial/Not Found" items.
2. **Review Data:**
   * **Double-click** a row to toggle it for export.
   * Use the **Threshold Slider** to adjust strictness of fuzzy matching.
3. **Manual Fixes (Optional):**
   * If a phrase wasn't found, select the row and click **"Find Manually"**.
   * The app will prompt you to search for the text inside the SRT file and link it manually.
4. **Modify Timestamps:**
   * Select rows and click **"Modify Timestamps"**.
   * You can add/subtract seconds from the Start or End time (e.g., `-0.2` start, `+0.5` end) to ensure the audio clip isn't cut off.

### 3. Export
Once satisfied, use the export buttons:
* **Get Excerpts:** Generates intermediate text files and cuts logic.
* **Get Timestamps:** Creates a new, filtered `.srt` file containing only the lines relevant to your study list.

## 🏗 Code Structure
* `main.py`: Entry point. Handles `QMainWindow`, UI layout, and Thread/Signal logic.
* `database.py`: Handles SQLite connections. Uses a `Lock` object to prevent race conditions during threaded writes.
* `subtitle_processor.py`: Contains the core NLP logic (lemmatization and matching).
* `utils.py`: Helper functions for parsing SRT and calculating timestamps.

---
*Developed as part of a Python Automation Portfolio.*