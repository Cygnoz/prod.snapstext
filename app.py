from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from flask_cors import CORS
from pymongo import MongoClient, errors
from bson import ObjectId
from gemini_output import gemini_output
import pymongo
from pymongo.errors import ServerSelectionTimeoutError
from bson.objectid import ObjectId

# DB Connection
try:
    client = MongoClient("mongodb+srv://pranavocr:rPMmg2osIHCE2h33@cluster0.38hav.mongodb.net/")
    db = client["OCR_DB"]
    
    print("Connected to MongoDB!")
except ServerSelectionTimeoutError as e:
    print("Connection failed:", e)

# Schema validation for the "invoice" collection


schema = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "properties": {
                "company_name": {
                    "bsonType": "string"
                },
                "header": {
                    "bsonType": "object"
                },
                "items": {
                    "bsonType": "array"
                },
                "footer": {
                    "bsonType": "object"
                },
                "bank_details": {
                    "bsonType": "object"
                }
            }
        }
    }
}

# Create the 'invoice' collection with validation (ensure this runs only once)
try:
    db.create_collection("invoice", **schema)
    print("Collection 'Invoice' created with schema validation.")
except errors.CollectionInvalid:
    print("Collection 'Invoice' already exists.")    
################
    

# Initialize Flask app

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["*"], "methods": ["GET", "POST", "PUT", "DELETE"]}})
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/api/invoices', methods=['GET'])
def get_all_invoice():
    try:
        print("Fetching documents from MongoDB...")
        
        # Fetch all invoices from the collection
        invoices = db.invoice.find()
        
        # Convert the cursor to a list of documents and convert ObjectId to string
        invoice_list = []
        for invoice in invoices:
            invoice['_id'] = str(invoice['_id'])  # Convert ObjectId to string
            invoice_list.append(invoice)
                
        return jsonify({'invoices': invoice_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def fn():
    return jsonify("READY")



@app.route('/api/invoice', methods=['POST'])
def add_or_update_invoice():
    try:
        # Extract data from the request
        invoice_data = request.get_json()
        print("Invoice Data Received:", invoice_data)
        
        # Check if '_id' exists in the invoice data
        if '_id' in invoice_data:
            try:
                invoice_data_id = ObjectId(invoice_data['_id']) 
                # Convert `_id` to ObjectId if necessary 
                print("Id present in invoice data", type(invoice_data_id), invoice_data_id)
                # Remove `_id` from `invoice_data` to avoid updating it
                del invoice_data['_id']
            except:
                pass  # Leave `_id` as-is if it isn't a valid ObjectId format

            # Perform upsert based on '_id' field
            print("Invoice Data Received:", invoice_data)
            result = db.invoice.find_one_and_update(
                {"_id": invoice_data_id},      # Query by '_id'
                {"$set": invoice_data},        # Replace document fields with invoice_data (without `_id`)
                upsert=True,                   # Insert if not found
                return_document=pymongo.ReturnDocument.AFTER  # Return updated document  
            )
            print("Result:", result)
            message = "Invoice created or updated successfully!"

            # Convert the `_id` in the result to string if it's present
            if result and '_id' in result: 
                result['_id'] = str(result['_id'])

            updated_data = result  # This will hold the updated document
        else:
            # If `_id` is not present, insert a new document
            print("Id not present in invoice data")
            invoice_number = invoice_data['header']['invoice_no']

# Print the extracted invoice number
            print("Invoice Number:", invoice_number)            
            # print(db.invoice.find_one(  {"": invoice_data_id}))

            result = db.invoice.insert_one(invoice_data) 
            message = "Invoice created successfully!"
            updated_data = {"_id": str(result.inserted_id)}  # Return only the inserted ID

        return jsonify({"message": message, "updated_data": updated_data}), 200 

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/invoice/<invoice_id>', methods=['DELETE'])   
def delete_invoice(invoice_id):
    try:
        # Convert the provided `invoice_id` to an ObjectId 
        invoice_object_id = ObjectId(invoice_id)
        
        # Attempt to delete the document by `_id`
        result = db.invoice.delete_one({"_id": invoice_object_id}) 
         
        if result.deleted_count == 1:
            message = "Invoice deleted successfully!"   
            status = 200  
        else:
            message = "Invoice not found."
            status = 404

        return jsonify({"message": message}), status

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/upload', methods=['POST'])
def test():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)


    organization_id = request.form.get("organization_id")
    print(organization_id)
    # System and user prompts
    system_prompt = """
    You are a specialist in understanding and extracting structured data from invoices.
    Ensure that:
    - Synonymous words (e.g., 'qty' and 'quantity', 'items' and 'products') should be interpreted as the same term and mapped to the same column in the output.
    - All extracted text values are converted to lowercase for uniformity.
    - The output is structured in JSON format with clear and appropriate JSON tags for each field based on the image content.
    - Please process the document and identify if it is a multi-page invoice. If the invoice spans multiple pages, continue processing each page as part of the same invoice, as long as the invoice number or header information matches. If a page contains a different invoice number or structure, treat it as a new invoice.
    - For single or multi-page invoices, extract the text in an object format. If the input consists of multiple pages, merge the content and output in a single object structure, not in an array format. Each field should be represented as key-value pairs in one object.
    - Ensured Inclusion of the "invoice" Key: Explicitly instructed to always include the "invoice" key in the JSON output, regardless of multi-page processing.
    Additionally, perform the following calculations when extracting invoice data:
    
    - **Gross Amount**: If a gross amount is not provided, calculate it as the sum of individual product prices multiplied by their quantities.
    - **Discount**: If a discount is not provided, set the discount to `0`. If a discount is provided, calculate it based on the formula: Gross Amount - (Net Amount), where Net Amount is the sum of all product prices before tax or discount.
    - **Net Amount**: If a net amount is not provided, calculate it as: Gross Amount - Discount.
    - **Tax Percentage**: If the tax percentage is not provided, calculate it using the formula: (Tax Amount / Net Amount) * 100. Use the Tax Amount and Net Amount fields if they are available.
    - **Tax Amount**: If a tax amount is not provided, calculate it as: Net Amount * (Tax Percentage / 100).
    - **Total Amount**: If a total amount is not provided, calculate it as: Net Amount + Tax Amount (or Gross Amount + Tax Amount if applicable).
    - **Due Date**: make the due date field as 01/01/2025.
    - If any of the above fields (Gross Amount, Discount, Net Amount, Tax Percentage, Tax Amount, Total Amount or Due date) are missing in the invoice, calculate them using the available values or based on the other available data.
 
    **Batch Number and Expiry Date**:
    - If a batch number and expiry date are present in the invoice, extract them and place them in the corresponding columns.
    - If they are not present, set their values as `null`.
 
    Ensure that the calculated values and extracted fields are consistent and accurate based on the fields available in the invoice.
    
    Example:
    the output should be  given format
    invoice = {
    company_name : 'ABC' ,
    header : {
        invoice_no : '',
        Supplier_Name : '',
        Supplier_address : '',
        Contact_Number : '',
        Invoice_Date : '',
        Due_Date: ''
    },
    items : [{
        product_name : '',
        name : '', 
        HSN_SAC : '',
        Quantity :'',
        Rate :'' ,
        Gross : ,
        Discount : ,
        Net_amount : ,
        Tax : ,
        Tax_amount
        Total_amount:'',
    }],
    footer : {
        CGST :'',
        SGST :'',
        batch_no :'', 
        expiry_date:'' ,
        payment_terms :'',
        # Total_Amount :'',
    }    ,  
    bank_details, : {
        Bank : '' ,
        Account_no :'',
        IFSC_code :''
};    
  if value is not there then  fill null
    
    """

    user_prompt = "Convert Invoice data into JSON format with appropriate JSON tags as required for the data in the image."

    # Get the output from the Gemini model
    output = gemini_output(filepath, system_prompt, user_prompt)
    return output


# Run the Flask app
if __name__ == '__main__':
    app.run( host="0.0.0.0",debug=True)