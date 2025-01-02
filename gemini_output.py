import google.generativeai as genai
from pathlib import Path
import mimetypes
import os
from dotenv import load_dotenv

load_dotenv()
# API key
GOOGLE_API_KEY = os.getenv('API_KEY')

# Configure API key
genai.configure(api_key=GOOGLE_API_KEY)

# Model Configuration
MODEL_CONFIG = {
    "temperature": 0.2,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

# Safety Settings of Model
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
]

# Initialize the model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-8b",
    generation_config=MODEL_CONFIG,
    safety_settings=safety_settings
)

def image_format(image_path):
    """
    Validate and read an image file. Supports PDF, PNG, JPEG, and WEBP.
    
    Parameters:
        image_path (str): Path to the image file.
        
    Returns:
        list: List containing MIME type and image data.
    
    Raises:
        FileNotFoundError: If the image file does not exist.
        ValueError: If the image format is unsupported.
    """
    img = Path(image_path)
    if not img.exists():
        raise FileNotFoundError(f"Could not find image: {img}")

    # Detect MIME type based on file extension
    mime_type, _ = mimetypes.guess_type(image_path)
    
    if mime_type not in ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']:
        raise ValueError(f"Unsupported file type: {mime_type}. Supported types are PDF, PNG, JPEG, and WEBP.")
    
    image_parts = [
        {
            "mime_type": mime_type,  # Automatically assign the correct MIME type
            "data": img.read_bytes(),
        }
    ]
    return image_parts

def gemini_output(image_path, system_prompt, user_prompt):
    """
    Generate output by processing an image with the Gemini model.
    
    Parameters:
        image_path (str): Path to the image file.
        system_prompt (str): System-level prompt to provide context.
        user_prompt (str): User-level prompt to instruct the model.
        
    Returns:
        str: The model's generated output.
    """
    
    image_info = image_format(image_path)
    input_prompt = [system_prompt, image_info[0], user_prompt]
    
    # Generate content using the model
    response = model.generate_content(input_prompt)
    
    # Return the text result from the response
    return response.text

