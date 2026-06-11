from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QTextEdit, QDialogButtonBox, QLabel
)

class ExamDetailsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exam Details")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Form Inputs
        form_layout = QFormLayout()
        
        self.input_school = QLineEdit()
        self.input_school.setPlaceholderText("e.g. St. Xavier's High School")
        
        self.input_exam = QLineEdit()
        self.input_exam.setPlaceholderText("e.g. Mathematics Mid-Term")
        
        self.input_time = QLineEdit("3 Hours")
        
        self.input_instructions = QTextEdit()
        self.input_instructions.setPlaceholderText("Enter instructions (one per line)...")
        self.input_instructions.setPlainText(
            "All questions are compulsory.\n"
            "The marks intended for questions are given in brackets [ ].\n"
            "Use of calculators is not permitted."
        )
        self.input_instructions.setMaximumHeight(100)
        
        form_layout.addRow("School Name:", self.input_school)
        form_layout.addRow("Exam Name:", self.input_exam)
        form_layout.addRow("Time Allowed:", self.input_time)
        form_layout.addRow("Instructions:", self.input_instructions)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_data(self):
        """Returns the dictionary needed for the PDF generator."""
        # Convert instructions text block into a list of strings
        raw_instr = self.input_instructions.toPlainText().split('\n')
        clean_instr = [line.strip() for line in raw_instr if line.strip()]
        
        return {
            "school_name": self.input_school.text() or "School Name",
            "exam_name": self.input_exam.text() or "Examination",
            "time_allowed": self.input_time.text(),
            "instructions": clean_instr
        }