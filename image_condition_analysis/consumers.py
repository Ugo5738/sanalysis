import json
from typing import Any, Dict
from urllib.parse import parse_qs

from analysis_service.config.logging_config import configure_logger
from channels.generic.websocket import AsyncWebsocketConsumer

logger = configure_logger(__name__)


class AnalysisProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Public, phone-less: use super_id passed via query string
        query_string = self.scope.get("query_string", b"")
        params = parse_qs(query_string.decode()) if query_string else {}
        super_id = params.get("super_id", [None])[0]
        if not super_id:
            logger.warning("WebSocket missing required super_id in query string")
            await self.close()
            return

        self.analysis_group_name = f"analysis_{super_id}"

        await self.channel_layer.group_add(self.analysis_group_name, self.channel_name)

        await self.accept()
        self.session_data: Dict[str, Any] = {}
        logger.info(f"WebSocket connected for group: {self.analysis_group_name}")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected. Close code: {close_code}")

        await self.channel_layer.group_discard(
            self.analysis_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        logger.info(f"=== MESSAGE RECEIVED ===")

        # Echo the message back to the WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    async def analysis_progress(self, event):
        message = event["message"]
        logger.info(f"Sending analysis progress: {message}")

        await self.send(
            text_data=json.dumps({"type": "analysis_progress", "message": message})
        )
