import os
import base64
import json
import re
import mimetypes
import requests
from dotenv import load_dotenv

load_dotenv()


class NvidiaNIMService:
    """NVIDIA NIM Service using Nemotron Vision-Language Model for bill extraction"""
    
    def __init__(self):
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.api_key = os.getenv("NVIDIA_API_KEY", "")
        self.model = "nvidia/nemotron-nano-12b-v2-vl"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Prompt for extracting bill items
        self.extraction_prompt = """Analyze this bill/invoice image and extract ALL items listed.

This could be either:
1. An ITEMIZED INVOICE with product names, quantities, and prices
2. A TAX SUMMARY/ANALYSIS document with HSN/SAC codes and taxable values

For each item/row, extract:
- serial_number: Product serial number, S.No, or item code (if visible)
- item_name: Name/description of the product (if available, otherwise null)
- hsn_code: HSN/SAC code (usually 4-8 digits)
- quantity: The quantity/qty of items (just the number, default to 1 if not visible)
- price: The price/amount/taxable value for this item (just the number)

For TAX SUMMARY documents: Extract each HSN/SAC row with its Taxable Value as the price.

Return ONLY a JSON array with the items. Example formats:

Itemized invoice:
[
  {"serial_number": "1", "item_name": "Samsung TV 55 inch", "hsn_code": "8528", "quantity": 1, "price": 45000},
  {"serial_number": "2", "item_name": "LG Refrigerator", "hsn_code": "8418", "quantity": 2, "price": 32000}
]

Tax summary (HSN-wise):
[
  {"serial_number": null, "item_name": null, "hsn_code": "85285200", "quantity": 1, "price": 16101.70},
  {"serial_number": null, "item_name": null, "hsn_code": "85235100", "quantity": 1, "price": 15254.40}
]

If no items are found, return: []
Return ONLY the JSON array, no other text."""

    def _read_image_as_base64(self, path):
        """Read image file and convert to base64"""
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("utf-8")
        mime, _ = mimetypes.guess_type(path)
        if mime is None:
            mime = "image/jpeg"
        return b64, mime

    def extract_text_from_image(self, image_path):
        """
        Extract text from image using NVIDIA Nemotron VLM
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        try:
            b64_str, mime = self._read_image_as_base64(image_path)
            
            print(f"\n{'='*50}")
            print(f"[OCR] Processing image: {image_path}")
            print(f"[OCR] Image size: {len(b64_str)} bytes (base64)")
            
            # Build content with image and prompt
            content = [
                {"type": "text", "text": self.extraction_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{b64_str}"
                    }
                }
            ]
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.2,  # Low temperature for more consistent output
                "top_p": 0.9,
                "stream": False
            }

            print(f"[OCR] Sending request to NVIDIA API...")
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json=payload, 
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"[OCR] Response received successfully")
            
            # Extract the response text
            extracted_text = self._parse_response(result)
            print(f"[OCR] Extracted content:\n{extracted_text[:500]}..." if len(extracted_text) > 500 else f"[OCR] Extracted content:\n{extracted_text}")
            print(f"{'='*50}\n")
            
            return extracted_text

        except requests.HTTPError as e:
            print(f"[OCR ERROR] HTTP Error: {e}")
            print(f"[OCR ERROR] Status: {response.status_code}")
            print(f"[OCR ERROR] Body: {response.text}")
            raise
        except Exception as e:
            print(f"[OCR ERROR] Error extracting text: {e}")
            raise

    def _parse_response(self, response):
        """Parse API response to extract text content"""
        try:
            # Standard OpenAI-style response format
            if isinstance(response, dict):
                choices = response.get('choices', [])
                if choices and len(choices) > 0:
                    message = choices[0].get('message', {})
                    content = message.get('content', '')
                    return content
            
            print(f"[OCR WARNING] Unexpected response format: {response}")
            return str(response)
        
        except Exception as e:
            print(f"[OCR ERROR] Error parsing response: {e}")
            return ""

    def extract_items_from_image(self, image_path, bill_type='purchase'):
        """
        Extract structured items directly from bill image
        
        Args:
            image_path: Path to the image file
            bill_type: 'purchase' or 'sale'
            
        Returns:
            List of item dictionaries
        """
        try:
            # Get raw text/JSON from VLM
            raw_response = self.extract_text_from_image(image_path)
            
            # Try to parse as JSON
            items = self._parse_json_items(raw_response, bill_type)
            
            print(f"[PARSER] Extracted {len(items)} items from bill")
            for i, item in enumerate(items):
                print(f"[PARSER] Item {i+1}: {item}")
            
            return items
            
        except Exception as e:
            print(f"[PARSER ERROR] Failed to extract items: {e}")
            return []

    def _parse_json_items(self, response_text, bill_type):
        """Parse JSON items from VLM response"""
        items = []
        
        try:
            # Clean up the response - remove markdown code blocks if present
            cleaned = response_text.strip()
            
            # Remove markdown code block markers
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Try to find JSON array in the response
            # Look for [ ... ] pattern
            match = re.search(r'\[[\s\S]*\]', cleaned)
            if match:
                json_str = match.group(0)
                parsed = json.loads(json_str)
                
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            # Normalize the item
                            price_key = f'{bill_type}_price'
                            item_name = item.get('item_name') or item.get('name') or item.get('description') or item.get('product')
                            hsn_code = str(item.get('hsn_code') or item.get('hsn') or item.get('hsncode') or item.get('hsn_sac') or '')

                            # Use HSN code as fallback for item_name if not available
                            if not item_name and hsn_code:
                                item_name = f"HSN: {hsn_code}"

                            normalized = {
                                'serial_number': item.get('serial_number') or item.get('sn') or item.get('serial'),
                                'item_name': item_name,
                                'hsn_code': hsn_code,
                                'quantity': self._parse_quantity(item.get('quantity') or item.get('qty') or item.get('units') or 1),
                                price_key: self._parse_price(item.get('price') or item.get('amount') or item.get('value') or item.get('taxable_value') or 0)
                            }

                            # Only add if we have at least a name/hsn or price
                            if normalized['item_name'] or normalized[price_key]:
                                items.append(normalized)
            else:
                print(f"[PARSER WARNING] No JSON array found in response")
                
        except json.JSONDecodeError as e:
            print(f"[PARSER ERROR] JSON decode error: {e}")
            print(f"[PARSER] Response was: {response_text[:500]}")
        except Exception as e:
            print(f"[PARSER ERROR] Error parsing items: {e}")
        
        return items

    def _parse_price(self, price_value):
        """Parse price value to float"""
        if isinstance(price_value, (int, float)):
            return float(price_value)

        if isinstance(price_value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[₹$,\s]', '', price_value)
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        return 0.0

    def _parse_quantity(self, qty_value):
        """Parse quantity value to integer"""
        if isinstance(qty_value, int):
            return max(1, qty_value)

        if isinstance(qty_value, float):
            return max(1, int(qty_value))

        if isinstance(qty_value, str):
            s = qty_value.strip()

            # Handle simple fractions like "1/2"
            frac_match = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', s)
            if frac_match:
                num = int(frac_match.group(1))
                den = int(frac_match.group(2))
                if den != 0:
                    try:
                        return max(1, int(float(num) / float(den)))
                    except (ValueError, OverflowError):
                        return 1
                return 1

            # Extract the first integer or decimal number from the string
            num_match = re.search(r'(\d+(?:\.\d+)?)', s)
            if num_match:
                num_str = num_match.group(1)
                try:
                    return max(1, int(float(num_str)))
                except ValueError:
                    return 1

            return 1

        return 1
