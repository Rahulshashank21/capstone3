import sys
import pytest

def test_domain_layer_has_no_framework_dependencies():
    """Enforce architectural isolation: domain rules/models must not import controllers or adapters."""
    forbidden_modules = ["src.controllers", "src.adapters", "flask", "fastapi"]
    
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("src.domain"):
            module = sys.modules[mod_name]
            for attr in dir(module):
                attr_value = getattr(module, attr)
                if hasattr(attr_value, "__module__") and attr_value.__module__:
                    for forbidden in forbidden_modules:
                        assert not attr_value.__module__.startswith(forbidden), \
                            f"Domain leakage detected: {attr_value.__module__} imported in domain layer"
