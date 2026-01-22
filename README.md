# Video-to-Anki Subtitle Processor

### 🛠 Automated ETL Tool for Language Learning

**Role:** Developer & QA Engineer
**Stack:** Python 3, **PyQt5** (GUI), **SQLite**, **NLP (pymorphy3)**, `pysrt`, Threading.

![Demo Animation](img/demo.gif)

## 🚀 Project Overview
This desktop application automates the creation of high-quality Anki flashcards from video content. It acts as an **ETL (Extract, Transform, Load)** pipeline that parses raw subtitles, synchronizes them with learning lists using morphological analysis, and extracts precise media clips.

**Key Engineering Challenges Solved:**
* **Concurrency:** Implemented `QThread` and thread-safe DB locking (`threading.Lock`) to perform heavy NLP parsing operations without freezing the UI.
* **Data Integrity:** "Smart Matching" algorithm using **Levenshtein distance** (`difflib`) and Lemmatization (`pymorphy3`) to match phrases regardless of word forms (e.g., "go" == "going").
* **Algorithmic Precision:** Custom logic to interpolate sub-sentence timestamps based on word density distribution (`utils.calculate_exact_timestamps`).
* **Persistence:** SQLite integration to save session state, allowing users to resume large projects after restart.

## ⚙️ Key Features
1.  **NLP-Driven Parsing:** Normalizes words to their base forms (lemmas) to find matches even if the tense or case differs.
2.  **Manual Override Mode:** Context menus and "Find Manually" feature allow users to patch missing data via external editor integration (Notepad).
3.  **Conflict Resolution:** Deduplication logic ensures that the same phrase is not processed twice across different timestamps.
4.  **Logging & Error Handling:** Comprehensive logging of parsing failures and I/O operations for debugging.

## 📂 Project Structure
* `app.py` - Main entry point, GUI logic (PyQt5), and Event Loop.
* `database.py` - Thread-safe SQLite wrapper for session persistence.
* `subtitle_processor.py` - Core business logic for phrase matching.
* `utils.py` - Math & NLP algorithms (Fuzzy matching, Timestamp calculation).
* `models.py` - SQL schema definitions.

## 🛠 Installation & Usage

### Prerequisites
* Python 3.10+
* FFmpeg (must be added to PATH)

### Setup
```bash
# Clone the repository
git clone [https://github.com/Andrei-Shishkov-QA/subtitle_processor.git](https://github.com/Andrei-Shishkov-QA/subtitle_processor.git)

# Install dependencies
pip install -r requirements.txt

# Running the App
python app.py