import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .services.blockchain_service import BlockchainService

class BlockchainConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # Join blockchain group
        await self.channel_layer.group_add("blockchain_updates", self.channel_name)
        
        # Send initial data
        initial_data = await self.get_blockchain_data()
        await self.send(text_data=json.dumps(initial_data))

    async def disconnect(self, close_code):
        # Leave blockchain group
        await self.channel_layer.group_discard("blockchain_updates", self.channel_name)

    async def blockchain_update(self, event):
        # Send update to WebSocket
        data = event['data']
        await self.send(text_data=json.dumps(data))

    @database_sync_to_async
    def get_blockchain_data(self):
        try:
            blockchain = BlockchainService()
            # Get latest blocks
            latest_blocks = blockchain.get_latest_blocks(10)
            # Get pending transactions
            pending_transactions = blockchain.get_pending_transactions()
            
            return {
                'type': 'blockchain_data',
                'blocks': latest_blocks,
                'pending_transactions': pending_transactions,
                'status': 'connected'
            }
        except Exception as e:
            return {
                'type': 'error',
                'message': str(e),
                'status': 'error'
            }