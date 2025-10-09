# lambda_functions/drug_info_tool/app.py
import json
import requests

def lambda_handler(event, context):
    # The agent sends parameters in a list. We find the one named 'drug_name'.
    parameters = event.get('parameters', [])
    drug_name = None
    for param in parameters:
        if param.get('name') == 'drug_name':
            drug_name = param.get('value')
            break

    if not drug_name:
        return build_response(event, {"error": "Could not find drug_name in the agent's request."})

    # Construct the API request URL using the corrected field names
    api_url = f"https://api.fda.gov/drug/label.json?search=(openfda.brand_name:\"{drug_name}\" OR openfda.generic_name:\"{drug_name}\")&limit=1"

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'results' in data and len(data['results']) > 0:
            drug_info = data['results'][0]
            openfda_data = drug_info.get('openfda', {})
            summary = {
                "brand_name": openfda_data.get('brand_name', ["N/A"])[0],
                "generic_name": openfda_data.get('generic_name', ["N/A"])[0],
                "purpose": drug_info.get('purpose', ["Not available."])[0],
                "warnings": drug_info.get('warnings', ["Not available."])[0]
            }
            return build_response(event, summary)
        else:
            return build_response(event, {"error": f"No information found for '{drug_name}'."})
    except Exception as e:
        return build_response(event, {"error": f"An unexpected error occurred: {str(e)}"})

def build_response(event, body):
    # Standard response format for Bedrock Agents
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'apiPath': event.get('apiPath'),
            'httpMethod': event.get('httpMethod'),
            'httpStatusCode': 200,
            'responseBody': {'application/json': {'body': json.dumps(body)}}
        }
    }