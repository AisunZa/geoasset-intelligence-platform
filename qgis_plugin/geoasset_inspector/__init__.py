def classFactory(iface):
    from .geoasset_inspector import GeoAssetInspector

    return GeoAssetInspector(iface)