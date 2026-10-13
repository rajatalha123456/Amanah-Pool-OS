"""Runs the copilot's pytest-style test functions without installing pytest (audit rule: no new dependencies).
Run from shariah-policy-copilot/backend:  venv/Scripts/python.exe ../../audit_reports/scripts/run_copilot_tests.py
"""
import importlib.util
import inspect
import pathlib
import sys
import traceback

sys.path.insert(0, str(pathlib.Path.cwd()))
passed = failed = 0
for path in sorted(pathlib.Path("tests").glob("test_*.py")):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        print(f"IMPORT ERROR {path}\n{traceback.format_exc()}")
        failed += 1
        continue
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("test_") or inspect.signature(fn).parameters:
            if name.startswith("test_"):
                print(f"SKIPPED {path.name}::{name} (needs pytest fixtures)")
            continue
        try:
            fn()
            passed += 1
            print(f"ok      {path.name}::{name}")
        except Exception:
            failed += 1
            print(f"FAILED  {path.name}::{name}\n{traceback.format_exc()}")
print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
