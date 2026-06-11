import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Force offscreen execution for PyQt6 in testing environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add the project root to the path so we can import 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog, QDialog
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from app.view.main_window import MainWindow
from app.view.question_widget import QuestionWidget
from app.utils.pdf_generator import PDFGenerator
from app.utils.ocr_service import OCRService

class TestEduScribeUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Creates the QApplication instance once for all tests."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        """Creates the main window before each test."""
        self.window = MainWindow()

    def tearDown(self):
        """Cleans up the main window."""
        self.window.close()
        self.window = None

    # --- COMPLETE UI TESTS ---
    
    def test_add_manual_question_ui(self):
        """Test adding manual questions via UI button click."""
        self.assertEqual(len(self.window.questions), 0)
        
        # Simulate manual question button click
        QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
        
        self.assertEqual(len(self.window.questions), 1)
        self.assertEqual(self.window.question_counter, 2)
        
        # Verify the widget has correct initial fields
        widget = self.window.questions[0]
        self.assertEqual(widget.lbl_number.text(), "Question 1")
        self.assertEqual(widget.spin_marks.value(), 1) # Default marks
        self.assertEqual(widget.text_edit.toPlainText(), "")

    def test_question_input_syncs_to_model(self):
        """Test that editing question text and marks updates the underlying model."""
        QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
        widget = self.window.questions[0]
        
        # Change marks
        widget.spin_marks.setValue(8)
        self.assertEqual(widget.model.marks, 8)
        
        # Change text
        widget.text_edit.setPlainText("Identify the value of $x$ in $2x + 5 = 15$.")
        self.assertEqual(widget.model.text, "Identify the value of $x$ in $2x + 5 = 15$.")

    def test_renumbering_on_deletion(self):
        """Test adding multiple questions and deleting one updates question numbers."""
        # Add 3 questions
        for _ in range(3):
            QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
            
        self.assertEqual(len(self.window.questions), 3)
        self.assertEqual(self.window.questions[0].lbl_number.text(), "Question 1")
        self.assertEqual(self.window.questions[1].lbl_number.text(), "Question 2")
        self.assertEqual(self.window.questions[2].lbl_number.text(), "Question 3")
        
        # Delete the middle question (Question 2)
        widget_to_delete = self.window.questions[1]
        self.window.delete_question(widget_to_delete)
        
        # Verify remaining questions are renumbered
        self.assertEqual(len(self.window.questions), 2)
        self.assertEqual(self.window.questions[0].lbl_number.text(), "Question 1")
        self.assertEqual(self.window.questions[0].model.id, 1)
        self.assertEqual(self.window.questions[1].lbl_number.text(), "Question 2")
        self.assertEqual(self.window.questions[1].model.id, 2)
        self.assertEqual(self.window.question_counter, 3)

    # --- CRITICAL UI TESTS ---

    @patch('PyQt6.QtWidgets.QMessageBox.question')
    def test_clear_all_questions_confirm_yes(self, mock_msgbox):
        """Test 'Clear All' button deletes all questions when user confirms Yes."""
        # Add questions
        for _ in range(3):
            QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.window.questions), 3)
        
        # Mock user clicking Yes on the confirmation dialog
        mock_msgbox.return_value = QMessageBox.StandardButton.Yes
        
        # Click clear all
        QTest.mouseClick(self.window.btn_clear, Qt.MouseButton.LeftButton)
        
        # Check that questions are cleared
        self.assertEqual(len(self.window.questions), 0)
        self.assertEqual(self.window.question_counter, 1)

    @patch('PyQt6.QtWidgets.QMessageBox.question')
    def test_clear_all_questions_confirm_no(self, mock_msgbox):
        """Test 'Clear All' button does not delete questions when user clicks No."""
        for _ in range(3):
            QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.window.questions), 3)
        
        # Mock user clicking No on the confirmation dialog
        mock_msgbox.return_value = QMessageBox.StandardButton.No
        
        QTest.mouseClick(self.window.btn_clear, Qt.MouseButton.LeftButton)
        
        # Verify questions are preserved
        self.assertEqual(len(self.window.questions), 3)

    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    def test_attach_image_to_question(self, mock_file_dialog):
        """Test attaching an image file to a question widget."""
        QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
        widget = self.window.questions[0]
        
        mock_file_dialog.return_value = ("C:/path/to/diagram.png", "Images (*.png *.jpg)")
        
        QTest.mouseClick(widget.btn_attach, Qt.MouseButton.LeftButton)
        
        self.assertEqual(widget.model.image_path, "C:/path/to/diagram.png")
        self.assertEqual(widget.lbl_image_status.text(), "Image: diagram.png")

    # --- FUNCTIONALITY TESTS ---

    @patch('app.utils.ocr_service.OCRService.extract_text')
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    def test_scan_image_ocr_success(self, mock_file_dialog, mock_ocr_extract):
        """Test successful OCR scan updates composer with extracted question text."""
        mock_file_dialog.return_value = ("C:/test_image.jpg", "Images (*.png *.jpg *.jpeg)")
        mock_ocr_extract.return_value = (True, "Evaluate the limit: $\\lim_{x \\to 0} \\frac{\\sin x}{x}$.")
        
        QTest.mouseClick(self.window.btn_ocr_scan, Qt.MouseButton.LeftButton)
        
        self.assertEqual(len(self.window.questions), 1)
        self.assertEqual(
            self.window.questions[0].text_edit.toPlainText(),
            "Evaluate the limit: $\\lim_{x \\to 0} \\frac{\\sin x}{x}$."
        )

    @patch('app.utils.ocr_service.OCRService.extract_text')
    @patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName')
    @patch('PyQt6.QtWidgets.QMessageBox.critical')
    def test_scan_image_ocr_failure(self, mock_critical, mock_file_dialog, mock_ocr_extract):
        """Test failed OCR scan shows error dialog and does not create new question."""
        mock_file_dialog.return_value = ("C:/test_image.jpg", "Images (*.png *.jpg *.jpeg)")
        mock_ocr_extract.return_value = (False, "API Error: Mathpix credential issue")
        
        QTest.mouseClick(self.window.btn_ocr_scan, Qt.MouseButton.LeftButton)
        
        self.assertEqual(len(self.window.questions), 0)
        mock_critical.assert_called_once()
        self.assertIn("Mathpix credential issue", mock_critical.call_args[0][2])

    @patch('app.view.exam_details_dialog.ExamDetailsDialog.exec')
    @patch('app.view.exam_details_dialog.ExamDetailsDialog.get_data')
    @patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
    @patch('app.utils.pdf_generator.PDFGenerator.generate_tex')
    def test_export_pdf_workflow(self, mock_generate_tex, mock_save_dialog, mock_get_data, mock_dialog_exec):
        """Test full workflow of exporting exam questions to latex/pdf."""
        # First test warning when no questions added
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            QTest.mouseClick(self.window.btn_export, Qt.MouseButton.LeftButton)
            mock_warning.assert_called_once()
            self.assertIn("add some questions first", mock_warning.call_args[0][2])

        # Add a question
        QTest.mouseClick(self.window.btn_add_manual, Qt.MouseButton.LeftButton)
        self.window.questions[0].text_edit.setPlainText("Test Question content")
        self.window.questions[0].spin_marks.setValue(10)
        
        # Setup mocks
        mock_dialog_exec.return_value = QDialog.DialogCode.Accepted
        mock_get_data.return_value = {
            "school_name": "Test Academy",
            "exam_name": "Final Exam",
            "time_allowed": "3 Hours",
            "instructions": ["Read carefully."]
        }
        mock_save_dialog.return_value = ("E:/Database/Eduscribe/test_export.tex", "LaTeX Files (*.tex)")
        mock_generate_tex.return_value = (True, "E:/Database/Eduscribe/test_export.tex")
        
        # Click export
        with patch('PyQt6.QtWidgets.QMessageBox.question') as mock_compile_question:
            mock_compile_question.return_value = QMessageBox.StandardButton.No
            QTest.mouseClick(self.window.btn_export, Qt.MouseButton.LeftButton)
            
            # Verify mocks were called correctly
            mock_dialog_exec.assert_called_once()
            mock_get_data.assert_called_once()
            mock_save_dialog.assert_called_once()
            mock_generate_tex.assert_called_once()
            
            # Verify total marks calculation, subject, and questions passing
            metadata = mock_generate_tex.call_args[0][0]
            self.assertEqual(metadata["max_marks"], "10")
            self.assertEqual(metadata["subject"], "General")
            self.assertEqual(len(metadata["questions"]), 1)
            self.assertEqual(metadata["questions"][0].text, "Test Question content")

if __name__ == '__main__':
    unittest.main()
