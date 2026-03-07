STYLE = """
/* ═══════ BASE ═══════ */
QMainWindow, QWidget          { background: #060d1a; color: #c8dff5; }
QWidget#page                  { background: #000000; }
QWidget#inner_bg              { background: #0a1628; }

/* ═══════ TIPOGRAFIA ═══════ */
QLabel#h1 {
    color: #ffffff; font-size: 44px; font-weight: 900;
    font-family: 'Segoe UI','Trebuchet MS',sans-serif; letter-spacing: -2px; }
QLabel#h2 {
    color: #e2f0ff; font-size: 22px; font-weight: 700;
    font-family: 'Segoe UI',sans-serif; }
QLabel#h3 {
    color: #e2f0ff; font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI',sans-serif; }
QLabel#tag {
    color: #4d8ec4; font-size: 11px; font-weight: 600;
    font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body  { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#ok    { color: #3de8a0; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#warn  { color: #f0b429; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#err   { color: #f03d5a; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#log_ok   { color: #3de8a0; font-size: 12px; font-family: 'Courier New'; }
QLabel#log_fail { color: #f03d5a; font-size: 12px; font-family: 'Courier New'; }
QLabel#log_warn { color: #f0b429; font-size: 12px; font-family: 'Courier New'; }

/* ═══════ SEPARADORES ═══════ */
QFrame#sep { background: #0f2035; min-height: 1px; max-height: 1px; }

/* ═══════ TARJETAS ═══════ */
QFrame#card        { background: #0a1628; border: 1px solid #0f2035;    border-radius: 16px; }
QFrame#card_blue   { background: #071833; border: 1px solid #1a4a8a;    border-radius: 16px; }
QFrame#card_green  { background: #041a12; border: 1px solid #1a7a50;    border-radius: 16px; }
QFrame#card_yellow { background: #1a1204; border: 1px solid #7a5a1a;    border-radius: 16px; }
QFrame#card_red    { background: #1a0409; border: 1px solid #7a1a2a;    border-radius: 16px; }
QFrame#card_log    { background: #060d1a; border: 1px solid #0f2035;    border-radius: 8px;  }

/* ═══════ BOTONES ═══════ */
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #0f4fd4);
    color: #fff; border: none; border-radius: 12px;
    padding: 20px 48px; font-size: 17px; font-weight: 800;
    font-family: 'Segoe UI',sans-serif; letter-spacing: 1px; min-width: 220px; }
QPushButton#btn_blue:hover   { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3a84ff, stop:1 #2060f0); }
QPushButton#btn_blue:pressed { background: #0e3eb8; }
QPushButton#btn_blue:disabled { background: #0d1f3a; color: #1a3a5c; }

QPushButton#btn_outline {
    background: transparent; color: #4d8ec4;
    border: 2px solid #1a3a5c; border-radius: 12px;
    padding: 18px 44px; font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI',sans-serif; min-width: 200px; }
QPushButton#btn_outline:hover { border-color: #4d8ec4; color: #c8dff5; background: #071833; }

QPushButton#btn_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1ac87a, stop:1 #0fa860);
    color: #000d08; border: none; border-radius: 12px;
    padding: 16px 36px; font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI',sans-serif; }
QPushButton#btn_green:hover    { background: #22e88a; }
QPushButton#btn_green:disabled { background: #0a2018; color: #0a3020; }

QPushButton#btn_red {
    background: #c0122a; color: #fff; border: none; border-radius: 12px;
    padding: 16px 36px; font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI',sans-serif; }
QPushButton#btn_red:hover { background: #e01535; }

QPushButton#btn_sm {
    background: #0a1628; color: #4d8ec4;
    border: 1px solid #1a3a5c; border-radius: 8px;
    padding: 8px 18px; font-size: 12px; font-family: 'Segoe UI',sans-serif; }
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }

QPushButton#btn_admin {
    background: transparent; color: #1a3a5c;
    border: 1px solid #0f2035; border-radius: 8px;
    padding: 10px 22px; font-size: 12px;
    font-family: 'Courier New'; letter-spacing: 2px; }
QPushButton#btn_admin:hover { color: #4d8ec4; border-color: #1a3a5c; }

QPushButton#tab {
    background: transparent; color: #3a5f84;
    border: none; border-bottom: 3px solid transparent;
    padding: 12px 24px; font-size: 13px; font-weight: 700;
    font-family: 'Segoe UI',sans-serif; border-radius: 0; }
QPushButton#tab:hover   { color: #7ca8d0; border-bottom-color: #1a3a5c; }
QPushButton#tab:checked { color: #4d8ec4; border-bottom-color: #1a6ef5; }

/* ═══════ INPUTS ═══════ */
QLineEdit#inp {
    background: #060d1a; border: 1.5px solid #0f2035; border-radius: 10px;
    color: #e2f0ff; padding: 14px 18px; font-size: 14px;
    font-family: 'Segoe UI',sans-serif; }
QLineEdit#inp:focus { border-color: #1a6ef5; }

QComboBox#combo {
    background: #060d1a; border: 1.5px solid #0f2035; border-radius: 10px;
    color: #e2f0ff; padding: 10px 14px; font-size: 13px;
    font-family: 'Segoe UI',sans-serif; }
QComboBox#combo:focus { border-color: #1a6ef5; }
QComboBox#combo::drop-down { border: none; }
QComboBox QAbstractItemView { background: #0a1628; color: #c8dff5; border: 1px solid #1a3a5c; }

/* ═══════ CAMARA ═══════ */
QLabel#cam {
    background: #030810; border: 2px solid #0f2035; border-radius: 14px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 12px; }

/* ═══════ PROGRESO ═══════ */
QFrame#prog_bg   { background: #0a1628; border-radius: 6px; min-height: 12px; max-height: 12px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #3de8a0);
    border-radius: 6px; min-height: 12px; max-height: 12px; }

/* ═══════ LOCKERS GRID ═══════ */
QFrame#lk_free { background: #041228; border: 2px solid #1a4a8a; border-radius: 12px; min-width: 110px; min-height: 90px; }
QFrame#lk_busy { background: #1a1204; border: 2px solid #5a3a08; border-radius: 12px; min-width: 110px; min-height: 90px; }

/* ═══════ BADGES ═══════ */
QLabel#badge_blue   { background: #071833; color: #4d8ec4; border: 1px solid #1a4a8a; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }
QLabel#badge_green  { background: #041a12; color: #3de8a0; border: 1px solid #1a7a50; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }
QLabel#badge_yellow { background: #1a1204; color: #f0b429; border: 1px solid #7a5a1a; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }
QLabel#badge_red    { background: #1a0409; color: #f03d5a; border: 1px solid #7a1a2a; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }

/* ═══════ SCROLLBAR ═══════ */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #060d1a; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #0f2035; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
