#!/usr/bin/env python3


TOOLBAR_STYLESHEET = """QToolBar {background-color: rgb(41, 45, 62);
                     color: rgba(248, 248, 242, 1) !important;
                     font-family: Segoe UI;
                     font-size: 13px;
                     text-align: left;}
                     
                     QToolBar::separator {
                     background-color: rgb(0, 173, 238);
                     width: 3px;
                     height: 3px;
                     }
                     """

MAIN_WINDOW_STYLESHEET = """
                        QWidget{ 
                        background-color: rgb(41, 45, 62);
                        color: rgba(248, 248, 242, 1) !important;
                        font-size: 15px;
                        }
                        QScrollBar:vertical {         
                        background:rgb(44, 49, 58);
                        width:7px;    
                        margin: 0px 0px 0px 0px;
                        }
                        QScrollBar::handle:vertical {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop: 0 rgb(103, 110, 149), stop: 0.5 rgb(103, 110, 149), stop:1 rgb(103, 110, 149));
                            min-height: 0px;
                        }
                        QScrollBar:horizontal {         
                            background:rgb(44, 49, 58);
                            height:7px;    
                            margin: 0px 0px 0px 0px;
                        }
                        QScrollBar::handle:horizontal {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop: 0 rgb(103, 110, 149), stop: 0.5 rgb(103, 110, 149), stop:1 rgb(103, 110, 149));
                        }
                        QMenuBar { 
                          color: #ffffff;
                          background-color: rgb(33, 37, 43);
                          font-size: 15px;
                        }

                        QPushButton {
                        border: 2px solid rgb(0, 173, 238);
                        border-radius: 6px;
                        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                          stop: 1 rgb(0, 173, 238), stop: 0.7 rgb(44, 49, 58));
                        min-width: 50px;
                        }

                        QLabel { 
                        border: 2px solid rgb(41, 45, 62);
                        padding-left: 7px;
                        border-left-color: rgb(0, 173, 238);
                        }
                        
                        QLineEdit, QPlainTextEdit { 
                        border: 0.5px solid rgb(0, 173, 238);
                        border-radius: 6px;
                        }
                        
                        QTabBar::tab {background: rgb(68, 66, 103);
                        border: 2px solid rgb(41, 45, 62);
                        border-radius: 3px;
                        min-height: 3ex;
                        }
                        QTabWidget {
                        border-style: outset;
                        border-color: rgba(248, 248, 242, 1);
                        border-width: 0.5px;
                        }
                        QToolBar {
                        border-style: outset;
                        border-color: rgba(75, 75, 75, 1);
                        border-width: 1px;
                        border-left-width: 0px;
                        border-right-width: 0px;
                        }
                        
                        QTabBar::tab:selected {background: rgb(51, 55, 95);
                        border: 2px solid rgb(41, 45, 62);
                        min-height: 2.5ex;
                        border-radius: 3px;
                        border-top-color: rgb(0, 173, 238);
                        }
                        QComboBox { combobox-popup: 0; }
                        
                        """

DOCK_BAR_TWO_LINK = """
                  QLabel { 
                        border: 1px solid rgb(41, 45, 62);
                        }
                  """

DOCK_BAR_LABEL = """
                  QLabel { 
                        border: 1px solid rgb(41, 45, 62);
                        border-radius: 2px;
                        border-bottom-color: rgb(0, 173, 238);
                        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                          stop: 1 rgb(0, 173, 238), stop: 0.85 rgb(41, 45, 62));
                        }
                  """

DROPDOWN_MENU_STYLE = "background-color: rgb(41, 45, 62);" \
                      "color: rgba(248, 248, 242, 1) !important;" \
                      "border: 2px solid rgb(44, 49, 58);" \
                      "border-left-color: rgb(189, 147, 249);" \
                      "font-family: Segoe UI;" \
                      "font-size: 13px;"

TEXT_BOX_STYLESHEET = "QLineEdit, QLabel{" \
                      "border-bottom: 1px solid rgb(0, 173, 238);" \
                      "}"

CHECK_BOX_STYLESHEET = "QCheckBox::indicator:unchecked" \
                       "{" \
                       "border: 0.5px solid rgb(0, 173, 238);" \
                       "background: none;" \
                       "}"

RADIO_BUTTON_STYLESHEET = "QRadioButton::indicator:unchecked" \
                          "{" \
                          "border: 0.5px solid rgb(0, 173, 238);" \
                          "background: none;" \
                          "border-radius:          7px;" \
                          "}"

SETTINGS_WIDGET_STYLESHEET = "#settingsWidget {background-color:rgb(41, 45, 62);}"

MENUS_STYLESHEET = "background-color: rgb(41, 45, 62);" \
                   "color: rgba(248, 248, 242, 1) !important;" \
                   "border: 1px solid rgb(44, 49, 58);" \
                   "border-bottom: 1px solid rgb(0, 173, 238);" \
                   "font-family: Segoe UI;" \
                   "font-size: 13px;" \
                   "text-align: left;"

MENUS_STYLESHEET_2 = """QMenu::item{
                         background-color: rgb(41, 45, 62);
                         color: rgba(248, 248, 242, 1) !important;
                         border-left: 1px solid rgb(0, 173, 238);
                         padding-right: 4px;
                         padding-bottom: 4px;
                         padding-top: 4px;
                         font-size: 15px;
                         text-align: left;
                         padding-left: 4px;
                         }
                        
                         QMenu::item:selected{
                         background-color: rgb(0, 85, 127);
                         color: rgb(255, 255, 255);
                         }
                         
                         QMenu::item:disabled {
                         background-color:rgb(81, 87, 114);
                         }"""

MERGE_STYLESHEET = """
                QWidget, QDialog{ 
                    background-color: rgb(41, 45, 62);
                    color: rgba(248, 248, 242, 1) !important;
                    font-family: Segoe UI;
                    font-size: 13px;}
                   
                   QScrollBar:vertical {         
                        background:rgb(44, 49, 58);
                        width:7px;    
                        margin: 0px 0px 0px 0px;
                        }
                        QScrollBar::handle:vertical {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop: 0 rgb(103, 110, 149), stop: 0.5 rgb(103, 110, 149), stop:1 rgb(103, 110, 149));
                            min-height: 0px;
                        }
                        QScrollBar:horizontal {         
                            background:rgb(44, 49, 58);
                            height:7px;    
                            margin: 0px 0px 0px 0px;
                        }
                        QScrollBar::handle:horizontal {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop: 0 rgb(103, 110, 149), stop: 0.5 rgb(103, 110, 149), stop:1 rgb(103, 110, 149));
                        }"""

RESOLUTION_WIZARD_STYLESHEET = "background-color: rgb(41, 45, 62);" \
                               "color: rgba(248, 248, 242, 1) !important;" \
                               "padding-bottom: 5px;" \
                               "font-family: Segoe UI;" \
                               "font-size: 13px;"

PATH_INPUT_STYLESHEET = """border: 2px solid rgb(44, 49, 58);
                        border-radius: 25px;
                        padding: 4px;
                        background-color: rgb(129, 133, 137);
                        color: rgba(248, 248, 242, 1) !important;
                        """

BUTTON_STYLESHEET = """
                        QPushButton {
                        border: 2px solid rgb(0, 173, 238);
                        border-radius: 6px;
                        color: rgba(248, 248, 242, 1) !important;
                        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                          stop: 1 rgb(0, 173, 238), stop: 0.7 rgb(44, 49, 58));
                        min-width: 80px;
                        }
                        QPushButton:pressed {
                            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                              stop: 0 #dadbde, stop: 1 #f6f7fa);
                        }
                    """

BUTTON_STYLESHEET_2 = """
                        QPushButton {
                        border: 2px solid rgb(0, 173, 238);
                        border-radius: 6px;
                        color: rgba(248, 248, 242, 1) !important;
                        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                          stop: 1 rgb(0, 173, 238), stop: 0.7 rgb(44, 49, 58));
                        
                        min-width: 300px;
                        
                        }
                        QPushButton:pressed {
                            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                              stop: 0 #dadbde, stop: 1 #f6f7fa);
                        }
                    """

SELECT_PROJECT_STYLESHEET = "background-color: rgb(41, 45, 62);" \
                            "color: rgba(248, 248, 242, 1) !important;" \
                            "border-color: rgb(0, 173, 238);"
