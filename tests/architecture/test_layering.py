import ast
import os
import pytest

def get_ast_imports(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports

def test_controllers_do_not_import_repositories_directly():
    """Architecture Rule: Controllers must communicate with Services, never Repositories directly."""
    controller_dir = "src/controllers"
    for fname in os.listdir(controller_dir):
        if fname.endswith(".py"):
            path = os.path.join(controller_dir, fname)
            imports = get_ast_imports(path)
            for imp in imports:
                assert not imp.startswith("src.repositories"), \
                    f"Direct repository access forbidden in controller: {fname} imports {imp}"

def test_services_do_not_import_controllers():
    """Architecture Rule: Services cannot depend on the Controller layer."""
    service_dir = "src/services"
    for fname in os.listdir(service_dir):
        if fname.endswith(".py"):
            path = os.path.join(service_dir, fname)
            imports = get_ast_imports(path)
            for imp in imports:
                assert not imp.startswith("src.controllers"), \
                    f"Inverted dependency: {fname} imports controller {imp}"

def test_domain_has_zero_external_third_party_dependencies():
    """Architecture Rule: Domain layer must be framework-agnostic with zero third-party dependencies."""
    domain_dir = "src/domain"
    allowed_prefixes = {"src.domain", "decimal", "enum", "datetime", "typing", "dataclasses", "uuid", "math"}
    for fname in os.listdir(domain_dir):
        if fname.endswith(".py"):
            path = os.path.join(domain_dir, fname)
            imports = get_ast_imports(path)
            for imp in imports:
                top_pkg = imp.split(".")[0]
                assert any(imp.startswith(p) for p in allowed_prefixes), \
                    f"Domain layer impurity: {fname} imports disallowed module {imp}"

def test_no_floating_point_casts_in_domain_rules():
    """Architecture Rule (NFR-01): Forbidden float() casts in domain rules and models."""
    domain_dir = "src/domain"
    for root, _, files in os.walk(domain_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r") as fp:
                    content = fp.read()
                    assert "float(" not in content, f"Forbidden float conversion in {path}"
