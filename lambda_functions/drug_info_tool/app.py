import json
import requests  # The library for making HTTP requests
from urllib.parse import quote

def lambda_handler(event, context):
    """
    This function is called by the Bedrock Agent.
    It takes a drug name, searches the openFDA API, and returns a summary.
    """
    # Debug logging - Log the incoming event for troubleshooting
    print(f"[DEBUG] Incoming event: {json.dumps(event, indent=2)}")
    print(f"[DEBUG] Context: {context}")
    
    # Extract the drug_name parameter from the agent's input
    # Try multiple possible formats that Bedrock Agent might use
    drug_name = None
    
    # Format 1: New Bedrock Agent format
    properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    print(f"[DEBUG] Format 1 - properties: {json.dumps(properties, indent=2)}")
    
    for prop in properties:
        if prop.get('name') == 'drug_name':
            drug_name = prop.get('value')
            print(f"[DEBUG] Found drug_name in Format 1: {drug_name}")
            break
    
    # Format 2: Direct parameters array
    if not drug_name:
        parameters = event.get('parameters', [])
        print(f"[DEBUG] Format 2 - parameters: {json.dumps(parameters, indent=2)}")
        for param in parameters:
            if param.get('name') == 'drug_name':
                drug_name = param.get('value')
                print(f"[DEBUG] Found drug_name in Format 2: {drug_name}")
                break
    
    # Format 3: Direct in requestBody
    if not drug_name:
        request_body = event.get('requestBody', {})
        print(f"[DEBUG] Format 3 - requestBody: {json.dumps(request_body, indent=2)}")
        drug_name = request_body.get('drug_name')
        if drug_name:
            print(f"[DEBUG] Found drug_name in Format 3: {drug_name}")
    
    # Format 4: Direct in event root
    if not drug_name:
        drug_name = event.get('drug_name')
        if drug_name:
            print(f"[DEBUG] Found drug_name in Format 4: {drug_name}")
    
    # Format 5: In inputText (for some Bedrock configurations)
    if not drug_name:
        input_text = event.get('inputText', '')
        print(f"[DEBUG] Format 5 - inputText: {input_text}")
        # Simple extraction from natural language
        if 'advil' in input_text.lower():
            drug_name = 'Advil'
            print(f"[DEBUG] Extracted drug_name from inputText: {drug_name}")
        elif 'tylenol' in input_text.lower():
            drug_name = 'Tylenol'
            print(f"[DEBUG] Extracted drug_name from inputText: {drug_name}")
    
    # Format 6: Bedrock Agent function calling format
    if not drug_name:
        function_input = event.get('input', {})
        if isinstance(function_input, dict):
            drug_name = function_input.get('drug_name')
            if drug_name:
                print(f"[DEBUG] Found drug_name in Format 6: {drug_name}")
    
    print(f"[DEBUG] Final drug_name: {drug_name}")

    # If still no drug_name found, try to extract from the entire event as a last resort
    if not drug_name:
        # Look for common drug names in the entire event structure
        event_str = json.dumps(event).lower()
        common_drugs = ['advil', 'tylenol', 'aspirin', 'ibuprofen', 'acetaminophen', 'motrin', 'aleve']
        
        for drug in common_drugs:
            if drug in event_str:
                drug_name = drug.capitalize()
                print(f"[DEBUG] Extracted '{drug_name}' from event content")
                break
    
    if not drug_name:
        print("[DEBUG] No drug name found in any format")
        return build_response(event, {
            "error": "I need to know the drug name to provide the warnings. Please provide the drug name.",
            "debug_info": "No drug_name parameter found in the request"
        })
    
    # Basic input validation
    if len(drug_name.strip()) < 2:
        return build_response(event, {"error": "Drug name must be at least 2 characters long."})
    
    drug_name = drug_name.strip()

    # Use the correct FDA API format
    api_url = f"https://api.fda.gov/drug/label.json?search=(openfda.brand_name:{drug_name.lower()} OR openfda.generic_name:{drug_name.lower()})&limit=1"
    print(f"[DEBUG] API URL: {api_url}")

    try:
        response = requests.get(api_url, timeout=10)
        print(f"[DEBUG] API Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        print(f"[DEBUG] API Response contains {len(data.get('results', []))} results")
    except requests.exceptions.RequestException as e:
        return build_response(event, {"error": f"API request failed: {str(e)}"})

    # Check if we got any results from any strategy
    if data and 'results' in data and len(data['results']) > 0:
            # --- This is the crucial parsing step ---
            # Extract only the most useful information from the complex response
            drug_info = data['results'][0]
            
            # Safe array access to prevent IndexError
            def safe_get_first(data, key, default="Not available."):
                value = data.get(key, [])
                return value[0] if value and len(value) > 0 else default
            
            # Safe access for nested OpenFDA data
            def safe_get_openfda(data, key, default="N/A"):
                openfda = data.get('openfda', {})
                value = openfda.get(key, [])
                return value[0] if value and len(value) > 0 else default
            
            print(f"[DEBUG] Drug info keys: {list(drug_info.keys())}")
            if 'openfda' in drug_info:
                print(f"[DEBUG] OpenFDA keys: {list(drug_info['openfda'].keys())}")
            
            # Check if the user specifically asked for warnings
            event_str = json.dumps(event).lower()
            asking_for_warnings = 'warning' in event_str
            
            # Extract drug information using correct FDA API structure
            summary = {
                "brand_name": safe_get_openfda(drug_info, 'brand_name'),
                "generic_name": safe_get_openfda(drug_info, 'generic_name'),
                "purpose": safe_get_first(drug_info, 'purpose'),
                "warnings": safe_get_first(drug_info, 'warnings'),
                "indications_and_usage": safe_get_first(drug_info, 'indications_and_usage')
            }
            
            # If specifically asking for warnings, provide a focused response
            if asking_for_warnings:
                warnings = summary['warnings']
                if warnings != "Not available.":
                    drug_name_display = summary['brand_name']
                    if summary['generic_name'] != "N/A" and summary['generic_name'] != summary['brand_name']:
                        drug_name_display += f" ({summary['generic_name']})"
                    
                    return build_response(event, {
                        "response": f"Here are the warnings for {drug_name_display}:",
                        "warnings": warnings
                    })
            
            return build_response(event, summary)
    else:
        # No results found with any strategy
        return build_response(event, {
            "error": f"No information found for '{drug_name}'. This could be because the drug is not in the FDA database or it's spelled differently.",
            "suggestion": "Try using the generic name instead (e.g., 'ibuprofen' instead of 'Advil')"
        })

def get_alternative_search(drug_name):
    """Get alternative search terms for common drug names"""
    drug_mappings = {
        'advil': '(openfda.brand_name:advil OR openfda.generic_name:ibuprofen)',
        'tylenol': '(openfda.brand_name:tylenol OR openfda.generic_name:acetaminophen)',
        'motrin': '(openfda.brand_name:motrin OR openfda.generic_name:ibuprofen)',
        'aleve': '(openfda.brand_name:aleve OR openfda.generic_name:naproxen)',
        'aspirin': '(openfda.brand_name:aspirin OR openfda.generic_name:aspirin)',
        'ibuprofen': '(openfda.brand_name:advil OR openfda.brand_name:motrin OR openfda.generic_name:ibuprofen)',
        'acetaminophen': '(openfda.brand_name:tylenol OR openfda.generic_name:acetaminophen)',
        'naproxen': '(openfda.brand_name:aleve OR openfda.generic_name:naproxen)'
    }
    
    return drug_mappings.get(drug_name.lower())

def build_response(event, body):
    """Helper function to build the standard Bedrock Agent response."""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'apiPath': event.get('apiPath'),
            'httpMethod': event.get('httpMethod'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(body)
                }
            }
        }
    }