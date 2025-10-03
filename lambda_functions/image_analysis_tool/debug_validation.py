#!/usr/bin/env python3
"""Debug script for validation"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("Starting debug validation...")

try:
    print("Importing run_end_to_end_validation...")
    import run_end_to_end_validation
    print("Import successful")
    
    print("Available functions:", [name for name in dir(run_end_to_end_validation) if not name.startswith('_')])
    
    print("Calling run_end_to_end_validation function...")
    result = run_end_to_end_validation.run_end_to_end_validation()
    print(f"Function returned: {result}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("Debug validation complete.")