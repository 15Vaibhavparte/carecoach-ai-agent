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
    properties = event.get('input', {}).get('RequestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])
    print(f"[DEBUG] Extracted properties: {json.dumps(properties, indent=2)}")

    drug_name = None
    for prop in properties:
        if prop.get('name') == 'drug_name':
            drug_name = prop.get('value')

    if not drug_name:
        return build_response(event, {"error": "Drug name not provided."})
    
    # Basic input validation
    if len(drug_name.strip()) < 2:
        return build_response(event, {"error": "Drug name must be at least 2 characters long."})
    
    drug_name = drug_name.strip()

    # Construct the API request URL with proper encoding
    # We search the drug label endpoint for the brand or generic name
    encoded_drug_name = quote(drug_name)
    api_url = f"https://api.fda.gov/drug/label.json?search=(brand_name:\"{encoded_drug_name}\" OR generic_name:\"{encoded_drug_name}\")&limit=1"
    print(f"[DEBUG] API URL: {api_url}")

    try:
        # Call the openFDA API with timeout
        response = requests.get(api_url, timeout=10)
        print(f"[DEBUG] API Response Status: {response.status_code}")
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()
        print(f"[DEBUG] API Response contains {len(data.get('results', []))} results")

        if 'results' in data and len(data['results']) > 0:
            # --- This is the crucial parsing step ---
            # Extract only the most useful information from the complex response
            drug_info = data['results'][0]
            
            # Safe array access to prevent IndexError
            def safe_get_first(data, key, default="Not available."):
                value = data.get(key, [])
                return value[0] if value and len(value) > 0 else default
            
            summary = {
                "brand_name": safe_get_first(drug_info, 'brand_name', "N/A"),
                "generic_name": safe_get_first(drug_info, 'generic_name', "N/A"),
                "purpose": safe_get_first(drug_info, 'purpose'),
                "warnings": safe_get_first(drug_info, 'warnings')
            }
            return build_response(event, summary)
        else:
            return build_response(event, {"error": f"No information found for '{drug_name}'."})

    except requests.exceptions.RequestException as e:
        return build_response(event, {"error": f"API request failed: {str(e)}"})
    except Exception as e:
        return build_response(event, {"error": f"An unexpected error occurred: {str(e)}"})

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