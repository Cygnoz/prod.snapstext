import jwt
import os
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
            # 'iat': int(datetime.utcnow().timestamp()),  # Issued At
            # 'nbf': int(datetime.utcnow().timestamp()),  # Not Before
            # 'exp': int((datetime.utcnow() + timedelta(hours=12)).timestamp())  # Expiry (12 hours)
        }

        # Generate and return the JWT token
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return token
    
    @staticmethod
    def verify_token(f):
        """
        Decorator to verify JWT token and return user details for protected routes.

        :param f: The route function to be decorated
        :return: The wrapped function with token verification and user details
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

                # Create user details dictionary
                user_details = {
                    'id': payload['id'],
                    'organizationId': payload['organizationId'],
                    'userName': payload['userName']
                }
                # Print user details for debugging
                print(f"User Details: {user_details}")
                # Attach user details to the request object
                request.user = user_details

                # Call the original function and get its response
                response = f(*args, **kwargs)

                # If response is a tuple (typical for Flask responses with status codes)
                if isinstance(response, tuple):
                    response_data, status_code = response
                    if isinstance(response_data, dict):
                        response_data['user'] = user_details
                        return jsonify(response_data), status_code
                    return response

                # If response is a dictionary
                if isinstance(response, dict):
                    response['user'] = user_details
                    return jsonify(response)

                # If response is already a Response object or any other type
                return response

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token has expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 403

        return decorated
