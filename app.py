from gevent import monkey
monkey.patch_all()
from flask import Flask, request, jsonify
import os
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from gemini_output import gemini_output
import json
import re
from datetime import datetime
import tempfile
import base64
from config import Config
from token_utils import TokenService
from dotenv import load_dotenv
from urllib.parse import quote_plus
import logging
from gevent.pywsgi import WSGIServer
import magic  # python-magic library for file type detection
import uuid
from invoiceController import add_invoice, get_all_invoices,get_partial_invoice,get_full_invoice,delete_invoice,update_status
from prompt import INVOICE_SYSTEM_PROMPT


# Initialize Flask app

app = Flask(__name__)


# CORS(app)
CORS(app, resources={r"/*": {"origins":"*"}})
# CORS(app, resources={r"/*": {"origins": ["https://dev.billbizz.cloud/"]}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Apply configuration
app.config.from_object(Config)
Config.init_app(app)


load_dotenv()

mongodb_uri = os.getenv("DATABASE")

try:
    client = MongoClient(mongodb_uri)
    db = client.get_database('BillBizz')
    app.config['db']=db
    logging.info("Connected to MongoDB")
    print("Connected to MongoDB")
except Exception as e:
    logging.error(f"Failed to connect to MongoDB: {str(e)}")

@app.route('/', methods=['GET'])
def fn():
    return jsonify("Snaptext UAT is Running \n V1")

# Generate Token Endpoint
@app.route('/api/generate-token', methods=['POST'])
def generate_token():
    """
    Endpoint to generate a token for an organization
    """
    data = request.get_json()
    organization_id = data.get('organizationId')
    
    if not organization_id:
        return jsonify({"error": "Organization ID is required"}), 400
    
    # Generate token
    token = TokenService.generate_token(data)
    
    return jsonify({
        "message": "Token generated successfully",
        "token": token
    }), 200



@app.route('/api/upload', methods=['POST'])
@TokenService.verify_token
def upload_purchase_bill():
    try:
        # Access user details set by the verify_token decorator
        user_details = request.user  # Contains 'id', 'organizationId', 'userName'
        organization_id = user_details.get('organizationId') 
        
        # Validate file upload
        data = request.json
        if not data or 'file' not in data:
            return jsonify({"error": "No file uploaded"}), 400
        image=data

        # Extract the base64 string 
        base64_string = data['file']
        if 'base64,' in base64_string:
            base64_string = base64_string.split('base64,')[1]
        
        # Decode the base64 string to bytes
        try:
            file_content = base64.b64decode(base64_string)
        except Exception as e:
            print(f"Error decoding base64 file: {str(e)}")
            return jsonify({"error": "Failed to decode file"}), 400
    
        # Detect file type using python-magic
        file_type = magic.from_buffer(file_content, mime=True)
        print(f"Detected file type: {file_type}")

        # List of supported file types
        SUPPORTED_TYPES = [
            'image/jpeg', 
            'image/png', 
            'application/pdf'
        ]

        # Validate file type
        if file_type not in SUPPORTED_TYPES:
            return jsonify({
                "error": "Unsupported file type", 
                "supported_types": SUPPORTED_TYPES
            }), 400

        # Create a unique temporary filename based on file type
        file_extension = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'application/pdf': '.pdf'
        }.get(file_type, '')

        # Create a temporary file with a unique name and correct extension
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_extension, 
                prefix=f'upload_{uuid.uuid4()}_'
            ) as temp_file:
                temp_file.write(file_content)
                image_path = temp_file.name

            # Comprehensive system prompt
            system_prompt = INVOICE_SYSTEM_PROMPT
            user_prompt = "Extract and structure the invoice data into a comprehensive JSON format for a purchase bill."

            try:
                # Get the output from the Gemini model (assuming it can handle multiple file types)
                output = gemini_output(image_path, system_prompt, user_prompt)
                
                # JSON extraction logic (same as previous implementation)
                def extract_json_from_text(text):
                    if "```json" in text:
                        start = text.find("```json") + 7
                        end = text.find("```", start)
                        if end == -1:
                            json_str = text[start:].strip()
                        else:
                            json_str = text[start:end].strip()
                    else:
                        json_str = text.strip()
                    
                    return json_str.strip('"\'')

                # Clean and parse the JSON
                cleaned_output = extract_json_from_text(output)
                
                try:
                    parsed_output = json.loads(cleaned_output)
                except json.JSONDecodeError:
                    import re
                    potential_json = re.search(r'\{.*\}', cleaned_output, re.DOTALL)
                    if potential_json:
                        parsed_output = json.loads(potential_json.group())
                    else:
                        raise

                print("Parsed Output:", parsed_output)
                
                # Structure the output
                structured_output = {
                    "invoice": parsed_output.get("invoice", {}),
                    # "file_type": file_type
                }

                # Push the data to MongoDB collection
                add_invoice(parsed_output,image, organization_id)

                response = {
                    "message": "Purchase bill uploaded successfully",
                    "purchase_bill_data": structured_output,
                }

                return jsonify(response), 200

            except json.JSONDecodeError as json_err:
                print(f"JSON Decode Error: {json_err}")
                print(f"Problematic JSON string: {cleaned_output}")
                return jsonify({
                    "error": "Failed to parse invoice data",
                    "details": str(json_err)
                }), 400

            except Exception as e:
                print(f"Error processing purchase bill: {str(e)}")
                return jsonify({
                    "error": "An unexpected error occurred while processing the purchase bill",
                    "details": str(e)
                }), 500

            finally:
                # Always remove the temporary file
                try:
                    os.unlink(image_path)
                except Exception as cleanup_err:
                    print(f"Error cleaning up temporary file: {cleanup_err}")

        except Exception as temp_file_err:
            print(f"Error creating temporary file: {temp_file_err}")
            return jsonify({
                "error": "Failed to create temporary file",
                "details": str(temp_file_err)
            }), 500

    except Exception as general_err:
        print(f"Unexpected error in upload_purchase_bill: {general_err}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(general_err)
        }), 500
    

@app.route('/api/get_all_invoices', methods=['GET'])
@TokenService.verify_token
def get_all_invoices_api():
    try:
        # Access user details set by the verify_token decorator
        user_details = request.user  # Contains 'id', 'organizationId', 'userName'
        organization_id = user_details.get('organizationId')
        invoices = get_all_invoices(organization_id=organization_id)
        return jsonify(invoices), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# View full invoice
@app.route('/api/view_full_invoice/<invoice_id>', methods=['GET'])
@TokenService.verify_token
def view_full_invoice(invoice_id):
    try:
        invoice = get_full_invoice(invoice_id)  # Use a unique function name
        if invoice:
            return jsonify(invoice), 200
        else:
            return jsonify({"error": "Invoice not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# View partial invoice  
@app.route('/api/view_invoice/<invoice_id>', methods=['GET'])
@TokenService.verify_token
def view_invoice(invoice_id):
    try:
        invoice = get_partial_invoice(invoice_id)  # Use a unique function name
        if invoice:
            return jsonify(invoice), 200
        else:
            return jsonify({"error": "Invoice not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
  
@app.route('/api/delete_invoice/<invoice_id>', methods=['DELETE'])
@TokenService.verify_token
def delete_invoice_api(invoice_id):
    try:
        result = delete_invoice(invoice_id)
        return jsonify(result), result[1]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/update_status/<invoice_id>', methods=['PUT'])
@TokenService.verify_token
def update_status_api(invoice_id):
    try:
        # Get the request data
        request_data = request.get_json(silent=True)
        
        # If request_data is a list, take just the first item (the document)
        if isinstance(request_data, list):
            update_data = request_data[0]
        else:
            update_data = request_data

        # If no data provided, use empty dict
        if update_data is None:
            update_data = {}
            
        # Call update_status and unpack the response
        response_dict, status_code = update_status(invoice_id, update_data)
        
        return jsonify(response_dict), status_code
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @app.route('/api/update_status/<invoice_id>', methods=['PUT'])
# def update_status_api(invoice_id):
#     try:
#         result = update_status(invoice_id,update_data=request.json)
#         return jsonify(result), result[1]
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


def parse_json_safely(output):
    print("Raw output received:", output) 
    """
    Attempt multiple methods to parse JSON
    """
    # List of parsing attempts
    parsing_methods = [
        # 1. Extract JSON from markdown code block and parse
        lambda x: json.loads(re.search(r'```json\n(.*?)```', x, re.DOTALL).group(1)),
        
        # 2. Direct parsing
        lambda x: json.loads(x),
        
        # 3. Stripped parsing
        lambda x: json.loads(x.strip()),
        
        # 4. Extract JSON between first { and last }
        lambda x: json.loads(re.search(r'\{.*\}', x, re.DOTALL).group(0))
    ]
    
    # Try each parsing method
    for method in parsing_methods:
        try:
            return method(output)
        except Exception as e:
            print(f"Parsing method failed: {str(e)}")
    
    # If all parsing fails
    raise ValueError("Cannot parse JSON from output")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    try:
        port = int(os.getenv("PORT", 5000))
        print(f"Starting production server on port {port}")
        logger.info(f"Starting production server on port {port}")
        
        # Use gevent WSGI server instead of Flask development server
        http_server = WSGIServer(('0.0.0.0', port), app)
        logger.info(f"Serving on http://0.0.0.0:{port}")
        http_server.serve_forever()
        
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise
