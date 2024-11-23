import os
import json

class LocalizationManager:
    def __init__(self, default_language='en'):
        self.default_language = default_language
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """Load all translation files from the localization directory"""
        localization_dir = 'src/localization'
        if not os.path.exists(localization_dir):
            os.makedirs(localization_dir)
            self._create_default_translation(localization_dir)
        for filename in os.listdir(localization_dir):
            if filename.endswith('.json'):
                language_code = filename[:-5]  # Remove .json extension
                with open(os.path.join(localization_dir, filename), 'r', encoding='utf-8') as f:
                    self.translations[language_code] = json.load(f)

    def _create_default_translation(self, directory):
        """Create default English translation file if it doesn't exist"""
        default_translations = {
            "event": {
                "create": {
                    "start": "Let's create a new event! What would you like to name it?",
                    "name_prompt": "Please provide a name for the event.",
                    "description_prompt": "Please provide a description for the event.",
                    "start_date_prompt": "When will the event start? (Format: YYYY-MM-DD HH:MM)",
                    "success": "Event created successfully! Event ID: {event_id}",
                    "error": "Error creating event: {error}",
                    "timeout": "Event creation timed out. Please try again."
                },
                "edit": {
                    "prompt": "What would you like to edit?",
                    "success": "Event updated successfully!",
                    "error": "Error updating event: {error}"
                },
                "close": {
                    "success": "Event {event_id} has been closed.",
                    "error": "Error closing event: {error}"
                },
                "open": {
                    "success": "Event {event_id} has been reopened.",
                    "error": "Error opening event: {error}"
                },
                "delete": {
                    "confirm": "Are you sure you want to delete this event?",
                    "success": "Event deleted successfully.",
                    "error": "Error deleting event: {error}"
                }
            },
            "errors": {
                "not_found": "Event not found.",
                "no_permission": "You don't have permission to perform this action.",
                "invalid_date": "Invalid date format. Please use YYYY-MM-DD HH:MM",
                "event_ended": "This event has already ended.",
                "event_closed": "This event is closed.",
                "role_full": "This role is already full.",
                "invalid_role": "Invalid role selected."
            },
            "buttons": {
                "sign_up": "Sign Up",
                "close": "Close Event",
                "delete": "Delete Event",
                "edit": "Edit Event"
            }
        }
        with open(os.path.join(directory, 'en.json'), 'w', encoding='utf-8') as f:
            json.dump(default_translations, f, indent=2)

    def get_text(self, language_code, key_path, **kwargs):
        """Get translated text for a given key path and language"""
        language = self.translations.get(language_code, self.translations[self.default_language])
        # Navigate through the nested dictionary using the key path
        keys = key_path.split('-')
        text = language
        for key in keys:
            text = text.get(key, None)
        if isinstance(text, str):
            return text.format(**kwargs)
        else:
            # If translation is missing, try default language
            if language_code != self.default_language:
                return self.get_text(self.default_language, key_path, **kwargs)
            return f"Missing translation: {key_path}"

    def add_language(self, language_code, translations):
        """Add a new language to the system"""
        filepath = f"src/localization/{language_code}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(translations, f, indent=2)
        self.translations[language_code] = translations
