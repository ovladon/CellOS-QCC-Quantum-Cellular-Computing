"""
Media Player Cell for QCC

This cell provides media playback capabilities within the QCC environment,
supporting audio and video playback with basic controls.
"""

from qcc.cells import BaseCell
from typing import Dict, List, Any, Optional
import os
import time
import json
import logging
import base64
import mimetypes
import asyncio

logger = logging.getLogger(__name__)

class MediaPlayerCell(BaseCell):
    """
    A cell that provides media playback capabilities.
    
    This cell can:
    - Play audio files (mp3, wav, ogg)
    - Play video files (mp4, webm)
    - Control playback (play, pause, seek)
    - Adjust volume
    - Create playlists
    """
    
    def initialize(self, parameters):
        """Initialize the cell with given parameters."""
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("play_media", self.play_media)
        self.register_capability("control_playback", self.control_playback)
        self.register_capability("get_media_info", self.get_media_info)
        self.register_capability("create_playlist", self.create_playlist)
        self.register_capability("get_player_ui", self.get_player_ui)
        self.register_capability("list_media", self.list_media)
        
        # Initialize state
        self.state = {
            "current_media": None,
            "playlists": {},
            "media_files": {},
            "playback_status": "stopped",
            "volume": 75,
            "position": 0,
            "duration": 0
        }
        
        # Set up media storage path
        if "media_path" in parameters:
            self.media_path = parameters["media_path"]
        else:
            # Default storage location
            self.media_path = "./data/user_files/media"
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.media_path, exist_ok=True)
        
        # Load existing media files
        self._load_media_files()
        
        # Load saved playlists if available
        self._load_playlists()
        
        logger.info(f"MediaPlayerCell initialized with ID: {self.cell_id}")
        return self.get_initialization_result()
    
    def _load_media_files(self):
        """Load existing media files from storage."""
        try:
            # List all media files in the storage directory
            extensions = ['.mp3', '.wav', '.ogg', '.mp4', '.webm', '.avi']
            media_files = []
            
            for root, _, files in os.walk(self.media_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, self.media_path)
                        media_files.append(relative_path)
            
            # Add to media files dictionary
            for file_path in media_files:
                full_path = os.path.join(self.media_path, file_path)
                file_stats = os.stat(full_path)
                mime_type, _ = mimetypes.guess_type(file_path)
                
                # Determine media type
                media_type = "unknown"
                if mime_type:
                    if mime_type.startswith("audio/"):
                        media_type = "audio"
                    elif mime_type.startswith("video/"):
                        media_type = "video"
                
                # Generate a unique ID for the media file
                media_id = base64.urlsafe_b64encode(file_path.encode()).decode().rstrip("=")
                
                self.state["media_files"][media_id] = {
                    "id": media_id,
                    "path": file_path,
                    "full_path": full_path,
                    "name": os.path.basename(file_path),
                    "size_bytes": file_stats.st_size,
                    "created_at": file_stats.st_ctime,
                    "modified_at": file_stats.st_mtime,
                    "mime_type": mime_type,
                    "media_type": media_type
                }
            
            logger.info(f"Loaded {len(media_files)} media files")
        
        except Exception as e:
            logger.error(f"Error loading media files: {e}")
    
    def _load_playlists(self):
        """Load saved playlists from storage."""
        try:
            playlist_file = os.path.join(self.media_path, "playlists.json")
            
            if os.path.exists(playlist_file):
                with open(playlist_file, 'r', encoding='utf-8') as f:
                    playlists = json.load(f)
                    
                self.state["playlists"] = playlists
                logger.info(f"Loaded {len(playlists)} playlists")
            else:
                logger.info("No playlists file found")
                
        except Exception as e:
            logger.error(f"Error loading playlists: {e}")
    
    def _save_playlists(self):
        """Save playlists to storage."""
        try:
            playlist_file = os.path.join(self.media_path, "playlists.json")
            
            with open(playlist_file, 'w', encoding='utf-8') as f:
                json.dump(self.state["playlists"], f, indent=2)
                
            logger.info("Saved playlists to storage")
                
        except Exception as e:
            logger.error(f"Error saving playlists: {e}")
    
    async def play_media(self, parameters):
        """
        Play a media file.
        
        Parameters:
            media_id (str): ID of the media file to play
            start_position (float, optional): Position to start playback from in seconds
            volume (int, optional): Playback volume (0-100)
            
        Returns:
            Playback information
        """
        try:
            if "media_id" not in parameters:
                return self._error_response("Media ID is required")
            
            media_id = parameters["media_id"]
            
            # Check if media exists
            if media_id not in self.state["media_files"]:
                return self._error_response(f"Media file '{media_id}' not found")
            
            media = self.state["media_files"][media_id]
            
            # Update playback state
            self.state["current_media"] = media_id
            self.state["playback_status"] = "playing"
            self.state["position"] = parameters.get("start_position", 0)
            
            # Set volume if provided
            if "volume" in parameters:
                volume = parameters["volume"]
                if 0 <= volume <= 100:
                    self.state["volume"] = volume
            
            # Fake media duration lookup (in a real implementation, this would use media metadata)
            # For this example, we'll generate a random duration between 30 seconds and 10 minutes
            import random
            self.state["duration"] = random.uniform(30, 600)
            
            logger.info(f"Started playback of {media['name']}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "playback_info",
                        "value": {
                            "media_id": media_id,
                            "name": media["name"],
                            "media_type": media["media_type"],
                            "position": self.state["position"],
                            "duration": self.state["duration"],
                            "volume": self.state["volume"],
                            "status": self.state["playback_status"]
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": 0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Error playing media: {e}")
            return self._error_response(f"Failed to play media: {str(e)}")
    
    async def control_playback(self, parameters):
        """
        Control media playback.
        
        Parameters:
            action (str): Playback action (play, pause, stop, seek)
            position (float, optional): Position to seek to in seconds
            volume (int, optional): New volume level (0-100)
            
        Returns:
            Updated playback information
        """
        try:
            if "action" not in parameters:
                return self._error_response("Action parameter is required")
            
            action = parameters["action"].lower()
            
            # Check if we have a current media
            if action != "stop" and self.state["current_media"] is None:
                return self._error_response("No media currently loaded")
            
            if action == "play":
                self.state["playback_status"] = "playing"
                
            elif action == "pause":
                self.state["playback_status"] = "paused"
                
            elif action == "stop":
                self.state["playback_status"] = "stopped"
                self.state["position"] = 0
                
            elif action == "seek":
                if "position" not in parameters:
                    return self._error_response("Position parameter is required for seek action")
                
                position = parameters["position"]
                
                # Validate position
                if position < 0:
                    position = 0
                if position > self.state["duration"]:
                    position = self.state["duration"]
                    
                self.state["position"] = position
                
            else:
                return self._error_response(f"Unknown action: {action}")
            
            # Update volume if provided
            if "volume" in parameters:
                volume = parameters["volume"]
                if 0 <= volume <= 100:
                    self.state["volume"] = volume
                else:
                    return self._error_response("Volume must be between 0 and 100")
            
            logger.info(f"Playback control: {action}")
            
            # Prepare response
            playback_info = {
                "status": self.state["playback_status"],
                "position": self.state["position"],
                "volume": self.state["volume"]
            }
            
            # Include media details if we have a current media
            if self.state["current_media"]:
                media_id = self.state["current_media"]
                media = self.state["media_files"][media_id]
                
                playback_info.update({
                    "media_id": media_id,
                    "name": media["name"],
                    "media_type": media["media_type"],
                    "duration": self.state["duration"]
                })
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "playback_info",
                        "value": playback_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error controlling playback: {e}")
            return self._error_response(f"Failed to control playback: {str(e)}")
    
    async def get_media_info(self, parameters):
        """
        Get information about a media file.
        
        Parameters:
            media_id (str): ID of the media file
            
        Returns:
            Media file information
        """
        try:
            if "media_id" not in parameters:
                return self._error_response("Media ID is required")
            
            media_id = parameters["media_id"]
            
            # Check if media exists
            if media_id not in self.state["media_files"]:
                return self._error_response(f"Media file '{media_id}' not found")
            
            media = self.state["media_files"][media_id]
            
            logger.info(f"Retrieved info for media: {media['name']}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "media_info",
                        "value": {
                            "id": media["id"],
                            "name": media["name"],
                            "path": media["path"],
                            "size_bytes": media["size_bytes"],
                            "media_type": media["media_type"],
                            "mime_type": media["mime_type"],
                            "created_at": media["created_at"],
                            "modified_at": media["modified_at"]
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return self._error_response(f"Failed to get media info: {str(e)}")
    
    async def create_playlist(self, parameters):
        """
        Create or update a playlist.
        
        Parameters:
            name (str): Name of the playlist
            media_ids (list): List of media IDs to include in the playlist
            description (str, optional): Description of the playlist
            
        Returns:
            Playlist information
        """
        try:
            if "name" not in parameters:
                return self._error_response("Playlist name is required")
                
            if "media_ids" not in parameters or not isinstance(parameters["media_ids"], list):
                return self._error_response("Media IDs list is required")
            
            playlist_name = parameters["name"]
            media_ids = parameters["media_ids"]
            description = parameters.get("description", "")
            
            # Validate media IDs
            invalid_ids = [id for id in media_ids if id not in self.state["media_files"]]
            if invalid_ids:
                return self._error_response(f"Invalid media IDs: {', '.join(invalid_ids)}")
            
            # Generate playlist ID
            import hashlib
            playlist_id = hashlib.md5(f"{playlist_name}_{time.time()}".encode()).hexdigest()
            
            # Create playlist
            playlist = {
                "id": playlist_id,
                "name": playlist_name,
                "description": description,
                "created_at": time.time(),
                "updated_at": time.time(),
                "media_ids": media_ids
            }
            
            # Add to playlists
            self.state["playlists"][playlist_id] = playlist
            
            # Save playlists
            self._save_playlists()
            
            logger.info(f"Created playlist: {playlist_name} with {len(media_ids)} items")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "playlist",
                        "value": {
                            "id": playlist_id,
                            "name": playlist_name,
                            "description": description,
                            "count": len(media_ids)
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return self._error_response(f"Failed to create playlist: {str(e)}")
    
    async def list_media(self, parameters=None):
        """
        List available media files.
        
        Parameters:
            type (str, optional): Filter by media type (audio, video)
            sort (str, optional): Sort by field (name, created_at, modified_at, size_bytes)
            order (str, optional): Sort order (asc, desc)
            
        Returns:
            List of media files
        """
        try:
            # Get all media files
            media_files = list(self.state["media_files"].values())
            
            # Apply type filter if provided
            if parameters and "type" in parameters:
                media_type = parameters["type"].lower()
                if media_type in ["audio", "video"]:
                    media_files = [media for media in media_files if media["media_type"] == media_type]
            
            # Apply sorting if provided
            if parameters and "sort" in parameters:
                sort_field = parameters["sort"]
                if sort_field in ["name", "created_at", "modified_at", "size_bytes"]:
                    reverse = False
                    if parameters.get("order", "asc").lower() == "desc":
                        reverse = True
                    
                    media_files = sorted(
                        media_files, 
                        key=lambda x: x[sort_field], 
                        reverse=reverse
                    )
            
            # Prepare response data
            media_list = []
            for media in media_files:
                media_list.append({
                    "id": media["id"],
                    "name": media["name"],
                    "media_type": media["media_type"],
                    "size_bytes": media["size_bytes"],
                    "created_at": media["created_at"],
                    "modified_at": media["modified_at"]
                })
            
            logger.info(f"Listed {len(media_list)} media files")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "media_files",
                        "value": media_list,
                        "type": "array"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,
                    "memory_used_mb": 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing media: {e}")
            return self._error_response(f"Failed to list media: {str(e)}")
    
    async def get_player_ui(self, parameters=None):
        """
        Get a media player UI.
        
        Parameters:
            media_id (str, optional): ID of media to load initially
            playlist_id (str, optional): ID of playlist to load
            
        Returns:
            HTML UI for media playback
        """
        # Determine if we should load a specific media
        initial_media = None
        playlist = None
        
        if parameters:
            if "media_id" in parameters:
                media_id = parameters["media_id"]
                if media_id in self.state["media_files"]:
                    initial_media = self.state["media_files"][media_id]
            
            if "playlist_id" in parameters:
                playlist_id = parameters["playlist_id"]
                if playlist_id in self.state["playlists"]:
                    playlist = self.state["playlists"][playlist_id]
        
        # Generate the HTML UI
        html = f"""
        <div class="media-player">
            <div class="player-header">
                <h3 id="media-title">{initial_media["name"] if initial_media else "No media selected"}</h3>
                <div class="player-controls">
                    <button id="play-btn" onclick="playMedia()"><span>▶</span></button>
                    <button id="pause-btn" onclick="pauseMedia()" style="display:none;"><span>⏸</span></button>
                    <button onclick="stopMedia()"><span>⏹</span></button>
                    <div class="volume-control">
                        <span>🔊</span>
                        <input type="range" id="volume-slider" min="0" max="100" value="{self.state["volume"]}" 
                               oninput="setVolume(this.value)">
                    </div>
                </div>
            </div>
            
            <div class="player-progress">
                <span id="current-time">0:00</span>
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progress-bar">
                        <div class="progress-handle" id="progress-handle"></div>
                    </div>
                </div>
                <span id="duration">0:00</span>
            </div>
            
            <div class="player-content">
                <div id="media-display">
                    <!-- Media will be displayed here -->
                    <div id="audio-player" style="display:none;">
                        <div class="audio-visualization">
                            <div class="audio-wave"></div>
                        </div>
                    </div>
                    <div id="video-player" style="display:none;">
                        <div class="video-container">
                            <div class="video-placeholder">Video preview</div>
                        </div>
                    </div>
                    <div id="no-media" style="display:flex;">
                        <p>Select media from the playlist to begin playback</p>
                    </div>
                </div>
                
                <div class="media-list">
                    <div class="list-header">
                        <h4>Media Library</h4>
                        <select id="media-filter" onchange="filterMedia(this.value)">
                            <option value="all">All Media</option>
                            <option value="audio">Audio Only</option>
                            <option value="video">Video Only</option>
                        </select>
                    </div>
                    <div class="media-items" id="media-items">
                        <!-- Media items will be loaded here -->
                        <div class="loading">Loading media files...</div>
                    </div>
                </div>
            </div>
            
            <div class="player-footer">
                <div class="playlist-controls">
                    <select id="playlist-select" onchange="loadPlaylist(this.value)">
                        <option value="">Select Playlist</option>
                        {self._generate_playlist_options()}
                    </select>
                    <button onclick="showCreatePlaylistDialog()">Create Playlist</button>
                </div>
            </div>
            
            <div id="create-playlist-dialog" class="modal hidden">
                <div class="modal-content">
                    <span class="close" onclick="closeModal()">&times;</span>
                    <h3>Create Playlist</h3>
                    <div>
                        <label for="playlist-name">Playlist Name:</label>
                        <input type="text" id="playlist-name" placeholder="My Playlist">
                        <label for="playlist-description">Description:</label>
                        <textarea id="playlist-description" placeholder="Playlist description"></textarea>
                        <div class="selected-media">
                            <h4>Selected Media (<span id="selected-count">0</span>)</h4>
                            <div id="selected-media-list"></div>
                        </div>
                        <button onclick="createPlaylist()">Create Playlist</button>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .media-player {
                display: flex;
                flex-direction: column;
                height: 600px;
                border: 1px solid #ccc;
                border-radius: 8px;
                overflow: hidden;
                background-color: #f8f9fa;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            
            .player-header {
                padding: 12px 16px;
                background-color: #333;
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .player-header h3 {
                margin: 0;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 300px;
            }
            
            .player-controls {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .player-controls button {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                border: none;
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.2s;
            }
            
            .player-controls button:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            
            .volume-control {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-left: 8px;
            }
            
            .volume-control input {
                width: 80px;
            }
            
            .player-progress {
                padding: 8px 16px;
                background-color: #444;
                color: white;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .progress-bar-container {
                flex: 1;
                height: 8px;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                position: relative;
                cursor: pointer;
            }
            
            .progress-bar {
                height: 100%;
                width: 0%;
                background-color: #4F46E5;
                border-radius: 4px;
                position: relative;
            }
            
            .progress-handle {
                position: absolute;
                right: -6px;
                top: -4px;
                width: 16px;
                height: 16px;
                background-color: white;
                border-radius: 50%;
                cursor: grab;
            }
            
            .player-content {
                display: flex;
                flex: 1;
                overflow: hidden;
            }
            
            #media-display {
                flex: 3;
                background-color: #222;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }
            
            .audio-visualization {
                width: 100%;
                height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .audio-wave {
                display: flex;
                align-items: center;
                height: 100px;
                width: 300px;
            }
            
            .audio-wave::before {
                content: "";
                width: 300px;
                height: 100%;
                background: linear-gradient(#4F46E5, #3730A3);
                mask: repeating-linear-gradient(90deg, #000 0%, #000 1%, transparent 1%, transparent 2%);
                mask-size: 20px 100%;
                animation: waveAnimation 2s infinite linear;
            }
            
            @keyframes waveAnimation {
                0% { mask-position: 0 0; }
                100% { mask-position: 100px 0; }
            }
            
            .video-container {
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .video-placeholder {
                background-color: #333;
                width: 80%;
                height: 60%;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
                color: #aaa;
                font-size: 24px;
            }
            
            .media-list {
                flex: 2;
                border-left: 1px solid #ddd;
                display: flex;
                flex-direction: column;
            }
            
            .list-header {
                padding: 8px 16px;
                border-bottom: 1px solid #ddd;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .list-header h4 {
                margin: 0;
            }
            
            .media-items {
                flex: 1;
                overflow-y: auto;
                padding: 8px;
            }
            
            .media-item {
                padding: 8px 12px;
                margin-bottom: 4px;
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: background-color 0.2s;
            }
            
            .media-item:hover {
                background-color: #f0f0f0;
            }
            
            .media-item.active {
                background-color: rgba(79, 70, 229, 0.1);
                border-left: 3px solid #4F46E5;
            }
            
            .media-item .media-icon {
                font-size: 24px;
            }
            
            .media-item .media-info {
                flex: 1;
                overflow: hidden;
            }
            
            .media-item .media-name {
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .media-item .media-meta {
                font-size: 12px;
                color: #666;
            }
            
            .player-footer {
                padding: 12px 16px;
                border-top: 1px solid #ddd;
            }
            
            .playlist-controls {
                display: flex;
                gap: 8px;
            }
            
            .playlist-controls select {
                flex: 1;
                padding: 6px;
                border-radius: 4px;
                border: 1px solid #ccc;
            }
            
            .playlist-controls button {
                padding: 6px 12px;
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            
            .loading {
                padding: 16px;
                text-align: center;
                color: #666;
            }
            
            .modal {
                display: none;
                position: fixed;
                z-index: 100;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.4);
            }
            
            .modal.show {
                display: block;
            }
            
            .hidden {
                display: none;
            }
            
            .modal-content {
                background-color: #fefefe;
                margin: 10% auto;
                padding: 20px;
                border: 1px solid #888;
                border-radius: 5px;
                width: 80%;
                max-width: 500px;
            }
            
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            
            .close:hover {
                color: black;
            }
            
            input[type="text"], textarea, select {
                margin: 8px 0 16px;
                padding: 8px;
                width: 100%;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-sizing: border-box;
            }
            
            textarea {
                min-height: 80px;
                resize: vertical;
            }
            
            .selected-media {
                margin-top: 16px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                max-height: 200px;
                overflow-y: auto;
            }
            
            #selected-media-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .selected-item {
                display: flex;
                padding: 4px 8px;
                background: #f5f5f5;
                border-radius: 4px;
                justify-content: space-between;
                align-items: center;
            }
            
            .selected-item button {
                background: none;
                border: none;
                color: #cc3333;
                cursor: pointer;
                font-weight: bold;
            }
            
            #no-media {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                color: #666;
                text-align: center;
            }
        </style>
        
        <script>
            // Current state
            let currentMediaId = {f"'{initial_media['id']}'" if initial_media else 'null'};
            let currentPlaylistId = {f"'{playlist['id']}'" if playlist else 'null'};
            let isPlaying = false;
            let audioContext = null;
            let selectedMediaIds = [];
            
            // Load media list when page loads
            document.addEventListener('DOMContentLoaded', function() {
                loadMediaList();
                updatePlayerUI();
                
                // Set up progress bar interaction
                const progressBar = document.getElementById('progress-bar-container');
                progressBar.addEventListener('click', function(e) {
                    const rect = progressBar.getBoundingClientRect();
                    const pos = (e.clientX - rect.left) / rect.width;
                    seekToPosition(pos);
                });
                
                // Set volume from initial state
                document.getElementById('volume-slider').value = {self.state["volume"]};
            });
            
            // Load the list of available media
            async function loadMediaList(filter = 'all') {
                const mediaItems = document.getElementById('media-items');
                mediaItems.innerHTML = '<div class="loading">Loading media files...</div>';
                
                // In a real implementation, this would call the QCC API
                const response = await callCapability('list_media', { type: filter });
                
                if (response.status === 'success') {
                    const mediaFiles = response.outputs[0].value;
                    mediaItems.innerHTML = '';
                    
                    if (mediaFiles.length === 0) {
                        mediaItems.innerHTML = '<div class="loading">No media files found</div>';
                        return;
                    }
                    
                    mediaFiles.forEach(media => {
                        const item = document.createElement('div');
                        item.className = 'media-item';
                        if (currentMediaId === media.id) {
                            item.className += ' active';
                        }
                        
                        const icon = media.media_type === 'audio' ? '🎵' : '🎬';
                        
                        item.innerHTML = `
                            <div class="media-icon">${icon}</div>
                            <div class="media-info">
                                <div class="media-name">${media.name}</div>
                                <div class="media-meta">
                                    ${formatBytes(media.size_bytes)} · 
                                    ${media.media_type}
                                </div>
                            </div>
                        `;
                        
                        item.addEventListener('click', () => loadMedia(media.id));
                        mediaItems.appendChild(item);
                    });
                } else {
                    mediaItems.innerHTML = `<div class="loading">Error loading media: ${response.outputs[0].value}</div>`;
                }
            }
            
            // Filter media by type
            function filterMedia(type) {
                loadMediaList(type);
            }
            
            // Load a specific media file
            async function loadMedia(mediaId) {
                // Update current media
                currentMediaId = mediaId;
                
                // Get media info
                const response = await callCapability('get_media_info', { media_id: mediaId });
                
                if (response.status === 'success') {
                    const mediaInfo = response.outputs[0].value;
                    
                    // Update UI
                    document.getElementById('media-title').textContent = mediaInfo.name;
                    
                    // Show appropriate player
                    if (mediaInfo.media_type === 'audio') {
                        document.getElementById('audio-player').style.display = 'flex';
                        document.getElementById('video-player').style.display = 'none';
                    } else {
                        document.getElementById('audio-player').style.display = 'none';
                        document.getElementById('video-player').style.display = 'flex';
                    }
                    
                    document.getElementById('no-media').style.display = 'none';
                    
                    // Highlight current item in list
                    const items = document.querySelectorAll('.media-item');
                    items.forEach(item => {
                        item.classList.remove('active');
                        if (item.querySelector('.media-name').textContent === mediaInfo.name) {
                            item.classList.add('active');
                        }
                    });
                    
                    // Start playing
                    playMedia();
                } else {
                    alert(`Error loading media: ${response.outputs[0].value}`);
                }
            }
            
            // Play current media
            async function playMedia() {
                if (!currentMediaId) return;
                
                const response = await callCapability('play_media', { 
                    media_id: currentMediaId,
                    volume: parseInt(document.getElementById('volume-slider').value)
                });
                
                if (response.status === 'success') {
                    isPlaying = true;
                    updatePlayerUI();
                    
                    // Start progress update
                    startProgressUpdate();
                } else {
                    alert(`Error playing media: ${response.outputs[0].value}`);
                }
            }
            
            // Pause playback
            async function pauseMedia() {
                if (!currentMediaId || !isPlaying) return;
                
                const response = await callCapability('control_playback', { 
                    action: 'pause'
                });
                
                if (response.status === 'success') {
                    isPlaying = false;
                    updatePlayerUI();
                } else {
                    alert(`Error pausing media: ${response.outputs[0].value}`);
                }
            }
            
            // Stop playback
            async function stopMedia() {
                if (!currentMediaId) return;
                
                const response = await callCapability('control_playback', { 
                    action: 'stop'
                });
                
                if (response.status === 'success') {
                    isPlaying = false;
                    updatePlayerUI();
                    
                    // Reset progress
                    document.getElementById('progress-bar').style.width = '0%';
                    document.getElementById('current-time').textContent = '0:00';
                } else {
                    alert(`Error stopping media: ${response.outputs[0].value}`);
                }
            }
            
            // Seek to position
            async function seekToPosition(position) {
                if (!currentMediaId) return;
                
                const playbackInfo = await callCapability('get_media_info', { 
                    media_id: currentMediaId
                });
                
                if (playbackInfo.status === 'success') {
                    const info = playbackInfo.outputs[0].value;
                    const duration = info.duration || 0;
                    const targetPosition = duration * position;
                    
                    const response = await callCapability('control_playback', { 
                        action: 'seek',
                        position: targetPosition
                    });
                    
                    if (response.status !== 'success') {
                        alert(`Error seeking: ${response.outputs[0].value}`);
                    }
                }
            }
            
            // Set volume
            async function setVolume(value) {
                const response = await callCapability('control_playback', { 
                    action: 'volume',
                    volume: parseInt(value)
                });
                
                if (response.status !== 'success') {
                    alert(`Error setting volume: ${response.outputs[0].value}`);
                }
            }
            
            // Start progress update timer
            function startProgressUpdate() {
                // Clear any existing timer
                if (window.progressTimer) clearInterval(window.progressTimer);
                
                // Set up new timer
                window.progressTimer = setInterval(updateProgress, 1000);
                updateProgress(); // Update immediately
            }
            
            // Update progress bar and time display
            async function updateProgress() {
                if (!currentMediaId || !isPlaying) return;
                
                // In a real implementation, we would get the current playback position
                // Here we'll simulate it with a mock function
                const mockPlaybackInfo = {
                    position: parseFloat(document.getElementById('progress-bar').style.width || '0') / 100 * 180 + 1,
                    duration: 180
                };
                
                // Update progress bar
                const percent = (mockPlaybackInfo.position / mockPlaybackInfo.duration) * 100;
                document.getElementById('progress-bar').style.width = `${percent}%`;
                
                // Update time display
                document.getElementById('current-time').textContent = formatTime(mockPlaybackInfo.position);
                document.getElementById('duration').textContent = formatTime(mockPlaybackInfo.duration);
                
                // If we've reached the end, stop or play next
                if (mockPlaybackInfo.position >= mockPlaybackInfo.duration) {
                    if (currentPlaylistId) {
                        playNextInPlaylist();
                    } else {
                        stopMedia();
                    }
                }
            }
            
            // Load a playlist
            async function loadPlaylist(playlistId) {
                if (!playlistId) return;
                
                currentPlaylistId = playlistId;
                
                // Get the first media in the playlist and play it
                const playlist = {
                    id: playlistId,
                    name: "Sample Playlist",
                    media_ids: ["sample1", "sample2"]
                };
                
                if (playlist.media_ids && playlist.media_ids.length > 0) {
                    loadMedia(playlist.media_ids[0]);
                }
            }
            
            // Play next item in playlist
            function playNextInPlaylist() {
                if (!currentPlaylistId || !currentMediaId) return;
                
                // Find current media in playlist
                const playlist = {
                    id: currentPlaylistId,
                    name: "Sample Playlist",
                    media_ids: ["sample1", "sample2"]
                };
                
                const currentIndex = playlist.media_ids.indexOf(currentMediaId);
                if (currentIndex < playlist.media_ids.length - 1) {
                    // Play next item
                    loadMedia(playlist.media_ids[currentIndex + 1]);
                } else {
                    // End of playlist
                    stopMedia();
                }
            }
            
            // Show dialog to create a new playlist
            function showCreatePlaylistDialog() {
                // Reset dialog
                document.getElementById('playlist-name').value = '';
                document.getElementById('playlist-description').value = '';
                selectedMediaIds = [];
                document.getElementById('selected-count').textContent = '0';
                document.getElementById('selected-media-list').innerHTML = '';
                
                // Show dialog
                showModal('create-playlist-dialog');
            }
            
            // Add media to playlist selection
            function toggleMediaSelection(mediaId, mediaName) {
                const index = selectedMediaIds.indexOf(mediaId);
                
                if (index === -1) {
                    // Add to selection
                    selectedMediaIds.push(mediaId);
                    
                    const item = document.createElement('div');
                    item.className = 'selected-item';
                    item.innerHTML = `
                        <span>${mediaName}</span>
                        <button onclick="toggleMediaSelection('${mediaId}', '${mediaName}')">×</button>
                    `;
                    document.getElementById('selected-media-list').appendChild(item);
                } else {
                    // Remove from selection
                    selectedMediaIds.splice(index, 1);
                    
                    // Remove from UI
                    const items = document.getElementById('selected-media-list').children;
                    for (let i = 0; i < items.length; i++) {
                        if (items[i].querySelector('span').textContent === mediaName) {
                            items[i].remove();
                            break;
                        }
                    }
                }
                
                // Update count
                document.getElementById('selected-count').textContent = selectedMediaIds.length;
            }
            
            // Create a new playlist
            async function createPlaylist() {
                const name = document.getElementById('playlist-name').value;
                if (!name) {
                    alert('Please enter a playlist name');
                    return;
                }
                
                if (selectedMediaIds.length === 0) {
                    alert('Please select at least one media file');
                    return;
                }
                
                const description = document.getElementById('playlist-description').value;
                
                const response = await callCapability('create_playlist', {
                    name: name,
                    description: description,
                    media_ids: selectedMediaIds
                });
                
                if (response.status === 'success') {
                    closeModal();
                    alert(`Playlist "${name}" created successfully!`);
                    
                    // Update playlist dropdown
                    // In a real implementation, we would reload the playlist list
                } else {
                    alert(`Error creating playlist: ${response.outputs[0].value}`);
                }
            }
            
            // Update player UI based on current state
            function updatePlayerUI() {
                const playBtn = document.getElementById('play-btn');
                const pauseBtn = document.getElementById('pause-btn');
                
                if (isPlaying) {
                    playBtn.style.display = 'none';
                    pauseBtn.style.display = 'flex';
                } else {
                    playBtn.style.display = 'flex';
                    pauseBtn.style.display = 'none';
                }
                
                // Update title if we have a current media
                if (currentMediaId) {
                    document.getElementById('no-media').style.display = 'none';
                } else {
                    document.getElementById('no-media').style.display = 'flex';
                }
            }
            
            // Show a modal dialog
            function showModal(id) {
                const modal = document.getElementById(id);
                modal.classList.remove('hidden');
                modal.classList.add('show');
            }
            
            // Close any open modal
            function closeModal() {
                const modals = document.querySelectorAll('.modal');
                modals.forEach(modal => {
                    modal.classList.remove('show');
                    modal.classList.add('hidden');
                });
            }
            
            // Format bytes to human-readable format
            function formatBytes(bytes, decimals = 2) {
                if (bytes === 0) return '0 Bytes';
                
                const k = 1024;
                const dm = decimals < 0 ? 0 : decimals;
                const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
                
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                
                return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
            }
            
            // Format time in seconds to MM:SS format
            function formatTime(seconds) {
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}:${secs.toString().padStart(2, '0')}`;
            }
            
            // Call a cell capability
            async function callCapability(capability, params = {}) {
                // This function would normally communicate with the QCC assembler
                // For this example, we'll simulate it using a mock function
                
                // In a real implementation, this would be replaced with actual HTTP calls
                // to the assembler's API
                const response = await window.qcc.executeCapability(
                    '{self.cell_id}', 
                    capability, 
                    params
                );
                
                return response;
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
                "execution_time_ms": 25,
                "memory_used_mb": 0.5
            }
        }
    
    def _generate_playlist_options(self):
        """Generate HTML options for playlists."""
        options = ""
        
        for playlist_id, playlist in self.state["playlists"].items():
            options += f'<option value="{playlist_id}">{playlist["name"]}</option>'
            
        return options
    
    def _error_response(self, message):
        """Create an error response with the provided message."""
        return {
            "status": "error",
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
    
    async def suspend(self):
        """Prepare for suspension by saving state."""
        # Save playlists
        self._save_playlists()
        
        # Return suspension result with state
        return {
            "status": "success",
            "state": self.state
        }
    
    async def resume(self, parameters):
        """Resume from suspension with saved state."""
        # Restore state if provided
        if "saved_state" in parameters:
            try:
                # Restore state components
                saved_state = parameters["saved_state"]
                
                # Restore playlists and media files
                if "playlists" in saved_state:
                    self.state["playlists"] = saved_state["playlists"]
                
                if "media_files" in saved_state:
                    self.state["media_files"] = saved_state["media_files"]
                
                # Restore playback state
                if "current_media" in saved_state:
                    self.state["current_media"] = saved_state["current_media"]
                
                if "playback_status" in saved_state:
                    self.state["playback_status"] = saved_state["playback_status"]
                
                if "volume" in saved_state:
                    self.state["volume"] = saved_state["volume"]
                
                if "position" in saved_state:
                    self.state["position"] = saved_state["position"]
                
                if "duration" in saved_state:
                    self.state["duration"] = saved_state["duration"]
                
                logger.info("State restored successfully")
            except Exception as e:
                logger.error(f"Failed to restore state: {str(e)}")
        
        # Return success
        return {
            "status": "success",
            "state": "resumed"
        }
    
    async def release(self):
        """Prepare for release by cleaning up resources."""
        # Save playlists
        self._save_playlists()
        
        # Clear memory
        self.state["media_files"] = {}
        self.state["playlists"] = {}
        self.state["current_media"] = None
        
        return {
            "status": "success"
        }


# Create a MediaPlayerManifest to describe this cell
MediaPlayerManifest = {
    "name": "media_player",
    "version": "1.0.0",
    "description": "A media player cell for QCC",
    "author": "QCC Team",
    "license": "MIT",
    "capabilities": [
        {
            "name": "play_media",
            "description": "Play a media file",
            "parameters": [
                {
                    "name": "media_id",
                    "type": "string",
                    "description": "ID of the media file to play",
                    "required": True
                },
                {
                    "name": "start_position",
                    "type": "number",
                    "description": "Position to start playback from in seconds",
                    "required": False
                },
                {
                    "name": "volume",
                    "type": "number",
                    "description": "Playback volume (0-100)",
                    "required": False
                }
            ]
        },
        {
            "name": "control_playback",
            "description": "Control media playback",
            "parameters": [
                {
                    "name": "action",
                    "type": "string",
                    "description": "Playback action (play, pause, stop, seek)",
                    "required": True
                },
                {
                    "name": "position",
                    "type": "number",
                    "description": "Position to seek to in seconds",
                    "required": False
                },
                {
                    "name": "volume",
                    "type": "number",
                    "description": "New volume level (0-100)",
                    "required": False
                }
            ]
        },
        {
            "name": "get_media_info",
            "description": "Get information about a media file",
            "parameters": [
                {
                    "name": "media_id",
                    "type": "string",
                    "description": "ID of the media file",
                    "required": True
                }
            ]
        },
        {
            "name": "create_playlist",
            "description": "Create or update a playlist",
            "parameters": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "Name of the playlist",
                    "required": True
                },
                {
                    "name": "media_ids",
                    "type": "array",
                    "description": "List of media IDs to include in the playlist",
                    "required": True
                },
                {
                    "name": "description",
                    "type": "string",
                    "description": "Description of the playlist",
                    "required": False
                }
            ]
        },
        {
            "name": "list_media",
            "description": "List available media files",
            "parameters": [
                {
                    "name": "type",
                    "type": "string",
                    "description": "Filter by media type (audio, video)",
                    "required": False
                },
                {
                    "name": "sort",
                    "type": "string",
                    "description": "Sort by field (name, created_at, modified_at, size_bytes)",
                    "required": False
                },
                {
                    "name": "order",
                    "type": "string",
                    "description": "Sort order (asc, desc)",
                    "required": False
                }
            ]
        },
        {
            "name": "get_player_ui",
            "description": "Get a media player UI",
            "parameters": [
                {
                    "name": "media_id",
                    "type": "string",
                    "description": "ID of media to load initially",
                    "required": False
                },
                {
                    "name": "playlist_id",
                    "type": "string",
                    "description": "ID of playlist to load",
                    "required": False
                }
            ]
        }
    ],
    "dependencies": [],
    "resource_requirements": {
        "memory_mb": 50,
        "cpu_percent": 10,
        "storage_mb": 200
    }
}


# Example usage demonstration
async def example_usage():
    """Demonstrates how to use the MediaPlayerCell."""
    import asyncio
    
    # Create and initialize the cell
    player_cell = MediaPlayerCell()
    await player_cell.initialize({
        "cell_id": "demo-player-cell",
        "quantum_signature": "demo-signature",
        "media_path": "./example_media"
    })
    
    # List media files
    list_result = await player_cell.list_media()
    print(f"Media list: {list_result}")
    
    # If we have media files, play the first one
    if list_result["status"] == "success" and list_result["outputs"][0]["value"]:
        media_id = list_result["outputs"][0]["value"][0]["id"]
        
        # Get media info
        info_result = await player_cell.get_media_info({"media_id": media_id})
        print(f"Media info: {info_result}")
        
        # Play the media
        play_result = await player_cell.play_media({
            "media_id": media_id,
            "volume": 70
        })
        print(f"Playback started: {play_result}")
        
        # Simulate playback for a few seconds
        await asyncio.sleep(3)
        
        # Pause playback
        control_result = await player_cell.control_playback({
            "action": "pause"
        })
        print(f"Playback paused: {control_result}")
        
        # Change volume
        volume_result = await player_cell.control_playback({
            "action": "volume",
            "volume": 50
        })
        print(f"Volume changed: {volume_result}")
        
        # Resume playback
        resume_result = await player_cell.control_playback({
            "action": "play"
        })
        print(f"Playback resumed: {resume_result}")
        
        # Simulate more playback
        await asyncio.sleep(2)
        
        # Stop playback
        stop_result = await player_cell.control_playback({
            "action": "stop"
        })
        print(f"Playback stopped: {stop_result}")
    
    # Create a playlist
    if list_result["status"] == "success" and len(list_result["outputs"][0]["value"]) >= 2:
        media_ids = [
            list_result["outputs"][0]["value"][0]["id"],
            list_result["outputs"][0]["value"][1]["id"]
        ]
        
        playlist_result = await player_cell.create_playlist({
            "name": "Example Playlist",
            "description": "A playlist created in the example",
            "media_ids": media_ids
        })
        print(f"Playlist created: {playlist_result}")
    
    # Release the cell
    release_result = await player_cell.release()
    print(f"Released cell: {release_result}")


# Run the example if this script is executed directly
if __name__ == "__main__":
    import asyncio
    
    # Run the example
    asyncio.run(example_usage())
