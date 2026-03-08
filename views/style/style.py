STYLE = """
/* ═══════ BASE ═══════ */
QMainWindow, QWidget          { background: #0a1a2f; color: #e0edff; }
QWidget#page                  { background: #000000; }
QWidget#inner_bg              { background: #11223b; }

/* ═══════ TIPOGRAFIA ═══════ */


/*
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
    color: #7aa9d9; font-size: 11px; font-weight: 600;
    font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body  { color: #a0c0e0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #a0c0e0; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; font-weight: 500; }
QLabel#ok    { color: #3de8a0; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#warn  { color: #f0b429; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#err   { color: #f03d5a; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#log_ok   { color: #3de8a0; font-size: 12px; font-family: 'Courier New'; }
QLabel#log_fail { color: #f03d5a; font-size: 12px; font-family: 'Courier New'; }
QLabel#log_warn { color: #f0b429; font-size: 12px; font-family: 'Courier New'; }
*/



/* ═══════ SEPARADORES ═══════ */
QFrame#sep { background: #1e3a5a; min-height: 1px; max-height: 1px; }

/* ═══════ TARJETAS ═══════ */
/*QFrame#card        { background: #11223b; border: 1px solid #1e3a5a;    border-radius: 16px; } */
/*QFrame#card_blue   { background: #0f2a44; border: 1px solid #2b5797;    border-radius: 16px; } */
QFrame#card_green  { background: #041a12; border: 1px solid #1a7a50;    border-radius: 16px; }
QFrame#card_yellow { background: #1a2a3a; border: 1px solid #5f7fa0;    border-radius: 16px; }
QFrame#card_red    { background: #2a1a2a; border: 1px solid #b04a6a;    border-radius: 16px; }
QFrame#card_log    { background: #0a1a2f; border: 1px solid #1e3a5a;    border-radius: 8px;  }

/* ═══════ BOTONES ═══════ */
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2b6eb0, stop:1 #1e4f8a);
    color: #fff; border: none; border-radius: 12px;
    padding: 20px 48px; font-size: 17px; font-weight: 800;
    font-family: 'Segoe UI',sans-serif; letter-spacing: 1px; min-width: 220px; }
QPushButton#btn_blue:hover   { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3a7fc9, stop:1 #2a5fa0); }
QPushButton#btn_blue:pressed { background: #17427a; }
QPushButton#btn_blue:disabled { background: #1e3048; color: #5f7fa0; }

QPushButton#btn_outline {
    background: transparent; color: #7aa9d9;
    border: 2px solid #2b4a70; border-radius: 12px;
    padding: 18px 44px; font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI',sans-serif; min-width: 200px; }
QPushButton#btn_outline:hover { border-color: #7aa9d9; color: #e0edff; background: #11223b; }

QPushButton#btn_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1ac87a, stop:1 #0fa860);
    color: #000d08; border: none; border-radius: 12px;
    padding: 16px 36px; font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI',sans-serif; }
QPushButton#btn_green:hover    { background: #22e88a; }
QPushButton#btn_green:disabled { background: #0a2018; color: #0a3020; }

QPushButton#btn_red {
    background: #b04a6a; color: #fff; border: none; border-radius: 12px;
    padding: 16px 36px; font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI',sans-serif; }
QPushButton#btn_red:hover { background: #c05a7a; }

QPushButton#btn_sm {
    background: #11223b; color: #7aa9d9;
    border: 1px solid #2b4a70; border-radius: 8px;
    padding: 8px 18px; font-size: 12px; font-family: 'Segoe UI',sans-serif; }
QPushButton#btn_sm:hover { color: #e0edff; border-color: #7aa9d9; }

QPushButton#btn_admin {
    background: transparent; color: #5f7fa0;
    border: 1px solid #1e3a5a; border-radius: 8px;
    padding: 10px 22px; font-size: 12px;
    font-family: 'Courier New'; letter-spacing: 2px; }
QPushButton#btn_admin:hover { color: #7aa9d9; border-color: #2b4a70; }

QPushButton#tab {
    background: transparent; color: #7aa9d9;
    border: none; border-bottom: 3px solid transparent;
    padding: 12px 24px; font-size: 13px; font-weight: 700;
    font-family: 'Segoe UI',sans-serif; border-radius: 0; }
QPushButton#tab:hover   { color: #ffffff; border-bottom-color: #7aa9d9; background: rgba(42, 74, 106, 0.3); }
QPushButton#tab:checked { color: #ffffff; border-bottom-color: #4a7db0; font-weight: 800; }

/* ═══════ INPUTS ═══════ */
QLineEdit#inp {
    background: #0a1a2f; border: 1.5px solid #1e3a5a; border-radius: 10px;
    color: #e2f0ff; padding: 14px 18px; font-size: 14px;
    font-family: 'Segoe UI',sans-serif; }
QLineEdit#inp:focus { border-color: #2b6eb0; }

QComboBox#combo {
    background: #0a1a2f; border: 1.5px solid #1e3a5a; border-radius: 10px;
    color: #e2f0ff; padding: 10px 14px; font-size: 13px;
    font-family: 'Segoe UI',sans-serif; }
QComboBox#combo:focus { border-color: #2b6eb0; }
QComboBox#combo::drop-down { border: none; }
QComboBox QAbstractItemView { background: #11223b; color: #e0edff; border: 1px solid #2b4a70; }

/* ═══════ CAMARA ═══════ */
QLabel#cam {
    background: #051020; border: 2px solid #1e3a5a; border-radius: 14px;
    color: #5f7fa0; font-family: 'Courier New'; font-size: 12px; }

/* ═══════ PROGRESO ═══════ */
QFrame#prog_bg   { background: #11223b; border-radius: 6px; min-height: 12px; max-height: 12px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2b6eb0, stop:1 #3de8a0);
    border-radius: 6px; min-height: 12px; max-height: 12px; }

/* ═══════ LOCKERS GRID ═══════ */
QFrame#lk_free { background: #0f2a44; border: 2px solid #2b5797; border-radius: 12px; min-width: 110px; min-height: 90px; }
QFrame#lk_busy { background: #1a2a4a; border: 2px solid #4a7db0; border-radius: 12px; min-width: 110px; min-height: 90px; }

/* ═══════ BADGES ═══════ */
QLabel#badge_blue   { background: #0f2a44; color: #ffffff; border: 2px solid #4a7db0; border-radius: 14px; padding: 4px 14px; font-size: 11px; font-family: 'Courier New'; letter-spacing: 2px; font-weight: 700; }
QLabel#badge_green  { background: #041a12; color: #3de8a0; border: 1px solid #1a7a50; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }
QLabel#badge_yellow { background: #1a2a3a; color: #f0b429; border: 1px solid #5f7fa0; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }
QLabel#badge_red    { background: #2a1a2a; color: #f06a8a; border: 1px solid #b04a6a; border-radius: 14px; padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px; }

/* ═══════ SCROLLBAR ═══════ */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #0a1a2f; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #1e3a5a; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""