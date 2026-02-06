import re
from typing import Dict, List, Optional

class BillProcessor:
    """Process extracted text from bills to identify items and prices"""
    
    def __init__(self):
        # Common patterns for Indian bills
        self.serial_patterns = [
            r'(?:serial\s*no\.?|s\.?n\.?|sr\.?\s*no\.?)\s*:?\s*([A-Z0-9\-]+)',
            r'(?:item\s*code|product\s*code)\s*:?\s*([A-Z0-9\-]+)',
        ]
        
        self.hsn_patterns = [
            r'(?:hsn|hsn\s*code)\s*:?\s*(\d{4,8})',
            r'hsn[:/\s]*(\d{4,8})',
        ]
        
        self.price_patterns = [
            r'(?:rs\.?|₹|inr)\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
            r'(?:amount|price|rate|value)\s*:?\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
            r'(?:total|subtotal)\s*:?\s*(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
        ]

        self.quantity_patterns = [
            r'(?:qty|quantity|units?|nos?|pcs?|pieces?)\s*:?\s*(\d+)',
            r'(\d+)\s*(?:qty|units?|nos?|pcs?|pieces?)',
        ]

    def parse_bill(self, text: str, bill_type: str = 'purchase') -> List[Dict]:
        """
        Parse bill text and extract items
        bill_type: 'purchase' or 'sale'
        Returns list of items with their details
        """
        items = []
        lines = text.split('\n')
        
        # Try to find tabular data first
        table_items = self._parse_table_format(lines, bill_type)
        if table_items:
            return table_items
        
        # Fallback to line-by-line parsing
        current_item = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                if current_item:
                    # Check if we have minimum required fields
                    if self._is_valid_item(current_item):
                        items.append(current_item)
                    current_item = {}
                continue
            
            # Extract serial number
            serial = self._extract_serial_number(line)
            if serial and 'serial_number' not in current_item:
                current_item['serial_number'] = serial
            
            # Extract HSN code
            hsn = self._extract_hsn_code(line)
            if hsn and 'hsn_code' not in current_item:
                current_item['hsn_code'] = hsn
            
            # Extract item name
            if 'item_name' not in current_item:
                item_name = self._extract_item_name(line)
                if item_name:
                    current_item['item_name'] = item_name
            
            # Extract quantity
            quantity = self._extract_quantity(line)
            if quantity and 'quantity' not in current_item:
                current_item['quantity'] = quantity

            # Extract price
            price = self._extract_price(line)
            if price and (bill_type + '_price') not in current_item:
                current_item[bill_type + '_price'] = price
        
        # Add last item if exists
        if current_item and self._is_valid_item(current_item):
            items.append(current_item)
        
        return items

    def _parse_table_format(self, lines: List[str], bill_type: str) -> List[Dict]:
        """Parse bills that have tabular format"""
        items = []
        header_found = False
        header_indices = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for header row
            if not header_found:
                lower_line = line.lower()
                if any(keyword in lower_line for keyword in ['item', 'description', 'particular', 'product']):
                    # Try to identify column positions
                    header_found = True
                    if 'serial' in lower_line or 's.no' in lower_line or 's no' in lower_line:
                        header_indices['serial'] = True
                    if 'hsn' in lower_line:
                        header_indices['hsn'] = True
                    if 'qty' in lower_line or 'quantity' in lower_line or 'units' in lower_line:
                        header_indices['quantity'] = True
                    if 'price' in lower_line or 'amount' in lower_line or 'rate' in lower_line:
                        header_indices['price'] = True
                continue
            
            # Parse data rows
            if header_found:
                item = self._parse_table_row(line, bill_type)
                if item and self._is_valid_item(item):
                    items.append(item)
        
        return items

    def _parse_table_row(self, line: str, bill_type: str) -> Optional[Dict]:
        """Parse a single table row"""
        item = {}
        
        # Split by multiple spaces or tabs
        parts = re.split(r'\s{2,}|\t', line)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check for serial number
            if re.match(r'^[A-Z0-9\-]+$', part) and len(part) <= 15:
                if 'serial_number' not in item:
                    item['serial_number'] = part
            
            # Check for HSN code
            if re.match(r'^\d{4,8}$', part):
                item['hsn_code'] = part
            
            # Check for quantity (small numbers typically 1-999)
            if re.match(r'^\d{1,3}$', part) and 'quantity' not in item:
                qty = int(part)
                if 1 <= qty <= 999:
                    item['quantity'] = qty
                    continue

            # Check for price
            price = self._extract_price(part)
            if price:
                item[bill_type + '_price'] = price

            # Check for item name (usually longer text)
            elif len(part) > 3 and not part.isdigit() and 'item_name' not in item:
                # Avoid storing serial numbers or codes as item names
                if not re.match(r'^[A-Z0-9\-]+$', part):
                    item['item_name'] = part
        
        return item if item else None

    def _extract_serial_number(self, text: str) -> Optional[str]:
        """Extract serial number from text"""
        text_lower = text.lower()
        for pattern in self.serial_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Look for alphanumeric codes
        match = re.search(r'\b([A-Z]{2,}\d{2,}|\d{2,}[A-Z]{2,})\b', text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return None

    def _extract_hsn_code(self, text: str) -> Optional[str]:
        """Extract HSN code from text"""
        for pattern in self.hsn_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_quantity(self, text: str) -> Optional[int]:
        """Extract quantity from text"""
        for pattern in self.quantity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    qty = int(match.group(1))
                    if 1 <= qty <= 99999:  # Reasonable quantity range
                        return qty
                except ValueError:
                    continue
        return None

    def _extract_item_name(self, text: str) -> Optional[str]:
        """Extract item name from text"""
        # Remove common prefixes and clean up
        text = re.sub(r'^(?:item|product|description|particular)\s*:?\s*', '', text, flags=re.IGNORECASE)
        text = text.strip()
        
        # Item name should be reasonable length and contain letters
        if len(text) > 2 and re.search(r'[a-zA-Z]', text):
            # Remove serial numbers, HSN codes, and prices from the name
            text = re.sub(r'\b(?:hsn|s\.?n\.?)\s*:?\s*\d+', '', text, flags=re.IGNORECASE)
            text = re.sub(r'(?:rs\.?|₹)\s*\d+', '', text, flags=re.IGNORECASE)
            text = text.strip()
            
            if text:
                return text
        
        return None

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from text"""
        for pattern in self.price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        # Fallback: look for any number with optional decimal
        match = re.search(r'\b(\d+(?:,\d+)*(?:\.\d{2})?)\b', text)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
                # Reasonable price range
                if 0.01 <= price <= 10000000:
                    return price
            except ValueError:
                pass
        
        return None

    def _is_valid_item(self, item: Dict) -> bool:
        """Check if item has minimum required fields"""
        # Must have at least item name or serial number
        has_identifier = 'item_name' in item or 'serial_number' in item or 'hsn_code' in item
        # Must have price
        has_price = 'purchase_price' in item or 'sale_price' in item
        
        return has_identifier and has_price

    def normalize_item_name(self, name: str) -> str:
        """Normalize item name for matching"""
        if not name:
            return ""
        # Convert to lowercase, remove extra spaces and special characters
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
