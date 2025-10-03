#!/usr/bin/env python3
"""Test script to check imports"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    from app import lambda_handler
    print("✓ app module imported successfully")
except Exception as e:
    print(f"❌ app import failed: {e}")

try:
    from models import ImageAnalysisRequest
    print("✓ models module imported successfully")
except Exception as e:
    print(f"❌ models import failed: {e}")

try:
    from config import config
    print("✓ config module imported successfully")
except Exception as e:
    print(f"❌ config import failed: {e}")

try:
    from test_data.fixtures import TestFixtures
    print("✓ test_data.fixtures imported successfully")
except Exception as e:
    print(f"❌ test_data.fixtures import failed: {e}")

print("Import testing complete.")