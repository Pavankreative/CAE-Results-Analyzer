from app.adapters.base import (
    AdapterError,
    AdapterInfo,
    AdapterRegistry,
    BaseAdapter,
    UnsupportedFormatError,
)
from app.adapters.csv_fields import CSVPointAdapter
from app.adapters.native import NativeJSONAdapter
from app.adapters.planned import PLANNED_ADAPTERS
from app.adapters.vtk_legacy import VTKLegacyAdapter

registry = AdapterRegistry()
registry.register(NativeJSONAdapter())
registry.register(VTKLegacyAdapter())
registry.register(CSVPointAdapter())
for _a in PLANNED_ADAPTERS:
    registry.register(_a)

__all__ = [
    "registry", "AdapterRegistry", "BaseAdapter", "AdapterInfo",
    "AdapterError", "UnsupportedFormatError", "NativeJSONAdapter",
    "VTKLegacyAdapter", "CSVPointAdapter",
]
