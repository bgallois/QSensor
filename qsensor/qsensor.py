'''MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''
from exporter import Exporter
import sensors as Sensors
from ui_qsensor import Ui_QSensor
import PySide6.QtXml
from PySide6.QtGui import QBrush, QColor
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Signal, Slot, QFile, QStandardPaths, Qt, QTimer, QCoreApplication, QSettings
from PySide6.QtWidgets import QSplitter, QApplication, QMainWindow, QFileDialog, QMessageBox, QLabel, QMdiArea, QMdiSubWindow, QTableWidget, QTableWidgetItem
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


dirname = os.path.dirname(PySide6.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path


class QSensor(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_QSensor()
        self.ui.setupUi(self)
        self.setWindowTitle("QSensor")
        style = QFile("")
        if style.open(QFile.ReadOnly):
            self.setStyleSheet(style.readAll().data().decode())
            style.close()

        self.splitter = QSplitter(self)
        self.setCentralWidget(self.splitter)
        self.table = QTableWidget(self)
        self.table.insertColumn(0)
        self.table.insertColumn(1)
        self.table.insertColumn(2)
        self.table.setHorizontalHeaderLabels(["Sensor", "Current", "Critical"])
        self.table.itemChanged.connect(self.trigger_view)
        self.table.horizontalHeader().setSectionResizeMode(
            PySide6.QtWidgets.QHeaderView.ResizeToContents)

        self.chart = QChart()
        self.view = QChartView(self.chart)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.table)
        self.splitter.setSizes([3*self.width()/4, self.width()/4])

        self.axis_x = QValueAxis()
        self.axis_x.setTickCount(10)
        self.axis_x.setRange(0, 10)
        self.axis_x.setTitleText("Time (s)")
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)

        self.axis_y_temp = QValueAxis()
        self.axis_y_temp.setTickCount(10)
        self.axis_y_temp.setTitleText("Degrees (°C)")
        self.axis_y_temp.setRange(0, 100)
        self.chart.addAxis(self.axis_y_temp, Qt.AlignmentFlag.AlignLeft)

        self.axis_y_per = QValueAxis()
        self.axis_y_per.setTickCount(10)
        self.axis_y_per.setTitleText("Usage (%)")
        self.axis_y_per.setRange(0, 110)
        self.chart.addAxis(self.axis_y_per, Qt.AlignmentFlag.AlignRight)

        self.period = 0.25
        self.count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)

        self.exporter = Exporter()
        self.init_plot()

        self.settings = QSettings()
        self.restoreGeometry(self.settings.value("main/geometry"))
        self.restoreState(self.settings.value("main/windowState"))

        self.ui.actionReset.triggered.connect(self.reset)
        self.ui.actionExport_2.triggered.connect(self.export)

        # Help menu
        self.ui.actionAboutQt.triggered.connect(qApp.aboutQt)
        self.ui.actionLicense.triggered.connect(lambda: QMessageBox.about(self, "License", "MIT  "
                                                                          "License\nCopyright (c) 2022 FastTrackOrg\nPermission is hereby granted, free of  "
                                                                          "charge, to any person obtaining a copy\nof this software and associated  "
                                                                          "documentation files (the 'Software'), to deal\nin the Software without restriction, "
                                                                          "including without limitation the rights\nto use, copy, modify, merge, publish, "
                                                                          "distribute, sublicense, and/or sell\ncopies of the Software, and to permit persons  "
                                                                          "to whom the Software is\nfurnished to do so, subject to the following conditions: "
                                                                          "\n\nThe above copyright notice and this permission notice shall be included in  "
                                                                          "all\ncopies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "
                                                                          "'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\nIMPLIED, INCLUDING BUT NOT "
                                                                          "LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\nFITNESS FOR A PARTICULAR PURPOSE AND "
                                                                          "NONINFRINGEMENT. IN NO EVENT SHALL THE\nAUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR "
                                                                          "ANY CLAIM, DAMAGES OR OTHER\nLIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR "
                                                                          "OTHERWISE, ARISING FROM,\nOUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR "
                                                                          "OTHER DEALINGS IN THE\nSOFTWARE."))

    def saveSettings(self):
        self.settings.setValue("main/geometry", self.saveGeometry())
        self.settings.setValue("main/windowState", self.saveState())

    def init_plot(self):
        sensors = Sensors.get_all()
        self.exporter.append(sensors)
        self.series = dict()
        for i, (sensor, value) in enumerate(sensors.items()):
            serie = QLineSeries()
            self.series[sensor] = serie
            self.series[sensor].setName(sensor)
            self.chart.addSeries(self.series[sensor])
            self.series[sensor].attachAxis(self.axis_x)
            if "usage" in sensor:
                self.series[sensor].attachAxis(self.axis_y_per)
            else:
                self.series[sensor].attachAxis(self.axis_y_temp)
            self.series[sensor].append(0, value["current"])
            self.chart.legend().setVisible(False)

            self.table.insertRow(i)
            item = QTableWidgetItem(sensor)
            item.setCheckState(Qt.CheckState.Checked)
            item.setBackground(QBrush(self.series[sensor].color()))
            self.table.setItem(i, 0, item)
            current_item = QTableWidgetItem(str(value["current"]))
            color = QColor("green")
            if value["current"] >= value["high"]:
                color = QColor("red")
            elif value["current"] / value["high"] >= 0.75 and value["current"] < value["high"]:
                color = QColor("yellow")
            current_item.setBackground(QBrush(color))
            self.table.setItem(i, 1, current_item)
            critical_item = QTableWidgetItem(str(value["critical"]))
            critical_item.setBackground(QBrush(QColor("red")))
            self.table.setItem(i, 2, critical_item)
        self.timer.start(1000)

    def update_plot(self):
        self.count += self.period
        sensors = Sensors.get_all()
        self.exporter.append(sensors)
        max_temp = 0
        for i, (sensor, value) in enumerate(sensors.items()):
            self.series[sensor].append(self.count, value["current"])
            current_item = QTableWidgetItem(str(value["current"]))
            color = QColor("green")
            if value["current"] >= value["high"]:
                color = QColor("red")
            elif value["current"] / value["high"] >= 0.75 and value["current"] < value["high"]:
                color = QColor("yellow")
            current_item.setBackground(QBrush(color))
            self.table.setItem(i, 1, current_item)
            if not "usage" in sensor:
                max_temp = max(max_temp, value["current"])

        if self.count % 10 == 0:
            self.axis_x.setRange(0, self.count + 10)
        self.axis_y_temp.setRange(0, max_temp + 10)

    def trigger_view(self, item):
        if item.column() == 0:
            if item.checkState() == Qt.CheckState.Checked:
                self.series[item.text()].setVisible(True)
            else:
                self.series[item.text()].setVisible(False)

    def reset(self):
        self.timer.stop()
        self.exporter.clear()
        self.count = 0
        self.chart.removeAllSeries()
        self.table.clearContents()
        for i in reversed(range(self.table.rowCount())):
            self.table.removeRow(i)
        self.axis_x.setRange(0, 10)
        self.init_plot()

    def export(self):
        file_name, __ = QFileDialog.getSaveFileName(self, self.tr("Export File"),
                                                    "/home/untitled.json",
                                                    self.tr("JSON (*.json)"))
        self.exporter.export(file_name)


def main():
    app = QApplication([])
    app.setApplicationName("QSensor")
    app.setApplicationVersion("0.0.0")
    app.setOrganizationName("bgallois")
    app.setOrganizationDomain("cc.gallois")
    widget = QSensor()
    widget.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
