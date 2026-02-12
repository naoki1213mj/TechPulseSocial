"""Cosmos DB conversation history for Social AI Studio.

Stores and retrieves conversation history using Azure Cosmos DB (NoSQL API).
Falls back to in-memory storage when Cosmos DB is not configured.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from src.config import COSMOS_CONTAINER, COSMOS_DATABASE, COSMOS_ENDPOINT

logger = logging.getLogger(__name__)

# Lazy-init Cosmos client
_cosmos_client = None
_container = None
_initialized = False


def _get_container():
    """Get or create Cosmos DB container client (lazy init)."""
    global _cosmos_client, _container, _initialized

    if _initialized:
        return _container

    _initialized = True

    if not COSMOS_ENDPOINT:
        logger.info("COSMOS_ENDPOINT not set — using in-memory history")
        return None

    try:
        from azure.cosmos import CosmosClient, PartitionKey
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        _cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=credential)

        # Create database if not exists
        database = _cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE)

        # Create container with /userId partition key
        # Note: offer_throughput is omitted for serverless Cosmos DB accounts
        _container = database.create_container_if_not_exists(
            id=COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/userId"),
        )

        logger.info(
            "Cosmos DB connected: %s, db=%s, container=%s",
            COSMOS_ENDPOINT,
            COSMOS_DATABASE,
            COSMOS_CONTAINER,
        )
        return _container

    except Exception as e:
        logger.warning("Cosmos DB init failed, falling back to in-memory: %s", e)
        return None


# In-memory fallback
_memory_store: dict[str, dict[str, Any]] = {}


def save_conversation(
    conversation_id: str,
    title: str,
    messages: list[dict],
    user_id: str = "anonymous",
) -> None:
    """Save or update a conversation."""
    container = _get_container()
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": conversation_id,
        "userId": user_id,
        "title": title,
        "messages": messages,
        "updatedAt": now,
        "createdAt": now,  # Cosmos upsert preserves existing createdAt via partial update
    }

    if container is not None:
        try:
            # Try to preserve existing createdAt
            try:
                existing = container.read_item(
                    item=conversation_id, partition_key=user_id
                )
                doc["createdAt"] = existing.get("createdAt", now)
            except Exception:
                pass  # New document — use current time

            container.upsert_item(doc)
            logger.debug("Saved conversation %s to Cosmos DB", conversation_id)
        except Exception as e:
            logger.error("Failed to save to Cosmos DB: %s", e)
            # Fallback to memory
            _memory_store[conversation_id] = doc
    else:
        if conversation_id not in _memory_store:
            doc["createdAt"] = now
        else:
            doc["createdAt"] = _memory_store[conversation_id].get("createdAt", now)
        _memory_store[conversation_id] = doc


def list_conversations(user_id: str = "anonymous") -> list[dict]:
    """List all conversations for a user, ordered by most recent first."""
    container = _get_container()

    if container is not None:
        try:
            query = (
                "SELECT c.id, c.title, c.createdAt, c.updatedAt "
                "FROM c WHERE c.userId = @userId "
                "ORDER BY c.updatedAt DESC"
            )
            items = list(
                container.query_items(
                    query=query,
                    parameters=[{"name": "@userId", "value": user_id}],
                    enable_cross_partition_query=False,
                )
            )
            return items
        except Exception as e:
            logger.error("Failed to list conversations from Cosmos DB: %s", e)
            return []
    else:
        # In-memory fallback
        convos = [
            {
                "id": v["id"],
                "title": v["title"],
                "createdAt": v.get("createdAt", ""),
                "updatedAt": v.get("updatedAt", ""),
            }
            for v in _memory_store.values()
            if v.get("userId", "anonymous") == user_id
        ]
        convos.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        return convos


def get_conversation(conversation_id: str, user_id: str = "anonymous") -> dict | None:
    """Get a single conversation with messages."""
    container = _get_container()

    if container is not None:
        try:
            item = container.read_item(item=conversation_id, partition_key=user_id)
            return item
        except Exception:
            return None
    else:
        return _memory_store.get(conversation_id)


def delete_conversation(conversation_id: str, user_id: str = "anonymous") -> bool:
    """Delete a conversation."""
    container = _get_container()

    if container is not None:
        try:
            container.delete_item(item=conversation_id, partition_key=user_id)
            return True
        except Exception as e:
            logger.error("Failed to delete conversation: %s", e)
            return False
    else:
        if conversation_id in _memory_store:
            del _memory_store[conversation_id]
            return True
        return False
