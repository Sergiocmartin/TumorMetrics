"""
TumorMetrics — 3D Slicer Extension
Segmentación de tumores y cálculo de métricas clínicas (volumen, RECIST, esfericidad).

Autor: Sergio Castaño Martin
Licencia: MIT
Repositorio: https://github.com/Sergiocmartin/TumorMetrics
"""

import os
import math
import vtk
import ctk
import qt
import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleWidget,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleTest,
)
import slicer.util


# ──────────────────────────────────────────────────────────────
# 1. MÓDULO — Metadatos que aparecen en el Extension Manager
# ──────────────────────────────────────────────────────────────

class TumorMetrics(ScriptedLoadableModule):
    """Metadatos del módulo (nombre, descripción, categoría)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent.title = "TumorMetrics"
        self.parent.categories = ["Oncology"]
        self.parent.dependencies = []
        self.parent.contributors = ["Sergio Castaño Martin"]
        self.parent.helpText = """
        Extensión para segmentación de tumores y cálculo de métricas clínicas:
        volumen (cm³), diámetro mayor RECIST (mm) y esfericidad.
        """
        self.parent.acknowledgementText = """
        Desarrollado como proyecto portfolio. Datos de prueba: TCIA (tcia.cancerimagingarchive.net).
        """


# ──────────────────────────────────────────────────────────────
# 2. WIDGET — Interfaz gráfica (panel izquierdo de Slicer)
# ──────────────────────────────────────────────────────────────

class TumorMetricsWidget(ScriptedLoadableModuleWidget):
    """Construye y gestiona la UI del módulo."""

    def setup(self):
        super().setup()

        # ── Sección: Entrada ──────────────────────────────────
        inputCollapsible = ctk.ctkCollapsibleButton()
        inputCollapsible.text = "Entrada"
        self.layout.addWidget(inputCollapsible)
        inputLayout = qt.QFormLayout(inputCollapsible)

        # Selector de volumen (imagen CT/MRI)
        self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputVolumeSelector.selectNodeUponCreation = True
        self.inputVolumeSelector.addEnabled = False
        self.inputVolumeSelector.removeEnabled = False
        self.inputVolumeSelector.noneEnabled = False
        self.inputVolumeSelector.showHidden = False
        self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        inputLayout.addRow("Volumen de entrada:", self.inputVolumeSelector)

        # Umbral de intensidad para segmentación inicial
        self.thresholdSlider = ctk.ctkRangeWidget()
        self.thresholdSlider.minimum = -1000
        self.thresholdSlider.maximum = 3000
        self.thresholdSlider.minimumValue = 100
        self.thresholdSlider.maximumValue = 400
        inputLayout.addRow("Umbral HU:", self.thresholdSlider)

        # ── Sección: Acciones ─────────────────────────────────
        actionCollapsible = ctk.ctkCollapsibleButton()
        actionCollapsible.text = "Segmentación"
        self.layout.addWidget(actionCollapsible)
        actionLayout = qt.QVBoxLayout(actionCollapsible)

        self.segmentButton = qt.QPushButton("Segmentar tumor")
        self.segmentButton.toolTip = "Aplica umbralización y crea una segmentación"
        self.segmentButton.enabled = True
        actionLayout.addWidget(self.segmentButton)

        self.computeButton = qt.QPushButton("Calcular métricas")
        self.computeButton.toolTip = "Calcula volumen, RECIST y esfericidad"
        self.computeButton.enabled = False
        actionLayout.addWidget(self.computeButton)

        # ── Sección: Resultados ───────────────────────────────
        resultsCollapsible = ctk.ctkCollapsibleButton()
        resultsCollapsible.text = "Métricas clínicas"
        self.layout.addWidget(resultsCollapsible)
        resultsLayout = qt.QFormLayout(resultsCollapsible)

        self.volumeLabel = qt.QLabel("—")
        self.volumeLabel.setStyleSheet("font-weight: bold; font-size: 14px;")
        resultsLayout.addRow("Volumen (cm³):", self.volumeLabel)

        self.recistLabel = qt.QLabel("—")
        self.recistLabel.setStyleSheet("font-weight: bold; font-size: 14px;")
        resultsLayout.addRow("Diámetro RECIST (mm):", self.recistLabel)

        self.sphericityLabel = qt.QLabel("—")
        self.sphericityLabel.setStyleSheet("font-weight: bold; font-size: 14px;")
        resultsLayout.addRow("Esfericidad (0–1):", self.sphericityLabel)

        # Botón exportar CSV
        self.exportButton = qt.QPushButton("Exportar CSV")
        self.exportButton.enabled = False
        self.layout.addWidget(self.exportButton)

        # Espaciador al final
        self.layout.addStretch(1)

        # ── Conectar señales ──────────────────────────────────
        self.segmentButton.connect("clicked(bool)", self.onSegmentButton)
        self.computeButton.connect("clicked(bool)", self.onComputeButton)
        self.exportButton.connect("clicked(bool)", self.onExportButton)

        # Referencia a la lógica
        self.logic = TumorMetricsLogic()
        self._segmentationNode = None
        self._metrics = {}

    def onSegmentButton(self):
        volumeNode = self.inputVolumeSelector.currentNode()
        if not volumeNode:
            slicer.util.errorDisplay("Selecciona un volumen primero.")
            return

        threshMin = self.thresholdSlider.minimumValue
        threshMax = self.thresholdSlider.maximumValue

        try:
            self._segmentationNode = self.logic.segmentTumor(
                volumeNode, threshMin, threshMax
            )
            self.computeButton.enabled = True
            slicer.util.infoDisplay("Segmentación completada. Revisa el resultado en las vistas.")
        except Exception as e:
            slicer.util.errorDisplay(f"Error en segmentación: {e}")

    def onComputeButton(self):
        volumeNode = self.inputVolumeSelector.currentNode()
        if not self._segmentationNode:
            slicer.util.errorDisplay("Primero realiza la segmentación.")
            return

        try:
            self._metrics = self.logic.computeMetrics(
                self._segmentationNode, volumeNode
            )
            self.volumeLabel.setText(f"{self._metrics['volume_cm3']:.2f}")
            self.recistLabel.setText(f"{self._metrics['recist_mm']:.1f}")
            self.sphericityLabel.setText(f"{self._metrics['sphericity']:.3f}")
            self.exportButton.enabled = True
        except Exception as e:
            slicer.util.errorDisplay(f"Error calculando métricas: {e}")

    def onExportButton(self):
        if not self._metrics:
            return
        path = qt.QFileDialog.getSaveFileName(
            None, "Guardar métricas", "", "CSV (*.csv)"
        )
        if path:
            self.logic.exportCSV(self._metrics, path)
            slicer.util.infoDisplay(f"Métricas exportadas a:\n{path}")


# ──────────────────────────────────────────────────────────────
# 3. LÓGICA — Procesamiento (separado de la UI)
# ──────────────────────────────────────────────────────────────

class TumorMetricsLogic(ScriptedLoadableModuleLogic):
    """
    Toda la lógica médica va aquí, separada de la UI.
    Esto permite testear la lógica sin abrir la interfaz gráfica.
    """

    def segmentTumor(self, volumeNode, threshMin, threshMax):
        """
        Crea una segmentación por umbralización de intensidad HU.
        Devuelve un vtkMRMLSegmentationNode.
        """
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentationNode.SetName("Tumor_Segmentation")
        segmentationNode.CreateDefaultDisplayNodes()
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(volumeNode)

        # Añadir segmento "Tumor"
        segmentId = segmentationNode.GetSegmentation().AddEmptySegment("Tumor")

        # Usar Segment Editor para aplicar el efecto Threshold
        segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        segmentEditorWidget.setSegmentationNode(segmentationNode)
        segmentEditorWidget.setSourceVolumeNode(volumeNode)

        segmentEditorNode.SetSelectedSegmentID(segmentId)
        segmentEditorWidget.setActiveEffectByName("Threshold")
        effect = segmentEditorWidget.activeEffect()
        effect.setParameter("MinimumThreshold", str(threshMin))
        effect.setParameter("MaximumThreshold", str(threshMax))
        effect.self().onApply()

        # Limpiar el editor
        segmentEditorWidget.setActiveEffectByName("None")
        slicer.mrmlScene.RemoveNode(segmentEditorNode)

        return segmentationNode

    def computeMetrics(self, segmentationNode, volumeNode):
        """
        Calcula métricas clínicas del tumor segmentado:
        - Volumen en cm³
        - Diámetro mayor (criterio RECIST) en mm
        - Esfericidad (0 = plano, 1 = esfera perfecta)
        """
        import SegmentStatistics

        # ── Volumen ───────────────────────────────────────────
        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
        segStatLogic.getParameterNode().SetParameter("ScalarVolume", volumeNode.GetID())
        segStatLogic.computeStatistics()
        stats = segStatLogic.getStatistics()

        segmentId = segmentationNode.GetSegmentation().GetNthSegmentID(0)
        volume_mm3 = stats[segmentId, "LabelmapSegmentStatisticsPlugin.voxel_count"] * \
                     self._getVoxelVolumeMm3(volumeNode)
        volume_cm3 = volume_mm3 / 1000.0

        # ── Diámetro RECIST (eje mayor del bounding box orientado) ──
        # Obtener labelmap
        labelmapNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(
            segmentationNode, labelmapNode, volumeNode
        )

        bounds = [0.0] * 6
        labelmapNode.GetRASBounds(bounds)
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        recist_mm = max(dx, dy, dz)

        slicer.mrmlScene.RemoveNode(labelmapNode)

        # ── Esfericidad ───────────────────────────────────────
        # Esfericidad = (pi^(1/3) * (6*V)^(2/3)) / A
        # Requiere superficie — la aproximamos desde el volumen y el bounding box
        # Para mayor precisión en fases avanzadas: usar vtkMassProperties
        surface_area_approx = self._estimateSurfaceArea(segmentationNode, volumeNode)
        if surface_area_approx > 0:
            sphericity = (math.pi ** (1/3) * (6 * volume_mm3) ** (2/3)) / surface_area_approx
            sphericity = min(sphericity, 1.0)
        else:
            sphericity = 0.0

        return {
            "volume_cm3": volume_cm3,
            "recist_mm": recist_mm,
            "sphericity": sphericity,
        }

    def _getVoxelVolumeMm3(self, volumeNode):
        """Devuelve el volumen de un vóxel en mm³."""
        spacing = volumeNode.GetSpacing()
        return spacing[0] * spacing[1] * spacing[2]

    def _estimateSurfaceArea(self, segmentationNode, volumeNode):
        """
        Estima el área de superficie del tumor usando la malla 3D.
        Devuelve el área en mm².
        """
        try:
            closedSurface = vtk.vtkPolyData()
            segmentationNode.GetClosedSurfaceRepresentation(
                segmentationNode.GetSegmentation().GetNthSegmentID(0),
                closedSurface
            )
            massProps = vtk.vtkMassProperties()
            massProps.SetInputData(closedSurface)
            massProps.Update()
            return massProps.GetSurfaceArea()
        except Exception:
            return 0.0

    def exportCSV(self, metrics, filePath):
        """Exporta las métricas calculadas a un archivo CSV."""
        import csv
        with open(filePath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=metrics.keys())
            writer.writeheader()
            writer.writerow(metrics)


# ──────────────────────────────────────────────────────────────
# 4. TESTS — Se ejecutan desde el módulo "Tests" de Slicer
# ──────────────────────────────────────────────────────────────

class TumorMetricsTest(ScriptedLoadableModuleTest):
    """
    Tests básicos para verificar que la lógica funciona.
    Ejecutar desde Slicer: Edit → Application Settings → Modules → Run tests
    """

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_MetricsOnSyntheticSphere()

    def test_MetricsOnSyntheticSphere(self):
        """
        Crea una esfera sintética y verifica que el volumen calculado
        se aproxima al volumen teórico (4/3 * pi * r^3).
        """
        self.delayDisplay("Creando volumen sintético de prueba...")

        # Crear volumen de prueba (100x100x100 vóxeles, espaciado 1mm)
        imageSize = [100, 100, 100]
        voxelType = vtk.VTK_FLOAT
        imageOrigin = [0.0, 0.0, 0.0]
        imageSpacing = [1.0, 1.0, 1.0]

        imageData = vtk.vtkImageData()
        imageData.SetDimensions(imageSize)
        imageData.AllocateScalars(voxelType, 1)
        imageData.GetPointData().GetScalars().Fill(0)

        # Rellenar una esfera de radio 20 mm centrada en (50,50,50)
        radius = 20
        center = [50, 50, 50]
        for z in range(imageSize[2]):
            for y in range(imageSize[1]):
                for x in range(imageSize[0]):
                    dist = math.sqrt(
                        (x - center[0])**2 +
                        (y - center[1])**2 +
                        (z - center[2])**2
                    )
                    if dist <= radius:
                        imageData.SetScalarComponentFromDouble(x, y, z, 0, 500.0)

        volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "TestSphere")
        volumeNode.SetOrigin(imageOrigin)
        volumeNode.SetSpacing(imageSpacing)
        volumeNode.SetAndObserveImageData(imageData)
        volumeNode.CreateDefaultDisplayNodes()

        # Segmentar y calcular métricas
        logic = TumorMetricsLogic()
        segNode = logic.segmentTumor(volumeNode, 400, 600)
        metrics = logic.computeMetrics(segNode, volumeNode)

        # Verificar volumen: esfera radio 20mm → V = 33510 mm³ = 33.51 cm³
        expected_cm3 = (4/3) * math.pi * (radius**3) / 1000.0
        tolerance = expected_cm3 * 0.05  # 5% de tolerancia

        self.assertAlmostEqual(
            metrics["volume_cm3"], expected_cm3,
            delta=tolerance,
            msg=f"Volumen esperado ~{expected_cm3:.1f} cm³, obtenido {metrics['volume_cm3']:.1f} cm³"
        )

        self.delayDisplay(
            f"Test completado correctamente.\n"
            f"Volumen: {metrics['volume_cm3']:.2f} cm³ (esperado ~{expected_cm3:.2f})\n"
            f"RECIST: {metrics['recist_mm']:.1f} mm\n"
            f"Esfericidad: {metrics['sphericity']:.3f}"
        )
