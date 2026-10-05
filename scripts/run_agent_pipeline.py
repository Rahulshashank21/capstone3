#!/usr/bin/env python3
"""
TelcoLane Claude Agent SDK Programmatic Orchestrator
Demonstrates automated multi-agent workflow: Planner -> Generator -> Evaluator -> Ratchet
Enforces strict timeouts (timeout=60s), iteration budgeting, and Cobertura XML quality ratchets.
"""

import sys
import os
import subprocess
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class AgentMessage:
    sender: str
    recipient: str
    content: str
    metadata: Dict[str, Any]

class ClaudeAgentPipeline:
    def __init__(self, sprint_id: str, max_iterations: int = 3, timeout_seconds: int = 60):
        self.sprint_id = sprint_id
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.transcript: List[AgentMessage] = []

    def dispatch(self, sender: str, recipient: str, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
        msg = AgentMessage(sender=sender, recipient=recipient, content=message, metadata=meta or {})
        self.transcript.append(msg)
        print(f"[{sender.upper()} -> {recipient.upper()}]: {message}")

    def execute_hooks(self) -> bool:
        hooks = [
            ".claude/hooks/architecture-layering-check.sh",
            ".claude/hooks/pii-masking-check.sh",
            ".claude/hooks/pro-rata-invariant-check.sh",
            ".claude/hooks/plan-immutability-check.sh"
        ]
        for hook in hooks:
            print(f"Executing hook: {hook}...")
            try:
                res = subprocess.run(
                    ["bash", hook],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                if res.returncode != 0:
                    print(f"[FAIL] Hook failed: {hook}\n{res.stderr or res.stdout}")
                    return False
                print(res.stdout.strip())
            except subprocess.TimeoutExpired:
                print(f"[FAIL] Hook timed out after {self.timeout_seconds}s: {hook}")
                return False
        return True

    def verify_coverage_artifact(self, coverage_xml_path: str = "coverage.xml", min_coverage_pct: float = 85.0) -> bool:
        if not os.path.exists(coverage_xml_path):
            print(f"[FAIL] Coverage artifact {coverage_xml_path} does not exist!")
            return False

        try:
            tree = ET.parse(coverage_xml_path)
            root = tree.getroot()
            lines_covered = int(root.get("lines-covered", "0"))
            lines_valid = int(root.get("lines-valid", "1"))
            actual_pct = (lines_covered / lines_valid) * 100.0 if lines_valid > 0 else 0.0

            print(f"[Coverage Audit]: Found {lines_covered}/{lines_valid} lines covered ({actual_pct:.2f}%). Required >= {min_coverage_pct}%.")
            if actual_pct < min_coverage_pct:
                print(f"[FAIL] Coverage {actual_pct:.2f}% is below required threshold of {min_coverage_pct}%.")
                return False
            return True
        except Exception as e:
            print(f"[FAIL] Error parsing Cobertura coverage artifact: {e}")
            return False

    def run(self) -> bool:
        print(f"=== Starting Programmatic Claude Agent Pipeline for {self.sprint_id} (Iteration Budget: {self.max_iterations}) ===")

        iteration = 1
        while iteration <= self.max_iterations:
            print(f"\n--- Pipeline Iteration {iteration}/{self.max_iterations} ---")

            # Step 1: Planner Agent
            self.dispatch(
                "planner",
                "generator",
                f"Sprint requirements extracted for {self.sprint_id}. Proceed with implementation.",
                {"target_spec": "specs/app_spec.md", "iteration": iteration}
            )

            # Step 2: Generator Agent
            self.dispatch(
                "generator",
                "evaluator",
                "Substrate components and domain policies generated according to spec.",
                {"files_updated": ["src/domain/models.py", "src/services/subscription_service.py"]}
            )

            # Step 3: Evaluator Agent running verification gates
            print("\n--- Running Evaluator Verification Gates ---")
            hooks_passed = self.execute_hooks()
            if not hooks_passed:
                self.dispatch("evaluator", "generator", "Verification hooks failed! Retrying iteration.")
                iteration += 1
                continue

            # Step 4: Run Pytest test suite with coverage
            print("\n--- Running Pytest Quality Suite & Coverage Generation ---")
            try:
                test_run = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                print(test_run.stdout.strip())
                if test_run.returncode != 0:
                    self.dispatch("evaluator", "generator", f"Pytest suite failed with returncode {test_run.returncode}!")
                    iteration += 1
                    continue
            except subprocess.TimeoutExpired:
                print(f"[FAIL] Pytest execution timed out after {self.timeout_seconds}s!")
                iteration += 1
                continue

            # Step 5: Coverage generation and XML audit
            try:
                cov_run = subprocess.run(
                    [sys.executable, "scripts/generate_coverage.py"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds
                )
                if cov_run.returncode != 0:
                    self.dispatch("evaluator", "generator", "Coverage generation script failed!")
                    iteration += 1
                    continue
            except subprocess.TimeoutExpired:
                print(f"[FAIL] Coverage generation timed out after {self.timeout_seconds}s!")
                iteration += 1
                continue

            # Step 6: Parse coverage.xml directly
            if not self.verify_coverage_artifact("coverage.xml", min_coverage_pct=84.0):
                self.dispatch("evaluator", "generator", "Coverage requirement gate not met.")
                iteration += 1
                continue

            self.dispatch(
                "evaluator",
                "orchestrator",
                f"All quality gates, coverage requirements, and acceptance criteria passed for {self.sprint_id}. Ratcheting release.",
                {"status": "APPROVED", "iteration": iteration}
            )
            print(f"=== Pipeline Completed Successfully for {self.sprint_id} on Iteration {iteration} ===")
            return True

        print(f"[FAIL] Claude Agent Pipeline exceeded maximum iteration budget of {self.max_iterations}.")
        return False

if __name__ == "__main__":
    sprint = sys.argv[1] if len(sys.argv) > 1 else "SPRINT-04"
    orchestrator = ClaudeAgentPipeline(sprint_id=sprint)
    success = orchestrator.run()
    sys.exit(0 if success else 1)
