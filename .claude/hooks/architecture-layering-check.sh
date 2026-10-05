#!/usr/bin/env bash
set -euo pipefail

echo "Running Architectural Layering Isolation Hook..."
python3 -c "
import os
import sys

domain_dir = 'src/domain'
forbidden_imports = ['fastapi', 'flask', 'starlette', 'src.controllers', 'src.adapters', 'src.repositories']

violations = []
for root, _, files in os.walk(domain_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                for line_no, line in enumerate(f, 1):
                    for forbidden in forbidden_imports:
                        if f'import {forbidden}' in line or f'from {forbidden}' in line:
                            violations.append(f'{filepath}:{line_no}: {line.strip()}')

if violations:
    print('[ERROR] Architectural layering violation detected in domain layer:')
    for v in violations:
        print(f'  {v}')
    sys.exit(1)

print('[PASS] Domain layer architectural isolation verified: Zero framework or outer-layer dependencies.')
"
