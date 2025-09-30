"""
Image Analysis Tool for Medication Identification

This package provides functionality to analyze images of medications using computer vision
and integrate with existing drug information services to provide comprehensive medication data.

Main components:
- app.py: Main Lambda handler and core processing logic
- models.py: Data models and interfaces
- config.py: Configuration settings and environment management

Usage:
    The main entry point is the lambda_handler function in app.py, which follows
    the Bedrock Agent pattern for AWS Lambda integration.
"""

from .models import (
    ImageAnalysisRequest,
    MedicationIdentification,
    CombinedResponse,
    VisionModelResponse,
    DrugInfoResult,
    ImageValidationResult,
    ImageQuality,
    ProcessingStatus,
    ImageAnalysisError,
    ImageValidationError,
    VisionModelError,
    DrugInfoError
)

from .config import Config, config

__version__ = "1.0.0"
__author__ = "CareCoach Development Team"

# Package-level exports
__all__ = [
    # Data models
    'ImageAnalysisRequest',
    'MedicationIdentification', 
    'CombinedResponse',
    'VisionModelResponse',
    'DrugInfoResult',
    'ImageValidationResult',
    
    # Enums
    'ImageQuality',
    'ProcessingStatus',
    
    # Exceptions
    'ImageAnalysisError',
    'ImageValidationError',
    'VisionModelError',
    'DrugInfoError',
    
    # Configuration
    'Config',
    'config'
]