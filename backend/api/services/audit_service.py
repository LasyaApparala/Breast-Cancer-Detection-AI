import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import settings

class AuditService:
    """Service for comprehensive audit logging and compliance tracking"""
    
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        self.audit_collection = self.db.audit_logs
    
    @staticmethod
    async def log_analysis_created(
        analysis_id: str,
        user_id: str,
        input_hash: str
    ):
        """Log when analysis is created"""
        await AuditService._log_event({
            "event_type": "analysis_created",
            "analysis_id": analysis_id,
            "user_id": user_id,
            "input_hash": input_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": None,  # Would be populated from request
            "user_agent": None   # Would be populated from request
        })
    
    @staticmethod
    async def log_analysis_completed(
        analysis_id: str,
        user_id: str,
        result: Dict[str, Any]
    ):
        """Log when analysis is completed"""
        # Create result hash for integrity verification
        result_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        await AuditService._log_event({
            "event_type": "analysis_completed",
            "analysis_id": analysis_id,
            "user_id": user_id,
            "result_hash": result_hash,
            "severity": result.get("severity"),
            "confidence": result.get("confidence"),
            "clinician_review_required": result.get("audit_trail", {}).get("clinician_review_required"),
            "model_version": result.get("audit_trail", {}).get("model_version"),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def log_analysis_failed(
        analysis_id: str,
        user_id: str,
        error: str
    ):
        """Log when analysis fails"""
        await AuditService._log_event({
            "event_type": "analysis_failed",
            "analysis_id": analysis_id,
            "user_id": user_id,
            "error_message": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def log_review_requested(
        analysis_id: str,
        user_id: str
    ):
        """Log when clinician review is requested"""
        await AuditService._log_event({
            "event_type": "review_requested",
            "analysis_id": analysis_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def log_clinician_review(
        analysis_id: str,
        clinician_id: str,
        approved: bool,
        notes: Optional[str] = None
    ):
        """Log clinician review completion"""
        await AuditService._log_event({
            "event_type": "clinician_review",
            "analysis_id": analysis_id,
            "clinician_id": clinician_id,
            "approved": approved,
            "review_notes": notes,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def log_data_access(
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str
    ):
        """Log data access for compliance"""
        await AuditService._log_event({
            "event_type": "data_access",
            "user_id": user_id,
            "resource_type": resource_type,  # e.g., "analysis", "patient_record"
            "resource_id": resource_id,
            "action": action,  # e.g., "read", "update", "delete"
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def log_authentication_event(
        user_id: str,
        event_type: str,  # "login", "logout", "failed_login"
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True
    ):
        """Log authentication events"""
        await AuditService._log_event({
            "event_type": "authentication",
            "user_id": user_id,
            "auth_event": event_type,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def _log_event(event_data: Dict[str, Any]):
        """Internal method to write audit event to MongoDB"""
        try:
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            db = client[settings.MONGODB_DB_NAME]
            await db.audit_logs.insert_one(event_data)
            client.close()
        except Exception as e:
            # In production, this would go to a dead letter queue or secondary logging
            print(f"Failed to write audit log: {e}")
    
    @staticmethod
    async def get_audit_trail(
        analysis_id: str,
        limit: int = 100
    ) -> list:
        """Retrieve complete audit trail for an analysis"""
        try:
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            db = client[settings.MONGODB_DB_NAME]
            
            cursor = db.audit_logs.find(
                {"analysis_id": analysis_id}
            ).sort("timestamp", -1).limit(limit)
            
            trail = []
            async for document in cursor:
                # Convert ObjectId to string for JSON serialization
                if "_id" in document:
                    document["_id"] = str(document["_id"])
                trail.append(document)
            
            client.close()
            return trail
            
        except Exception as e:
            print(f"Failed to retrieve audit trail: {e}")
            return []
    
    @staticmethod
    async def verify_analysis_integrity(
        analysis_id: str,
        expected_input_hash: str,
        expected_result_hash: Optional[str] = None
    ) -> bool:
        """Verify the integrity of analysis data"""
        try:
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            db = client[settings.MONGODB_DB_NAME]
            
            # Check input hash
            input_log = await db.audit_logs.find_one({
                "analysis_id": analysis_id,
                "event_type": "analysis_created"
            })
            
            if not input_log or input_log.get("input_hash") != expected_input_hash:
                return False
            
            # Check result hash if provided
            if expected_result_hash:
                result_log = await db.audit_logs.find_one({
                    "analysis_id": analysis_id,
                    "event_type": "analysis_completed"
                })
                
                if not result_log or result_log.get("result_hash") != expected_result_hash:
                    return False
            
            client.close()
            return True
            
        except Exception as e:
            print(f"Failed to verify integrity: {e}")
            return False
