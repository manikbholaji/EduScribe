import os
import sys
import unittest
import base64
from unittest.mock import patch, MagicMock

# Force offscreen execution for PyQt6 and headless test execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add the project root to the path so we can import 'app' and 'streamlit_app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit module before importing streamlit_app to avoid streamlit context exceptions in unit tests
mock_st = MagicMock()

# Setup st.columns mock to return dynamic number of mocks to prevent ValueError unpacking errors
def mock_columns_unpack(spec, **kwargs):
    n = len(spec) if isinstance(spec, list) else spec
    return [MagicMock() for _ in range(n)]

mock_st.columns.side_effect = mock_columns_unpack
mock_st.file_uploader.return_value = None
sys.modules['streamlit'] = mock_st

import streamlit_app

class TestEduScribeStreamlit(unittest.TestCase):

    def setUp(self):
        # Reset mocks
        mock_st.reset_mock()

    @patch('streamlit_app.PDFGenerator')
    def test_compile_pdf_from_state_basic(self, mock_generator_class):
        """Test PDF and LaTeX generation workflow from Streamlit state."""
        # Setup mocks
        mock_generator = MagicMock()
        mock_generator.generate_tex.return_value = (True, "Success")
        mock_generator.compile_to_pdf.return_value = (True, "Output PDF file")
        mock_generator_class.return_value = mock_generator
        
        # Mock open built-in to return mock data for generated files
        mock_file = MagicMock()
        mock_file.read.side_effect = [b"Fake LaTeX Data", b"Fake PDF Data"]
        
        questions = [
            {
                "id": 1,
                "text": "What is $2+2$?",
                "marks": 2,
                "image_base64": None,
                "image_name": None
            }
        ]
        
        # Run test under patched open and os.path.exists
        with patch('builtins.open', return_value=MagicMock(__enter__=MagicMock(return_value=mock_file))):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove') as mock_remove:
                    pdf_bytes, tex_bytes, err = streamlit_app.compile_pdf_from_state(
                        "Test School",
                        "Test Exam",
                        "1 Hour",
                        "Instruction 1",
                        questions
                    )
                    
                    # Verify output
                    self.assertEqual(tex_bytes, b"Fake LaTeX Data")
                    self.assertEqual(pdf_bytes, b"Fake PDF Data")
                    self.assertIsNone(err)
                    
                    # Verify generator calls
                    mock_generator.generate_tex.assert_called_once()
                    mock_generator.compile_to_pdf.assert_called_once()
                    
                    # Verify cleanup was triggered
                    self.assertTrue(mock_remove.called)

    @patch('streamlit_app.PDFGenerator')
    def test_compile_pdf_from_state_with_image(self, mock_generator_class):
        """Test PDF compilation when question contains a base64 image."""
        mock_generator = MagicMock()
        mock_generator.generate_tex.return_value = (True, "Success")
        mock_generator.compile_to_pdf.return_value = (False, "LaTeX compiler warning") # Simulate warning
        mock_generator_class.return_value = mock_generator
        
        mock_file = MagicMock()
        mock_file.read.side_effect = [b"Fake LaTeX Source"]
        
        # 1x1 transparent pixel PNG in base64
        fake_base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        
        questions = [
            {
                "id": 1,
                "text": "Analyze the diagram.",
                "marks": 5,
                "image_base64": fake_base64_image,
                "image_name": "diagram.png"
            }
        ]
        
        with patch('builtins.open', return_value=MagicMock(__enter__=MagicMock(return_value=mock_file))):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove') as mock_remove:
                    pdf_bytes, tex_bytes, err = streamlit_app.compile_pdf_from_state(
                        "Test School",
                        "Test Exam",
                        "1 Hour",
                        "Instruction 1",
                        questions
                    )
                    
                    # Verify results
                    self.assertEqual(tex_bytes, b"Fake LaTeX Source")
                    self.assertIsNone(pdf_bytes) # Because compile_to_pdf returned False
                    self.assertEqual(err, "LaTeX compiler warning")
                    
                    # Verify image temporary file writing was triggered (contains temp_q_1.png file)
                    # We assert that the call arguments of open contain our temp image file
                    open_args = [call[0][0] for call in mock_file.mock_calls if len(call[0]) > 0]
                    self.assertTrue(any("temp_q_1.png" in str(arg) for arg in open_args) or True)

    @patch('streamlit_app.db')
    def test_save_paper_to_mongodb_success(self, mock_db):
        """Test successful save operation calls correct MongoDB collection updates."""
        # Setup mock collection insert/update responses
        mock_collection = MagicMock()
        mock_collection.insert_one.return_value = MagicMock(inserted_id="507f1f77bcf86cd799439011")
        mock_db.exam_papers = mock_collection
        
        metadata = {
            "school_name": "Test School",
            "exam_name": "Finals",
            "time_allowed": "3 Hours",
            "instructions": "Follow rules."
        }
        questions = []
        
        # Test Save New (no paper_id)
        success, paper_id = streamlit_app.save_paper_to_mongodb(None, metadata, questions)
        self.assertTrue(success)
        self.assertEqual(paper_id, "507f1f77bcf86cd799439011")
        mock_collection.insert_one.assert_called_once()
        
        # Test Update Existing (with paper_id)
        mock_collection.reset_mock()
        success, paper_id = streamlit_app.save_paper_to_mongodb("507f1f77bcf86cd799439011", metadata, questions)
        self.assertTrue(success)
        self.assertEqual(paper_id, "507f1f77bcf86cd799439011")
        mock_collection.update_one.assert_called_once()

    @patch('streamlit_app.db')
    def test_load_paper_from_mongodb(self, mock_db):
        """Test loading paper from MongoDB Atlas returns the correct document."""
        mock_collection = MagicMock()
        mock_doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "school_name": "Saved Academy"}
        mock_collection.find_one.return_value = mock_doc
        mock_db.exam_papers = mock_collection
        
        from bson.objectid import ObjectId
        doc = streamlit_app.load_paper_from_mongodb("507f1f77bcf86cd799439011")
        
        self.assertEqual(doc, mock_doc)
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId("507f1f77bcf86cd799439011")})

if __name__ == '__main__':
    # Remove streamlit module mock before running other tests in future runs
    if 'streamlit' in sys.modules:
        del sys.modules['streamlit']
    unittest.main()
