from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QSpinBox, QPushButton, QLabel, QFileDialog, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

class QuestionWidget(QWidget):
    # Signals to communicate with the Main Window
    delete_requested = pyqtSignal(QWidget)
    content_changed = pyqtSignal() 

    def __init__(self, question_model, parent=None):
        super().__init__(parent)
        self.model = question_model
        self.setup_ui()

    def setup_ui(self):
        # Card Styling
        self.setObjectName("QuestionCard")
        self.setStyleSheet("""
            QWidget#QuestionCard {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                margin-bottom: 10px;
            }
            QLabel { font-weight: bold; color: #2f3640; }
        """)
        
        layout = QVBoxLayout(self)

        # --- Top Row: Label, Marks, Delete ---
        top_row = QHBoxLayout()
        
        self.lbl_number = QLabel(f"Question {self.model.id}")
        top_row.addWidget(self.lbl_number)
        
        top_row.addStretch()
        
        top_row.addWidget(QLabel("Marks:"))
        self.spin_marks = QSpinBox()
        self.spin_marks.setRange(1, 20)
        self.spin_marks.setValue(self.model.marks)
        self.spin_marks.valueChanged.connect(self.update_model)
        top_row.addWidget(self.spin_marks)
        
        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setStyleSheet("background-color: #e84118; color: white; border-radius: 3px;")
        self.btn_delete.clicked.connect(self.request_delete)
        top_row.addWidget(self.btn_delete)
        
        layout.addLayout(top_row)

        # --- Middle Row: Text Area ---
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Type your question here (or use LaTeX logic like $x^2$)...")
        self.text_edit.setMinimumHeight(80)
        self.text_edit.setText(self.model.text)
        self.text_edit.textChanged.connect(self.update_model)
        layout.addWidget(self.text_edit)

        # --- Bottom Row: Image Attach ---
        img_row = QHBoxLayout()
        self.btn_attach = QPushButton("📎 Attach Image")
        self.btn_attach.clicked.connect(self.attach_image)
        self.btn_attach.setStyleSheet("background-color: #f5f6fa; color: black; border: 1px solid #ccc;")
        img_row.addWidget(self.btn_attach)
        
        self.lbl_image_status = QLabel("No image attached")
        self.lbl_image_status.setStyleSheet("font-weight: normal; color: #7f8c8d; font-style: italic;")
        img_row.addWidget(self.lbl_image_status)
        
        img_row.addStretch()
        layout.addLayout(img_row)

    def update_model(self):
        """Syncs UI state back to the data model."""
        self.model.text = self.text_edit.toPlainText()
        self.model.marks = self.spin_marks.value()
        self.content_changed.emit()

    def attach_image(self):
        import os
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.model.image_path = file_path
            self.lbl_image_status.setText(f"Image: {os.path.basename(file_path)}")
            self.content_changed.emit()

    def request_delete(self):
        self.delete_requested.emit(self)