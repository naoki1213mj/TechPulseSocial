"""Tests for src/database.py — in-memory CRUD operations."""

import time

from src.database import (
    delete_conversation,
    get_conversation,
    list_conversations,
    save_conversation,
)


class TestSaveAndGet:
    """Test save and get operations."""

    def test_save_and_retrieve(self):
        save_conversation("conv-1", "First Chat", [{"role": "user", "content": "hi"}])
        result = get_conversation("conv-1")
        assert result is not None
        assert result["id"] == "conv-1"
        assert result["title"] == "First Chat"
        assert len(result["messages"]) == 1

    def test_get_nonexistent(self):
        result = get_conversation("does-not-exist")
        assert result is None

    def test_save_preserves_created_at(self):
        save_conversation("conv-2", "Chat 2", [{"role": "user", "content": "msg1"}])
        first = get_conversation("conv-2")
        created_at = first["createdAt"]

        # Small delay to ensure updatedAt differs
        time.sleep(0.01)

        # Update the same conversation
        save_conversation(
            "conv-2",
            "Chat 2 Updated",
            [
                {"role": "user", "content": "msg1"},
                {"role": "assistant", "content": "reply"},
            ],
        )
        updated = get_conversation("conv-2")
        assert updated["createdAt"] == created_at  # Preserved
        assert updated["title"] == "Chat 2 Updated"
        assert len(updated["messages"]) == 2

    def test_multiple_conversations(self):
        save_conversation("c1", "First", [])
        save_conversation("c2", "Second", [])
        assert get_conversation("c1") is not None
        assert get_conversation("c2") is not None


class TestListConversations:
    """Test list operation."""

    def test_empty_list(self):
        result = list_conversations()
        assert result == []

    def test_list_returns_all(self):
        save_conversation("c1", "First", [])
        save_conversation("c2", "Second", [])
        result = list_conversations()
        assert len(result) == 2

    def test_list_ordered_by_updated_at_desc(self):
        save_conversation("c1", "Old", [])
        time.sleep(0.01)
        save_conversation("c2", "New", [])
        result = list_conversations()
        assert result[0]["id"] == "c2"
        assert result[1]["id"] == "c1"

    def test_list_fields(self):
        save_conversation("c1", "Title", [])
        result = list_conversations()
        item = result[0]
        assert "id" in item
        assert "title" in item
        assert "createdAt" in item
        assert "updatedAt" in item

    def test_list_filters_by_user_id(self):
        save_conversation("c1", "User A chat", [], user_id="user-a")
        save_conversation("c2", "User B chat", [], user_id="user-b")
        result_a = list_conversations(user_id="user-a")
        result_b = list_conversations(user_id="user-b")
        assert len(result_a) == 1
        assert result_a[0]["id"] == "c1"
        assert len(result_b) == 1
        assert result_b[0]["id"] == "c2"


class TestDeleteConversation:
    """Test delete operation."""

    def test_delete_existing(self):
        save_conversation("c1", "To Delete", [])
        assert delete_conversation("c1") is True
        assert get_conversation("c1") is None

    def test_delete_nonexistent(self):
        assert delete_conversation("nope") is False

    def test_delete_does_not_affect_others(self):
        save_conversation("c1", "Keep", [])
        save_conversation("c2", "Delete", [])
        delete_conversation("c2")
        assert get_conversation("c1") is not None
        assert get_conversation("c2") is None
