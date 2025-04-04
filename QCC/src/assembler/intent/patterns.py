"""
Pattern definitions for the Intent Interpreter.

This module defines regex patterns for identifying user intents,
and the mapping between patterns and required capabilities.
"""

# Regular expression patterns for recognizing user intents
intentPatterns = {
    # Content creation and manipulation
    "create_document": r'\b(create|make|start|generate|write|draft)\s+a?\s*(document|doc|text|letter|email|report|essay|summary|article|post|message)\b',
    "edit_document": r'\b(edit|modify|change|update|revise)\s+a?\s*(document|doc|text|letter|email|report|essay|summary|article|post|message)\b',
    "format_document": r'\b(format|style|layout|arrange)\s+a?\s*(document|doc|text|letter|email|report|essay|summary|article|post|message)\b',
    
    # Media handling
    "image_viewing": r'\b(view|show|display|see|open)\s+a?\s*(image|photo|picture|pic|photograph|png|jpg|jpeg|gif)\b',
    "image_editing": r'\b(edit|modify|change|update|adjust|filter)\s+a?\s*(image|photo|picture|pic|photograph|png|jpg|jpeg|gif)\b',
    "video_playback": r'\b(watch|play|view|show|run)\s+a?\s*(video|movie|film|clip|youtube|mp4|avi|mov)\b',
    "audio_playback": r'\b(listen|play|hear)\s+a?\s*(audio|music|sound|song|track|mp3|wav|podcast)\b',
    
    # File operations
    "file_browsing": r'\b(browse|find|search|list)\s+a?\s*(file|folder|directory|document|location)\b',
    "file_management": r'\b(move|copy|delete|rename)\s+a?\s*(file|folder|directory|document)\b',
    
    # Data analysis
    "data_analysis": r'\b(analyze|analyse|examine|investigate|study|research)\s+a?\s*(data|information|statistics|numbers|figures|results)\b',
    "data_visualization": r'\b(visualize|visualise|chart|graph|plot|display)\s+a?\s*(data|information|statistics|numbers|figures|results)\b',
    "calculation": r'\b(calculate|compute|figure out|solve|find)\s+a?\s*(equation|formula|expression|sum|average|mean|median|percentage)\b',
    
    # Web and communication
    "web_browsing": r'\b(browse|open|go to|visit|navigate to|view)\s+a?\s*(website|site|webpage|url|link|address|http|www)\b',
    "web_search": r'\b(search|find|look up|google|query|research)\s+a?\s*(information|info|topic|subject|question|web|internet|online)\b',
    "communication": r'\b(send|compose|write)\s+a?\s*(email|message|chat|text|sms)\b',
    
    # App-specific
    "calculator": r'\b(calculator|calculate|compute|math|arithmetic|add|subtract|multiply|divide)\b',
    "calendar": r'\b(calendar|schedule|appointment|meeting|event|reminder|date)\b',
    "weather": r'\b(weather|forecast|temperature|climate|rain|snow|sunny|cloudy)\b',
    "maps": r'\b(map|directions|navigate|location|address|route|path|distance)\b',
    
    # Generic app requests
    "app_request": r'\b(open|start|launch|run|use)\s+a?\s*(app|application|program|software)\b',
    
    # UI elements
    "ui_request": r'\b(show|display|present|interface|ui|screen|button|menu|form|input)\b',
    
    # Help and information
    "help_request": r'\b(help|assist|support|guide|tutorial|instructions|how to|how do I)\b',
    "info_request": r'\b(tell|inform|what is|who is|where is|when is|why is|how is|information about|define|explain|describe)\b'
}

# Mapping between intent patterns and required capabilities
capabilityMapping = {
    "create_document": [
        {"name": "text_generation", "parameters": {"mode": "creative"}, "priority": 1, "confidence": 0.9},
        {"name": "file_system", "parameters": {"access": "write"}, "priority": 2, "confidence": 0.8}
    ],
    "edit_document": [
        {"name": "text_generation", "parameters": {"mode": "editing"}, "priority": 1, "confidence": 0.9},
        {"name": "file_system", "parameters": {"access": "read_write"}, "priority": 2, "confidence": 0.8}
    ],
    "format_document": [
        {"name": "text_generation", "parameters": {"mode": "formatting"}, "priority": 2, "confidence": 0.8},
        {"name": "ui_rendering", "parameters": {"type": "document_editor"}, "priority": 1, "confidence": 0.9}
    ],
    
    "image_viewing": [
        {"name": "media_processing", "parameters": {"type": "image", "mode": "view"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "image_viewer"}, "priority": 2, "confidence": 0.9}
    ],
    "image_editing": [
        {"name": "media_processing", "parameters": {"type": "image", "mode": "edit"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "image_editor"}, "priority": 2, "confidence": 0.9}
    ],
    "video_playback": [
        {"name": "media_processing", "parameters": {"type": "video", "mode": "play"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "video_player"}, "priority": 2, "confidence": 0.9}
    ],
    "audio_playback": [
        {"name": "media_processing", "parameters": {"type": "audio", "mode": "play"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "audio_player"}, "priority": 2, "confidence": 0.9}
    ],
    
    "file_browsing": [
        {"name": "file_system", "parameters": {"access": "read"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "file_browser"}, "priority": 2, "confidence": 0.9}
    ],
    "file_management": [
        {"name": "file_system", "parameters": {"access": "read_write"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "file_manager"}, "priority": 2, "confidence": 0.9}
    ],
    
    "data_analysis": [
        {"name": "data_analysis", "parameters": {"mode": "analysis"}, "priority": 1, "confidence": 0.9},
        {"name": "text_generation", "parameters": {"mode": "analytical"}, "priority": 2, "confidence": 0.8}
    ],
    "data_visualization": [
        {"name": "data_analysis", "parameters": {"mode": "visualization"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "data_visualizer"}, "priority": 2, "confidence": 0.9}
    ],
    "calculation": [
        {"name": "arithmetic", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "calculator"}, "priority": 2, "confidence": 0.8}
    ],
    
    "web_browsing": [
        {"name": "web_browser", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "web_view"}, "priority": 2, "confidence": 0.9}
    ],
    "web_search": [
        {"name": "web_search", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "text_generation", "parameters": {"mode": "informative"}, "priority": 2, "confidence": 0.8},
        {"name": "ui_rendering", "parameters": {"type": "search_results"}, "priority": 3, "confidence": 0.8}
    ],
    "communication": [
        {"name": "text_generation", "parameters": {"mode": "communication"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "message_composer"}, "priority": 2, "confidence": 0.8}
    ],
    
    "calculator": [
        {"name": "arithmetic", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "calculator"}, "priority": 2, "confidence": 0.9}
    ],
    "calendar": [
        {"name": "calendar", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "calendar"}, "priority": 2, "confidence": 0.9}
    ],
    "weather": [
        {"name": "weather", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "weather"}, "priority": 2, "confidence": 0.9}
    ],
    "maps": [
        {"name": "maps", "parameters": {}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "map"}, "priority": 2, "confidence": 0.9}
    ],
    
    "app_request": [
        {"name": "app_launcher", "parameters": {}, "priority": 1, "confidence": 0.8}
    ],
    
    "ui_request": [
        {"name": "ui_rendering", "parameters": {"type": "general"}, "priority": 1, "confidence": 0.8}
    ],
    
    "help_request": [
        {"name": "text_generation", "parameters": {"mode": "instructional"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "help_display"}, "priority": 2, "confidence": 0.8}
    ],
    "info_request": [
        {"name": "text_generation", "parameters": {"mode": "informative"}, "priority": 1, "confidence": 0.9},
        {"name": "ui_rendering", "parameters": {"type": "information_display"}, "priority": 2, "confidence": 0.8}
    ]
}
