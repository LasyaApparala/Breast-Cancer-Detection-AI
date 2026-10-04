"""
MongoDB Audit Trail Service for HIPAA-compliant logging.

Implements append-only audit logging for all clinical actions,
including physician overrides, with MongoDB storage.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import motor.motor_asyncio
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """Audit trail entry model."""
    
    entry_id: str = Field(default_factory=lambda: str(UUID))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    user_name: str
    user_role: str
    action_type: str  # "classification", "override", "view", "export", etc.
    session_id: Optional[str] = None
    patient_id: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list)
    
    # Action-specific data
    action_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    source_service: str = "backend"
    
    # Compliance fields
    phi_accessed: bool = False
    phi_modified: bool = False


class OverrideAuditEntry(BaseModel):
    """Specific audit entry for physician overrides."""
    
    entry_id: str = Field(default_factory=lambda: str(UUID))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    user_name: str
    user_role: str
    license_number: str
    session_id: str
    
    # Override details
    original_label: str
    override_label: str
    original_confidence: float
    override_reason: str
    clinical_notes: Optional[str] = None
    
    # Context
    patient_id: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list)
    features_used: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class MongoDBAuditService:
    """
    MongoDB-based audit trail service.
    
    Provides append-only logging for HIPAA compliance with
    immutable audit trails for all clinical actions.
    """
    
    def __init__(self, mongodb_url: str, database_name: str):
        """
        Initialize MongoDB audit service.
        
        Parameters
        ----------
        mongodb_url : str
            MongoDB connection string
        database_name : str
            Database name for audit collections
        """
        self.mongodb_url = mongodb_url
        self.database_name = database_name
        self.client = None
        self.db = None
        self.audit_collection = None
        self.override_collection = None
    
    async def connect(self) -> None:
        """Establish MongoDB connection."""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_url)
            self.db = self.client[self.database_name]
            
            # Create collections with indexes
            self.audit_collection = self.db.audit_trail
            self.override_collection = self.db.physician_overrides
            
            # Create indexes for efficient querying
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB audit database: {self.database_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self) -> None:
        """Create indexes for audit collections."""
        # Audit trail indexes
        await self.audit_collection.create_index([("timestamp", -1)])
        await self.audit_collection.create_index([("user_id", 1)])
        await self.audit_collection.create_index([("session_id", 1)])
        await self.audit_collection.create_index([("action_type", 1)])
        await self.audit_collection.create_index([("patient_id", 1)])
        
        # Override collection indexes
        await self.override_collection.create_index([("timestamp", -1)])
        await self.override_collection.create_index([("user_id", 1)])
        await self.override_collection.create_index([("session_id", 1)])
        await self.override_collection.create_index([("license_number", 1)])
        
        logger.info("MongoDB audit indexes created")
    
    async def log_audit_entry(self, entry: AuditEntry) -> str:
        """
        Log an audit entry to MongoDB.
        
        Parameters
        ----------
        entry : AuditEntry
            Audit entry to log
        
        Returns
        -------
        str
            Entry ID of the logged entry
        """
        try:
            result = await self.audit_collection.insert_one(entry.dict())
            logger.info(f"Audit entry logged: {entry.entry_id}")
            return entry.entry_id
            
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
            raise
    
    async def log_override(
        self,
        override_entry: OverrideAuditEntry
    ) -> str:
        """
        Log a physician override to MongoDB.
        
        Parameters
        ----------
        override_entry : OverrideAuditEntry
            Override entry to log
        
        Returns
        -------
        str
            Entry ID of the logged override
        """
        try:
            # Log to both general audit and specific override collection
            await self.log_audit_entry(
                AuditEntry(
                    user_id=override_entry.user_id,
                    user_name=override_entry.user_name,
                    user_role=override_entry.user_role,
                    action_type="physician_override",
                    session_id=override_entry.session_id,
                    patient_id=override_entry.patient_id,
                    document_ids=override_entry.document_ids,
                    action_data={
                        "original_label": override_entry.original_label,
                        "override_label": override_entry.override_label,
                        "original_confidence": override_entry.original_confidence,
                        "override_reason": override_entry.override_reason,
                        "clinical_notes": override_entry.clinical_notes,
                        "license_number": override_entry.license_number
                    },
                    phi_accessed=True,
                    phi_modified=True
                )
            )
            
            result = await self.override_collection.insert_one(override_entry.dict())
            logger.info(f"Physician override logged: {override_entry.entry_id}")
            return override_entry.entry_id
            
        except Exception as e:
            logger.error(f"Failed to log physician override: {e}")
            raise
    
    async def get_user_audit_trail(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get audit trail for a specific user.
        
        Parameters
        ----------
        user_id : str
            User ID to query
        limit : int
            Maximum number of entries to return
        
        Returns
        -------
        List[Dict]
            List of audit entries
        """
        try:
            cursor = self.audit_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(limit)
            
            entries = await cursor.to_list(length=limit)
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get user audit trail: {e}")
            return []
    
    async def get_session_audit_trail(
        self,
        session_id: str
    ) -> List[Dict]:
        """
        Get complete audit trail for a session.
        
        Parameters
        ----------
        session_id : str
            Session ID to query
        
        Returns
        -------
        List[Dict]
            List of audit entries for the session
        """
        try:
            cursor = self.audit_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", 1)
            
            entries = await cursor.to_list(length=None)
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get session audit trail: {e}")
            return []
    
    async def get_overrides_by_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get all overrides by a specific physician.
        
        Parameters
        ----------
        user_id : str
            User ID to query
        limit : int
            Maximum number of entries to return
        
        Returns
        -------
        List[Dict]
            List of override entries
        """
        try:
            cursor = self.override_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", -1).limit(limit)
            
            entries = await cursor.to_list(length=limit)
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get user overrides: {e}")
            return []
    
    async def get_overrides_by_session(
        self,
        session_id: str
    ) -> List[Dict]:
        """
        Get all overrides for a specific session.
        
        Parameters
        ----------
        session_id : str
            Session ID to query
        
        Returns
        -------
        List[Dict]
            List of override entries
        """
        try:
            cursor = self.override_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", -1)
            
            entries = await cursor.to_list(length=None)
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get session overrides: {e}")
            return []
    
    async def get_override_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get statistics on physician overrides.
        
        Parameters
        ----------
        start_date : datetime, optional
            Start date for statistics
        end_date : datetime, optional
            End date for statistics
        
        Returns
        -------
        Dict
            Override statistics
        """
        try:
            query = {}
            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date
                if end_date:
                    query["timestamp"]["$lte"] = end_date
            
            total_overrides = await self.override_collection.count_documents(query)
            
            # Group by user
            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$user_id",
                    "count": {"$sum": 1},
                    "user_name": {"$first": "$user_name"},
                    "license_number": {"$first": "$license_number"}
                }},
                {"$sort": {"count": -1}}
            ]
            
            user_stats = await self.override_collection.aggregate(pipeline).to_list(length=None)
            
            # Group by original label
            label_pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$original_label",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            label_stats = await self.override_collection.aggregate(label_pipeline).to_list(length=None)
            
            return {
                "total_overrides": total_overrides,
                "by_user": user_stats,
                "by_original_label": label_stats,
                "date_range": {
                    "start": start_date,
                    "end": end_date
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get override statistics: {e}")
            return {}
    
    async def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB audit connection closed")
