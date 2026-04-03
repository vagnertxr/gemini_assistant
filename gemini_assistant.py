# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis
import qgis.PyQt.QtCore as _qc
_QT6 = [int(x) for x in _qc.qVersion().split(".")][0] >= 6

if _QT6:
    from qgis.PyQt.QtCore import Qt
    _RightDockWidgetArea = Qt.DockWidgetArea.RightDockWidgetArea
else:
    from qgis.PyQt.QtCore import Qt
    _RightDockWidgetArea = Qt.RightDockWidgetArea

class GeminiAssistant:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dockwidget = None
        self.action = None
        self.menu = u'&Gemini QGIS Assistant'

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.svg')
        icon = QIcon(icon_path)
        
        self.action = QAction(icon, u'Show Gemini Assistant', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.dockwidget:
            self.iface.removeDockWidget(self.dockwidget)
            self.dockwidget.deleteLater()
            self.dockwidget = None
        
        if self.action:
            self.iface.removePluginMenu(self.menu, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        if not self.dockwidget:
            from .gemini_dockwidget import GeminiDockWidget
            self.dockwidget = GeminiDockWidget(self.iface)
            self.iface.addDockWidget(_RightDockWidgetArea, self.dockwidget)
        
        self.dockwidget.show()
