from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from flask_cors import CORS
# from pymongo import MongoClient, errors
# from bson import ObjectId
from gemini_output import gemini_output
# import pymongo
# from pymongo.errors import ServerSelectionTimeoutError
# from bson.objectid import ObjectId
import json
import re
from datetime import datetime
from config import Config
from token_utils import TokenService
import jwt 



# Initialize Flask app

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["*"], "methods": ["GET", "POST", "PUT", "DELETE"]}})
app.config['UPLOAD_FOLDER'] = 'uploads'

# Apply configuration
app.config.from_object(Config)
Config.init_app(app)


# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])



@app.route('/', methods=['GET'])
def fn():
    return jsonify("OCR is running")


# Generate Token Endpoint (Optional, but recommended)
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
    # Validate file upload
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    
    # Secure and save the file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Get organization ID from request
    organization_id = request.form.get("organization_id")
    
    # Comprehensive system prompt
    system_prompt = """
    You are an expert at extracting structured data from purchase invoices.
    Follow these strict guidelines:
    1. Return a VALID JSON response
    2. Use lowercase for all string values
    3. Use null for unknown/missing values
    4. Ensure numeric fields are numbers
    5. Include all requested fields even if empty

    Required JSON Structure:
    {
        "supplier_name": "string",
        "bill_number": "string",
        "bill_date": "string",
        "due_date": "string",
        "supplier_id": "string",
        "supplier_country": "string",
        "supplier_state": "string",
        "purchase_order_number": "string",
        "purchase_order_date": "string",
        "source_of_supply": "string",
        "destination_of_supply": "string",
        "payment_terms": "string", 
        "payment_mode": "string",
        "paid_status": "string",
        "subtotal": 0.0,
        "total_tax_amount": 0.0,
        "grand_total": 0.0,
        "paid_amount": 0.0,
        "balance_amount": 0.0,
        "items": [
            {
                "item_id": "string",
                "item_name": "string", 
                "quantity": 0.0,
                "cost_price": 0.0,
                "tax_rate": 0.0,
                "item_discount": 0.0,
                "discount_type": "string",
                "sgst_rate": 0.0,
                "cgst_rate": 0.0,
                "igst_rate": 0.0,
                "vat_rate": 0.0,
                "sgst_amount": 0.0,
                "cgst_amount": 0.0,
                "igst_amount": 0.0,
                "vat_amount": 0.0
            }
        ]
    }
    """

    user_prompt = "Extract and structure the invoice data into a comprehensive JSON format for a purchase bill."

    # Get the output from the Gemini model
    try:
        output = gemini_output(filepath, system_prompt, user_prompt)
        
        # Debug: Print raw output
        print("Raw Gemini Output:", output)
        
        # Multiple JSON parsing attempts
        invoice_data = parse_json_safely(output)
        
        # Map extracted data to Mongoose schema
        purchase_bill_data = {
            "organizationId": organization_id,
            "supplierId": invoice_data.get('supplier_id', ''),
            "supplierDisplayName": invoice_data.get('supplier_name', ''),
            
            # Supplier Billing Address
            "supplierBillingCountry": invoice_data.get('supplier_country', ''),
            "supplierBillingState": invoice_data.get('supplier_state', ''),
            
            # Bill Details
            "billNumber": invoice_data.get('bill_number', ''),
            "billDate": invoice_data.get('bill_date', ''),
            "dueDate": invoice_data.get('due_date', ''),
            
            # Purchase Order Details
            "orderNumber": invoice_data.get('purchase_order_number', ''),
            "puchaseOrderDate": invoice_data.get('purchase_order_date', ''),
            
            # Supply Information
            "sourceOfSupply": invoice_data.get('source_of_supply', ''),
            "destinationOfSupply": invoice_data.get('destination_of_supply', ''),
            
            # Payment Details
            "paymentTerms": invoice_data.get('payment_terms', ''),
            "paymentMode": invoice_data.get('payment_mode', ''),
            "paidStatus": invoice_data.get('paid_status', ''),
            
            # Items
            "items": [
                {
                    "itemId": item.get('item_id', ''),
                    "itemName": item.get('item_name', ''),
                    "itemQuantity": item.get('quantity', 0),
                    "itemCostPrice": item.get('cost_price', 0),
                    "itemTax": item.get('tax_rate', 0),
                    "itemDiscount": item.get('item_discount', 0),
                    "itemDiscountType": item.get('discount_type', ''),
                    "itemSgst": item.get('sgst_rate', 0),
                    "itemCgst": item.get('cgst_rate', 0),
                    "itemIgst": item.get('igst_rate', 0),
                    "itemVat": item.get('vat_rate', 0),
                    "itemSgstAmount": item.get('sgst_amount', 0),
                    "itemCgstAmount": item.get('cgst_amount', 0),
                    "itemIgstAmount": item.get('igst_amount', 0),
                    "itemVatAmount": item.get('vat_amount', 0),
                } for item in invoice_data.get('items', [])
            ],
            
            # Financial Summary
            "subTotal": invoice_data.get('subtotal', 0),
            "totalItem": len(invoice_data.get('items', [])),
            "sgst": invoice_data.get('total_sgst', 0),
            "cgst": invoice_data.get('total_cgst', 0),
            "igst": invoice_data.get('total_igst', 0),
            "vat": invoice_data.get('total_vat', 0),
            "transactionDiscount": invoice_data.get('total_discount', 0),
            "transactionDiscountType": invoice_data.get('discount_type', ''),
            "totalTaxAmount": invoice_data.get('total_tax_amount', 0),
            "grandTotal": invoice_data.get('grand_total', 0),
            "paidAmount": invoice_data.get('paid_amount', 0),
            "balanceAmount": invoice_data.get('balance_amount', 0),
            
            # Additional Details
            "createdDate": datetime.now().isoformat()
        }
        
        # Save to MongoDB
        # Assuming PurchaseBill is a MongoDB collection
        # purchase_bill_collection = db['purchase_bill']
        # purchase_bill_id = purchase_bill_collection.insert_one(purchase_bill_data).inserted_id
        return jsonify({
            "message": "Purchase bill uploaded successfully",
            "purchase_bill_data": purchase_bill_data
        }), 200
    
    except Exception as e:
        # Detailed error logging
        print(f"Error processing purchase bill: {str(e)}")
        return jsonify({
            "error": "Failed to process purchase bill",
            "details": str(e),
            "raw_output": output  # Include raw output for debugging
        }), 500

        
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


# Run the Flask app
if __name__ == '__main__':
    app.run( host="0.0.0.0",debug=True)