# Test Data and Fixtures

This directory contains comprehensive test data, fixtures, mock responses, and test utilities for the medication image identification system.

## ✅ Task 9.2 Completion Status

**COMPLETED**: Mock responses and test utilities have been fully implemented with comprehensive coverage.

## Overview

The test data includes:
- **Sample Images**: Base64-encoded test images with known expected results
- **Test Cases**: Structured test cases with validation criteria
- **Fixtures**: Utilities and helpers for testing
- **Edge Cases**: Problematic scenarios for error handling validation

## Files

### `sample_images.py`
Contains programmatically generated test images encoded as base64 strings:
- **Clear medication images**: High-quality images with expected successful identification
- **Edge case images**: Blurry, empty, or problematic images for error testing
- **Format variations**: Different image formats (JPEG, PNG) for format validation

### `test_cases.py`
Structured test cases with:
- Expected results for each test image
- Validation criteria and success metrics
- Test scenarios grouped by functionality
- Performance test case definitions

### `fixtures.py`
Test utilities and fixtures including:
- `TestFixtures` class for centralized test data access
- Response validation utilities
- Test request generators
- Data export/import functions

### `mock_responses.py` ✅ **NEW - COMPLETED**
Comprehensive mock responses for testing:
- **Vision model responses**: Realistic responses for all test scenarios (Advil, Tylenol, Ibuprofen, etc.)
- **DrugInfoTool responses**: Complete drug information with proper formatting
- **Error responses**: All error scenarios with user-friendly messages
- **MockResponseGenerator**: Dynamic response generation utilities
- **ResponseValidator**: Format and content validation utilities

### `test_utilities.py` ✅ **NEW - COMPLETED**
Advanced testing utilities and framework:
- **TestExecutor**: Run individual and batch test cases with validation
- **MockManager**: Manage mock patches and response history
- **PerformanceTestRunner**: Concurrent and load testing capabilities
- **TestDataGenerator**: Generate edge cases, boundary tests, and stress data
- **ResponseValidator**: Comprehensive result validation framework

### `scenario_generator.py` ✅ **NEW - COMPLETED**
Scenario-based test generation:
- **Happy path scenarios**: Successful identification workflows
- **Error handling scenarios**: Failure cases and edge conditions
- **Performance scenarios**: Load and concurrent testing definitions
- **Integration scenarios**: End-to-end workflow validation
- **Security scenarios**: Input validation and privacy testing
- **User experience scenarios**: Error messaging and feedback validation

### `comprehensive_test_runner.py` ✅ **NEW - COMPLETED**
Main test orchestration framework:
- **Full test suite execution**: Runs all test categories automatically
- **Performance testing integration**: Load and concurrent test execution
- **Mock handler creation**: Built-in mock for testing without real implementation
- **Comprehensive reporting**: Detailed results with recommendations
- **Test session management**: History tracking and result export

## Usage Examples

### Basic Test Image Access
```python
from test_data.fixtures import fixtures, BASE64_TEST_IMAGES

# Get a specific test image
advil_image = fixtures.get_base64_image('advil_clear')

# Get all base64 images
all_images = BASE64_TEST_IMAGES
```

### Creating Test Requests
```python
from test_data.fixtures import create_test_request

# Create a Bedrock Agent format request
request = create_test_request('advil_clear', 'bedrock_agent_format')

# Create multiple requests for batch testing
requests = create_batch_test_requests(['advil_clear', 'tylenol_clear'])
```

### Response Validation
```python
from test_data.fixtures import ResponseValidator, EXPECTED_RESULTS

validator = ResponseValidator()
expected = EXPECTED_RESULTS['advil_clear']

# Validate successful response
result = validator.validate_success_response(api_response, expected)

# Validate error response  
result = validator.validate_error_response(error_response, expected)
```

### Test Scenarios
```python
from test_data.test_cases import get_test_scenario

# Get happy path test cases
happy_path = get_test_scenario('happy_path')
test_cases = happy_path['test_cases']

# Get edge case scenarios
edge_cases = get_test_scenario('edge_cases')
```

## Test Categories

### Clear Single Medication
- `advil_clear`: Clear Advil 200mg image
- `tylenol_clear`: Clear Tylenol 500mg image  
- `ibuprofen_generic`: Generic ibuprofen image

### Edge Cases
- `blurry_medication`: Poor quality/blurry image
- `multiple_medications`: Multiple medications in one image
- `no_medication`: Image with no medication present
- `empty_image`: Blank/empty image
- `partial_text`: Partially visible medication text

### Format Validation
- `jpeg_high_quality`: High-quality JPEG format
- `png_transparent`: PNG format image

## Expected Results Structure

Each test image has associated expected results:
```python
{
    "expected_name": "Advil",           # Expected medication name
    "expected_dosage": "200mg",         # Expected dosage
    "expected_confidence": 0.9,         # Expected confidence score
    "expected_error": None,             # Expected error type (if any)
    "test_category": "clear_single_medication",
    "description": "Clear image of Advil 200mg medication"
}
```

## Test Scenarios

### Happy Path
Tests successful identification of clear medication images:
- Minimum 90% success rate expected
- Average confidence > 0.8
- All required fields present

### Edge Cases  
Tests error handling for problematic images:
- Should fail gracefully
- Should provide helpful error messages
- Should suggest alternatives

### Format Validation
Tests support for different image formats:
- JPEG, PNG, WebP support
- Consistent results across formats

### Performance Testing
Tests system performance and limits:
- Large image processing
- Concurrent request handling
- Memory efficiency

## Integration with Tests

The test data integrates with the existing test suite:

```python
# In your test files
from test_data.fixtures import fixtures, create_test_request
from test_data.test_cases import create_test_cases

class TestMedicationIdentification:
    def test_clear_medications(self):
        for case in fixtures.get_successful_test_cases():
            request = create_test_request(case['name'])
            # Test with request...
    
    def test_error_handling(self):
        for case in fixtures.get_error_test_cases():
            request = create_test_request(case['name'])
            # Test error scenarios...
```

## Extending Test Data

To add new test images:

1. Add image data to `sample_images.py`:
```python
"new_medication": {
    "base64": create_test_image("NEW MED\n100mg"),
    "expected_name": "New Med",
    "expected_dosage": "100mg",
    "expected_confidence": 0.8,
    "test_category": "clear_single_medication"
}
```

2. Test cases are automatically generated from image data
3. Update scenarios in `test_cases.py` if needed

## Requirements Coverage

This test data addresses the following requirements:
- **2.3**: Multiple medication handling
- **2.4**: Clear medication identification  
- **2.5**: Confidence scoring
- **6.1**: Error handling for no medication detected
- **6.2**: Poor image quality handling

## Notes

- All test images are programmatically generated to avoid copyright issues
- Base64 encoding allows easy integration with API testing
- Validation utilities ensure consistent test result evaluation
- Performance test cases help validate system limits and efficiency

## ✅ Task 9.2 Implementation Summary

### Mock Vision Model Responses
- **8 comprehensive scenarios**: Clear medications, blurry images, no medication, multiple items
- **Realistic response format**: Matches actual vision model API structure
- **Confidence scoring**: Appropriate confidence levels for each scenario
- **Error handling**: Proper error responses with helpful suggestions

### Mock DrugInfoTool Responses  
- **5 medication responses**: Advil, Tylenol, Ibuprofen, Aspirin, Metformin
- **Complete drug information**: Brand names, generic names, warnings, directions
- **Error scenarios**: Medication not found, API errors, rate limiting
- **Proper status codes**: 200, 404, 429, 500 responses

### Test Utilities Framework
- **TestExecutor**: Runs tests with comprehensive validation
- **MockManager**: Manages response history and patches
- **PerformanceTestRunner**: Concurrent (up to 10) and load testing
- **TestDataGenerator**: Edge cases, boundaries, stress tests, regression tests

### Scenario Coverage
- **Happy Path**: 3 scenarios covering successful identifications
- **Error Handling**: 4 scenarios covering all failure modes
- **Edge Cases**: 3 scenarios for boundary conditions
- **Performance**: 2 scenarios for load and concurrent testing
- **Integration**: 2 scenarios for end-to-end workflows
- **Security**: 2 scenarios for input validation and privacy
- **User Experience**: 2 scenarios for error messaging

### Comprehensive Test Runner
- **Full automation**: Single command runs all test categories
- **Mock integration**: Built-in mock handler for testing framework
- **Performance metrics**: Response times, throughput, success rates
- **Detailed reporting**: Results with actionable recommendations
- **Export capabilities**: JSON export of all test results

## Quick Start with New Components

### Run Complete Test Suite
```python
from test_data.comprehensive_test_runner import test_runner

# Run full test suite (uses built-in mock if no handler provided)
results = test_runner.run_full_test_suite()
print(f"Success Rate: {results['overall_summary']['success_rate']:.2%}")

# Run with your actual handler
results = test_runner.run_full_test_suite(your_lambda_handler)
```

### Use Mock Responses
```python
from test_data.mock_responses import get_mock_response, MockResponseGenerator

# Get predefined mock responses
vision_response = get_mock_response('vision', 'advil_clear')
drug_response = get_mock_response('drug_info', 'advil')

# Generate custom responses
generator = MockResponseGenerator()
custom_response = generator.generate_combined_response(
    medication_name='Custom Med',
    confidence=0.85,
    dosage='100mg'
)
```

### Performance Testing
```python
from test_data.test_utilities import PerformanceTestRunner

runner = PerformanceTestRunner()

# Test concurrent handling (5 simultaneous requests)
concurrent_results = runner.run_concurrent_test(
    your_handler, test_data, max_concurrent=5
)

# Load test (2 requests/second for 30 seconds)
load_results = runner.run_load_test(
    your_handler, duration_seconds=30, requests_per_second=2
)
```

### Scenario-Based Testing
```python
from test_data.scenario_generator import scenario_generator

# Get specific scenario types
happy_scenarios = scenario_generator.get_scenario('happy_path')
error_scenarios = scenario_generator.get_scenario('error_handling')

# Generate complete test suite from scenarios
test_suite = scenario_generator.generate_test_suite_from_scenarios()
```

## Validation Coverage

The implemented utilities provide comprehensive validation for:

### Response Format Validation ✅
- Vision model response structure
- DrugInfoTool response format
- Combined response validation
- Error response format checking

### Content Validation ✅
- Medication name accuracy
- Confidence score ranges (0.0 to 1.0)
- Required field presence
- Drug information completeness

### Performance Validation ✅
- Response time thresholds
- Concurrent request handling
- Memory usage efficiency
- Throughput measurements

### Error Handling Validation ✅
- Proper error message format
- User-friendly language
- Actionable suggestions
- Appropriate error codes

### Integration Validation ✅
- End-to-end workflow testing
- Service interaction validation
- Error propagation testing
- Data consistency checking

## Requirements Addressed

This implementation addresses all requirements from task 9.2:

- ✅ **Write mock vision model responses for testing** - Complete with 8 scenarios
- ✅ **Create mock DrugInfoTool responses** - 5 medications + error scenarios  
- ✅ **Implement test utilities for response validation** - Comprehensive validation framework
- ✅ **Write test data generators for various scenarios** - Edge cases, boundaries, stress tests

**Requirements Coverage**: 2.1, 2.2, 3.1, 3.2, 6.1, 6.2, 6.3, 6.4, 6.5 ✅