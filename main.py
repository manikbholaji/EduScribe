import sys
from PyQt6.QtWidgets import QApplication
from app.view.main_window import MainWindow

def main():
    # 1. Create the Application
    app = QApplication(sys.argv)
    
    # 2. Create the Main Window
    window = MainWindow()
    
    # 3. Show and Run
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()