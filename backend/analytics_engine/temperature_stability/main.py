# main.py
# Standalone entry point — run from anywhere:
#   python backend/analytics_engine/temperature_stability/main.py
# or from within the temperature_stability/ directory:
#   python main.py

import sys
import os

if __name__ == "__main__":
    # Resolve the backend/ root (two levels up from this file) and add it to
    # sys.path so the package import below works regardless of where the script
    # is launched from.
    backend_root = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    from analytics_engine.temperature_stability.job_runner import start_scheduler
    start_scheduler()
