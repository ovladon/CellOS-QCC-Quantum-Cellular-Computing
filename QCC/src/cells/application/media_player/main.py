"""
Media Player Cell Implementation for QCC

This cell provides media playback capabilities, allowing users to play
audio and video files within the QCC ecosystem.
"""

import asyncio
import logging
import time
import os
import mimetypes
from typing import Dict, List, Any, Optional, Tuple

from qcc.cells import BaseCell
from qcc.common.exceptions import CellError, CellConnectionError, CapabilityExecutionError

logger = logging.getLogger(__name__)

class MediaPlayerCell(BaseCell):
    """
    A cell that provides media playback capabilities.
    
    This cell allows users to:
    - Play audio and video files
    - Control playback (pause, resume, seek)
    - Create and manage playlists
    - Display media information
    
    The cell works with file_system cells to access media files.
    """
    
    def initialize(self, parameters):
        """
        Initialize the media player cell with parameters.
        
        Args:
            parameters: Initialization parameters including cell_id and context
        
        Returns:
            Initialization result with capabilities and requirements
        """
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("media_player", self.media_player_interface)
        self.register_capability("play_media", self.play_media)
        self.register_capability("control_playback", self.control_playback)
        self.register_capability("manage_playlist", self.manage_playlist)
        self.register_capability("get_media_info", self.get_media_info)
        
        # Initialize media state
        self.current_media = None
        self.playlists = {}
        self.playback_state = "stopped"
        self.playback_position = 0
        self.volume = 0.8  # Range 0.0 to 1.0
        
        # Required connections for full functionality
        self.required_connections = ["file_system"]
        
        # Extract any settings from parameters
        self.settings = parameters.get("configuration", {}).get("settings", {})
        
        # Default settings
        self.settings.setdefault("supported_audio_formats", ["mp3", "wav", "ogg", "m4a", "flac"])
        self.settings.setdefault("supported_video_formats", ["mp4", "webm", "ogv"])
        self.settings.setdefault("max_playlist_items", 100)
        self.settings.setdefault("autoplay", True)
        
        logger.info(f"Media player cell initialized with ID: {self.cell_id}")
        
        return self.get_initialization_result()
    
    def get_initialization_result(self):
        """Get the initialization result with capabilities and requirements."""
        return {
            "status": "success",
            "cell_id": self.cell_id,
            "capabilities": [
                {
                    "name": "media_player",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "media_id",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "playlist_id",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "theme",
                            "type": "string",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "html",
                            "type": "string",
                            "format": "html"
                        }
                    ]
                },
                {
                    "name": "play_media",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "media_path",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "media_id",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "media_url",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "start_position",
                            "type": "number",
                            "required": False
                        },
                        {
                            "name": "volume",
                            "type": "number",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "media_id",
                            "type": "string"
                        },
                        {
                            "name": "status",
                            "type": "string"
                        },
                        {
                            "name": "media_info",
                            "type": "object"
                        }
                    ]
                },
                {
                    "name": "control_playback",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "action",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "media_id",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "position",
                            "type": "number",
                            "required": False
                        },
                        {
                            "name": "volume",
                            "type": "number",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "success",
                            "type": "boolean"
                        },
                        {
                            "name": "state",
                            "type": "object"
                        }
                    ]
                },
                {
                    "name": "manage_playlist",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "action",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "playlist_id",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "playlist_name",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "media_items",
                            "type": "array",
                            "required": False
                        },
                        {
                            "name": "media_id",
                            "type": "string",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "success",
                            "type": "boolean"
                        },
                        {
                            "name": "playlist_id",
                            "type": "string"
                        },
                        {
                            "name": "playlist",
                            "type": "object"
                        }
                    ]
                },
                {
                    "name": "get_media_info",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "media_path",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "media_id",
                            "type": "string",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "success",
                            "type": "boolean"
                        },
                        {
                            "name": "media_info",
                            "type": "object"
                        }
                    ]
                }
            ],
            "required_connections": self.required_connections,
            "resource_usage": {
                "memory_mb": 30,
                "storage_mb": 5
            }
        }
    
    async def media_player_interface(self, parameters=None) -> Dict[str, Any]:
        """
        Generate the media player user interface.
        
        Args:
            parameters: Optional parameters for UI customization
                - media_id: ID of media to display
                - playlist_id: ID of playlist to display
                - theme: UI theme (light or dark)
        
        Returns:
            HTML interface for the media player
        """
        parameters = parameters or {}
        theme = parameters.get("theme", "light")
        media_id = parameters.get("media_id", self.current_media)
        playlist_id = parameters.get("playlist_id")
        
        # Get current media information
        media_info = {}
        if media_id:
            media_result = await self.get_media_info({"media_id": media_id})
            if media_result["status"] == "success":
                media_info = next((o for o in media_result["outputs"] if o["name"] == "media_info"), {}).get("value", {})
        
        # Get playlist information
        playlist = {}
        if playlist_id and playlist_id in self.playlists:
            playlist = self.playlists[playlist_id]
        
        # Determine media type (audio or video)
        media_type = media_info.get("type", "audio")
        media_title = media_info.get("title", "Unknown Media")
        media_path = media_info.get("path", "")
        media_url = f"/api/files/{media_path}" if media_path else ""
        
        # Generate HTML for the player interface
        html = f"""
        <div class="media-player {theme}-theme" id="media-player-{self.cell_id}">
            <div class="player-header">
                <div class="media-title">{media_title}</div>
                <div class="player-controls">
                    <button onclick="playerAction('previous')" class="control-button" title="Previous">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" fill="currentColor"/></svg>
                    </button>
                    <button onclick="playerAction('play')" class="control-button play-button" title="Play">
                        <svg viewBox="0 0 24 24" width="32" height="32"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>
                    </button>
                    <button onclick="playerAction('pause')" class="control-button" title="Pause">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" fill="currentColor"/></svg>
                    </button>
                    <button onclick="playerAction('stop')" class="control-button" title="Stop">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M6 6h12v12H6z" fill="currentColor"/></svg>
                    </button>
                    <button onclick="playerAction('next')" class="control-button" title="Next">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" fill="currentColor"/></svg>
                    </button>
                </div>
            </div>
            
            <div class="player-body">
                <div class="media-container">
                    {f'<video id="media-element" controls src="{media_url}"></video>' if media_type == 'video' else f'<audio id="media-element" controls src="{media_url}"></audio>'}
                </div>
            </div>
            
            <div class="player-progress">
                <div class="time-display current-time">0:00</div>
                <div class="progress-bar-container">
                    <div class="progress-bar">
                        <div class="progress-bar-fill" style="width: 0%"></div>
                    </div>
                </div>
                <div class="time-display duration">0:00</div>
            </div>
            
            <div class="player-footer">
                <div class="volume-control">
                    <svg viewBox="0 0 24 24" width="20" height="20"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" fill="currentColor"/></svg>
                    <input type="range" min="0" max="100" value="{int(self.volume * 100)}" class="volume-slider" onchange="setVolume(this.value)">
                </div>
                <div class="playback-rate">
                    <select onchange="setPlaybackRate(this.value)">
                        <option value="0.5">0.5x</option>
                        <option value="0.75">0.75x</option>
                        <option value="1" selected>1x</option>
                        <option value="1.25">1.25x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2">2x</option>
                    </select>
                </div>
            </div>
            
            <!-- Playlist section -->
            {self._generate_playlist_html(playlist) if playlist else ""}
        </div>
        
        <style>
            .media-player {
                display: flex;
                flex-direction: column;
                width: 100%;
                max-width: 800px;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                background-color: white;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
            }
            
            .light-theme {
                background-color: white;
                color: #333;
            }
            
            .dark-theme {
                background-color: #2d2d2d;
                color: #f0f0f0;
            }
            
            .player-header {
                padding: 12px 16px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .dark-theme .player-header {
                border-color: #444;
            }
            
            .media-title {
                font-weight: 500;
                font-size: 16px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 300px;
            }
            
            .player-controls {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .control-button {
                background: none;
                border: none;
                cursor: pointer;
                color: #555;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                transition: background-color 0.2s;
            }
            
            .dark-theme .control-button {
                color: #ddd;
            }
            
            .control-button:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            .dark-theme .control-button:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            .play-button {
                background-color: #f2f2f2;
                width: 48px;
                height: 48px;
            }
            
            .dark-theme .play-button {
                background-color: #444;
            }
            
            .player-body {
                position: relative;
                width: 100%;
                background-color: black;
            }
            
            .media-container {
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            video, audio {
                width: 100%;
                display: block;
            }
            
            .player-progress {
                display: flex;
                align-items: center;
                padding: 4px 16px;
                gap: 8px;
            }
            
            .time-display {
                font-size: 12px;
                font-family: monospace;
                min-width: 40px;
            }
            
            .progress-bar-container {
                flex-grow: 1;
                cursor: pointer;
            }
            
            .progress-bar {
                height: 4px;
                background-color: #ddd;
                border-radius: 2px;
                position: relative;
            }
            
            .dark-theme .progress-bar {
                background-color: #555;
            }
            
            .progress-bar-fill {
                position: absolute;
                height: 100%;
                width: 0%;
                background-color: #1a73e8;
                border-radius: 2px;
            }
            
            .player-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 16px 12px;
                border-top: 1px solid #eee;
            }
            
            .dark-theme .player-footer {
                border-color: #444;
            }
            
            .volume-control {
                display: flex;
                align-items: center;
                gap: 8px;
                width: 150px;
            }
            
            .volume-slider {
                width: 100px;
            }
            
            .playback-rate select {
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #ddd;
                background-color: white;
                font-size: 14px;
            }
            
            .dark-theme .playback-rate select {
                background-color: #3d3d3d;
                color: #f0f0f0;
                border-color: #555;
            }
            
            .playlist-container {
                max-height: 300px;
                overflow-y: auto;
                border-top: 1px solid #eee;
            }
            
            .dark-theme .playlist-container {
                border-color: #444;
            }
            
            .playlist-header {
                padding: 8px 16px;
                font-weight: 500;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .playlist-items {
                list-style: none;
                margin: 0;
                padding: 0;
            }
            
            .playlist-item {
                padding: 8px 16px;
                border-top: 1px solid #eee;
                display: flex;
                align-items: center;
                cursor: pointer;
            }
            
            .dark-theme .playlist-item {
                border-color: #444;
            }
            
            .playlist-item:hover {
                background-color: #f5f5f5;
            }
            
            .dark-theme .playlist-item:hover {
                background-color: #3a3a3a;
            }
            
            .playlist-item.active {
                background-color: #e3f2fd;
            }
            
            .dark-theme .playlist-item.active {
                background-color: #2c3e50;
            }
            
            .playlist-item-number {
                margin-right: 12px;
                color: #777;
                font-size: 14px;
                width: 24px;
                text-align: right;
            }
            
            .dark-theme .playlist-item-number {
                color: #aaa;
            }
            
            .playlist-item-title {
                flex-grow: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .playlist-item-duration {
                font-size: 14px;
                color: #777;
                margin-left: 12px;
            }
            
            .dark-theme .playlist-item-duration {
                color: #aaa;
            }
        </style>
        
        <script>
            // Initialize player
            const mediaElement = document.getElementById('media-element');
            const progressFill = document.querySelector('.progress-bar-fill');
            const currentTimeDisplay = document.querySelector('.current-time');
            const durationDisplay = document.querySelector('.duration');
            const cellId = '{self.cell_id}';
            
            let currentMediaId = "{media_id or ''}";
            let currentPlaylistId = "{playlist_id or ''}";
            let isPlaying = false;
            
            // Format time in seconds to mm:ss format
            function formatTime(seconds) {
                if (isNaN(seconds)) return '0:00';
                seconds = Math.floor(seconds);
                const minutes = Math.floor(seconds / 60);
                seconds = seconds % 60;
                return `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
            
            // Update progress bar and time displays
            function updateProgress() {
                if (!mediaElement) return;
                
                const currentTime = mediaElement.currentTime;
                const duration = mediaElement.duration || 0;
                
                // Update time displays
                currentTimeDisplay.textContent = formatTime(currentTime);
                durationDisplay.textContent = formatTime(duration);
                
                // Update progress bar
                if (duration > 0) {
                    const progress = (currentTime / duration) * 100;
                    progressFill.style.width = `${progress}%`;
                }
            }
            
            // Initialize event listeners if media element exists
            if (mediaElement) {
                // Update progress every second
                setInterval(updateProgress, 1000);
                
                // Update on timeupdate event
                mediaElement.addEventListener('timeupdate', updateProgress);
                
                // Update when metadata is loaded
                mediaElement.addEventListener('loadedmetadata', updateProgress);
                
                // Handle clicks on progress bar
                const progressBar = document.querySelector('.progress-bar');
                progressBar.addEventListener('click', (e) => {
                    const rect = progressBar.getBoundingClientRect();
                    const clickPosition = (e.clientX - rect.left) / rect.width;
                    if (mediaElement.duration) {
                        mediaElement.currentTime = clickPosition * mediaElement.duration;
                        updateProgress();
                    }
                });
                
                // Auto play if setting is enabled
                if ({str(self.settings.get("autoplay", True)).lower()}) {
                    mediaElement.play().catch(e => console.log('Auto-play prevented:', e));
                }
            }
            
            // Player control functions
            async function playerAction(action) {
                try {
                    const response = await fetch(`/api/cells/${cellId}/capabilities/control_playback`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            action: action,
                            media_id: currentMediaId
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        // Handle player-specific actions locally
                        if (mediaElement) {
                            if (action === 'play') {
                                mediaElement.play();
                                isPlaying = true;
                            } else if (action === 'pause') {
                                mediaElement.pause();
                                isPlaying = false;
                            } else if (action === 'stop') {
                                mediaElement.pause();
                                mediaElement.currentTime = 0;
                                isPlaying = false;
                            }
                        }
                    }
                } catch (error) {
                    console.error(`Error with player action ${action}:`, error);
                }
            }
            
            // Set volume
            function setVolume(value) {
                const volumeValue = parseInt(value) / 100;
                if (mediaElement) {
                    mediaElement.volume = volumeValue;
                }
                
                // Also update server-side volume
                fetch(`/api/cells/${cellId}/capabilities/control_playback`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: 'volume',
                        volume: volumeValue
                    })
                }).catch(error => console.error('Error setting volume:', error));
            }
            
            // Set playback rate
            function setPlaybackRate(value) {
                if (mediaElement) {
                    mediaElement.playbackRate = parseFloat(value);
                }
            }
            
            // Play media from playlist
            async function playPlaylistItem(mediaId) {
                try {
                    const response = await fetch(`/api/cells/${cellId}/capabilities/play_media`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            media_id: mediaId,
                            playlist_id: currentPlaylistId
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        // Reload the player with the new media
                        window.location.reload();
                    }
                } catch (error) {
                    console.error('Error playing media:', error);
                }
            }
        </script>
        """
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "html",
                    "value": html,
                    "type": "string",
                    "format": "html"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 10,
                "memory_used_mb": 0.5
            }
        }
    
    def _generate_playlist_html(self, playlist):
        """Generate HTML for playlist display."""
        items_html = ""
        active_item = self.current_media
        
        for index, item in enumerate(playlist.get("items", [])):
            item_class = "playlist-item"
            if item.get("id") == active_item:
                item_class += " active"
                
            items_html += f"""
            <li class="{item_class}" onclick="playPlaylistItem('{item.get('id')}')">
                <div class="playlist-item-number">{index + 1}</div>
                <div class="playlist-item-title">{item.get('title', 'Unknown')}</div>
                <div class="playlist-item-duration">{item.get('duration_formatted', '0:00')}</div>
            </li>
            """
            
        return f"""
        <div class="playlist-container">
            <div class="playlist-header">
                <div>{playlist.get('name', 'Playlist')}</div>
                <div>{len(playlist.get('items', []))} items</div>
            </div>
            <ul class="playlist-items">
                {items_html}
            </ul>
        </div>
        """
    
    async def play_media(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Play media from file path, media ID, or URL.
        
        Args:
            parameters: Media parameters
                - media_path: Path to media file
                - media_id: ID of existing media
                - media_url: URL of media to play
                - start_position: Starting position in seconds
                - volume: Playback volume (0.0 to 1.0)
        
        Returns:
            Media ID and status
        """
        # At least one of media_path, media_id, or media_url must be provided
        if not any(param in parameters for param in ["media_path", "media_id", "media_url"]):
            return self._error_response("At least one of media_path, media_id, or media_url must be provided")
        
        # Set volume if provided
        if "volume" in parameters:
            self.volume = max(0.0, min(1.0, float(parameters["volume"])))
        
        # If media_id is provided and it exists, use it
        if "media_id" in parameters and parameters["media_id"] in self._get_media_cache():
            media_id = parameters["media_id"]
            media_info = self._get_media_cache()[media_id]
            self.current_media = media_id
            self.playback_state = "playing"
            self.playback_position = parameters.get("start_position", 0)
            
            logger.info(f"Playing media by ID: {media_id}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "media_id",
                        "value": media_id,
                        "type": "string"
                    },
                    {
                        "name": "status",
                        "value": "playing",
                        "type": "string"
                    },
                    {
                        "name": "media_info",
                        "value": media_info,
                        "type": "object"
                    }
                ]
            }
        
        # If media_path is provided, load from file system
        if "media_path" in parameters:
            media_path = parameters["media_path"]
            
            # Validate file format
            file_ext = os.path.splitext(media_path)[1].lower().lstrip('.')
            supported_audio_formats = self.settings.get("supported_audio_formats", [])
            supported_video_formats = self.settings.get("supported_video_formats", [])
            
            if file_ext not in supported_audio_formats and file_ext not in supported_video_formats:
                return self._error_response(f"Unsupported file format: {file_ext}")
            
            # Try to get file from file_system cell
            file_system_cell = self._get_connected_cell_by_capability("file_system")
            
            if file_system_cell:
                try:
                    # Get file info from file system
                    file_info_result = await self.call_capability(
                        cell_id=file_system_cell,
                        capability="get_file_info",
                        parameters={"path": media_path}
                    )
                    
                    if file_info_result["status"] != "success":
                        return self._error_response(f"Failed to get file info: {file_info_result.get('error', 'Unknown error')}")
                    
                    # Extract file info
                    file_info_output = next((o for o in file_info_result["outputs"] if o["name"] == "file_info"), None)
                    
                    if not file_info_output:
                        return self._error_response("Failed to get file info")
                    
                    file_info = file_info_output["value"]
                    
                    # Create media info
                    media_type = "video" if file_ext in supported_video_formats else "audio"
                    
                    # Generate a unique media ID
                    media_id = f"media_{int(time.time())}_{len(self._get_media_cache())}"
                    
                    # Create media info
                    media_info = {
                        "id": media_id,
                        "path": media_path,
                        "title": os.path.basename(media_path),
                        "type": media_type,
                        "format": file_ext,
                        "size": file_info.get("size", 0),
                        "created_at": file_info.get("created_at"),
                        "modified_at": file_info.get("modified_at"),
                        "mime_type": mimetypes.guess_type(media_path)[0] or f"{media_type}/{file_ext}",
                        "duration": 0,  # Will be updated when played
                        "metadata": {}
                    }
                    
                    # Add to media cache
                    self._get_media_cache()[media_id] = media_info
                    
                    # Set as current media
                    self.current_media = media_id
                    self.playback_state = "playing"
                    self.playback_position = parameters.get("start_position", 0)
                    
                    logger.info(f"Playing media from path: {media_path}")
                    
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "media_id",
                                "value": media_id,
                                "type": "string"
                            },
                            {
                                "name": "status",
                                "value": "playing",
                                "type": "string"
                            },
                            {
                                "name": "media_info",
                                "value": media_info,
                                "type": "object"
                            }
                        ]
                    }
                    
                except Exception as e:
                    logger.error(f"Error playing media from path: {e}")
                    return self._error_response(f"Error playing media: {str(e)}")
            else:
                return self._error_response("No file_system cell connected, cannot load media file")
        
        # If media_url is provided, play from URL
        if "media_url" in parameters:
            media_url = parameters["media_url"]
            
            # Try to determine media type from URL
            url_ext = os.path.splitext(media_url)[1].lower().lstrip('.')
            supported_audio_formats = self.settings.get("supported_audio_formats", [])
            supported_video_formats = self.settings.get("supported_video_formats", [])
            
            if url_ext in supported_video_formats:
                media_type = "video"
            elif url_ext in supported_audio_formats:
                media_type = "audio"
            else:
                # Default to audio if can't determine
                media_type = "audio"
            
            # Generate a unique media ID
            media_id = f"media_{int(time.time())}_{len(self._get_media_cache())}"
            
            # Create media info
            media_info = {
                "id": media_id,
                "url": media_url,
                "title": os.path.basename(media_url) or "Media from URL",
                "type": media_type,
                "format": url_ext,
                "mime_type": mimetypes.guess_type(media_url)[0] or f"{media_type}/{url_ext}",
                "duration": 0,  # Will be updated when played
                "metadata": {}
            }
            
            # Add to media cache
            self._get_media_cache()[media_id] = media_info
            
            # Set as current media
            self.current_media = media_id
            self.playback_state = "playing"
            self.playback_position = parameters.get("start_position", 0)
            
            logger.info(f"Playing media from URL: {media_url}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "media_id",
                        "value": media_id,
                        "type": "string"
                    },
                    {
                        "name": "status",
                        "value": "playing",
                        "type": "string"
                    },
                    {
                        "name": "media_info",
                        "value": media_info,
                        "type": "object"
                    }
                ]
            }
        
        return self._error_response("Failed to play media")
    
    async def control_playback(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Control media playback.
        
        Args:
            parameters: Control parameters
                - action: Control action (play, pause, stop, seek, volume, next, previous)
                - media_id: ID of media to control (uses current if not provided)
                - position: Seek position in seconds
                - volume: Volume level (0.0 to 1.0)
        
        Returns:
            Success indicator and current playback state
        """
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"]
        media_id = parameters.get("media_id", self.current_media)
        
        # If no current media and no media_id provided, return error
        if not media_id:
            return self._error_response("No media currently playing and no media_id provided")
        
        # If media_id provided but doesn't exist, return error
        if media_id and media_id not in self._get_media_cache():
            return self._error_response(f"Media not found: {media_id}")
        
        try:
            if action == "play":
                # Start or resume playback
                self.playback_state = "playing"
                self.current_media = media_id
                
            elif action == "pause":
                # Pause playback
                self.playback_state = "paused"
                
            elif action == "stop":
                # Stop playback and reset position
                self.playback_state = "stopped"
                self.playback_position = 0
                
            elif action == "seek":
                # Seek to position
                if "position" not in parameters:
                    return self._error_response("Position parameter is required for seek action")
                
                self.playback_position = max(0, float(parameters["position"]))
                
            elif action == "volume":
                # Set volume
                if "volume" not in parameters:
                    return self._error_response("Volume parameter is required for volume action")
                
                self.volume = max(0.0, min(1.0, float(parameters["volume"])))
                
            elif action in ["next", "previous"]:
                # Get current playlist
                current_playlist_id = None
                current_index = -1
                
                # Find which playlist contains current media and the index
                for playlist_id, playlist in self.playlists.items():
                    for i, item in enumerate(playlist.get("items", [])):
                        if item.get("id") == media_id:
                            current_playlist_id = playlist_id
                            current_index = i
                            break
                    if current_playlist_id:
                        break
                
                if not current_playlist_id:
                    return self._error_response("Current media is not in any playlist")
                
                playlist = self.playlists[current_playlist_id]
                playlist_items = playlist.get("items", [])
                
                if not playlist_items:
                    return self._error_response("Playlist is empty")
                
                # Calculate new index
                if action == "next":
                    new_index = (current_index + 1) % len(playlist_items)
                else:  # previous
                    new_index = (current_index - 1) % len(playlist_items)
                
                # Get the new media item
                new_media = playlist_items[new_index]
                new_media_id = new_media.get("id")
                
                if not new_media_id:
                    return self._error_response("Invalid media in playlist")
                
                # Play the new media
                play_result = await self.play_media({"media_id": new_media_id})
                if play_result["status"] != "success":
                    return self._error_response(f"Failed to play next media: {play_result.get('error', 'Unknown error')}")
                
                # Return success with new media info
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "state",
                            "value": {
                                "playback_state": self.playback_state,
                                "current_media": new_media_id,
                                "media_info": new_media
                            },
                            "type": "object"
                        }
                    ]
                }
                
            else:
                return self._error_response(f"Unsupported action: {action}")
            
            # Get current media info
            media_info = self._get_media_cache().get(media_id, {})
            
            # Return current state
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "state",
                        "value": {
                            "playback_state": self.playback_state,
                            "current_media": media_id,
                            "playback_position": self.playback_position,
                            "volume": self.volume,
                            "media_info": media_info
                        },
                        "type": "object"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error controlling playback: {e}")
            return self._error_response(f"Error controlling playback: {str(e)}")
    
    async def manage_playlist(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage playlists.
        
        Args:
            parameters: Playlist parameters
                - action: Action to perform (create, add, remove, clear, get)
                - playlist_id: ID of playlist (for actions other than create)
                - playlist_name: Name of playlist (for create action)
                - media_items: Media items to add (for add action)
                - media_id: Media ID to remove (for remove action)
        
        Returns:
            Success indicator and playlist information
        """
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"]
        
        try:
            if action == "create":
                # Create a new playlist
                if "playlist_name" not in parameters:
                    return self._error_response("Playlist name is required for create action")
                
                playlist_name = parameters["playlist_name"]
                
                # Generate a unique playlist ID
                playlist_id = f"playlist_{int(time.time())}_{len(self.playlists)}"
                
                # Create playlist
                self.playlists[playlist_id] = {
                    "id": playlist_id,
                    "name": playlist_name,
                    "created_at": time.time(),
                    "modified_at": time.time(),
                    "items": []
                }
                
                logger.info(f"Created playlist: {playlist_name} ({playlist_id})")
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "playlist_id",
                            "value": playlist_id,
                            "type": "string"
                        },
                        {
                            "name": "playlist",
                            "value": self.playlists[playlist_id],
                            "type": "object"
                        }
                    ]
                }
                
            elif action in ["add", "remove", "clear", "get"]:
                # These actions require a playlist ID
                if "playlist_id" not in parameters:
                    return self._error_response("Playlist ID is required")
                
                playlist_id = parameters["playlist_id"]
                
                # Check if playlist exists
                if playlist_id not in self.playlists:
                    return self._error_response(f"Playlist not found: {playlist_id}")
                
                playlist = self.playlists[playlist_id]
                
                if action == "add":
                    # Add media items to playlist
                    if "media_items" not in parameters:
                        return self._error_response("Media items parameter is required for add action")
                    
                    media_items = parameters["media_items"]
                    
                    if not isinstance(media_items, list):
                        return self._error_response("Media items must be an array")
                    
                    # Check if we would exceed the max playlist items
                    max_items = self.settings.get("max_playlist_items", 100)
                    if len(playlist["items"]) + len(media_items) > max_items:
                        return self._error_response(f"Adding these items would exceed the maximum playlist size of {max_items}")
                    
                    # Add items to playlist
                    for item in media_items:
                        if isinstance(item, str):
                            # If item is a string, assume it's a media ID
                            media_id = item
                            
                            # Check if media exists
                            if media_id not in self._get_media_cache():
                                logger.warning(f"Media ID not found: {media_id}")
                                continue
                            
                            media_info = self._get_media_cache()[media_id]
                            
                            # Add to playlist
                            playlist["items"].append({
                                "id": media_id,
                                "title": media_info.get("title", "Unknown"),
                                "type": media_info.get("type", "audio"),
                                "duration": media_info.get("duration", 0),
                                "duration_formatted": self._format_duration(media_info.get("duration", 0))
                            })
                            
                        elif isinstance(item, dict) and "id" in item:
                            # If item is a dictionary, use it directly
                            # Ensure required fields are present
                            if "title" not in item:
                                item["title"] = "Unknown"
                            
                            if "type" not in item:
                                item["type"] = "audio"
                            
                            if "duration" not in item:
                                item["duration"] = 0
                            
                            if "duration_formatted" not in item:
                                item["duration_formatted"] = self._format_duration(item.get("duration", 0))
                            
                            playlist["items"].append(item)
                    
                    # Update modified timestamp
                    playlist["modified_at"] = time.time()
                    
                    logger.info(f"Added {len(media_items)} items to playlist: {playlist_id}")
                    
                elif action == "remove":
                    # Remove a media item from playlist
                    if "media_id" not in parameters:
                        return self._error_response("Media ID parameter is required for remove action")
                    
                    media_id = parameters["media_id"]
                    
                    # Find and remove the item
                    playlist["items"] = [item for item in playlist["items"] if item.get("id") != media_id]
                    
                    # Update modified timestamp
                    playlist["modified_at"] = time.time()
                    
                    logger.info(f"Removed media {media_id} from playlist: {playlist_id}")
                    
                elif action == "clear":
                    # Clear all items from playlist
                    playlist["items"] = []
                    
                    # Update modified timestamp
                    playlist["modified_at"] = time.time()
                    
                    logger.info(f"Cleared playlist: {playlist_id}")
                
                # Return updated playlist info (for all actions)
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "playlist_id",
                            "value": playlist_id,
                            "type": "string"
                        },
                        {
                            "name": "playlist",
                            "value": playlist,
                            "type": "object"
                        }
                    ]
                }
                
            elif action == "list":
                # List all playlists
                playlist_list = [
                    {
                        "id": playlist_id,
                        "name": playlist["name"],
                        "item_count": len(playlist.get("items", [])),
                        "created_at": playlist.get("created_at")
                    }
                    for playlist_id, playlist in self.playlists.items()
                ]
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "playlists",
                            "value": playlist_list,
                            "type": "array"
                        }
                    ]
                }
                
            else:
                return self._error_response(f"Unsupported action: {action}")
                
        except Exception as e:
            logger.error(f"Error managing playlist: {e}")
            return self._error_response(f"Error managing playlist: {str(e)}")
    
    async def get_media_info(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get information about media.
        
        Args:
            parameters: Parameters for media info request
                - media_path: Path to media file
                - media_id: ID of existing media
        
        Returns:
            Media information
        """
        # Either media_path or media_id must be provided
        if "media_path" not in parameters and "media_id" not in parameters:
            return self._error_response("Either media_path or media_id must be provided")
        
        try:
            # If media_id is provided, check if it exists in cache
            if "media_id" in parameters:
                media_id = parameters["media_id"]
                
                if media_id in self._get_media_cache():
                    media_info = self._get_media_cache()[media_id]
                    
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "success",
                                "value": True,
                                "type": "boolean"
                            },
                            {
                                "name": "media_info",
                                "value": media_info,
                                "type": "object"
                            }
                        ]
                    }
                else:
                    return self._error_response(f"Media not found: {media_id}")
            
            # If media_path is provided, get info from file
            if "media_path" in parameters:
                media_path = parameters["media_path"]
                
                # Check file extension
                file_ext = os.path.splitext(media_path)[1].lower().lstrip('.')
                supported_audio_formats = self.settings.get("supported_audio_formats", [])
                supported_video_formats = self.settings.get("supported_video_formats", [])
                
                if file_ext not in supported_audio_formats and file_ext not in supported_video_formats:
                    return self._error_response(f"Unsupported file format: {file_ext}")
                
                # Check if connected to file_system cell
                file_system_cell = self._get_connected_cell_by_capability("file_system")
                
                if file_system_cell:
                    # Get file info from file system
                    file_info_result = await self.call_capability(
                        cell_id=file_system_cell,
                        capability="get_file_info",
                        parameters={"path": media_path}
                    )
                    
                    if file_info_result["status"] != "success":
                        return self._error_response(f"Failed to get file info: {file_info_result.get('error', 'Unknown error')}")
                    
                    # Extract file info
                    file_info_output = next((o for o in file_info_result["outputs"] if o["name"] == "file_info"), None)
                    
                    if not file_info_output:
                        return self._error_response("Failed to get file info")
                    
                    file_info = file_info_output["value"]
                    
                    # Create media info
                    media_type = "video" if file_ext in supported_video_formats else "audio"
                    
                    # Generate a unique media ID (since we don't have it in cache)
                    media_id = f"media_{int(time.time())}_{len(self._get_media_cache())}"
                    
                    media_info = {
                        "id": media_id,
                        "path": media_path,
                        "title": os.path.basename(media_path),
                        "type": media_type,
                        "format": file_ext,
                        "size": file_info.get("size", 0),
                        "created_at": file_info.get("created_at"),
                        "modified_at": file_info.get("modified_at"),
                        "mime_type": mimetypes.guess_type(media_path)[0] or f"{media_type}/{file_ext}",
                        "duration": 0,  # Will be updated when played
                        "metadata": {}
                    }
                    
                    # Add to media cache
                    self._get_media_cache()[media_id] = media_info
                    
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "success",
                                "value": True,
                                "type": "boolean"
                            },
                            {
                                "name": "media_info",
                                "value": media_info,
                                "type": "object"
                            }
                        ]
                    }
                else:
                    return self._error_response("No file_system cell connected, cannot get media info")
                
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return self._error_response(f"Error getting media info: {str(e)}")
    
    def _get_media_cache(self) -> Dict[str, Dict[str, Any]]:
        """Get or initialize the media cache."""
        if not hasattr(self, "_media_cache"):
            self._media_cache = {}
        return self._media_cache
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to mm:ss format."""
        if not seconds:
            return "0:00"
        
        minutes = seconds // 60
        seconds = seconds % 60
        
        return f"{minutes}:{seconds:02d}"
    
    def _get_connected_cell_by_capability(self, capability: str) -> Optional[str]:
        """
        Find a connected cell with the specified capability.
        
        Args:
            capability: The capability to look for
        
        Returns:
            Cell ID of a connected cell with the capability, or None if not found
        """
        for connection in self.connections:
            if hasattr(connection, 'capabilities') and capability in connection.capabilities:
                return connection.id
        return None
    
    async def call_capability(self, cell_id: str, capability: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a capability on another cell.
        
        Args:
            cell_id: ID of the cell to call
            capability: Capability to call
            parameters: Parameters for the capability
        
        Returns:
            Result of the capability call
        
        Raises:
            CellConnectionError: If the cell is not connected
            CapabilityExecutionError: If the capability call fails
        """
        # In a real implementation, this would use the cell runtime messaging system
        # This is a simplified implementation for demonstration
        
        # Check if the cell is connected
        cell_connected = any(c.id == cell_id for c in self.connections)
        if not cell_connected:
            raise CellConnectionError(f"Cell {cell_id} is not connected")
        
        try:
            # Simulate calling the capability
            # In a real implementation, this would use the cell runtime's API
            logger.debug(f"Calling capability {capability} on cell {cell_id}")
            
            # Return a mock result for demonstration
            # This would be replaced with the actual capability call in a real implementation
            if capability == "get_file_info":
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "file_info",
                            "value": {
                                "size": 1024 * 1024,  # 1MB
                                "created_at": time.time() - 86400,  # 1 day ago
                                "modified_at": time.time() - 3600,  # 1 hour ago
                                "mime_type": "audio/mpeg",
                                "is_directory": False
                            },
                            "type": "object"
                        }
                    ]
                }
            elif capability == "read_file":
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "content",
                            "value": "File content would be here.",
                            "type": "string"
                        }
                    ]
                }
            elif capability == "write_file":
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        }
                    ]
                }
            else:
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        }
                    ]
                }
            
        except Exception as e:
            raise CapabilityExecutionError(f"Error calling {capability} on cell {cell_id}: {str(e)}")
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
        
        Returns:
            Error response dictionary
        """
        logger.error(f"Error in media player cell: {message}")
        return {
            "status": "error",
            "error": message,
            "outputs": [
                {
                    "name": "error",
                    "value": message,
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 1,
                "memory_used_mb": 0.1
            }
        }
    
    async def suspend(self) -> Dict[str, Any]:
        """
        Prepare for suspension by saving state.
        
        Returns:
            Suspension result with saved state
        """
        try:
            # Prepare state for suspension
            state = {
                "current_media": self.current_media,
                "playback_state": self.playback_state,
                "playback_position": self.playback_position,
                "volume": self.volume,
                "playlists": self.playlists,
                "media_cache": self._get_media_cache(),
                "settings": self.settings
            }
            
            # If currently playing, pause playback
            if self.playback_state == "playing":
                self.playback_state = "paused"
            
            result = {
                "status": "success",
                "state": "suspended",
                "saved_state": state
            }
            
            logger.info("Media player cell suspended")
            return result
            
        except Exception as e:
            logger.error(f"Error during suspension: {e}")
            return {
                "status": "error",
                "state": "error",
                "error": f"Suspension failed: {str(e)}"
            }
    
    async def resume(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume from suspension with saved state.
        
        Args:
            parameters: Resume parameters including saved state
        
        Returns:
            Resume result
        """
        try:
            # Restore state if provided
            if "saved_state" in parameters:
                saved_state = parameters["saved_state"]
                
                if "current_media" in saved_state:
                    self.current_media = saved_state["current_media"]
                
                if "playback_state" in saved_state:
                    self.playback_state = saved_state["playback_state"]
                
                if "playback_position" in saved_state:
                    self.playback_position = saved_state["playback_position"]
                
                if "volume" in saved_state:
                    self.volume = saved_state["volume"]
                
                if "playlists" in saved_state:
                    self.playlists = saved_state["playlists"]
                
                if "media_cache" in saved_state:
                    self._media_cache = saved_state["media_cache"]
                
                if "settings" in saved_state:
                    self.settings.update(saved_state["settings"])
                
                logger.info("Media player cell resumed with saved state")
            else:
                logger.warning("Resumed without saved state")
            
            return {
                "status": "success",
                "state": "active"
            }
            
        except Exception as e:
            logger.error(f"Error during resume: {e}")
            return {
                "status": "error",
                "state": "error",
                "error": f"Resume failed: {str(e)}"
            }
    
    async def release(self) -> Dict[str, Any]:
        """
        Prepare for release.
        
        Returns:
            Release result
        """
        try:
            # Stop playback
            self.playback_state = "stopped"
            self.current_media = None
            self.playback_position = 0
            
            # Clear state
            self.playlists = {}
            if hasattr(self, "_media_cache"):
                self._media_cache = {}
            
            logger.info("Media player cell released")
            
            return {
                "status": "success",
                "state": "released"
            }
            
        except Exception as e:
            logger.error(f"Error during release: {e}")
            return {
                "status": "error",
                "state": "error",
                "error": f"Release failed: {str(e)}"
            }
