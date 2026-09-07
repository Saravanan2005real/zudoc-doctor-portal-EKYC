import json
import hmac
import hashlib
import time
import logging
import requests
import threading
import requests
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal

from entities.webhook import WebhookEndpoint, WebhookDelivery, WebhookDeliveryStatus, WebhookEventType
from entities.application import Application

logger = logging.getLogger(__name__)

class WebhookDispatcher:
    """
    Handles dispatching webhooks to registered company endpoints.
    In a full production environment, this should be wired into Celery or an SQS queue.
    For this implementation, it is designed to be invoked via FastAPI BackgroundTasks.
    """
    
    MAX_RETRIES = 3
    
    @staticmethod
    def _generate_signature(payload: str, secret: str) -> str:
        secret_bytes = secret.encode('utf-8')
        payload_bytes = payload.encode('utf-8')
        signature = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
        return signature

    @staticmethod
    def trigger_event(company_id: int, application_id: int, event_type: WebhookEventType, payload: dict):
        """
        Entry point to trigger an event. Finds all matching endpoints and queues deliveries.
        """
        db: Session = SessionLocal()
        try:
            endpoints = db.query(WebhookEndpoint).filter(
                WebhookEndpoint.company_id == company_id,
                WebhookEndpoint.is_active == True
            ).all()
            
            for endpoint in endpoints:
                if event_type.value in endpoint.subscribed_events:
                    # Create the delivery record
                    delivery = WebhookDelivery(
                        endpoint_id=endpoint.id,
                        application_id=application_id,
                        event_type=event_type.value,
                        payload=payload,
                        status=WebhookDeliveryStatus.PENDING
                    )
                    db.add(delivery)
                    db.commit()
                    db.refresh(delivery)
                    
                    # Dispatch asynchronously
                    thread = threading.Thread(target=WebhookDispatcher._execute_delivery, args=(delivery.id,))
                    thread.start()
        finally:
            db.close()

    @staticmethod
    def _execute_delivery(delivery_id: int):
        db: Session = SessionLocal()
        try:
            delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
            if not delivery:
                return
                
            endpoint = delivery.endpoint
            
            # Formulate the payload string and signature
            timestamp = str(int(time.time()))
            # Standardize payload structure
            full_payload = {
                "event": delivery.event_type,
                "timestamp": timestamp,
                "data": delivery.payload
            }
            payload_str = json.dumps(full_payload, separators=(',', ':'))
            signature = WebhookDispatcher._generate_signature(payload_str, endpoint.secret_hash) # In prod, decrypt raw secret
            
            headers = {
                "Content-Type": "application/json",
                "ZuDoc-Signature": signature,
                "ZuDoc-Timestamp": timestamp
            }
            
            for attempt in range(1, WebhookDispatcher.MAX_RETRIES + 1):
                delivery.attempt_count = attempt
                try:
                    response = requests.post(endpoint.url, data=payload_str, headers=headers, timeout=10)
                    delivery.response_code = response.status_code
                    
                    if 200 <= response.status_code < 300:
                        delivery.status = WebhookDeliveryStatus.SUCCESS
                        delivery.delivered_at = datetime.utcnow()
                        break
                    else:
                        raise requests.exceptions.RequestException(f"Non-200 response: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Webhook delivery {delivery.id} failed attempt {attempt}: {str(e)}")
                    if attempt == WebhookDispatcher.MAX_RETRIES:
                        delivery.status = WebhookDeliveryStatus.FAILED
                    else:
                        # Simple exponential backoff sleep (not ideal for async threads, but okay for demo)
                        time.sleep(2 ** attempt)
            
            db.commit()
        finally:
            db.close()
