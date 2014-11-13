"""
QGIS Affine plugin
"""

from PyQt4.QtGui import QAction
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QIcon
from PyQt4.QtCore import SIGNAL

from qgis.core import QgsFeature
from qgis.core import QgsFeatureRequest
from qgis.core import QgsMapLayerRegistry
from qgis.core import QgsPoint
from qgis.gui import QgsMessageViewer

from .ui import Ui_ui

class qgsAffine(QDialog, Ui_ui):
    """Affine transformation class"""

    def __init__(self, iface):
        """Initialize the class"""
        self.iface = iface
        QDialog.__init__(self, iface.mainWindow())
        self.setupUi(self)
        self.a = 1
        self.b = 0
        self.c = 0
        self.d = 1
        self.tx = 0
        self.ty = 0
        self.action = None

    def initGui(self):
        """Initialize the GUI"""

        # create action that will start plugin configuration
        self.action = QAction(
                QIcon(":plugins/qgsAffine/icon.svg"),
                "Affine (Rotation, Translation, Scale)",
                self.iface.mainWindow())
        self.action.setWhatsThis("Configuration for test plugin")
        self.action.connect(self.action, SIGNAL("triggered()"), self.run)

        # add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)

        #add to Vector menu
        action = self.iface.mainWindow().menuBar().actions()[3]
        nextAction = action.menu().actions()[3]
        action.menu().insertAction(nextAction, self.action)
        if hasattr(self.iface, "addPluginToVectorMenu"):
            self.iface.addPluginToVectorMenu(
                    "&Geoprocessing Tools",
                    self.action)
        else:
            self.iface.addPluginToMenu("&Geoprocessing Tools", self.action)

        # INSERT EVERY SIGNAL CONECTION HERE!
        self.pushButtonRun.connect(
                self.pushButtonRun,
                SIGNAL("clicked()"), self.affine)
        self.pushButtonInvert.connect(
                self.pushButtonInvert,
                SIGNAL("clicked()"), self.invert)
        self.pushButtonClose.connect(
                self.pushButtonClose,
                SIGNAL("clicked()"), self.finish)


    def unload(self):
        """Remove the plugin menu item and icon"""
        if hasattr(self.iface, "addPluginToVectorMenu"):
            self.iface.removePluginVectorMenu(
                    "&Geoprocessing Tools",
                    self.action)
        else:
            self.iface.removePluginMenu("&Geoprocessing Tools", self.action)
        self.iface.removeToolBarIcon(self.action)


    def run(self):
        """Create and show a configuration dialog or something similar"""
        self.comboBoxLayer.clear()
        for item in self.listlayers(0):
            self.comboBoxLayer.addItem(item)

        self.show()

    def listlayers(self, layertype):
        """Get a list of all layers"""
        layersmap = QgsMapLayerRegistry.instance().mapLayers()
        layerslist = []
        for (name, layer) in layersmap.iteritems():
            if layertype == layer.type():
                layerslist.append(name)
        return layerslist

    def getLayerByName(self, layername):
        """Get a layer by its name"""
        layersmap = QgsMapLayerRegistry.instance().mapLayers()
        for (name, layer) in layersmap.iteritems():
            if layername == name:
                return layer

    def setaffine(self):
        """Set transformation matrix values"""
        self.a = self.spinA.value()
        self.b = self.spinB.value()
        self.tx = self.spinTx.value()
        self.c = self.spinC.value()
        self.d = self.spinD.value()
        self.ty = self.spinTy.value()

    def affine(self):
        """Run the transformation currently set on the UI"""
        self.setaffine()
        self.doaffine()

    def invert(self):
        """Invert the transformation matrix"""
        # matrix form: x' = A x + b
        # --> x = A^-1 x' - A^-1 b
        # A^-1 = [d -b; -c a] / det A
        # only valid if det A = a d - b c != 0
        self.setaffine()
        det = self.a * self.d - self.b * self.c
        if det == 0:
            warn = QgsMessageViewer()
            warn.setMessageAsPlainText("Transformation is not invertable.")
            warn.showMessage()
            return
        a = self.d / det
        b = -self.b / det
        c = -self.c / det
        d = self.a / det
        tx = -a * self.tx - b * self.ty
        ty = -c * self.tx - d * self.ty
        self.spinA.setValue(a)
        self.spinB.setValue(b)
        self.spinC.setValue(c)
        self.spinD.setValue(d)
        self.spinTx.setValue(tx)
        self.spinTy.setValue(ty)
        self.setaffine()

    def finish(self):
        """Stop the plugin"""
        self.close()

    def doaffine(self):
        """Apply the transformation matrix"""
        warn = QgsMessageViewer()
        vlayer = self.getLayerByName(self.comboBoxLayer.currentText())
        if self.radioButtonWholeLayer.isChecked():
            vlayer.removeSelection()
            vlayer.invertSelection()
        if vlayer is None:
            warn.setMessageAsPlainText("Select a layer to transform.")
            warn.showMessage()
            return
        featids = vlayer.selectedFeaturesIds()
        result = {}
        features = {}
        if vlayer.geometryType() == 2:
            start = 1
        else:
            start = 0
        print vlayer.name()
        if not vlayer.isEditable():
            warn.setMessageAsPlainText("Layer not in edit mode.")
            warn.showMessage()
        else:
            for fid in featids:
                features[fid] = QgsFeature()
                if not vlayer.getFeatures(QgsFeatureRequest()\
                        .setFilterFid(fid)).nextFeature(features[fid]):
                    continue
                result[fid] = features[fid].geometry()
                i = start
                vertex = result[fid].vertexAt(i)
                while vertex != QgsPoint(0, 0):
                    # matrix form: x' = A x + b
                    # x' = a x + b y + tx
                    # y' = c x + d y + ty
                    newx = self.a * vertex.x() + self.b * vertex.y() + self.tx
                    newy = self.c * vertex.x() + self.d * vertex.y() + self.ty
                    #geom.
                    #print vertex.x(), vertex.y(), newx, newy
                    vlayer.moveVertex(newx, newy, fid, i)
                    #print vertex.x,vertex.y,newx,newy,fid,i
                    i += 1
                    vertex = result[fid].vertexAt(i)
            #vlayer.commitChanges()
            #vlayer.updateExtents()
            #vlayer.updateGeometryValues(result)

            self.iface.mapCanvas().zoomToSelected()
        #self.iface.mapCanvas().refresh()
        #print "ok"
