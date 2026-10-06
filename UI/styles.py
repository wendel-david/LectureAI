TEXT = "#111318"
TEXT_MUTED = "#6B7280"
TEXT_FAINT = "#9CA3AF"
BORDER = "#E5E7EB"
SURFACE = "#F7F8FA"      # sidebar
SURFACE_ALT = "#F3F4F6"  # segmented control, selected rows
SURFACE_SOFT = "#FAFAFA" # transcript box
BLUE = "#2563EB"
BLUE_SOFT = "#EEF2FF"
GREEN = "#16A34A"
GREEN_TEXT = "#15803D"
GREEN_SOFT = "#E7F6EC"
AMBER = "#D97706"
AMBER_SOFT = "#FEF3C7"
RED = "#DC2626"
RED_DOT = "#E5484D"
RED_BORDER = "#F3C7C7"
MONO = '"SF Mono", Menlo, Monaco, monospace'

STYLESHEET = f"""
QWidget {{
    font-size: 14px;
    color: {TEXT};
}}
QMainWindow, #content, #page {{
    background: white;
}}
QToolTip {{
    color: {TEXT};
    background: white;
    border: 1px solid {BORDER};
}}

/* Sidebar */
#sidebar {{
    background: {SURFACE};
    border-right: 1px solid #ECEDEF;
}}
QLabel#logoText {{
    font-size: 17px;
    font-weight: 600;
}}
QLabel#sidebarSection {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QPushButton#navButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 9px 10px;
    text-align: left;
    font-size: 15px;
    font-weight: 400;
    color: #374151;
}}
QPushButton#navButton:hover {{
    background: #EFF0F2;
}}
QPushButton#navButton:checked {{
    background: white;
    border: 1px solid {BORDER};
    color: {TEXT};
    font-weight: 500;
}}

/* Text */
QLabel#pageTitle {{
    font-size: 30px;
    font-weight: 700;
}}
QLabel#heroTitle {{
    font-size: 28px;
    font-weight: 700;
}}
QLabel#pageHeader {{
    font-size: 15px;
    font-weight: 500;
    color: #374151;
}}
QLabel#cardTitle {{
    font-size: 16px;
    font-weight: 600;
}}
QLabel#muted {{
    color: {TEXT_MUTED};
}}
QLabel#faint {{
    color: {TEXT_FAINT};
    font-size: 13px;
}}
QLabel#fieldLabel {{
    font-size: 13px;
    font-weight: 500;
}}
QLabel#timer {{
    font-family: {MONO};
    font-size: 44px;
    font-weight: 600;
}}
QLabel#scoreText {{
    font-size: 44px;
    font-weight: 700;
}}

/* Status pill */
QLabel#pill {{
    border-radius: 11px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 500;
}}
QLabel#pill[state="done"] {{
    background: {GREEN_SOFT};
    color: {GREEN_TEXT};
}}
QLabel#pill[state="working"] {{
    background: {AMBER_SOFT};
    color: #92400E;
}}
QLabel#pill[state="none"] {{
    background: {SURFACE_ALT};
    color: {TEXT_MUTED};
}}

/* Buttons */
QPushButton {{
    background: {TEXT};
    color: white;
    border: 1px solid {TEXT};
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: #2A2D33;
}}
QPushButton:disabled {{
    background: #C7CAD1;
    border-color: #C7CAD1;
}}
QPushButton#secondary {{
    background: white;
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QPushButton#secondary:hover {{
    background: {SURFACE_SOFT};
}}
QPushButton#secondary:disabled {{
    color: {TEXT_FAINT};
}}
QPushButton#danger {{
    background: white;
    color: {RED};
    border: 1px solid {RED_BORDER};
}}
QPushButton#danger:hover {{
    background: #FEF2F2;
}}
QPushButton#flat {{
    background: transparent;
    border: none;
    color: #374151;
    padding: 6px 8px;
    font-weight: 400;
}}
QPushButton#flat:hover {{
    background: {SURFACE_ALT};
}}
QPushButton#link {{
    background: transparent;
    border: none;
    color: {TEXT_MUTED};
    padding: 0;
    font-weight: 400;
}}
QPushButton#link:hover {{
    color: {TEXT};
}}
QPushButton#iconButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px;
}}
QPushButton#iconButton:hover {{
    background: {SURFACE_ALT};
}}

/* Segmented tabs */
QFrame#segmented {{
    background: {SURFACE_ALT};
    border-radius: 10px;
}}
QPushButton#segment {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 7px 14px;
    color: {TEXT_MUTED};
    font-size: 15px;
    font-weight: 400;
}}
QPushButton#segment:checked {{
    background: white;
    border: 1px solid {BORDER};
    color: {TEXT};
    font-weight: 600;
}}

/* Inputs */
QLineEdit {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 11px 12px;
    background: white;
    font-size: 15px;
    selection-background-color: {BLUE};
}}
QLineEdit:focus {{
    border: 1px solid {BLUE};
}}
QComboBox {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px 12px;
    background: white;
    font-size: 15px;
}}
QComboBox:focus {{
    border: 1px solid {BLUE};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}

/* Cards, tables and boxes */
QFrame#card, QFrame#table {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#tableHeader {{
    background: #F9FAFB;
    border: none;
    border-bottom: 1px solid {BORDER};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
QFrame#tableRow {{
    background: transparent;
    border: none;
    border-bottom: 1px solid #F0F1F3;
}}
QFrame#tableRow:hover {{
    background: #F9FAFB;
}}
QLabel#columnLabel {{
    color: {TEXT_MUTED};
    font-size: 13px;
    font-weight: 500;
}}
QLabel#rowTitle {{
    font-size: 16px;
    font-weight: 600;
}}
QLabel#rowText {{
    font-size: 15px;
    color: #374151;
}}
QFrame#divider {{
    background: {BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QFrame#transcriptBox {{
    background: {SURFACE_SOFT};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QTextBrowser, QTextEdit {{
    background: transparent;
    border: none;
    font-size: 15px;
    selection-background-color: {BLUE};
    selection-color: white;
}}
QFrame#dropZone {{
    border: 1px dashed #CDD1D6;
    border-radius: 10px;
    background: white;
}}
QFrame#dropZone:hover, QFrame#dropZone[dragging="true"] {{
    border-color: {BLUE};
    background: #F8FAFF;
}}

/* Assistant action cards */
QFrame#actionCard {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#actionCard:hover {{
    background: {SURFACE_SOFT};
}}
QFrame#actionCard[selected="true"] {{
    border: 1px solid {BLUE};
    background: white;
}}
QLabel#iconSquare {{
    background: {BLUE_SOFT};
    border-radius: 8px;
}}
QLabel#iconSquare[selected="true"] {{
    background: {BLUE};
}}

/* History list */
QListWidget#history {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget#history::item {{
    border-radius: 8px;
    margin-bottom: 2px;
}}
QListWidget#history::item:hover {{
    background: {SURFACE_SOFT};
}}
QListWidget#history::item:selected {{
    background: {SURFACE_ALT};
}}
QLabel#historyTitle {{
    font-size: 15px;
    font-weight: 600;
}}

/* Quiz */
QLabel#questionNumber {{
    font-family: {MONO};
    color: {TEXT_FAINT};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#questionText {{
    font-size: 17px;
    font-weight: 600;
}}
QFrame#optionCard {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: white;
}}
QFrame#optionCard:hover {{
    background: {SURFACE_SOFT};
}}
QFrame#optionCard[selected="true"] {{
    border: 1px solid {BLUE};
    background: #F8FAFF;
}}
QLabel#optionLetter {{
    background: {SURFACE_ALT};
    border-radius: 5px;
    font-size: 12px;
    font-weight: 700;
}}
QLabel#optionLetter[selected="true"] {{
    background: {BLUE};
    color: white;
}}
QLabel#optionText {{
    font-size: 15px;
}}

/* Progress, sliders, scroll */
QProgressBar {{
    border: none;
    border-radius: 3px;
    background: {SURFACE_ALT};
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background: {BLUE};
}}
QSlider::groove:horizontal {{
    height: 4px;
    border-radius: 2px;
    background: {SURFACE_ALT};
}}
QSlider::sub-page:horizontal {{
    border-radius: 2px;
    background: {TEXT};
}}
QSlider::handle:horizontal {{
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
    background: {TEXT};
}}
QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: #C9CCD1;
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}
QSplitter::handle {{
    background: transparent;
}}
"""
