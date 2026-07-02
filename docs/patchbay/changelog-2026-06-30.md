# Changelog - June 30, 2026

## Changes made

### 1. TalkView.swift - Audio response toggle and text input mode swap
- Moved the audio response toggle from SettingsView into the chat screen (TalkView). It now appears as a small toggle switch in a controls row at the bottom of the chat screen, alongside the voice/text mode swap button.
- Added a swap button (keyboard icon / mic icon) that toggles between voice recording mode and text input mode.
- The record button is shown by default. Tapping the swap button replaces it with the text entry field, and tapping again goes back to the record button.
- Added a smooth animation when swapping between modes.

### 2. SettingsView.swift - Removed audio response toggle and chunked audio toggle
- The audio response toggle has been removed from settings since it now lives in the chat screen.
- The chunked audio toggle has been removed entirely. Audio chunking by paragraph is now a server-side default and not configurable by the user.
- Renamed the "Audio" section to "Text-to-Speech" since it now only contains the TTS provider picker.

### 3. TurnSettings.swift - Removed chunkedAudio property
- Removed the `chunkedAudio` property from the TurnSettings struct and its associated UserDefaults lookup in the `current` getter.

### 4. ServerClient.swift - Always send chunked_audio as true
- Changed the chunked_audio field in the multipart form data to always send "true" instead of reading from settings.
