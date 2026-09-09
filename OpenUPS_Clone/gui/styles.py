LEGACY_QSS = """
QMainWindow, QDialog, QWidget {
    background: #efefef;
    color: #202020;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 9pt;
}
QGroupBox {
    border: 1px solid #9b9b9b;
    border-radius: 0px;
    margin-top: 8px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 7px;
    padding: 0 3px;
}
QLineEdit, QComboBox, QPlainTextEdit {
    background: white;
    border: 1px solid #9d9d9d;
    padding: 2px 4px;
    min-height: 19px;
}
QLineEdit[readOnly="true"] {
    background: #f8f8f8;
    color: #333333;
}
QPushButton {
    border: 1px solid #8b8b8b;
    border-top-color: #d9d9d9;
    border-left-color: #d9d9d9;
    background: #eeeeee;
    min-height: 24px;
    padding: 2px 10px;
}
QPushButton:pressed, QPushButton:checked {
    background: #d8e8f6;
    border: 1px solid #548cc0;
}
QPushButton:disabled, QComboBox:disabled, QLineEdit:disabled {
    color: #777777;
    background: #e5e5e5;
}
QProgressBar {
    border: 1px solid #8d8d8d;
    background: white;
    text-align: center;
    min-height: 18px;
}
QProgressBar::chunk { background: #43a9e8; }
QToolTip { background: #ffffdc; color: #111; border: 1px solid #777; }
"""

