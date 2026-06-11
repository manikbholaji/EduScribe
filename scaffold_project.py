import os
from pathlib import Path

def create_structure():
    # Define the root directory name
    root_dir = Path(".")

    # Define the folder structure
    directories = [
        "app",
        "app/model",
        "app/view",
        "app/view/ui",  # For .ui files if we use Qt Designer later
        "app/controller",
        "app/utils",
        "assets",
        "assets/images",
        "assets/templates", # For Jinja2/LaTeX templates
        "tests",
        "data" # For SQLite DB
    ]

    # Define files to create with initial content
    files = {
        "requirements.txt": (
            "PyQt6==6.8.0\n"
            "Jinja2==3.1.4\n"
            "requests==2.32.3\n"
            "Pillow==11.0.0\n"
        ),
        "app/__init__.py": "",
        "app/model/__init__.py": "",
        "app/view/__init__.py": "",
        "app/controller/__init__.py": "",
        "main.py": (
            "import sys\n"
            "from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget\n"
            "from PyQt6.QtCore import Qt\n\n"
            "class MainWindow(QMainWindow):\n"
            "    def __init__(self):\n"
            "        super().__init__()\n"
            "        self.setWindowTitle('EduScribe - Initial Setup Test')\n"
            "        self.setMinimumSize(800, 600)\n\n"
            "        # Central Widget\n"
            "        layout = QVBoxLayout()\n"
            "        label = QLabel('Phase 1: Environment Setup Complete! ✅')\n"
            "        label.setAlignment(Qt.AlignmentFlag.AlignCenter)\n"
            "        font = label.font()\n"
            "        font.setPointSize(20)\n"
            "        label.setFont(font)\n"
            "        \n"
            "        layout.addWidget(label)\n"
            "        container = QWidget()\n"
            "        container.setLayout(layout)\n"
            "        self.setCentralWidget(container)\n\n"
            "if __name__ == '__main__':\n"
            "    app = QApplication(sys.argv)\n"
            "    window = MainWindow()\n"
            "    window.show()\n"
            "    sys.exit(app.exec())\n"
        )
    }

    print(f"🚀 Initializing EduScribe Project Structure...")

    # Create directories
    for dir_path in directories:
        path = root_dir / dir_path
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(f"   [OK] Created directory: {dir_path}")
        except Exception as e:
            print(f"   [ERR] Failed to create {dir_path}: {e}")

    # Create files
    for file_path, content in files.items():
        path = root_dir / file_path
        try:
            if not path.exists():
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"   [OK] Created file: {file_path}")
            else:
                print(f"   [SKIP] File already exists: {file_path}")
        except Exception as e:
            print(f"   [ERR] Failed to create {file_path}: {e}")

    print("\n✅ Project scaffolding complete!")
    print("👉 Next Step: Follow the instructions in 'phase_1_guide.md' to activate your environment.")

if __name__ == "__main__":
    create_structure()