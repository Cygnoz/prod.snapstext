# Invoice Extractor Backend API

### 1. File Upload and Text Extraction

- **URL**: `/api/upload`
- **Method**: `POST`
- **Description**: Uploads an invoice file (PDF or image) and extracts relevant data.
- **Request Body**: `multipart/form-data` with a file field named `file`.
- **Response**:
    ```json
    {
      "extracted_data": {
        "Invoice Number": "INV12345",
        "Date": "2023-01-01",
        "Customer Name": "John Doe",
        "Total Amount": "$500.00",
        "Tax Amount": "$50.00",
        "Due Date": "2023-01-30",
        "GST": "18%",
        "Product Details": "Product A - $300, Product B - $200",
        "Bill To": "ABC Corp, 123 Street, City",
        "Shipping Address": "XYZ Corp, 456 Avenue, City"
      }
    }
    ```

### 2. QR Code Generation

- **URL**: `/api/generate_qr`
- **Method**: `POST`
- **Description**: Generates a QR code containing the provided text data.
- **Request Body**:
    ```json
    {
      "data": "Optional text data for QR code"
    }
    ```
- **Response**:
    ```json
    {
      "qr_path": "path/to/generated/qr_code.png"
    }
    ```
