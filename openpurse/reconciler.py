from typing import List, Optional, Set
from .models import PaymentMessage, Pain002Message

class Reconciler:
    """
    Engine to link related financial messages across their lifecycle.
    
    This utility allows matching disjointed messages (e.g. pain.001 initiation vs 
    pain.002 status report) using shared identifiers and amount verification.
    """

    @staticmethod
    def is_match(msg_a: PaymentMessage, msg_b: PaymentMessage, fuzzy_amount: bool = False) -> bool:
        """
        Determines if two messages are logically linked.
        
        Matches primarily on EndToEndId. Also checks MsgId for related status reports (pain.002).
        If fuzzy_amount is True, allows matching even if amounts differ slightly (to handle fees).
        """
        id_match = False

        # 1. Direct End-to-End Match (Strongest link)
        if msg_a.end_to_end_id and msg_b.end_to_end_id:
            if msg_a.end_to_end_id == msg_b.end_to_end_id:
                id_match = True

        # 2. Status Report Reference (pain.002 matching original MsgId)
        if not id_match:
            if isinstance(msg_a, Pain002Message) and msg_a.original_message_id == msg_b.message_id:
                id_match = True
            elif isinstance(msg_b, Pain002Message) and msg_b.original_message_id == msg_a.message_id:
                id_match = True

        if not id_match:
            return False

        # 3. Reference in amounts (Verification step)
        if msg_a.amount and msg_b.amount and msg_a.currency == msg_b.currency:
            try:
                amt_a = float(msg_a.amount)
                amt_b = float(msg_b.amount)
                
                if fuzzy_amount:
                    # Allow 1% difference for fees
                    return abs(amt_a - amt_b) <= (max(amt_a, amt_b) * 0.01)
                else:
                    return amt_a == amt_b
            except ValueError:
                # If amounts aren't numeric, fallback to string match if they exist
                return msg_a.amount == msg_b.amount

        return True # Default to True if one amount is missing but IDs match

    @staticmethod
    def find_matches(primary: PaymentMessage, candidates: List[PaymentMessage]) -> List[PaymentMessage]:
        """
        Returns a list of all messages in candidates that match the primary message.
        """
        matches = []
        for candidate in candidates:
            if candidate == primary:
                continue
            if Reconciler.is_match(primary, candidate):
                matches.append(candidate)
        return matches

    @staticmethod
    def trace_lifecycle(seed: PaymentMessage, all_messages: List[PaymentMessage]) -> List[PaymentMessage]:
        """
        Recursively builds a chronological chain of related messages starting from a seed.
        """
        timeline = [seed]
        seen_ids = {id(seed)}
        
        queue = [seed]
        while queue:
            current = queue.pop(0)
            matches = Reconciler.find_matches(current, all_messages)
            
            for match in matches:
                if id(match) not in seen_ids:
                    seen_ids.add(id(match))
                    timeline.append(match)
                    queue.append(match)
                    
        # Note: In a real world scenario, we would sort by a timestamp if available.
        # Since our models currently treat timestamps as optional strings, we return the discovery order.
        return timeline
