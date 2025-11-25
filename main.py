from PyQt5 import QtWidgets
import plm_control_panel
import sqlalchemy.sql.default_comparator


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    plm_control = plm_control_panel.PLMControl()
    plm_control.ui_start_dialog.show()
    sys.exit(app.exec_())
