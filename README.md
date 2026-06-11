# EduScribe 📄✏️

EduScribe is a premium desktop application built with **Python** and **PyQt6** designed to help educators create, format, and generate professional exam papers seamlessly.

With EduScribe, teachers can write questions in standard text, use complex **LaTeX mathematical notation**, attach graphics/diagrams, scan handwritten or printed questions via **OCR**, and export the final compiled question paper directly to high-quality LaTeX (`.tex`) and PDF formats.

---

## ✨ Features

- **Intuitive GUI**: Sleek and modern user interface designed for distraction-free exam paper composition.
- **LaTeX Math Support**: Write questions using inline or block LaTeX syntax (e.g., $E = mc^2$ or $\int_a^b f(x)dx$).
- **Image Attachments**: Attach diagrams, charts, or maps to specific questions.
- **OCR Scan (Mathpix API)**: Instantly digitize printed or handwritten questions from images into structured LaTeX.
- **Dynamic Marks Calculator**: Automatically calculates total examination marks as questions are added or removed.
- **Renumbering**: Automatically handles item numbering and ordering when questions are added, modified, or deleted.
- **Instant LaTeX & PDF Export**: Generates perfectly styled exam papers using custom Jinja2 LaTeX templates.
- **Testing Suite**: Includes a robust test suite covering unit models, PDF generation, UI event handlers, and end-to-end functionality.

---

## 🛠️ Tech Stack

- **Core**: Python 3.10+
- **GUI Framework**: PyQt6
- **Template Engine**: Jinja2 (configured for LaTeX compilation syntax)
- **OCR Engine**: Mathpix API
- **Document Rendering**: LaTeX (`pdflatex`)

---

## 🚀 Getting Started

### Prerequisites

To compile PDF copies directly from the app, you need a LaTeX distribution installed and added to your system `PATH`:
- **Windows**: [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/)
- **macOS**: [MacTeX](https://www.tug.org/mactex/)
- **Linux**: `texlive-full`

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/EduScribe.git
   cd EduScribe
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

Execute the main script from the root directory:
```bash
python main.py
```

---

## 🧪 Testing Suite

EduScribe utilizes Python's built-in `unittest` framework combined with `PyQt6.QtTest` for headless UI/UX verification.

Run the test suite:
```bash
python run_tests.py
```

The tests cover:
1. **Model Tests**: Question object initialization and modification rules.
2. **UI Tests**: Add manual questions, text inputs, dynamic renumbering, delete handlers, and image attachments.
3. **Critical Path Tests**: Confirm clear-all prompts and dialog state machines.
4. **Functionality Tests**: OCR scanning simulations and full Jinja2 LaTeX compilation workflow.

---

## 📂 Project Structure

```text
EduScribe/
│
├── app/
│   ├── controller/      # Controller modules for event handling
│   ├── model/           # Core models (e.g. Question)
│   ├── utils/           # Utilities (OCRService, PDFGenerator)
│   └── view/            # GUI Components (MainWindow, Dialogs, Styles)
│
├── assets/
│   ├── images/          # Application graphics
│   └── templates/       # Jinja2 LaTeX templates (exam_template.tex)
│
├── tests/               # Test suites (test_suite.py, test_ui.py)
│
├── requirements.txt     # Dependency constraints
├── run_tests.py         # Test runner script
└── main.py              # Application entrypoint
```

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
