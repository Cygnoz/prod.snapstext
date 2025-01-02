from flask import Flask, request, jsonify
import os
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import date
from bson import ObjectId
from uuid import uuid4

load_dotenv()

username = os.getenv("MONGODB_USERNAME")
password = os.getenv("MONGODB_PASSWORD")
 
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)
 
# class Item(BaseModel):
#     item_id: str = Field(..., alias="itemId")
#     item_name: str = Field(..., alias="itemName")
#     item_quantity: int = Field(..., alias="itemQuantity")
#     item_cost_price: float = Field(..., alias="itemCostPrice")
#     item_tax: float = Field(..., alias="itemTax")
#     item_discount: float = Field(..., alias="itemDiscount")
#     item_discount_type: str = Field(..., alias="itemDiscountType")
#     item_sgst: float = Field(..., alias="itemSgst")
#     item_cgst: float = Field(..., alias="itemCgst")
#     item_igst: float = Field(..., alias="itemIgst")
#     item_vat: float = Field(..., alias="itemVat")
#     item_sgst_amount: float = Field(..., alias="itemSgstAmount")
#     item_cgst_amount: float = Field(..., alias="itemCgstAmount")
#     item_igst_amount: float = Field(..., alias="itemIgstAmount")
#     item_vat_amount: float = Field(..., alias="itemVatAmount")

# class Invoice(BaseModel):
#     organization_id: str = Field(..., alias="organizationId")
#     supplier_id: str = Field(..., alias="supplierId")
#     supplier_display_name: str = Field(..., alias="supplierDisplayName")
#     supplier_billing_country: str = Field(..., alias="supplierBillingCountry")
#     supplier_billing_state: str = Field(..., alias="supplierBillingState")
#     bill_number: str = Field(..., alias="billNumber")
#     bill_date: str = Field(..., alias="billDate")
#     due_date: str = Field(..., alias="dueDate")
#     order_number: str = Field(..., alias="orderNumber")
#     purchase_order_date: str = Field(..., alias="puchaseOrderDate")
#     source_of_supply: str = Field(..., alias="sourceOfSupply")
#     destination_of_supply: str = Field(..., alias="destinationOfSupply")
#     payment_terms: str = Field(..., alias="paymentTerms")
#     payment_mode: str = Field(..., alias="paymentMode")
#     paid_status: str = Field(..., alias="paidStatus")
#     items: List[Item]
#     sub_total: float = Field(..., alias="subTotal")
#     total_item: int = Field(..., alias="totalItem")
#     sgst: float
#     cgst: float
#     igst: float
#     vat: float
#     transaction_discount: float = Field(..., alias="transactionDiscount")
#     transaction_discount_type: str = Field(..., alias="transactionDiscountType")
#     total_tax_amount: float = Field(..., alias="totalTaxAmount")
#     grand_total: float = Field(..., alias="grandTotal")
#     paid_amount: float = Field(..., alias="paidAmount")
#     balance_amount: float = Field(..., alias="balanceAmount")
#     bank_name: str = Field(..., alias="bankName")
#     account_number: str = Field(..., alias="accountNumber")
#     branch_name: str = Field(..., alias="branchName")
#     ifsc_code: str = Field(..., alias="ifscCode")

# MongoDB connection string
mongodb_uri = f"mongodb+srv://{encoded_username}:{encoded_password}@billbizz.val4sxs.mongodb.net/BillBizz?retryWrites=true&w=majority&appName=BillBizz"
client = MongoClient(mongodb_uri)
db = client.get_database('BillBizz') 
invoice_collection = db.get_collection('invoices')  

# Invoice add to DB
def add_invoice(purchase_bill_data,image,organization_id):
    if purchase_bill_data is None:
        purchase_bill_data = request.json
        # Add unique IDs to each item
    if 'items' in purchase_bill_data:
        for idx, item in enumerate(purchase_bill_data['items'], start=1):
            item['item_id'] = str(idx)  # Generate sequential ID
    purchase_bill_data['image'] = image
    purchase_bill_data['organization_id'] = organization_id
    purchase_bill_data['uploaded_date'] = date.today().strftime("%d-%m-%Y")
    purchase_bill_data['status'] = "Need review"
    invoice_collection.insert_one(purchase_bill_data)
    return {"message": "Invoice added successfully"}, 201

    
def view_invoice(invoice_id):
    try:
        invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)}, {"_id":0})
        if invoice:
            return invoice, 200
        else:
            return {"error": "Invoice not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def get_all_invoices(organization_id):
    # Find all documents matching the organization_id
    query = {'organization_id': organization_id}
    
    # Only fetch required fields
    projection = {
        '_id': 1,
        'invoice.header.supplier_name': 1,
        'invoice.header.invoice_no': 1,
        'invoice.header.invoice_date': 1,
        'status': 1,
        'review_date': 1
    }
    # Execute MongoDB query and convert cursor to list
    # invoices = list(invoice_collection.find(query))
    invoices = invoice_collection.find(query, projection)

    # Convert ObjectId to string for each invoice
    # for invoice in invoices:
    #     invoice['_id'] = str(invoice['_id'])
    
    # return invoices
    return [{
        'supplier_name': doc['invoice']['header']['supplier_name'],
        'invoice_no': doc['invoice']['header']['invoice_no'],
        'bill_date': doc['invoice']['header']['invoice_date'],
        'status': doc['status'],
        'review_date': doc.get('review_date', None),
        '_id': str(doc['_id'])
    } for doc in invoices]

def delete_invoice(invoice_id):
    try:
        result = invoice_collection.delete_one({"_id": ObjectId(invoice_id)})
        if result.deleted_count == 1:
            return {"message": "Invoice deleted successfully"}, 200
        else:
            return {"error": "Invoice not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def update_status(invoice_id, update_data):
    """
    Update invoice status and optionally other fields with proper change detection
    
    Args:
        invoice_id (str): The ID of the invoice to update
        update_data (dict, optional): Additional fields to update
        
    Returns:
        tuple: (response_dict, status_code)
    """
    try:
        # Check if invoice exists
        invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)})
        if not invoice:
            return {"error": "Invoice not found"}, 404

        # Default status update fields
        update_fields = {
            "status": "Reviewed",
            "review_date": date.today().strftime("%d-%m-%Y")
        }
        
        # Merge additional fields if provided
        if update_data:
            update_fields.update(update_data)
        
        # Check for changes before updating
        changes_detected = {
            key: update_fields[key]
            for key in update_fields
            if str(update_fields[key]) != str(invoice.get(key))
        }

        if not changes_detected:
            return {"error": "No changes detected"}, 400

        # Perform the update
        result = invoice_collection.update_one(
            {"_id": ObjectId(invoice_id)},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0:
            return {"message": "Invoice status updated successfully"}, 200
        else:
            return {"error": "Update failed - no changes applied"}, 400

    except Exception as e:
        return {"error": f"Update failed: {str(e)}"}, 500


# def update_status(invoice_id, update_data):
#     """
#     Update invoice status and optionally other fields with proper change detection
    
#     Args:
#         invoice_id (str): The ID of the invoice to update
#         update_data (dict, optional): Additional fields to update
        
#     Returns:
#         tuple: (response_dict, status_code)
#     """
#     try:
#         # First check if invoice exists
#         invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)})
#         if not invoice:
#             return {"error": "Invoice not found"}, 404

#         # Initialize the update data with default status fields
#         # Force status to be different from current to ensure update
#         update_fields = {
#             "status": "Reviewed",
#             "review_date": date.today().strftime("%d-%m-%Y")
#         }
        
#         # If additional update data is provided, merge it with status fields
#         if update_data:
#             update_fields.update(update_data)
        
#         # Perform the update
#         result = invoice_collection.update_one(
#             {"_id": ObjectId(invoice_id)},
#             {"$set": update_fields}
#         )
        
#         # Verify the update
#         updated_invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)})
        
#         if updated_invoice:
#             # Compare relevant fields to confirm update
#             fields_changed = any(
#                 str(updated_invoice.get(key)) != str(invoice.get(key))
#                 for key in update_fields.keys()
#             )
            
#             if fields_changed:
#                 return {"message": "Invoice status updated successfully"}, 200
#             else:
#                 return {"error": "Update failed - no changes detected"}, 400
#         else:
#             return {"error": "Failed to verify update"}, 500
            
#     except Exception as e:
#         return {"error": f"Update failed: {str(e)}"}, 500
 

# if __name__ == '__main__':
#     app.run(debug=True)
