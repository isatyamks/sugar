# Copyright (C) 2024 Sugar Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import json
import time
from gi.repository import GLib

from jarabe.journal import model

# This would ideally be an environment variable or config setting
AI_SERVICE_URL = "http://localhost:8000/api/v1/reflect"

# Maximum number of past journal entries to fetch for history context
MAX_HISTORY_ENTRIES = 5


class ReflectionService(object):
    """
    Service to handle AI reflection logic.

    Retrieves activity context and past journal history from the
    Sugar Datastore, then generates a reflection prompt (currently
    mocked, will call FastAPI backend in production).
    """

    def __init__(self):
        self._pending_reflections = {}

    # ── Journal Data Retrieval ──────────────────────────────────

    def get_activity_context(self, metadata):
        """
        Extract the activity context dict from raw journal metadata.

        This is the data we send to the backend as 'context' in the
        ReflectionRequest schema.

        Args:
            metadata: Dict from journal model.get(object_id).

        Returns:
            Dict with keys matching our backend's ActivityContext schema:
            activity_id, bundle_id, title, description, mime_type,
            tags, duration_seconds.
        """
        # Calculate session duration from timestamps if available
        duration = None
        try:
            timestamp = int(metadata.get('timestamp', 0))
            creation_time = int(metadata.get('creation_time', 0))
            if timestamp > 0 and creation_time > 0:
                duration = timestamp - creation_time
        except (ValueError, TypeError):
            pass

        # Parse tags (stored as space-separated string in Sugar)
        tags_raw = metadata.get('tags', '')
        if isinstance(tags_raw, str) and tags_raw.strip():
            tags = [t.strip() for t in tags_raw.split() if t.strip()]
        else:
            tags = []

        context = {
            'activity_id': metadata.get('activity_id', ''),
            'bundle_id': metadata.get('bundle_id',
                                      metadata.get('activity', '')),
            'title': metadata.get('title', 'Untitled'),
            'description': metadata.get('description', ''),
            'mime_type': metadata.get('mime_type', ''),
            'tags': tags,
            'duration_seconds': duration,
        }

        logging.debug('ReflectionService: Built context for %s: '
                       'bundle=%s duration=%s',
                       context['title'], context['bundle_id'],
                       context['duration_seconds'])
        return context

    def get_activity_history(self, bundle_id, exclude_uid=None,
                             limit=MAX_HISTORY_ENTRIES):
        """
        Fetch past journal entries for the same activity type.

        Queries the Sugar Datastore via model.find_entries() to get
        the most recent entries matching the given bundle_id. This
        provides continuity-aware context for reflection prompting.

        Args:
            bundle_id: Activity bundle identifier
                       (e.g. 'org.laptop.Write').
            exclude_uid: UID of the current entry to exclude from
                         history (avoids reflecting on itself).
            limit: Maximum number of past entries to return.

        Returns:
            List of dicts, each containing:
            - title: str
            - description: str
            - timestamp: int (unix)
            - reflection: str or None (last reflection answer if any)
        """
        if not bundle_id:
            logging.warning('ReflectionService: No bundle_id, '
                            'cannot fetch history')
            return []

        # Query the Journal datastore for past entries of same type
        # Sorted by most recent first (default in find_entries)
        query = {'bundle_id': bundle_id}

        # Fetch one extra in case we need to exclude the current entry
        raw_entries = model.find_entries(query, limit=limit + 1)

        history = []
        for entry in raw_entries:
            uid = entry.get('uid', '')

            # Skip the current entry
            if exclude_uid and uid == exclude_uid:
                continue

            # Extract the last reflection answer if one exists
            last_reflection = None
            ai_reflections_json = entry.get('ai_reflections', '')
            if ai_reflections_json:
                try:
                    reflections_list = json.loads(ai_reflections_json)
                    if reflections_list:
                        last_reflection = reflections_list[-1].get(
                            'answer', None)
                except (json.JSONDecodeError, TypeError, IndexError):
                    pass

            history_entry = {
                'title': entry.get('title', ''),
                'description': entry.get('description', ''),
                'timestamp': int(entry.get('timestamp', 0)),
                'reflection': last_reflection,
            }
            history.append(history_entry)

            if len(history) >= limit:
                break

        logging.debug('ReflectionService: Found %d history entries for %s',
                       len(history), bundle_id)
        return history

    def get_past_reflections(self, metadata):
        """
        Get all past AI reflections stored on this specific journal entry.

        Reads the 'ai_reflections' custom metadata field, which stores
        a JSON array of {timestamp, prompt, answer, model_version} dicts.

        Args:
            metadata: Dict from journal model.get(object_id).

        Returns:
            List of reflection dicts, or empty list.
        """
        raw = metadata.get('ai_reflections', '')
        if not raw:
            return []
        try:
            reflections = json.loads(raw)
            if isinstance(reflections, list):
                return reflections
        except (json.JSONDecodeError, TypeError):
            logging.warning('ReflectionService: Corrupt ai_reflections '
                            'field for %s', metadata.get('uid', '?'))
        return []

    # ── Prompt Generation (mock → will call backend) ────────────

    def get_reflection_prompt(self, metadata, history, callback):
        """
        Get a reflection prompt for the given activity.

        Currently uses a local mock. In production, this will POST to
        the FastAPI backend at AI_SERVICE_URL with the activity context
        and history.

        Args:
            metadata: Journal entry metadata dict.
            history: List of past activity history dicts (from
                     get_activity_history).
            callback: Function(prompt_str) called when prompt is ready.
        """
        logging.debug('ReflectionService: Requesting prompt for %s '
                       '(with %d history entries)',
                       metadata.get('title', 'Untitled'), len(history))

        # Simulate network delay
        GLib.timeout_add_seconds(
            1, self._mock_api_response, metadata, history, callback)

    def _mock_api_response(self, metadata, history, callback):
        """
        Returns a mock prompt based on activity type and history.

        In production, this will be replaced by an HTTP POST to the
        FastAPI backend. The backend will use the context + history
        to select a framework and generate an LLM-powered prompt.
        """
        mime_type = metadata.get('mime_type', 'unknown')
        title = metadata.get('title', 'Untitled')
        history_count = len(history)

        # History-aware prompting: adapt the question based on
        # whether the learner has done this activity type before
        if history_count == 0:
            # First time with this activity type
            if 'image' in mime_type:
                prompt = ("I see you created a picture titled '{}'. "
                          "What feelings were you trying to express "
                          "with these colors?").format(title)
            elif 'text' in mime_type:
                prompt = ("You wrote '{}'. What was the most "
                          "challenging part of writing this?").format(title)
            else:
                prompt = ("You just finished '{}'. What did you learn "
                          "while working on this today?").format(title)
        else:
            # Returning learner — reference past work for continuity
            last_title = history[0].get('title', 'your previous work')
            last_reflection = history[0].get('reflection', '')

            if last_reflection:
                prompt = ("Last time you worked on '{}', you reflected: "
                          "'{}'. Now that you've finished '{}', how has "
                          "your thinking changed?").format(
                              last_title, last_reflection[:100], title)
            else:
                prompt = ("You've worked on {} similar activities before. "
                          "Comparing '{}' to '{}', what did you do "
                          "differently this time?").format(
                              history_count, title, last_title)

        logging.debug('ReflectionService: Generated prompt: %s', prompt)
        callback(prompt)
        return False  # Remove the GLib timeout source

    # ── Save ────────────────────────────────────────────────────

    def save_reflection(self, object_id, prompt, answer):
        """
        Save the reflection to the datastore metadata.

        Stores structured data in the 'ai_reflections' custom field
        (JSON array), and also appends to 'description' for visibility
        in the standard Journal detail view.

        Args:
            object_id: Journal entry UID.
            prompt: The reflection question that was shown.
            answer: The learner's written response.

        Returns:
            True on success, False on failure.
        """
        logging.debug('ReflectionService: Saving reflection for %s',
                       object_id)

        try:
            metadata = model.get(object_id)
            if not metadata:
                logging.error('ReflectionService: No metadata found '
                              'for %s', object_id)
                return False

            # Create a structured reflection entry
            reflection_entry = {
                'timestamp': int(time.time()),
                'prompt': prompt,
                'answer': answer,
                'model_version': 'mock-v1'
            }

            # Load existing reflections if any
            existing = self.get_past_reflections(metadata)
            existing.append(reflection_entry)
            metadata['ai_reflections'] = json.dumps(existing)

            # Also append to description so user sees it in standard view
            current_desc = metadata.get('description', '')
            if current_desc:
                current_desc += '\n\n'
            current_desc += ("--- AI Reflection ---\n"
                             "Q: {}\nA: {}").format(prompt, answer)
            metadata['description'] = current_desc

            model.write(metadata)
            logging.debug('ReflectionService: Saved successfully.')
            return True

        except Exception as e:
            logging.exception('ReflectionService: Error saving '
                              'reflection: %s', e)
            return False


_instance = None


def get_service():
    global _instance
    if _instance is None:
        _instance = ReflectionService()
    return _instance
