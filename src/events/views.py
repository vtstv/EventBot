﻿import discord
from discord.ui import View, Button

class EventSignupView(View):
    def __init__(self, event_manager, event_id, templates, timeout=None):
        super().__init__(timeout=timeout)
        self.event_manager = event_manager
        self.event_id = event_id
        self.templates = templates
        self._add_role_buttons()

    def _add_role_buttons(self):
        event = self.event_manager.db.get_event(self.event_id)
        if not event or not event['template_name']:
            self.add_item(Button(label="Sign Up", custom_id=f"signup_{self.event_id}_participant"))
            return
        template = self.templates.get(event['template_name'])
        if not template:
            return
        for role_name, role_info in template['roles'].items():
            button = Button(
                label=f"{role_name}",
                emoji=role_info['emoji'],
                custom_id=f"signup_{self.event_id}_{role_name}"
            )
            self.add_item(button)
        # Add Cancel button
        self.add_item(Button(label="Cancel", custom_id=f"cancel_{self.event_id}", style=discord.ButtonStyle.danger))

class EventManagementView(View):
    def __init__(self, event_manager, event_id, timeout=None):
        super().__init__(timeout=timeout)
        self.event_manager = event_manager
        self.event_id = event_id
        # Add management buttons
        self.add_item(Button(label="Edit", custom_id=f"edit_{event_id}", style=discord.ButtonStyle.primary))
