from flask import Flask, request, jsonify
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
from datetime import date
from bson import ObjectId

load_dotenv()

mongodb_uri = os.getenv("DATABASE")
client = MongoClient(mongodb_uri)
db = client.get_database('BillBizz') 
invoice_collection = db.get_collection('invoices')  


from typing import Dict, Any, List

def transform_invoice_data(purchase_bill_data: Dict[Any, Any]) -> Dict[str, Any]:
    """Transform the data while maintaining the original structure but using new field names"""
    invoice_data = purchase_bill_data.get('invoice', {})
    header = invoice_data.get('header', {})
    footer = invoice_data.get('footer', {})
    bank_details = invoice_data.get('bank_details', {})

    # Get image string directly from the image object
    
    image_string = purchase_bill_data.get('image', {})
    
    # Transform items while keeping original structure
    transformed_items = []
    for item in invoice_data.get('items', []):
        # Remove currency symbols and commas from numeric strings
        rate = str(item.get('rate', '0')).replace(',', '').replace('₹', '')
        quantity = str(item.get('quantity', '0')).replace(',', '')
        discount = str(item.get('discount', '0')).replace(',', '')

        transformed_item = {
            'itemId': str(len(transformed_items) + 1),  
            'itemName': item.get('product_name', ''),
            'itemHsn': item.get('hsn_sac', ''), 
            'itemQuantity': quantity,
            'itemCostPrice': rate,
            'itemDiscount': discount,
            'itemDiscountType': 'percentage',
            'itemGrossAmount': item.get('gross', '0').replace(',', ''),  
            'itemTotalAmount': item.get('total_amount', '0').replace(',', ''), 
            'itemBatchNo': item.get('batch_no', ''), 
            "itemTax": str(float(item.get('cgst_amount', '0').replace(',', '')) + float(item.get('sgst_amount', '0').replace(',', ''))),
            "itemAmount": str(float(item.get('net_amount', '0').replace(',', '')) + float(item.get('cgst_amount', '0').replace(',', '')) + float(item.get('sgst_amount', '0').replace(',', ''))),
            "itemSgst": item.get('sgst', '0'),
            "itemCgst": item.get('cgst', '0'),
            'itemIgst': '0',
            'itemVat': '0',
            "itemSgstAmount": item.get('sgst_amount', '0.0'),
            "itemCgstAmount": item.get('cgst_amount', '0.0'),
            'taxPreference': 'tax_inclusive',
            'purchaseAccountId': ''
        }
        transformed_items.append(transformed_item)

    # Create the nested structure with new field names
    transformed_data = {
        'invoice': {
            'companyName': header.get('supplier_name', ''),
            'header': {
                'billNumber': header.get('invoice_no', ''),
                'supplierDisplayName': header.get('supplier_name', ''),
                'supplierId': header.get('supplier_id', ''),
                'supplierAddress': header.get('supplier_address', ''),
                'supplierPhone': header.get('supplier_phone', ''),
                'billDate': header.get('invoice_date', ''),
                'dueDate': header.get('due_date', ''),
                'sourceOfSupply': '',
                'destinationOfSupply': '',
                'taxMode': 'tax_inclusive',
                'orderNumber': '',
                'purchaseOrderDate': '',
                'expectedShipmentDate': '',
                'paymentMode': '',
                'PaidThrough': ''
            },
            'items': transformed_items,
            'footer': {
                'cgst': str(float(footer.get('total_tax_amount', '0').replace(',', ''))/2),
                'sgst': str(float(footer.get('total_tax_amount', '0').replace(',', ''))/2),
                'igst': '0',
                # 'paymentTerms': footer.get('payment_terms', ''),
                'addNotes': footer.get('additional_notes', ''),
                'termsAndConditions': footer.get('additional_notes', ''),
                'subTotal': str(sum(float(item.get('net_amount', '0').replace(',', '')) for item in invoice_data.get('items', []))),
                'totalItem': str(len(invoice_data.get('items', []))),
                'transactionDiscountType': 'percentage',
                'transactionDiscount': '0',
                'transactionDiscountAmount': '0',
                'totalTaxAmount': str(sum(
                    float(item.get('cgst_amount', '0').replace(',', '')) + 
                    float(item.get('sgst_amount', '0').replace(',', ''))
                    for item in invoice_data.get('items', []))),
                'itemTotalDiscount': '0',
                'roundOffAmount': '0',
                'grandTotal': footer.get('grand_total', '0').replace(',', ''),
                'balanceAmount': footer.get('grand_total', '0').replace(',', ''),
                'paidAmount': '0'
            },
            'bank_details': {
                'bankName': bank_details.get('bank_name', ''),
                'accountNo': bank_details.get('account_no', ''),
                'branchName': bank_details.get('branch_name', ''),
                'ifscCode': bank_details.get('ifsc_code', '')
            },
            'otherDetails': {
                'otherExpenseAmount': '0',
                'otherExpenseAccountId': '',
                'otherExpenseReason': '',
                'vehicleNo': '',
                'freightAmount': '0',
                'freightAccountId': '',
                'paidStatus': 'unpaid',
                'shipmentPreference': '',
                'paidAccountId': ''
            }
        },
        'image': image_string,
        'organizationId': purchase_bill_data.get('organization_id', ''),
        'uploadedDate': date.today().strftime("%d-%m-%Y"),
        'status': "Need review"
    }
    
    return transformed_data

def add_invoice(purchase_bill_data: Dict[Any, Any] = None, image: str = None, organization_id: str = None):
    """Add transformed invoice data to the database"""
    if purchase_bill_data is None:
        purchase_bill_data = request.json
    
    # Transform the data while maintaining original structure
    transformed_data = transform_invoice_data(purchase_bill_data)
    
    # Add additional required fields if provided
    if image:
        transformed_data['image'] = image
    if organization_id:
        transformed_data['organizationId'] = organization_id
    
    # Insert into database
    invoice_collection.insert_one(transformed_data)
    
    return {"message": "Invoice added successfully"}, 201
    
def get_full_invoice(invoice_id):
    try:
        invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)}, {"_id":0})
        if invoice:
            return invoice, 200
        else:
            return {"error": "Invoice not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def get_partial_invoice(invoice_id):
    try:
        invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)}, {"_id": 0})
        if not invoice:
            return {"error": "No invoice found"}, 404

        # Mapping the required structure
        invoice_data = {
            "supplierId": invoice["invoice"]["header"].get("supplierId", ""),
            "supplierDisplayName": invoice["invoice"]["header"].get("supplierDisplayName", ""),
            "supplierInvoiceNum": invoice["invoice"]["header"].get("billNumber", ""),
            # "supplierInvoiceNum": invoice["invoice"]["header"].get("supplierInvoiceNum", ""),
            "sourceOfSupply": invoice["invoice"]["header"].get("sourceOfSupply", ""),
            "destinationOfSupply": invoice["invoice"]["header"].get("destinationOfSupply", ""),
            "taxMode": invoice["invoice"]["header"].get("taxMode", ""),
            "orderNumber": invoice["invoice"]["header"].get("orderNumber", ""),
            "purchaseOrderDate": invoice["invoice"]["header"].get("purchaseOrderDate", ""),
            "expectedShipmentDate": invoice["invoice"]["header"].get("expectedShipmentDate", ""),
            # "paymentTerms": invoice["invoice"]["header"].get("paymentTerms", ""),
            "paymentMode": invoice["invoice"]["header"].get("paymentMode", ""),
            "PaidThrough": invoice["invoice"]["header"].get("PaidThrough", ""),
            "billDate": invoice["invoice"]["header"].get("billDate", ""),
            "dueDate": invoice["invoice"]["header"].get("dueDate", ""),
            "items": [],
            "otherExpenseAmount": invoice["invoice"].get("otherExpenseAmount", ""),
            "otherExpenseAccountId": invoice["invoice"].get("otherExpenseAccountId", ""),
            "otherExpenseReason": invoice["invoice"].get("otherExpenseReason", ""),
            "vehicleNo": invoice["invoice"].get("vehicleNo", ""),
            "freightAmount": invoice["invoice"].get("freightAmount", ""),
            "freightAccountId": invoice["invoice"].get("freightAccountId", ""),
            "addNotes": invoice["invoice"].get("addNotes", ""),
            "termsAndConditions": invoice["invoice"].get("termsAndConditions", ""),
            "attachFiles": invoice["invoice"].get("attachFiles", ""),
            "subTotal": invoice["invoice"].get("subTotal", ""),
            "totalItem": invoice["invoice"].get("totalItem", ""),
            "sgst": invoice["invoice"]["footer"]["sgst"],
            "cgst": invoice["invoice"]["footer"]["cgst"],
            "igst": invoice["invoice"]["footer"]["igst"],
            "transactionDiscountType": invoice["invoice"].get("transactionDiscountType", ""),
            "transactionDiscount": invoice["invoice"].get("transactionDiscount", ""),
            "transactionDiscountAmount": invoice["invoice"].get("transactionDiscountAmount", ""),
            "total_tax_amount": invoice["invoice"].get("totalTaxAmount", ""),
            "itemTotalDiscount": invoice["invoice"].get("itemTotalDiscount", ""),
            "roundOffAmount": invoice["invoice"].get("roundOffAmount", ""),
            "paidStatus": invoice["invoice"].get("paidStatus", ""),
            "shipmentPreference": invoice["invoice"].get("shipmentPreference", ""),
            "grandTotal": invoice["invoice"].get("grandTotal", ""),
            "balanceAmount": invoice["invoice"].get("balanceAmount", ""),
            "paidAmount": invoice["invoice"].get("paidAmount", ""),
            "paidAccountId": invoice["invoice"].get("paidAccountId", ""),
            "purchaseOrderId": invoice["invoice"].get("purchaseOrderId", ""),
        }

        # Populate items list

        for item in invoice["invoice"].get("items", []):
            invoice_data["items"].append({
            "itemId": item.get("itemId", ""),
            "itemName": item.get("itemName", ""),
            "itemHsn": item.get("itemHsn", ""),
            "itemQuantity": item.get("itemQuantity", ""),
            "itemCostPrice": item.get("itemCostPrice", ""),
            "itemDiscount": item.get("itemDiscount", ""),
            "itemDiscountType": item.get("itemDiscountType", ""),
            "itemSgst": item.get("itemSgst", "0"),  
            "itemCgst": item.get("itemCgst", "0"), 
            "itemTax": str(float(item.get("itemSgstAmount", "0").replace(',', '')) + float(item.get("itemCgstAmount", "0").replace(',', ''))),
            # "itemTax": item.get("itemTax", ""),
            "itemIgst": item.get("itemIgst", "0"),
            "itemVat": item.get("itemVat", "0"),
            "itemGrossAmount": item.get("itemGrossAmount", "0"),
            "itemAmount": item.get("itemAmount", "0"),
            "itemTotalAmount": item.get("itemTotalAmount", "0"),
            "itemBatchNo": item.get("itemBatchNo", ""),
            "itemSgstAmount": item.get("itemSgstAmount", "0"),  
            "itemCgstAmount": item.get("itemCgstAmount", "0"),  
            "taxPreference": item.get("taxPreference", ""),
            "purchaseAccountId": item.get("purchaseAccountId", ""),
            })

        return invoice_data, 200

    except Exception as e:
        return {"error": str(e)}, 500



def get_all_invoices(organization_id):
    # Find all documents matching the organization_id
    query = {'organizationId': organization_id}
    
    # Only fetch required fields
    projection = {
        '_id': 1,
        'invoice.header.supplierDisplayName': 1,
        'invoice.header.billNumber': 1,
        # 'invoice.header.invoice_date': 1,
        'uploadedDate': 1,
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
        'supplierDisplayName': doc['invoice']['header']['supplierDisplayName'],
        'billNumber': doc['invoice']['header']['billNumber'],
        'uploadedDate': doc['uploadedDate'],
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
            return {"error": "No invoice found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500


def update_status(invoice_id, update_data):
    """
    Update invoice status and items with frontend-provided IDs
    
    Args:
        invoice_id (str): The ID of the invoice to update
        update_data (dict): Contains item IDs in order and other update fields
        
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
        
        # Handle items update if provided in update_data
        if update_data and "items" in update_data:
            existing_items = invoice["invoice"]["items"]
            
            # Update item IDs while preserving all other item data
            if len(update_data["items"]) == len(existing_items):
                updated_items = []
                for idx, frontend_id in enumerate(update_data["items"]):
                    updated_item = existing_items[idx].copy()
                    updated_item["itemId"] = frontend_id
                    updated_items.append(updated_item)
                
                # Add updated items to update_fields
                update_fields["invoice.items"] = updated_items
            else:
                return {"error": "Number of items doesn't match"}, 400

        # Merge other update fields if provided
        if update_data:
            other_updates = {k: v for k, v in update_data.items() if k != "items"}
            update_fields.update(other_updates)
        
        # Check for changes before updating
        # original_status = invoice.get("status", "")
        # if update_fields["status"] == original_status and "invoice.items" not in update_fields:
        #     return {"error": "No changes detected"}, 400

        # Perform the update
        result = invoice_collection.update_one(
            {"_id": ObjectId(invoice_id)},
            {"$set": update_fields}
        )
        
        if result.modified_count > 0:
            return {"message": "Invoice updated successfully"}, 200
        else:
            return {"error": "Update failed - no changes applied"}, 400

    except Exception as e:
        return {"error": f"Update failed: {str(e)}"}, 500
