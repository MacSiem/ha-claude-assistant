"""Action handler for Claude Assistant integration."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service import async_call_from_config

from .const import (
    DANGEROUS_DOMAINS,
    DANGEROUS_SERVICES,
    ACTION_CATEGORY_SAFE,
    ACTION_CATEGORY_MODERATE,
    ACTION_CATEGORY_DANGEROUS,
    ACTION_CATEGORY_CRITICAL,
    ACTION_CONFIRMATION_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ActionHandler:
    """Handles action classification and confirmation."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize action handler.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass
        self.pending_actions: dict[str, dict[str, Any]] = {}
        self.action_confirmations: dict[str, asyncio.Event] = {}

    async def async_classify_action(
        self, domain: str, service: str, entity_id: Optional[str] = None
    ) -> str:
        """Classify an action by danger level.

        Args:
            domain: Service domain
            service: Service name
            entity_id: Optional target entity ID

        Returns:
            Action category (safe, moderate, dangerous, critical)
        """
        service_call = f"{domain}.{service}"

        # Critical operations
        if domain in ["alarm_control_panel"] and service in ["alarm_disarm"]:
            return ACTION_CATEGORY_CRITICAL

        # Dangerous operations
        if service_call in DANGEROUS_SERVICES:
            return ACTION_CATEGORY_DANGEROUS

        if domain in DANGEROUS_DOMAINS:
            return ACTION_CATEGORY_DANGEROUS

        # Moderate operations
        moderate_services = [
            "automation.trigger",
            "script.turn_on",
            "scene.turn_on",
        ]
        if service_call in moderate_services:
            return ACTION_CATEGORY_MODERATE

        # Default to safe
        return ACTION_CATEGORY_SAFE

    async def async_request_confirmation(
        self, action: dict[str, Any], safety_level: str
    ) -> bool:
        """Request user confirmation for an action.

        Args:
            action: Action dict with domain, service, entity_id, data
            safety_level: Current safety level setting

        Returns:
            True if action requires confirmation, False otherwise
        """
        category = await self.async_classify_action(
            action.get("domain", ""),
            action.get("service", ""),
            action.get("entity_id"),
        )

        # Check if confirmation needed based on safety level
        if safety_level == "none":
            return False

        if safety_level == "all_actions":
            return True

        if safety_level == "dangerous_only":
            return category in [ACTION_CATEGORY_DANGEROUS, ACTION_CATEGORY_CRITICAL]

        return False

    async def async_create_pending_action(
        self, action: dict[str, Any], context: Optional[str] = None
    ) -> str:
        """Create a pending action awaiting confirmation.

        Args:
            action: Action dict with domain, service, entity_id, data
            context: Optional context/reason for the action

        Returns:
            Action ID
        """
        action_id = str(uuid.uuid4())

        category = await self.async_classify_action(
            action.get("domain", ""),
            action.get("service", ""),
            action.get("entity_id"),
        )

        self.pending_actions[action_id] = {
            "id": action_id,
            "domain": action.get("domain"),
            "service": action.get("service"),
            "entity_id": action.get("entity_id"),
            "data": action.get("data", {}),
            "category": category,
            "context": context,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=ACTION_CONFIRMATION_TIMEOUT),
            "status": "pending",
        }

        # Create event for this action
        self.action_confirmations[action_id] = asyncio.Event()

        # Schedule timeout
        asyncio.create_task(self._action_timeout(action_id))

        # Send notification
        await self._send_confirmation_notification(action_id)

        _LOGGER.info(
            "Created pending action %s: %s.%s",
            action_id,
            action.get("domain"),
            action.get("service"),
        )

        return action_id

    async def async_execute_action(self, action_id: str) -> bool:
        """Execute a confirmed action.

        Args:
            action_id: ID of the pending action

        Returns:
            True if execution was successful
        """
        if action_id not in self.pending_actions:
            _LOGGER.warning("Action %s not found", action_id)
            return False

        action = self.pending_actions[action_id]

        if action["status"] != "pending":
            _LOGGER.warning("Action %s is not pending (status: %s)", action_id, action["status"])
            return False

        try:
            # Call the service
            await self.hass.services.async_call(
                domain=action["domain"],
                service=action["service"],
                service_data=action.get("data", {}),
                target={"entity_id": action["entity_id"]} if action.get("entity_id") else {},
                blocking=True,
            )

            action["status"] = "executed"
            action["executed_at"] = datetime.now()

            _LOGGER.info("Executed action %s successfully", action_id)
            return True

        except HomeAssistantError as err:
            _LOGGER.error("Failed to execute action %s: %s", action_id, err)
            action["status"] = "failed"
            action["error"] = str(err)
            return False

    async def async_reject_action(self, action_id: str, reason: Optional[str] = None) -> bool:
        """Reject a pending action.

        Args:
            action_id: ID of the pending action
            reason: Optional rejection reason

        Returns:
            True if action was rejected
        """
        if action_id not in self.pending_actions:
            _LOGGER.warning("Action %s not found", action_id)
            return False

        action = self.pending_actions[action_id]

        if action["status"] != "pending":
            _LOGGER.warning("Action %s is not pending", action_id)
            return False

        action["status"] = "rejected"
        action["rejection_reason"] = reason
        action["rejected_at"] = datetime.now()

        _LOGGER.info("Rejected action %s: %s", action_id, reason)
        return True

    async def async_get_pending_actions(self) -> list[dict[str, Any]]:
        """Get all pending actions.

        Returns:
            List of pending action dicts
        """
        pending = []

        for action in self.pending_actions.values():
            if action["status"] == "pending":
                # Check if expired
                if datetime.now() > action["expires_at"]:
                    await self.async_reject_action(action["id"], "Confirmation timeout")
                else:
                    pending.append(
                        {
                            "id": action["id"],
                            "domain": action["domain"],
                            "service": action["service"],
                            "entity_id": action["entity_id"],
                            "category": action["category"],
                            "context": action["context"],
                            "created_at": action["created_at"].isoformat(),
                            "expires_at": action["expires_at"].isoformat(),
                        }
                    )

        return pending

    async def async_cleanup_expired_actions(self) -> None:
        """Clean up expired pending actions."""
        expired_ids = []

        for action_id, action in self.pending_actions.items():
            if action["status"] == "pending" and datetime.now() > action["expires_at"]:
                expired_ids.append(action_id)

        for action_id in expired_ids:
            await self.async_reject_action(action_id, "Automatic timeout")
            _LOGGER.info("Cleaned up expired action %s", action_id)

    async def _action_timeout(self, action_id: str) -> None:
        """Handle action confirmation timeout.

        Args:
            action_id: ID of the action
        """
        try:
            await asyncio.sleep(ACTION_CONFIRMATION_TIMEOUT)

            if (
                action_id in self.pending_actions
                and self.pending_actions[action_id]["status"] == "pending"
            ):
                await self.async_reject_action(action_id, "Confirmation timeout")
                _LOGGER.info("Action %s timed out", action_id)
        except asyncio.CancelledError:
            pass

    async def _send_confirmation_notification(self, action_id: str) -> None:
        """Send notification for action confirmation.

        Args:
            action_id: ID of the action
        """
        action = self.pending_actions[action_id]

        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Claude Assistant - Action Confirmation",
                    "message": (
                        f"Claude wants to execute: {action['domain']}.{action['service']}\n"
                        f"Entity: {action['entity_id']}\n"
                        f"Category: {action['category']}\n"
                        f"Context: {action['context']}\n\n"
                        f"Action ID: {action_id}\n"
                        f"Expires in 5 minutes"
                    ),
                    "notification_id": f"claude_{action_id}",
                },
            )
        except HomeAssistantError as err:
            _LOGGER.error("Failed to send notification: %s", err)
