# import jwt
# import os
# from functools import wraps
# from flask import request, jsonify
# from dotenv import load_dotenv
# from datetime import datetime, timedelta

# class TokenVerification:
#     @staticmethod
#     def generate_token(organization_id):
#         """
#         Generate a simple token for the organization
        
#         :param organization_id: Organization identifier
#         :return: JWT token
#         """
#         # Use a secret key from environment or a default
#         load_dotenv()
#         secret_key = os.getenv('JWT_SECRET')
        
#         # Create a payload with just the organization ID
#         payload = {
#             'organizationId': organization_id
#         }
        
#         # Generate token
#         token = jwt.encode(payload, secret_key, algorithm='HS256')
#         return token
    
#     @staticmethod
#     def verify_token(f):
#         """
#         Decorator to verify token for routes
        
#         :param f: Route function to be decorated
#         :return: Wrapped function with token verification
#         """
#         @wraps(f)
#         def decorated(*args, **kwargs):
#             # Check for Authorization header
#             auth_header = request.headers.get('Authorization')
            
#             # If no Authorization header is present
#             if not auth_header:
#                 return jsonify({"error": "Authorization token is missing"}), 403
            
#             try:
#                 # Split the header to extract the token (Bearer <token>)
#                 token = auth_header.split(' ')[1]
                
#                 # Decode the token 
#                 secret_key = os.getenv('JWT_SECRET')
#                 payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                
#                 # Verify organization ID
#                 organization_id = payload.get('organizationId')
                
#                 if not organization_id:
#                     return jsonify({"error": "Invalid token structure"}), 403
                
#                 # Attach organization ID to the request
#                 request.organization_id = organization_id
            
#             except jwt.ExpiredSignatureError:
#                 return jsonify({"error": "Token has expired"}), 401
            
#             except jwt.InvalidTokenError:
#                 return jsonify({"error": "Invalid token"}), 403
            
#             # Call the original route function
#             return f(*args, **kwargs)
        
#         return decorated

# @staticmethod
# def generate_token(user):
#     load_dotenv()
#     secret_key = os.getenv('JWT_SECRET')
    
#     # Debug: Print secret key and ensure it's not None
#     print(f"Secret Key: {secret_key}")
#     if not secret_key:
#         raise ValueError("JWT_SECRET is not set in environment variables")

#     request_ip = request.remote_addr
#     request_user_agent = request.headers.get('User-Agent')
    
#     payload = {
#         'id': user['_id'],
#         'organizationId': user['organizationId'],
#         'userName': user['userName'],
#         'ip': request_ip,
#         'userAgent': request_user_agent,
#         'iat': int(datetime.now().timestamp()),
#         'nbf': int(datetime.now().timestamp()),
#     }
    
#     exp = datetime.utcnow() + timedelta(hours=12)
#     payload['exp'] = exp
    
#     # Debug: Print payload before encoding
#     print(f"Token Payload: {payload}")
    
#     token = jwt.encode(payload, secret_key, algorithm='HS256')
    
#     # Debug: Print generated token
#     print(f"Generated Token: {token}")
    
#     return token

# @staticmethod
# def TokenVerification(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         auth_header = request.headers.get('Authorization')
        
#         if not auth_header:
#             return jsonify({"error": "Authorization token is missing"}), 403
        
#         try:
#             token = auth_header.split(' ')[1]
            
#             # Debug: Print received token
#             print(f"Received Token: {token}")
            
#             secret_key = os.getenv('JWT_SECRET')
            
#             # Debug: Print secret key
#             print(f"Verification Secret Key: {secret_key}")
            
#             payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
#             # Debug: Print decoded payload
#             print(f"Decoded Payload: {payload}")
            
#             organization_id = payload.get('organizationId')
            
#             if not organization_id:
#                 return jsonify({"error": "Invalid token structure"}), 403
            
#             request.organization_id = organization_id
        
#         except jwt.ExpiredSignatureError:
#             return jsonify({"error": "Token has expired"}), 401
        
#         except jwt.InvalidTokenError as e:
#             # Debug: Print specific error details
#             print(f"Token Verification Error: {e}")
#             return jsonify({"error": "Invalid token"}), 403
        
#         return f(*args, **kwargs)
    
#     return decorated

import jwt
import os
from datetime import datetime, timedelta
from flask import request, jsonify
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JWT secret key (from environment variables)
SECRET_KEY = os.getenv('JWT_SECRET')

if not SECRET_KEY:
    raise ValueError("JWT_SECRET is not set in environment variables")


class TokenService:
    @staticmethod
    def generate_token(user):
        print("hello")
        """
        Generate a JWT token for the user.

        :param user: Dictionary containing user information (id, organizationId, userName)
        :return: Encoded JWT token
        """
        # Collect client metadata
        request_ip = request.remote_addr
        request_user_agent = request.headers.get('User-Agent')

        # Define the payload with user details and metadata
        payload = {
            'id': user['id'],  # User ID
            'userName': user['userName'],  # User Name
            'organizationId': user['organizationId'],  # Organization ID
            'ip': request_ip,  # IP Address
            'userAgent': request_user_agent,  # User Agent
            'iat': int(datetime.utcnow().timestamp()),  # Issued At
            'nbf': int(datetime.utcnow().timestamp()),  # Not Before
            'exp': int((datetime.utcnow() + timedelta(hours=12)).timestamp())  # Expiry (12 hours)
        }

        # Generate and return the JWT token
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return token

    @staticmethod
    def verify_token(f):
        """
        Decorator to verify JWT token for protected routes.

        :param f: The route function to be decorated
        :return: The wrapped function with token verification
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            # Get the Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({"error": "Authorization token is missing"}), 403

            try:
                # Extract the token from the header
                token = auth_header.split(' ')[1]

                # Decode the token
                payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

                # Attach organizationId and other details to the request
                request.user = {
                    'id': payload['id'],
                    'organizationId': payload['organizationId'],
                    'userName': payload['userName'],
                }
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token has expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 403

            # Proceed to the original route function
            return f(*args, **kwargs)

        return decorated
