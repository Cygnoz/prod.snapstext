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
