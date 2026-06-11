from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QComboBox, QScrollArea, 
    QSplitter, QFrame, QFileDialog, QMessageBox, QInputDialog, QDialog
)
from PyQt6.QtCore import Qt
from app.view.styles import MAIN_STYLE
from app.model.question import Question
from app.view.question_widget import QuestionWidget
from app.utils.ocr_service import OCRService
from app.utils.pdf_generator import PDFGenerator
from app.view.exam_details_dialog import ExamDetailsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EduScribe - Question Paper Generator")
        self.setMinimumSize(1200, 800)
        
        # State Data
        self.questions = [] # List of QuestionWidget objects
        self.question_counter = 1

        # Apply global styles
        self.setStyleSheet(MAIN_STYLE)

        # Main Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_ui()

    def setup_ui(self):
        # 1. LEFT SIDEBAR (Tools)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title/Logo Area
        title_label = QLabel("EduScribe Tools")
        title_label.setObjectName("SidebarTitle")
        self.sidebar_layout.addWidget(title_label)

        # Subject Toggle
        self.subject_combo = QComboBox()
        self.subject_combo.addItems(["General", "Mathematics", "Science (Physics/Chem)"])
        self.subject_combo.setStyleSheet("padding: 8px; margin: 10px; background: white;")
        self.sidebar_layout.addWidget(self.subject_combo)

        # Action Buttons
        self.btn_add_manual = QPushButton("➕ Add Manual Question")
        self.btn_ocr_scan = QPushButton("📷 Scan Image (OCR)")
        
        # [NEW] Clear All Button (Phase 6)
        self.btn_clear = QPushButton("🗑️ Clear All Questions")
        self.btn_clear.setStyleSheet("background-color: #d63031; color: white; margin-top: 20px;")
        
        self.btn_export = QPushButton("📄 Export to PDF")
        
        self.sidebar_layout.addWidget(self.btn_add_manual)
        self.sidebar_layout.addWidget(self.btn_ocr_scan)
        self.sidebar_layout.addWidget(self.btn_clear) # Added to layout
        self.sidebar_layout.addStretch() 
        self.sidebar_layout.addWidget(self.btn_export)

        # Connect Signals (Events)
        self.btn_add_manual.clicked.connect(self.add_manual_question)
        self.btn_ocr_scan.clicked.connect(self.scan_image_question)
        self.btn_clear.clicked.connect(self.clear_all_questions) # Connected signal
        self.btn_export.clicked.connect(self.export_pdf) 

        # 2. CENTER PANEL (Composer)
        self.composer_area = QScrollArea()
        self.composer_area.setWidgetResizable(True)
        self.composer_content = QWidget()
        self.composer_layout = QVBoxLayout(self.composer_content)
        self.composer_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.composer_area.setWidget(self.composer_content)

        # 3. RIGHT PANEL (Preview)
        self.preview_panel = QFrame()
        self.preview_panel.setObjectName("PreviewPanel")
        self.preview_layout = QVBoxLayout(self.preview_panel)
        
        self.preview_label = QLabel("Output Logs will appear here")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.preview_layout.addWidget(self.preview_label)

        # 4. SPLITTER (Allows resizing)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.composer_area)
        self.splitter.addWidget(self.preview_panel)
        
        # Set initial widths (Sidebar=200, Composer=600, Preview=400)
        self.splitter.setSizes([200, 600, 400])

        # Add splitter to main layout
        self.main_layout.addWidget(self.splitter)

    # --- ACTION HANDLERS ---

    def add_manual_question(self):
        """Creates a blank question widget."""
        self.create_question_entry("")

    def scan_image_question(self):
        """Opens file dialog, sends to OCR, and populates result."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image to Scan", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return

        self.statusBar().showMessage("Processing OCR... Please wait...")
        
        success, result = OCRService.extract_text(file_path)
        
        self.statusBar().clearMessage()
        
        if success:
            self.create_question_entry(result)
        else:
            QMessageBox.critical(self, "OCR Failed", result)

    def create_question_entry(self, text):
        """Helper to create model and widget."""
        q_model = Question(self.question_counter, text=text)
        q_widget = QuestionWidget(q_model)
        q_widget.delete_requested.connect(self.delete_question)
        self.composer_layout.addWidget(q_widget)
        self.questions.append(q_widget)
        self.question_counter += 1

    def delete_question(self, widget):
        """Removes a question from the UI and list."""
        self.composer_layout.removeWidget(widget)
        widget.deleteLater()
        if widget in self.questions:
            self.questions.remove(widget)
        self.renumber_questions()

    # [NEW] Clear All Method (Phase 6)
    def clear_all_questions(self):
        """Removes all questions from the list."""
        if not self.questions:
            return

        confirm = QMessageBox.question(
            self, "Confirm Clear", 
            "Are you sure you want to remove all questions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # We iterate backwards to delete safely
            for widget in reversed(self.questions):
                self.delete_question(widget)
            
            self.question_counter = 1
            if self.statusBar():
                self.statusBar().showMessage("All questions cleared.", 3000)

    def renumber_questions(self):
        """Updates the visible question numbers."""
        for idx, widget in enumerate(self.questions):
            widget.lbl_number.setText(f"Question {idx + 1}")
            widget.model.id = idx + 1
        self.question_counter = len(self.questions) + 1

    def export_pdf(self):
        """Generates the LaTeX file and attempts to compile PDF."""
        if not self.questions:
            QMessageBox.warning(self, "Empty", "Please add some questions first!")
            return

        # 1. Get Exam Metadata via Dialog
        dialog = ExamDetailsDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return # User cancelled
            
        exam_metadata = dialog.get_data()
        
        # Add dynamic max marks calculation
        total_marks = sum(q.model.marks for q in self.questions)
        exam_metadata["max_marks"] = str(total_marks)
        exam_metadata["questions"] = [q.model for q in self.questions]

        # 2. Select Save Location
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Exam Paper", "exam_paper.tex", "LaTeX Files (*.tex)"
        )
        if not save_path:
            return

        # 3. Generate .tex
        generator = PDFGenerator()
        success, msg = generator.generate_tex(exam_metadata, save_path)

        if success:
            log_msg = f"✅ Generated: {save_path}\n"
            
            # 4. Attempt Compile (Optional)
            compile_choice = QMessageBox.question(
                self, "Compile PDF?", 
                "TeX file generated.\nDo you have LaTeX (pdflatex) installed to compile to PDF?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if compile_choice == QMessageBox.StandardButton.Yes:
                self.preview_label.setText("Compiling PDF... Please wait.")
                # Force UI update
                self.repaint() 
                
                pdf_success, pdf_msg = generator.compile_to_pdf(save_path)
                if pdf_success:
                    log_msg += f"✅ Compiled: {pdf_msg}"
                    QMessageBox.information(self, "Success", f"PDF Created successfully at:\n{pdf_msg}")
                else:
                    log_msg += f"❌ Compilation Failed: {pdf_msg}"
                    QMessageBox.warning(self, "Compilation Error", pdf_msg)
            
            self.preview_label.setText(log_msg)
        else:
            QMessageBox.critical(self, "Error", f"Failed to generate file: {msg}")