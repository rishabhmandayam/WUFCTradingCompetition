# exchange/participant_manager.py

from typing import Dict, Any
from Participant import Participant


class ParticipantManager:
    def __init__(self):
        self.participants: Dict[str, Participant] = {}

    def add_participant(self, participant: Participant):
        if participant.participant_id not in self.participants:
            self.participants[participant.participant_id] = participant

    def get_participant(self, participant_id: str) -> Participant:
        return self.participants.get(participant_id)
    
    def get_participant_balance(self, participant_id: str):
        currParticipant = self.participants.get(participant_id)
        if currParticipant is not None:
            return currParticipant.get_balance
        else: raise ValueError("looking for a participant that doesn't exist")

    def get_all_participants(self) -> Dict[str, Participant]:
        return self.participants

    def contains_participant(self, participant_id: str) -> bool:
        return participant_id in self.participants
    

    def send_execution_report(
        self, 
        buyer_participant_id: str, 
        seller_participant_id: str, 
        trade_details: Dict[str, Any]
    ):

        buyer_report = {
            'order_id': trade_details['buyer_order_id'],
            'symbol': trade_details['symbol'],
            'side': 'buy',
            'price': trade_details['buy_price'],
            'quantity': trade_details['quantity']
        }

        seller_report = {
            'order_id': trade_details['seller_order_id'],
            'symbol': trade_details['symbol'],
            'side': 'sell',
            'price': trade_details['sell_price'],
            'quantity': trade_details['quantity']
        }

        buyer = self.get_participant(buyer_participant_id)
        if buyer:
            buyer.receive_execution_report(buyer_report)


        seller = self.get_participant(seller_participant_id)
        if seller:
            seller.receive_execution_report(seller_report)


