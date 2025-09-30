"""
Data models and interfaces for image processing and medication identification.
This module defines the core data structures used throughout the image analysis tool.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum

class ImageQuality(Enum):
    """Enumeration for image quality assessment"""
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"

class ProcessingStatus(Enum):
    """Enumeration for processing status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class ImageAnalysisRequest:
    """
    Data model for image analysis requests.
    
    Attributes:
        image_data: Base64 encoded image string
        prompt: Analysis prompt for the vision model
        max_file_size: Maximum allowed file size in bytes
        allowed_formats: List of supported image formats
    """
    image_data: str
    prompt: str = "Identify the medication name and dosage in this image"
    max_file_size: int = 10 * 1024 * 1024  # 10MB default
    allowed_formats: List[str] = None
    
    def __post_init__(self):
        if self.allowed_formats is None:
            self.allowed_formats = ['jpeg', 'jpg', 'png', 'webp']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

@dataclass
class ImageValidationResult:
    """
    Data model for image validation results.
    
    Attributes:
        valid: Whether the image passed validation
        error: Error message if validation failed
        size: Size of the image in bytes
        format_detected: Detected image format
    """
    valid: bool
    error: str = ""
    size: int = 0
    format_detected: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

@dataclass
class MedicationIdentification:
    """
    Data model for medication identification results.
    
    Attributes:
        medication_name: Identified medication name
        dosage: Identified dosage information
        confidence: Confidence score (0.0 to 1.0)
        alternative_names: List of alternative medication names
        image_quality: Assessment of image quality
        raw_response: Raw response from vision model
    """
    medication_name: str
    dosage: str = ""
    confidence: float = 0.0
    alternative_names: List[str] = None
    image_quality: str = ImageQuality.UNKNOWN.value
    raw_response: str = ""
    
    def __post_init__(self):
        if self.alternative_names is None:
            self.alternative_names = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if identification has high confidence"""
        return self.confidence >= threshold
    
    def has_valid_identification(self) -> bool:
        """Check if medication was successfully identified"""
        return bool(self.medication_name and self.medication_name.lower() not in ['unknown', 'not found', ''])

@dataclass
class VisionModelResponse:
    """
    Data model for vision model API responses.
    
    Attributes:
        success: Whether the API call was successful
        response_text: Text response from the model
        usage: Token usage information
        error: Error message if call failed
        processing_time: Time taken for processing
    """
    success: bool
    response_text: str = ""
    usage: Dict[str, Any] = None
    error: str = ""
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

@dataclass
class DrugInfoResult:
    """
    Data model for drug information retrieval results.
    
    Attributes:
        success: Whether drug info was successfully retrieved
        data: Drug information data
        error: Error message if retrieval failed
        source: Source of the drug information
    """
    success: bool
    data: Dict[str, Any] = None
    error: str = ""
    source: str = "DrugInfoTool"
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)

@dataclass
class CombinedResponse:
    """
    Data model for the complete response combining vision and drug info.
    
    Attributes:
        identification: Medication identification results
        drug_info: Detailed drug information
        processing_time: Total processing time
        success: Overall success status
        error_message: Error message if processing failed
        metadata: Additional metadata about the processing
    """
    identification: MedicationIdentification
    drug_info: Dict[str, Any] = None
    processing_time: float = 0.0
    success: bool = True
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.drug_info is None:
            self.drug_info = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        result = asdict(self)
        # Convert nested dataclass to dict
        if isinstance(self.identification, MedicationIdentification):
            result['identification'] = self.identification.to_dict()
        return result
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the response"""
        self.metadata[key] = value

# Interface definitions for extensibility

class ImageProcessor:
    """Interface for image processing operations"""
    
    def validate_image(self, image_data: str, max_size: int, allowed_formats: List[str]) -> ImageValidationResult:
        """Validate image format and size"""
        raise NotImplementedError
    
    def preprocess_image(self, image_data: str) -> str:
        """Preprocess image for optimal vision model input"""
        raise NotImplementedError

class VisionModelClient:
    """Interface for vision model interactions"""
    
    def analyze_image(self, image_data: str, prompt: str) -> VisionModelResponse:
        """Analyze image using vision model"""
        raise NotImplementedError
    
    def extract_medication_info(self, response_text: str) -> MedicationIdentification:
        """Extract medication information from model response"""
        raise NotImplementedError

class DrugInfoClient:
    """Interface for drug information retrieval"""
    
    def get_drug_info(self, drug_name: str) -> DrugInfoResult:
        """Retrieve detailed drug information"""
        raise NotImplementedError

# Error classes for specific error handling

class ImageAnalysisError(Exception):
    """Base exception for image analysis errors"""
    pass

class ImageValidationError(ImageAnalysisError):
    """Exception for image validation failures"""
    pass

class VisionModelError(ImageAnalysisError):
    """Exception for vision model processing failures"""
    pass

class DrugInfoError(ImageAnalysisError):
    """Exception for drug information retrieval failures"""
    pass