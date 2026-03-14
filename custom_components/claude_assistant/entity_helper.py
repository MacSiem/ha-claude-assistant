"""Entity helper utilities for Claude Assistant integration."""

import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)


class EntityHelper:
    """Helper for entity operations."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize entity helper.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass

    def get_entity_state(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Get state of a specific entity.

        Args:
            entity_id: Entity ID to query

        Returns:
            State dict or None if not found
        """
        state = self.hass.states.get(entity_id)

        if not state:
            return None

        return {
            "entity_id": entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
        }

    def get_entities_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """Get all entities in a specific domain.

        Args:
            domain: Domain to query

        Returns:
            List of entity state dicts
        """
        entities = []

        for entity_id in self.hass.states.async_entity_ids(domain):
            state = self.hass.states.get(entity_id)
            if state:
                entities.append(
                    {
                        "entity_id": entity_id,
                        "state": state.state,
                        "attributes": dict(state.attributes),
                    }
                )

        return entities

    def get_all_entities(self) -> dict[str, dict[str, Any]]:
        """Get all entities in Home Assistant.

        Returns:
            Dictionary of all entity states
        """
        entities = {}

        for entity_id in self.hass.states.async_entity_ids():
            state = self.hass.states.get(entity_id)
            if state:
                entities[entity_id] = {
                    "state": state.state,
                    "attributes": dict(state.attributes),
                }

        return entities

    def get_entity_friendly_name(self, entity_id: str) -> str:
        """Get friendly name of an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Friendly name or entity ID if not found
        """
        state = self.hass.states.get(entity_id)

        if not state:
            return entity_id

        return state.attributes.get("friendly_name", entity_id)

    def entity_exists(self, entity_id: str) -> bool:
        """Check if an entity exists.

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity exists
        """
        return self.hass.states.get(entity_id) is not None

    def get_entities_summary(self) -> str:
        """Get a summary of available entities.

        Returns:
            Formatted summary string
        """
        summary_parts = []
        domains = {}

        # Group entities by domain
        for entity_id in self.hass.states.async_entity_ids():
            domain = entity_id.split(".")[0]
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(entity_id)

        # Format summary
        for domain in sorted(domains.keys()):
            summary_parts.append(f"\n{domain.upper()} ({len(domains[domain])} entities)")

            for entity_id in sorted(domains[domain])[:5]:  # Show first 5
                state = self.hass.states.get(entity_id)
                if state:
                    friendly_name = state.attributes.get("friendly_name", entity_id)
                    summary_parts.append(f"  - {friendly_name}: {state.state}")

            if len(domains[domain]) > 5:
                summary_parts.append(f"  ... and {len(domains[domain]) - 5} more")

        return "\n".join(summary_parts)
