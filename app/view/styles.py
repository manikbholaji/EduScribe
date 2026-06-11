# This file holds the CSS-like styling for our Qt application

MAIN_STYLE = """
QMainWindow {
    background-color: #f5f6fa;
}

/* Sidebar Styling */
QFrame#Sidebar {
    background-color: #2f3640;
    min-width: 200px;
    max-width: 200px;
}

QLabel#SidebarTitle {
    color: #dcdde1;
    font-size: 16px;
    font-weight: bold;
    padding: 10px;
    margin-bottom: 20px;
}

QPushButton {
    background-color: #353b48;
    color: white;
    border: none;
    padding: 12px;
    text-align: left;
    font-size: 14px;
    border-radius: 4px;
    margin: 4px 10px;
}

QPushButton:hover {
    background-color: #40739e;
}

/* Central Composer Area */
QScrollArea {
    border: none;
    background-color: #ffffff;
}

/* Preview Panel */
QFrame#PreviewPanel {
    background-color: #dcdde1;
    border-left: 1px solid #b2bec3;
}
"""