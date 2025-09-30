"""
Vision model client for AWS Bedrock multimodal models.
This module handles all interactions with vision models for medication identification.
"""

import json
import boto3
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from botocore.exceptions import ClientError, BotoCoreError

from models import VisionModelResponse, MedicationIdentification, ImageQuality
from config import config

logger = logging.getLogger(__name__)

class VisionModelClient:
    """
    Client for interacting with AWS Bedrock vision models.
    Handles API calls, response parsing, and error handling.
    """
    
    def __init__(self, model_id: str = None, region: str = None):
        """
        Initialize the vision model client.
        
        Args:
            model_id: Bedrock model ID to use (defaults to config value)
            region: AWS region (defaults to config value)
        """
        self.model_id = model_id or config.BEDROCK_MODEL_ID
        self.region = region or config.AWS_REGION
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.region)
        
        # Prompt templates for different scenarios
        self.prompt_templates = {
            'standard': self._get_standard_prompt(),
            'detailed': self._get_detailed_prompt(),
            'confidence_check': self._get_confidence_check_prompt()
        }
    
    def analyze_image(self, image_data: str, prompt: str = None, media_type: str = "image/jpeg") -> VisionModelResponse:
        """
        Analyze image using the vision model.
        
        Args:
            image_data: Base64 encoded image data
            prompt: Analysis prompt (uses default if not provided)
            media_type: MIME type of the image
            
        Returns:
            VisionModelResponse with analysis results
        """
        start_time = time.time()
        
        try:
            # Use provided prompt or default
            if not prompt:
                prompt = self.prompt_templates['standard']
            
            # Prepare the request for Meta Llama 3.2 11B Instruct (multimodal)
            request_body = {
                "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}\n\n[Image: {media_type} base64 data provided]<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                "max_gen_len": config.MAX_TOKENS,
                "temperature": 0.1,
                "top_p": 0.9,
                "images": [
                    {
                        "format": media_type.split('/')[-1],  # Extract format from media_type
                        "source": {
                            "bytes": image_data
                        }
                    }
                ]
            }
            
            logger.info(f"Calling vision model {self.model_id}")
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            processing_time = time.time() - start_time
            
            # Extract response text from Meta Llama response format
            response_text = response_body.get('generation', '')
            if not response_text:
                # Fallback to other possible response fields
                response_text = response_body.get('outputs', [{}])[0].get('text', '') if response_body.get('outputs') else ''
            
            logger.info(f"Vision model response received in {processing_time:.2f}s")
            
            return VisionModelResponse(
                success=True,
                response_text=response_text,
                usage=response_body.get('prompt_token_count', {}),  # Meta Llama usage format
                processing_time=processing_time
            )
            
        except ClientError as e:
            processing_time = time.time() - start_time
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            logger.error(f"AWS ClientError in vision model call: {error_code} - {error_message}")
            
            return VisionModelResponse(
                success=False,
                error=f"Vision model API error: {error_message}",
                processing_time=processing_time
            )
            
        except BotoCoreError as e:
            processing_time = time.time() - start_time
            logger.error(f"BotoCoreError in vision model call: {str(e)}")
            
            return VisionModelResponse(
                success=False,
                error=f"Vision model connection error: {str(e)}",
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Unexpected error in vision model call: {str(e)}")
            
            return VisionModelResponse(
                success=False,
                error=f"Vision model processing failed: {str(e)}",
                processing_time=processing_time
            )
    
    def analyze_with_confidence_check(self, image_data: str, media_type: str = "image/jpeg") -> VisionModelResponse:
        """
        Analyze image with explicit confidence assessment.
        
        Args:
            image_data: Base64 encoded image data
            media_type: MIME type of the image
            
        Returns:
            VisionModelResponse with confidence-focused analysis
        """
        return self.analyze_image(
            image_data=image_data,
            prompt=self.prompt_templates['confidence_check'],
            media_type=media_type
        )
    
    def analyze_detailed(self, image_data: str, media_type: str = "image/jpeg") -> VisionModelResponse:
        """
        Perform detailed analysis with comprehensive information extraction.
        
        Args:
            image_data: Base64 encoded image data
            media_type: MIME type of the image
            
        Returns:
            VisionModelResponse with detailed analysis
        """
        return self.analyze_image(
            image_data=image_data,
            prompt=self.prompt_templates['detailed'],
            media_type=media_type
        )
    
    def detect_media_type(self, image_data: str) -> str:
        """
        Detect the media type of a base64 encoded image.
        
        Args:
            image_data: Base64 encoded image data
            
        Returns:
            MIME type string (e.g., 'image/jpeg', 'image/png')
        """
        try:
            import base64
            
            # Decode first few bytes to check magic numbers
            decoded_data = base64.b64decode(image_data[:100])  # First ~75 bytes should be enough
            
            # Check for common image format magic numbers
            if decoded_data.startswith(b'\xff\xd8\xff'):
                return "image/jpeg"
            elif decoded_data.startswith(b'\x89PNG\r\n\x1a\n'):
                return "image/png"
            elif decoded_data.startswith(b'RIFF') and b'WEBP' in decoded_data[:20]:
                return "image/webp"
            else:
                # Default to JPEG if unknown
                logger.warning("Unknown image format, defaulting to image/jpeg")
                return "image/jpeg"
                
        except Exception as e:
            logger.warning(f"Failed to detect media type: {str(e)}, defaulting to image/jpeg")
            return "image/jpeg"
    
    def _get_standard_prompt(self) -> str:
        """Get the standard medication identification prompt."""
        return """
Analyze this image of a medication and extract the following information:

1. **Medication Name**: The brand name or generic name visible on the medication or packaging
2. **Dosage**: The strength/dosage information (e.g., 200mg, 500mg, 10mg/5ml)
3. **Confidence Level**: Your confidence in the identification (high, medium, or low)

Instructions:
- If multiple medications are visible, focus on the most prominent one
- If the image is unclear or no medication is identifiable, clearly state this
- Be specific about what you can see and what you cannot determine
- If you can see partial information, mention what is visible

Please format your response clearly with the medication name, dosage, and confidence level.
"""
    
    def _get_detailed_prompt(self) -> str:
        """Get the detailed medication identification prompt."""
        return """
Perform a comprehensive analysis of this medication image and provide detailed information:

1. **Medication Identification**:
   - Brand name (if visible)
   - Generic name (if identifiable)
   - Manufacturer (if visible)

2. **Dosage Information**:
   - Strength/dosage (e.g., 200mg, 500mg)
   - Form (tablet, capsule, liquid, etc.)
   - Quantity visible (if applicable)

3. **Visual Characteristics**:
   - Color and shape
   - Markings, imprints, or numbers
   - Packaging type (bottle, blister pack, etc.)

4. **Image Quality Assessment**:
   - Clarity of the image (good, fair, poor)
   - Lighting conditions
   - Any factors affecting identification

5. **Confidence Assessment**:
   - Overall confidence level (high, medium, low)
   - Specific aspects you're confident about
   - Areas of uncertainty

Please be thorough and specific in your analysis.
"""
    
    def _get_confidence_check_prompt(self) -> str:
        """Get the confidence-focused prompt."""
        return """
Analyze this medication image with a focus on confidence assessment:

1. **What can you identify with HIGH confidence?**
   - Clearly visible text, numbers, or markings
   - Obvious visual characteristics

2. **What can you identify with MEDIUM confidence?**
   - Partially visible or somewhat unclear elements
   - Reasonable inferences based on visible features

3. **What is UNCERTAIN or LOW confidence?**
   - Unclear, blurry, or partially obscured elements
   - Assumptions that cannot be verified from the image

4. **Overall Assessment**:
   - Primary medication name (if identifiable)
   - Dosage information (if visible)
   - Overall confidence level for the identification

Please be honest about limitations and uncertainties in the identification.
"""

class MedicationExtractor:
    """
    Utility class for extracting structured medication information from vision model responses.
    """
    
    def __init__(self):
        """Initialize the medication extractor."""
        self.confidence_keywords = {
            'high': ['clearly visible', 'confident', 'high confidence', 'certain', 'definite', 'obvious'],
            'medium': ['likely', 'appears to be', 'moderate confidence', 'probably', 'seems to be'],
            'low': ['unclear', 'difficult', 'low confidence', 'blurry', 'uncertain', 'cannot determine']
        }
    
    def extract_medication_info(self, vision_response: str) -> MedicationIdentification:
        """
        Parse vision model response to extract structured medication information.
        
        Args:
            vision_response: Raw text response from vision model
            
        Returns:
            MedicationIdentification with extracted information
        """
        try:
            # Initialize default values
            medication_name = ""
            dosage = ""
            confidence = 0.0
            image_quality = ImageQuality.UNKNOWN.value
            alternative_names = []
            
            response_lower = vision_response.lower()
            
            # Extract confidence level
            confidence = self._extract_confidence(response_lower)
            
            # Determine image quality based on confidence and keywords
            image_quality = self._determine_image_quality(response_lower, confidence)
            
            # Extract medication name
            medication_name = self._extract_medication_name(vision_response)
            
            # Extract dosage information
            dosage = self._extract_dosage(vision_response)
            
            # Extract alternative names if mentioned
            alternative_names = self._extract_alternative_names(vision_response)
            
            logger.info(f"Extracted medication: {medication_name}, dosage: {dosage}, confidence: {confidence}")
            
            return MedicationIdentification(
                medication_name=medication_name,
                dosage=dosage,
                confidence=confidence,
                alternative_names=alternative_names,
                image_quality=image_quality,
                raw_response=vision_response
            )
            
        except Exception as e:
            logger.error(f"Failed to extract medication info: {str(e)}")
            return MedicationIdentification(
                medication_name="",
                dosage="",
                confidence=0.0,
                image_quality=ImageQuality.POOR.value,
                raw_response=vision_response
            )
    
    def _extract_confidence(self, response_lower: str) -> float:
        """Extract confidence score from response text."""
        import re
        
        # Look for percentage confidence first (most specific)
        percentage_pattern = r'(\d+)%\s*confident'
        match = re.search(percentage_pattern, response_lower)
        if match:
            percentage = int(match.group(1))
            return min(percentage / 100.0, 1.0)
        
        percentage_pattern = r'(\d+)%\s*confidence'
        match = re.search(percentage_pattern, response_lower)
        if match:
            percentage = int(match.group(1))
            return min(percentage / 100.0, 1.0)
        
        # Look for explicit confidence levels
        confidence_pattern = r'(high|medium|moderate|low)\s+confidence'
        match = re.search(confidence_pattern, response_lower)
        if match:
            level = match.group(1)
            if level == 'high':
                return 0.9
            elif level in ['medium', 'moderate']:
                return 0.7
            elif level == 'low':
                return 0.3
        
        # Check for keyword-based confidence (order matters - check low confidence first)
        if any(keyword in response_lower for keyword in self.confidence_keywords['low']):
            return 0.3
        elif any(keyword in response_lower for keyword in self.confidence_keywords['high']):
            return 0.9
        elif any(keyword in response_lower for keyword in self.confidence_keywords['medium']):
            return 0.7
        
        # Default to medium confidence if no clear indicators
        return 0.5
    
    def _determine_image_quality(self, response_lower: str, confidence: float) -> str:
        """Determine image quality based on response content and confidence."""
        quality_indicators = {
            'poor': ['poor quality', 'difficult to read', 'low resolution', 'blurry', 'unclear', 'very blurry', 'insufficient lighting'],
            'fair': ['fair quality', 'somewhat clear', 'adequate', 'partially visible', 'some text is readable'],
            'good': ['good quality', 'clear', 'sharp', 'well-lit', 'clearly visible']
        }
        
        # Check for explicit quality mentions (check poor first, then fair, then good)
        for quality, keywords in quality_indicators.items():
            if any(keyword in response_lower for keyword in keywords):
                return quality
        
        # Infer quality from confidence level if no explicit mentions
        if confidence >= 0.8:
            return ImageQuality.GOOD.value
        elif confidence >= 0.5:
            return ImageQuality.FAIR.value
        else:
            return ImageQuality.POOR.value
    
    def _extract_medication_name(self, response: str) -> str:
        """Extract medication name from response."""
        import re
        
        # Common patterns for medication names - prioritize brand name when available
        patterns = [
            r'medication name[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'brand name[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'drug name[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'generic name[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'identified as[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'appears to be[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'this is[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)',
            r'likely[:\s]+([A-Za-z0-9\']+(?:\s+[A-Za-z0-9\']+)*?)(?:\s*\n|\s*$|\s*\.|\s*,)'
        ]
        
        # Try to find the best medication name by checking all patterns
        found_names = []
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the extracted name
                name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
                # Clean up the name but preserve important multi-word names
                # Remove obvious non-medication words and stop at certain phrases
                stop_words = ['tablet', 'capsule', 'liquid', 'with', 'and', 'the', 'per', 'dose', 'form', 'coating', 'other', 'ingredients']
                stop_phrases = ['with', 'and other', 'other ingredients', 'coating']
                
                # Check for stop phrases first
                for phrase in stop_phrases:
                    if phrase in name.lower():
                        name = name[:name.lower().index(phrase)].strip()
                        break
                
                # Remove common descriptive phrases that follow medication names
                descriptive_phrases = ['based', 'visible', 'packaging', 'colors', 'partial', 'text', 'appears', 'store', 'brand']
                words = name.split()
                filtered_words = []
                
                for word in words:
                    if word.lower() in descriptive_phrases:
                        break
                    filtered_words.append(word)
                
                if filtered_words:
                    name = ' '.join(filtered_words)
                
                name_words = []
                for word in name.split():
                    # Stop at dosage information
                    if any(unit in word.lower() for unit in ['mg', 'mcg', 'ml', 'g']) and any(char.isdigit() for char in word):
                        break
                    elif word.lower() not in stop_words:
                        name_words.append(word)
                name = ' '.join(name_words)
                
                # Check if this is a valid medication name
                invalid_names = ['unknown', 'unclear', 'not visible', 'medication', 'drug', 'not clearly', 'not', 'clearly', 'a medication']
                if len(name) > 1 and name.lower() not in invalid_names:
                    found_names.append((pattern, name))
        
        # Return the best name found - prioritize by pattern order but skip invalid ones
        for pattern, name in found_names:
            return name
        
        return ""
    
    def _extract_dosage(self, response: str) -> str:
        """Extract dosage information from response."""
        import re
        
        # Common dosage patterns - more comprehensive
        patterns = [
            # Complex dosage patterns (mg/ml, mg/5ml, etc.) - most specific first
            r'([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|mcg|units?)/[0-9]*(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))',
            r'dosage[:\s]+([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|mcg|units?)/[0-9]*(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))',
            r'strength[:\s]+([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|mcg|units?)/[0-9]*(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))',
            
            # Simple dosage patterns
            r'dosage[:\s]+([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))',
            r'strength[:\s]+([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))',
            r'dose[:\s]+([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))',
            
            # General number + unit patterns (less specific, so last)
            r'([0-9]+(?:\.[0-9]+)?\s*(?:mg|g|ml|mcg|units?))'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Return the first reasonable dosage found
                for match in matches:
                    if isinstance(match, str) and len(match.strip()) > 0:
                        return match.strip()
        
        return ""
    
    def _extract_alternative_names(self, response: str) -> List[str]:
        """Extract alternative medication names if mentioned."""
        import re
        
        alternative_names = []
        
        # Look for patterns indicating alternative names - more specific patterns
        patterns = [
            r'also known as[:\s]+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*?)(?:\s|$|\n)',
            r'generic name[:\s]+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*?)(?:\s|$|\n)',
            r'brand name[:\s]+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*?)(?:\s|$|\n)',
            r'alternative[:\s]+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*?)(?:\s|$|\n)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)
                # Remove common non-medication words
                stop_words = ['dosage', 'strength', 'mg', 'tablet', 'capsule', 'liquid', 'with', 'and', 'the']
                name_words = [word for word in name.split() if word.lower() not in stop_words]
                name = ' '.join(name_words)
                
                if len(name) > 1 and name.lower() not in ['unknown', 'unclear', 'not visible', 'medication', 'drug']:
                    alternative_names.append(name)
        
        return list(set(alternative_names))  # Remove duplicates