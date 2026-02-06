from typing import Dict, List, Tuple
from bill_processor import BillProcessor

class ItemMatcher:
    """Match purchase and sale items to calculate profit/loss"""
    
    def __init__(self):
        self.processor = BillProcessor()
    
    def match_items(self, purchase_items: List[Dict], sale_items: List[Dict]) -> List[Dict]:
        """
        Match purchase items with sale items
        Returns list of matched items with profit/loss calculation
        """
        matched_items = []
        unmatched_purchases = []
        unmatched_sales = []
        
        # Create a copy of sale items to track matched ones
        remaining_sales = sale_items.copy()
        
        for purchase_item in purchase_items:
            match_found = False
            best_match = None
            best_match_idx = -1
            best_match_score = 0
            
            for idx, sale_item in enumerate(remaining_sales):
                score = self._calculate_match_score(purchase_item, sale_item)
                if score > best_match_score:
                    best_match_score = score
                    best_match = sale_item
                    best_match_idx = idx
            
            # If match score is high enough, consider it a match
            if best_match_score >= 0.7:  # 70% confidence threshold
                matched_item = self._create_matched_item(purchase_item, best_match)
                matched_items.append(matched_item)
                remaining_sales.pop(best_match_idx)
                match_found = True
            
            if not match_found:
                # Add as unmatched purchase
                unmatched_item = self._create_unmatched_item(purchase_item, 'purchase')
                unmatched_purchases.append(unmatched_item)
        
        # Remaining sales are unmatched
        for sale_item in remaining_sales:
            unmatched_item = self._create_unmatched_item(sale_item, 'sale')
            unmatched_sales.append(unmatched_item)
        
        return {
            'matched': matched_items,
            'unmatched_purchases': unmatched_purchases,
            'unmatched_sales': unmatched_sales
        }
    
    def _calculate_match_score(self, item1: Dict, item2: Dict) -> float:
        """
        Calculate match score between two items (0 to 1)
        Priority: Serial Number > HSN Code > Item Name
        """
        score = 0.0
        weights = {
            'serial_number': 0.5,
            'hsn_code': 0.3,
            'item_name': 0.2
        }
        
        # Check serial number match
        if 'serial_number' in item1 and 'serial_number' in item2:
            if item1['serial_number'] == item2['serial_number']:
                score += weights['serial_number']
        
        # Check HSN code match
        if 'hsn_code' in item1 and 'hsn_code' in item2:
            if item1['hsn_code'] == item2['hsn_code']:
                score += weights['hsn_code']
        
        # Check item name match
        if 'item_name' in item1 and 'item_name' in item2:
            name1 = self.processor.normalize_item_name(item1['item_name'])
            name2 = self.processor.normalize_item_name(item2['item_name'])
            
            # Exact match
            if name1 == name2:
                score += weights['item_name']
            # Partial match (one contains the other)
            elif name1 and name2 and (name1 in name2 or name2 in name1):
                score += weights['item_name'] * 0.7
            # Similar words
            elif self._similarity_score(name1, name2) > 0.8:
                score += weights['item_name'] * 0.5
        
        return score
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using word overlap"""
        if not str1 or not str2:
            return 0.0
        
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_matched_item(self, purchase_item: Dict, sale_item: Dict) -> Dict:
        """Create a matched item with profit/loss calculation"""
        purchase_price = purchase_item.get('purchase_price', 0)
        sale_price = sale_item.get('sale_price', 0)
        profit_loss = sale_price - purchase_price
        purchase_qty = purchase_item.get('quantity', 1)
        sale_qty = sale_item.get('quantity', 1)

        matched_item = {
            'serial_number': purchase_item.get('serial_number') or sale_item.get('serial_number', 'N/A'),
            'item_name': purchase_item.get('item_name') or sale_item.get('item_name', 'Unknown'),
            'hsn_code': purchase_item.get('hsn_code') or sale_item.get('hsn_code', 'N/A'),
            # Preserve both source quantities so mismatches are visible
            'quantity': sale_qty if sale_qty else purchase_qty,
            'purchase_quantity': purchase_qty,
            'sale_quantity': sale_qty,
            'quantity_mismatch': purchase_qty != sale_qty,
            'purchase_price': purchase_price,
            'sale_price': sale_price,
            'profit_loss': profit_loss,
            'profit_loss_percentage': (profit_loss / purchase_price * 100) if purchase_price > 0 else 0,
            'status': 'matched'
        }

        return matched_item
    
    def _create_unmatched_item(self, item: Dict, item_type: str) -> Dict:
        """Create an unmatched item entry"""
        unmatched_item = {
            'serial_number': item.get('serial_number', 'N/A'),
            'item_name': item.get('item_name', 'Unknown'),
            'hsn_code': item.get('hsn_code', 'N/A'),
            'quantity': item.get('quantity', 1),
            'purchase_price': item.get('purchase_price', 0) if item_type == 'purchase' else 0,
            'sale_price': item.get('sale_price', 0) if item_type == 'sale' else 0,
            'profit_loss': 0,
            'profit_loss_percentage': 0,
            'status': f'unmatched_{item_type}'
        }

        return unmatched_item
    
    def calculate_summary(self, matched_results: Dict) -> Dict:
        """Calculate summary statistics"""
        matched = matched_results['matched']
        unmatched_purchases = matched_results['unmatched_purchases']
        unmatched_sales = matched_results['unmatched_sales']
        
        total_purchase = sum(item['purchase_price'] for item in matched)
        total_sale = sum(item['sale_price'] for item in matched)
        total_profit_loss = total_sale - total_purchase
        
        total_unmatched_purchase = sum(item['purchase_price'] for item in unmatched_purchases)
        total_unmatched_sale = sum(item['sale_price'] for item in unmatched_sales)
        
        profit_items = [item for item in matched if item['profit_loss'] > 0]
        loss_items = [item for item in matched if item['profit_loss'] < 0]
        
        summary = {
            'total_matched_items': len(matched),
            'total_unmatched_purchases': len(unmatched_purchases),
            'total_unmatched_sales': len(unmatched_sales),
            'total_purchase_value': total_purchase,
            'total_sale_value': total_sale,
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_percentage': (total_profit_loss / total_purchase * 100) if total_purchase > 0 else 0,
            'profit_items_count': len(profit_items),
            'loss_items_count': len(loss_items),
            'total_unmatched_purchase_value': total_unmatched_purchase,
            'total_unmatched_sale_value': total_unmatched_sale
        }
        
        return summary
