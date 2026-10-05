#!/usr/bin/env python3
"""
TelcoLane Cobertura Coverage Generator
Leverages Python 3.13's native sys.monitoring subsystem to record exact line execution
across asynchronous event loops and threadpools with zero overhead, generating a compliant
Cobertura coverage.xml report.
"""

import os
import sys
import dis
import time
import pytest
import xml.etree.ElementTree as ET

def get_executable_lines(file_path: str):
    """Extracts all executable line numbers from Python bytecode."""
    lines = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_obj = compile(f.read(), file_path, "exec")
        
        def recurse_code(co):
            for _, l in dis.findlinestarts(co):
                if l is not None:
                    lines.add(l)
            for c in co.co_consts:
                if hasattr(c, "co_code"):
                    recurse_code(c)
        recurse_code(code_obj)
    except Exception as e:
        print(f"Warning: could not inspect {file_path}: {e}")
    return sorted(lines)

def run_suite_with_coverage(output_xml: str = "coverage.xml"):
    root_dir = os.path.abspath(os.getcwd())
    src_dir = os.path.join(root_dir, "src")

    # Collect executable lines for all Python files in src/
    all_files = {}
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith(".py") and "__pycache__" not in root:
                full_path = os.path.join(root, f)
                valid_lines = get_executable_lines(full_path)
                if valid_lines:
                    all_files[full_path] = valid_lines

    # Use Python 3.13 sys.monitoring
    executed_lines = set()
    TOOL_ID = sys.monitoring.COVERAGE_ID
    sys.monitoring.use_tool_id(TOOL_ID, "telcolane_cobertura")

    def line_callback(code, line_number):
        executed_lines.add((code.co_filename, line_number))
        return sys.monitoring.DISABLE

    sys.monitoring.register_callback(TOOL_ID, sys.monitoring.events.LINE, line_callback)
    sys.monitoring.set_events(TOOL_ID, sys.monitoring.events.LINE)

    print(">>> Executing Pytest test suite under sys.monitoring instrumentation...")
    start_time = time.time()
    try:
        ret_code = pytest.main(["-q", "tests/"])
    finally:
        sys.monitoring.free_tool_id(TOOL_ID)
    duration = time.time() - start_time
    print(f">>> Pytest completed in {duration:.2f}s with exit code {ret_code}")

    if ret_code != 0:
        print("ERROR: Test suite did not pass cleanly. Aborting coverage report.")
        return False

    # Compute coverage metrics
    total_valid = 0
    total_covered = 0
    file_stats = {}

    for path, valid_lines in sorted(all_files.items()):
        covered = set(l for (f, l) in executed_lines if f == path).intersection(valid_lines)
        total_valid += len(valid_lines)
        total_covered += len(covered)
        rate = (len(covered) / len(valid_lines)) if valid_lines else 1.0
        file_stats[path] = {
            "valid": valid_lines,
            "covered": covered,
            "rate": rate
        }

    overall_rate = (total_covered / total_valid) if total_valid else 1.0
    print(f"\n==================== Line Coverage Summary ====================")
    for path, stats in sorted(file_stats.items()):
        rel = os.path.relpath(path, root_dir)
        cov_count = len(stats["covered"])
        val_count = len(stats["valid"])
        pct = stats["rate"] * 100
        print(f"  {rel:45} {cov_count:4}/{val_count:4} ({pct:5.1f}%)")
    print("---------------------------------------------------------------")
    print(f"  TOTAL COVERAGE: {total_covered}/{total_valid} ({overall_rate * 100:.2f}%)")
    print("===============================================================\n")

    # Generate Cobertura XML DOM
    cov_elem = ET.Element("coverage", {
        "version": "7.4.0",
        "timestamp": str(int(time.time())),
        "lines-valid": str(total_valid),
        "lines-covered": str(total_covered),
        "line-rate": f"{overall_rate:.4f}",
        "branches-covered": "0",
        "branches-valid": "0",
        "branch-rate": "0",
        "complexity": "0"
    })

    sources_elem = ET.SubElement(cov_elem, "sources")
    source_elem = ET.SubElement(sources_elem, "source")
    source_elem.text = root_dir

    packages_elem = ET.SubElement(cov_elem, "packages")
    package_elem = ET.SubElement(packages_elem, "package", {
        "name": "src",
        "line-rate": f"{overall_rate:.4f}",
        "branch-rate": "0",
        "complexity": "0"
    })

    classes_elem = ET.SubElement(package_elem, "classes")
    for path, stats in sorted(file_stats.items()):
        rel_path = os.path.relpath(path, root_dir)
        class_name = rel_path.replace(os.sep, ".").rstrip(".py")
        cls_elem = ET.SubElement(classes_elem, "class", {
            "name": class_name,
            "filename": rel_path,
            "line-rate": f"{stats['rate']:.4f}",
            "branch-rate": "0",
            "complexity": "0"
        })
        lines_elem = ET.SubElement(cls_elem, "lines")
        for line_num in stats["valid"]:
            hits = 1 if line_num in stats["covered"] else 0
            ET.SubElement(lines_elem, "line", {
                "number": str(line_num),
                "hits": str(hits)
            })

    tree = ET.ElementTree(cov_elem)
    ET.indent(tree, space="  ")
    tree.write(output_xml, encoding="utf-8", xml_declaration=True)
    print(f">>> Successfully written Cobertura report to {output_xml}")
    return True

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "coverage.xml"
    success = run_suite_with_coverage(output_xml=out)
    sys.exit(0 if success else 1)
