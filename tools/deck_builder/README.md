# 🃏 Anki Deck Builder Automation
A powerful GUI tool designed to automate the creation of rich media Anki decks. It streamlines the process of combining text, audio (Google TTS), images, and video clips into ready-to-use `.apkg` files.
Designed for language learners and educators who need to generate high-quality flashcards in bulk.

## 🎥 Demos

### 2. Deck Builder (Generation Process)
![Deck Builder Demo](img/demo_animation(deck_builder).gif)

## ✨ Features

* **GUI Interface:** User-friendly interface built with `tkinter` for easy configuration.
* **Google Cloud TTS:** High-quality neural audio generation for phrases.
* **Smart Video Handling:** Automatic compatibility checks for different platforms:
    * `.mp4` (iOS & Android compatible)
    * `.m4v` (iOS optimized)
    * `.webm` (PC & Android optimized)
* **Flexible Layouts:** Support for "Front-to-Back", "Back-to-Front", and "Mixed" card types.
* **Media Processing:** Automatic resizing and formatting of images and videos.
* **Naming Convention:** Auto-generates detailed filenames containing deck stats, date, and compatibility info.

## 🛠 Tech Stack

* **Language:** Python 3.10+
* **GUI:** Tkinter
* **Media Processing:** MoviePy, Pillow (PIL), FFmpeg
* **Anki Integration:** `genanki`
* **Cloud Services:** Google Cloud Text-to-Speech API

## 🚀 Installation & Setup

### 1. Prerequisites
Ensure you have [FFmpeg](https://ffmpeg.org/download.html) installed on your system (required for video processing).

### 2. Install Dependencies
Navigate to the tool directory and install the required packages:

```bash
cd tools/deck_builder
pip install -r requirements.txt
```
### 3. Google Cloud TTS Setup
To use high-quality audio, you need a Google Cloud Service Key.
1. Place your JSON key file in the `keys/` directory.
2. Follow the detailed instructions in `keys/README.txt` to configure the Project ID.

## 📂 Input Data Structure
The tool expects a specific folder structure for input data. By default, it looks into the `input` folder, but you can select any directory via the GUI.

**Required File Structure:**

```text
/your_input_folder/
├── ru_text.txt       # List of Russian phrases (one per line)
├── en_text.txt       # List of English translations (one per line)
├── images/           # Images named by number: 001.jpg, 002.jpg...
└── video/            # Videos named by number: 001.mp4, 002.mp4...
```

> **Note:** The tool includes an "Import Videos" feature that attempts to automatically rename and index video files if they contain numbers (e.g., `my_video_45.mp4` -> `045.mp4`).

## 📖 Usage Guide

1. **Run the Application:**
```bash
python main.py
```
2. **Select Input Directory:** Choose the folder containing your text files and media.
3. **Import Data:**
   * Click **"Import Phrases"** to load text from `.txt` files.
   * Click **"Import Videos"** to index and prepare video files.
4. **Configure Deck:**
   * Set the **Deck Name**.
   * Choose **Deck Type** (e.g., Mixed for double-sided cards).
   * Select **Video Format** based on your target device (iOS/Android).
   * Customize card fields (Front/Back content order).
5. **Generate:** Click **"Create Deck"**. The result will be saved in the `output/` folder.

## 📱 Video Compatibility Guide

* The tool adapts the deck based on the target platform:
| Format   | Target Platform |                      Description                     |
| :------- | :-------------- | :--------------------------------------------------- |
| **MP4**  | iOS & Android   | Universal format, best compatibility.                |
| **M4V**  | iOS             | Optimized for Apple devices.                         |
| **WEBM** | PC & Android    | Lightweight, open web format (not supported on iOS). |

## 📝 License

* This project is part of a personal portfolio.