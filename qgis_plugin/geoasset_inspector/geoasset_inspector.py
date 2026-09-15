import json
import urllib.error
import urllib.request

from qgis.PyQt.QtWidgets import (
    QAction,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)


class GeoAssetInspector:

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.result_layer = None

    def initGui(self):
        self.action = QAction(
            "GeoAsset Inspector",
            self.iface.mainWindow(),
        )

        self.action.triggered.connect(self.open_dialog)

        self.iface.addPluginToMenu(
            "&GeoAsset Intelligence",
            self.action,
        )

        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu(
                "&GeoAsset Intelligence",
                self.action,
            )

            self.iface.removeToolBarIcon(self.action)

    def open_dialog(self):
        if self.dialog is None:
            self.create_dialog()

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def create_dialog(self):
        self.dialog = QDialog(
            self.iface.mainWindow()
        )

        self.dialog.setWindowTitle(
            "GeoAsset Inspector"
        )

        self.dialog.resize(480, 420)

        main_layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.api_url_input = QLineEdit(
            "http://127.0.0.1:8001"
        )

        self.pipeline_id_input = QLineEdit(
            "469"
        )

        form_layout.addRow(
            "GeoAsset API:",
            self.api_url_input,
        )

        form_layout.addRow(
            "Pipeline ID:",
            self.pipeline_id_input,
        )

        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()

        self.load_button = QPushButton(
            "Find Pipeline"
        )

        self.load_button.clicked.connect(
            self.load_pipeline
        )

        button_layout.addWidget(
            self.load_button
        )

        main_layout.addLayout(
            button_layout
        )

        self.results = QTextEdit()
        self.results.setReadOnly(True)

        main_layout.addWidget(
            self.results
        )

        self.dialog.setLayout(
            main_layout
        )

    def load_pipeline(self):
        pipeline_text = (
            self.pipeline_id_input
            .text()
            .strip()
        )

        try:
            pipeline_id = int(
                pipeline_text
            )
        except ValueError:
            QMessageBox.warning(
                self.dialog,
                "Invalid Pipeline ID",
                "Pipeline ID must be an integer.",
            )
            return

        base_url = (
            self.api_url_input
            .text()
            .strip()
            .rstrip("/")
        )

        try:
            details = self.get_json(
                f"{base_url}/pipelines/{pipeline_id}"
            )

            geojson = self.get_json(
                f"{base_url}/pipelines/"
                f"{pipeline_id}/geojson"
            )

            self.display_details(
                details
            )

            self.display_pipeline(
                geojson
            )

        except urllib.error.HTTPError as error:
            if error.code == 404:
                QMessageBox.warning(
                    self.dialog,
                    "Pipeline Not Found",
                    (
                        f"Pipeline {pipeline_id} "
                        "was not found."
                    ),
                )
            else:
                QMessageBox.critical(
                    self.dialog,
                    "API Error",
                    (
                        "The GeoAsset API returned "
                        f"HTTP {error.code}."
                    ),
                )

        except urllib.error.URLError:
            QMessageBox.critical(
                self.dialog,
                "Connection Error",
                (
                    "Could not connect to the "
                    "GeoAsset API.\n\n"
                    "Make sure Docker Compose "
                    "or FastAPI is running."
                ),
            )

        except Exception as error:
            QMessageBox.critical(
                self.dialog,
                "GeoAsset Inspector Error",
                str(error),
            )

    def get_json(self, url):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=10,
        ) as response:
            return json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    def display_details(self, data):
        risk_score = data.get(
            "risk_score",
            "N/A",
        )

        flood_exposure = data.get(
            "flood_exposure_percent",
            "N/A",
        )

        text = (
            f"Asset Code: "
            f"{data.get('asset_code', 'N/A')}\n\n"

            f"Pipeline ID: "
            f"{data.get('pipeline_id', 'N/A')}\n"

            f"Material: "
            f"{data.get('material', 'N/A')}\n"

            f"Diameter: "
            f"{data.get('diameter_mm', 'N/A')} mm\n"

            f"Installation Year: "
            f"{data.get('installation_year', 'N/A')}\n"

            f"Condition: "
            f"{data.get('condition', 'N/A')}\n"

            f"Status: "
            f"{data.get('status', 'N/A')}\n\n"

            f"RISK ASSESSMENT\n"
            f"------------------------\n"

            f"Risk Score: "
            f"{risk_score}\n"

            f"Risk Level: "
            f"{data.get('risk_level', 'N/A')}\n"

            f"Failures: "
            f"{data.get('failure_count', 'N/A')}\n"

            f"Buildings within 100 m: "
            f"{data.get('buildings_within_100m', 'N/A')}\n"

            f"Flood Exposure: "
            f"{flood_exposure}%\n"

            f"Days Since Inspection: "
            f"{data.get('days_since_last_inspection', 'N/A')}"
        )

        self.results.setPlainText(
            text
        )

    def display_pipeline(self, geojson):
        geometry = geojson.get(
            "geometry"
        )

        if not geometry:
            raise ValueError(
                "API response contains no geometry."
            )

        geometry_type = geometry.get(
            "type"
        )

        if geometry_type != "LineString":
            raise ValueError(
                (
                    "Expected LineString geometry, "
                    f"received {geometry_type}."
                )
            )

        coordinates = geometry.get(
            "coordinates",
            [],
        )

        if len(coordinates) < 2:
            raise ValueError(
                "Pipeline geometry is invalid."
            )

        points = [
            QgsPointXY(
                float(coordinate[0]),
                float(coordinate[1]),
            )
            for coordinate in coordinates
        ]

        layer = QgsVectorLayer(
            (
                "LineString?"
                "crs=EPSG:4326&"
                "field=pipeline_id:integer&"
                "field=asset_code:string&"
                "field=risk_score:double&"
                "field=risk_level:string"
            ),
            "GeoAsset Selected Pipeline",
            "memory",
        )

        if not layer.isValid():
            raise RuntimeError(
                "Could not create QGIS memory layer."
            )

        provider = layer.dataProvider()

        properties = geojson.get(
            "properties",
            {},
        )

        feature = QgsFeature(
            layer.fields()
        )

        feature.setGeometry(
            QgsGeometry.fromPolylineXY(
                points
            )
        )

        feature.setAttributes(
            [
                properties.get(
                    "pipeline_id"
                ),
                properties.get(
                    "asset_code"
                ),
                properties.get(
                    "risk_score"
                ),
                properties.get(
                    "risk_level"
                ),
            ]
        )

        provider.addFeature(
            feature
        )

        layer.updateExtents()

        if self.result_layer is not None:
            QgsProject.instance().removeMapLayer(
                self.result_layer.id()
            )

        QgsProject.instance().addMapLayer(
            layer
        )

        self.result_layer = layer

        self.iface.setActiveLayer(
            layer
        )

        extent = layer.extent()
        extent.scale(3.0)

        self.iface.mapCanvas().setExtent(
            extent
        )

        self.iface.mapCanvas().refresh()