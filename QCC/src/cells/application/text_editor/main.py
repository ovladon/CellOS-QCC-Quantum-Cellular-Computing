"""
Text Editor Cell Implementation for QCC

This cell provides text editing capabilities, allowing users to create,
edit, save, and load text documents within the QCC ecosystem.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import json

from qcc.cells import BaseCell
from qcc.common.exceptions import CellError, CellConnectionError, CapabilityExecutionError

logger = logging.getLogger(__name__)

class TextEditorCell(BaseCell):
    """
    A cell that provides text editing capabilities.
    
    This cell allows users to:
    - Create new text documents
    - Edit existing documents
    - Save documents (in collaboration with file_system cells)
    - Load documents (in collaboration with file_system cells)
    - Perform common text operations (search, replace, etc.)
    
    The cell can work standalone for in-memory document editing,
    but requires a file_system cell connection for persistence.
    """
    
    def initialize(self, parameters):
        """
        Initialize the text editor cell with parameters.
        
        Args:
            parameters: Initialization parameters including cell_id and context
        
        Returns:
            Initialization result with capabilities and requirements
        """
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("text_editor", self.text_editor_interface)
        self.register_capability("create_document", self.create_document)
        self.register_capability("edit_document", self.edit_document)
        self.register_capability("save_document", self.save_document)
        self.register_capability("load_document", self.load_document)
        self.register_capability("text_operations", self.text_operations)
        
        # Initialize document storage
        self.documents = {}
        self.current_document_id = None
        
        # Required connections for full functionality
        self.required_connections = ["file_system"]  # Optional but recommended
        
        # Extract any settings from parameters
        self.settings = parameters.get("configuration", {}).get("settings", {})
        
        # Default settings
        self.settings.setdefault("max_document_size_kb", 1024)  # 1MB limit by default
        self.settings.setdefault("auto_save_interval_sec", 60)  # 60 seconds
        self.settings.setdefault("max_documents", 10)  # Maximum number of open documents
        
        # Setup auto-save if enabled
        if self.settings.get("auto_save_enabled", False):
            self._setup_auto_save()
        
        logger.info(f"Text editor cell initialized with ID: {self.cell_id}")
        
        return self.get_initialization_result()
    
    def get_initialization_result(self):
        """Get the initialization result with capabilities and requirements."""
        return {
            "status": "success",
            "cell_id": self.cell_id,
            "capabilities": [
                {
                    "name": "text_editor",
                    "version": "1.0.0",
                    "parameters": [],
                    "inputs": [],
                    "outputs": [
                        {
                            "name": "html",
                            "type": "string",
                            "format": "html"
                        }
                    ]
                },
                {
                    "name": "create_document",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "title",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "content",
                            "type": "string",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "document_id",
                            "type": "string"
                        }
                    ]
                },
                {
                    "name": "edit_document",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "document_id",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "content",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "position",
                            "type": "object",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "success",
                            "type": "boolean"
                        },
                        {
                            "name": "document",
                            "type": "object"
                        }
                    ]
                },
                {
                    "name": "save_document",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "document_id",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "path",
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
                            "name": "path",
                            "type": "string"
                        }
                    ]
                },
                {
                    "name": "load_document",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "path",
                            "type": "string",
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "name": "document_id",
                            "type": "string"
                        },
                        {
                            "name": "document",
                            "type": "object"
                        }
                    ]
                },
                {
                    "name": "text_operations",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "operation",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "document_id",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "params",
                            "type": "object",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "success",
                            "type": "boolean"
                        },
                        {
                            "name": "result",
                            "type": "any"
                        }
                    ]
                }
            ],
            "required_connections": self.required_connections,
            "resource_usage": {
                "memory_mb": 20,
                "storage_mb": 5
            }
        }
    
    def _setup_auto_save(self):
        """Setup auto-save functionality."""
        interval = self.settings.get("auto_save_interval_sec", 60)
        
        async def auto_save_loop():
            while True:
                await asyncio.sleep(interval)
                if self.current_document_id:
                    try:
                        await self.save_document({
                            "document_id": self.current_document_id
                        })
                        logger.debug(f"Auto-saved document: {self.current_document_id}")
                    except Exception as e:
                        logger.error(f"Auto-save failed: {e}")
        
        # Start auto-save loop in the background
        asyncio.create_task(auto_save_loop())
        logger.info(f"Auto-save configured with interval: {interval} seconds")
    
    async def text_editor_interface(self, parameters=None) -> Dict[str, Any]:
        """
        Generate the text editor user interface.
        
        Args:
            parameters: Optional parameters for UI customization
        
        Returns:
            HTML interface for the text editor
        """
        parameters = parameters or {}
        theme = parameters.get("theme", "light")
        document_id = parameters.get("document_id", self.current_document_id)
        
        # Get document content if a document is specified
        document_content = ""
        document_title = "Untitled"
        
        if document_id and document_id in self.documents:
            document = self.documents[document_id]
            document_content = document.get("content", "")
            document_title = document.get("title", "Untitled")
        
        # Generate HTML for the editor interface
        html = f"""
        <div class="text-editor {theme}-theme">
            <div class="editor-header">
                <div class="title-bar">
                    <input type="text" id="document-title" value="{document_title}" placeholder="Untitled">
                </div>
                <div class="toolbar">
                    <button onclick="createDocument()">New</button>
                    <button onclick="saveDocument()">Save</button>
                    <button onclick="loadDocument()">Open</button>
                    <span class="separator">|</span>
                    <button onclick="formatText('bold')"><b>B</b></button>
                    <button onclick="formatText('italic')"><i>I</i></button>
                    <button onclick="formatText('underline')"><u>U</u></button>
                    <span class="separator">|</span>
                    <button onclick="searchText()">Search</button>
                    <button onclick="replaceText()">Replace</button>
                </div>
            </div>
            <div class="editor-body">
                <textarea id="editor-content" placeholder="Start typing...">{document_content}</textarea>
            </div>
            <div class="editor-footer">
                <span id="status">Ready</span>
                <span id="word-count">Words: 0</span>
            </div>
        </div>
        
        <style>
            .text-editor {{
                display: flex;
                flex-direction: column;
                width: 100%;
                height: 500px;
                border: 1px solid #ccc;
                border-radius: 5px;
                overflow: hidden;
            }}
            
            .editor-header {{
                background-color: #f5f5f5;
                padding: 10px;
                border-bottom: 1px solid #ccc;
            }}
            
            .title-bar {{
                margin-bottom: 10px;
            }}
            
            #document-title {{
                width: 100%;
                padding: 5px;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 3px;
            }}
            
            .toolbar {{
                display: flex;
                gap: 5px;
                align-items: center;
            }}
            
            .toolbar button {{
                padding: 5px 10px;
                background-color: #fff;
                border: 1px solid #ccc;
                border-radius: 3px;
                cursor: pointer;
            }}
            
            .toolbar button:hover {{
                background-color: #eee;
            }}
            
            .separator {{
                color: #ccc;
                margin: 0 5px;
            }}
            
            .editor-body {{
                flex-grow: 1;
                position: relative;
            }}
            
            #editor-content {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                padding: 10px;
                font-size: 14px;
                line-height: 1.5;
                border: none;
                resize: none;
                outline: none;
            }}
            
            .editor-footer {{
                background-color: #f5f5f5;
                padding: 5px 10px;
                border-top: 1px solid #ccc;
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #666;
            }}
            
            /* Dark theme */
            .dark-theme {{
                background-color: #2d2d2d;
                color: #f0f0f0;
                border-color: #555;
            }}
            
            .dark-theme .editor-header,
            .dark-theme .editor-footer {{
                background-color: #383838;
                border-color: #555;
            }}
            
            .dark-theme #document-title,
            .dark-theme #editor-content {{
                background-color: #2d2d2d;
                color: #f0f0f0;
                border-color: #555;
            }}
            
            .dark-theme .toolbar button {{
                background-color: #444;
                color: #f0f0f0;
                border-color: #666;
            }}
            
            .dark-theme .toolbar button:hover {{
                background-color: #555;
            }}
        </style>
        
        <script>
            // Initialize editor
            const editor = document.getElementById('editor-content');
            const titleInput = document.getElementById('document-title');
            const statusElement = document.getElementById('status');
            const wordCountElement = document.getElementById('word-count');
            
            let currentDocumentId = "{document_id or ''}";
            
            // Update word count
            function updateWordCount() {{
                const text = editor.value;
                const words = text.trim() ? text.trim().split(/\\s+/).length : 0;
                wordCountElement.textContent = `Words: ${{words}}`;
            }}
            
            // Initialize word count
            updateWordCount();
            
            // Add event listeners
            editor.addEventListener('input', () => {{
                updateWordCount();
                updateStatus('Editing...');
            }});
            
            titleInput.addEventListener('input', () => {{
                updateStatus('Title changed');
            }});
            
            editor.addEventListener('keydown', (e) => {{
                // Save on Ctrl+S
                if (e.ctrlKey && e.key === 's') {{
                    e.preventDefault();
                    saveDocument();
                }}
            }});
            
            // Editor functions
            function updateStatus(message) {{
                statusElement.textContent = message;
                // Clear status after 3 seconds
                setTimeout(() => {{
                    if (statusElement.textContent === message) {{
                        statusElement.textContent = 'Ready';
                    }}
                }}, 3000);
            }}
            
            async function createDocument() {{
                const title = titleInput.value || 'Untitled';
                
                try {{
                    const response = await fetch(`/api/cells/{self.cell_id}/capabilities/create_document`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            title: title,
                            content: ''
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        currentDocumentId = result.outputs.find(o => o.name === 'document_id').value;
                        editor.value = '';
                        updateWordCount();
                        updateStatus('New document created');
                    }}
                }} catch (error) {{
                    updateStatus(`Error: ${{error.message}}`);
                }}
            }}
            
            async function saveDocument() {{
                if (!currentDocumentId) {{
                    await createDocument();
                }}
                
                try {{
                    // First update the document content
                    const editResponse = await fetch(`/api/cells/{self.cell_id}/capabilities/edit_document`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            document_id: currentDocumentId,
                            content: editor.value,
                            title: titleInput.value
                        }})
                    }});
                    
                    const editResult = await editResponse.json();
                    
                    if (editResult.status === 'success') {{
                        // Then save to file system
                        const saveResponse = await fetch(`/api/cells/{self.cell_id}/capabilities/save_document`, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                document_id: currentDocumentId
                            }})
                        }});
                        
                        const saveResult = await saveResponse.json();
                        
                        if (saveResult.status === 'success') {{
                            updateStatus('Document saved');
                        }} else {{
                            updateStatus(`Save error: ${{saveResult.error}}`);
                        }}
                    }}
                }} catch (error) {{
                    updateStatus(`Error: ${{error.message}}`);
                }}
            }}
            
            async function loadDocument() {{
                const path = prompt('Enter document path to load:');
                
                if (!path) return;
                
                try {{
                    const response = await fetch(`/api/cells/{self.cell_id}/capabilities/load_document`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            path: path
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        const documentOutput = result.outputs.find(o => o.name === 'document').value;
                        const documentIdOutput = result.outputs.find(o => o.name === 'document_id').value;
                        
                        currentDocumentId = documentIdOutput;
                        editor.value = documentOutput.content;
                        titleInput.value = documentOutput.title;
                        
                        updateWordCount();
                        updateStatus('Document loaded');
                    }} else {{
                        updateStatus(`Load error: ${{result.error}}`);
                    }}
                }} catch (error) {{
                    updateStatus(`Error: ${{error.message}}`);
                }}
            }}
            
            function formatText(format) {{
                const start = editor.selectionStart;
                const end = editor.selectionEnd;
                const selectedText = editor.value.substring(start, end);
                let formattedText = '';
                
                switch (format) {{
                    case 'bold':
                        formattedText = `**${{selectedText}}**`;
                        break;
                    case 'italic':
                        formattedText = `*${{selectedText}}*`;
                        break;
                    case 'underline':
                        formattedText = `_${{selectedText}}_`;
                        break;
                }}
                
                if (start !== end) {{
                    editor.value = editor.value.substring(0, start) + formattedText + editor.value.substring(end);
                    editor.setSelectionRange(start + 2, end + 2);
                    editor.focus();
                    updateStatus(`Text formatted: ${{format}}`);
                }}
            }}
            
            function searchText() {{
                const searchTerm = prompt('Enter search term:');
                
                if (!searchTerm) return;
                
                const text = editor.value;
                const position = text.indexOf(searchTerm);
                
                if (position !== -1) {{
                    editor.focus();
                    editor.setSelectionRange(position, position + searchTerm.length);
                    updateStatus(`Found: "${{searchTerm}}"`);
                }} else {{
                    updateStatus(`Not found: "${{searchTerm}}"`);
                }}
            }}
            
            function replaceText() {{
                const searchTerm = prompt('Enter search term:');
                if (!searchTerm) return;
                
                const replaceTerm = prompt('Enter replacement:');
                if (replaceTerm === null) return;
                
                const text = editor.value;
                const newText = text.replace(new RegExp(searchTerm, 'g'), replaceTerm);
                
                if (text !== newText) {{
                    editor.value = newText;
                    updateWordCount();
                    updateStatus(`Replaced: "${{searchTerm}}" with "${{replaceTerm}}"`);
                }} else {{
                    updateStatus(`Not found: "${{searchTerm}}"`);
                }}
            }}
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
    
    async def create_document(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.
        
        Args:
            parameters: Document creation parameters
                - title: Document title
                - content: Initial document content (optional)
        
        Returns:
            Document ID of the created document
        """
        if "title" not in parameters:
            return self._error_response("Title parameter is required")
        
        title = parameters["title"]
        content = parameters.get("content", "")
        
        # Check if we're at the document limit
        if len(self.documents) >= self.settings.get("max_documents", 10):
            # Find least recently accessed document to remove
            oldest_doc_id = min(
                self.documents.keys(),
                key=lambda doc_id: self.documents[doc_id].get("last_accessed", 0)
            )
            del self.documents[oldest_doc_id]
            logger.info(f"Document limit reached, removed oldest document: {oldest_doc_id}")
        
        # Create a new document with a unique ID
        document_id = f"doc_{int(time.time())}_{len(self.documents)}"
        
        # Store the document
        self.documents[document_id] = {
            "title": title,
            "content": content,
            "created_at": time.time(),
            "modified_at": time.time(),
            "last_accessed": time.time(),
            "metadata": {
                "word_count": len(content.split()) if content else 0,
                "character_count": len(content)
            }
        }
        
        # Set as current document
        self.current_document_id = document_id
        
        logger.info(f"Created new document: {title} ({document_id})")
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "document_id",
                    "value": document_id,
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 1,
                "memory_used_mb": 0.1
            }
        }
    
    async def edit_document(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit an existing document.
        
        Args:
            parameters: Edit parameters
                - document_id: ID of the document to edit
                - content: New content
                - title: New title (optional)
                - position: Position information for partial edits (optional)
        
        Returns:
            Success indicator and updated document
        """
        if "document_id" not in parameters:
            return self._error_response("Document ID parameter is required")
        
        document_id = parameters["document_id"]
        
        # Check if the document exists
        if document_id not in self.documents:
            return self._error_response(f"Document not found: {document_id}")
        
        document = self.documents[document_id]
        
        # Update content if provided
        if "content" in parameters:
            # Check content size limits
            content = parameters["content"]
            content_size_kb = len(content.encode('utf-8')) / 1024
            max_size_kb = self.settings.get("max_document_size_kb", 1024)
            
            if content_size_kb > max_size_kb:
                return self._error_response(f"Document size exceeds limit: {content_size_kb}KB > {max_size_kb}KB")
            
            # Update the content
            document["content"] = content
            
            # Update metadata
            document["metadata"]["word_count"] = len(content.split()) if content else 0
            document["metadata"]["character_count"] = len(content)
        
        # Update title if provided
        if "title" in parameters:
            document["title"] = parameters["title"]
        
        # Update timestamps
        document["modified_at"] = time.time()
        document["last_accessed"] = time.time()
        
        # Set as current document
        self.current_document_id = document_id
        
        logger.debug(f"Updated document: {document_id}")
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "success",
                    "value": True,
                    "type": "boolean"
                },
                {
                    "name": "document",
                    "value": document,
                    "type": "object"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 2,
                "memory_used_mb": 0.2
            }
        }
    
    async def save_document(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save document to the file system.
        
        Args:
            parameters: Save parameters
                - document_id: ID of the document to save
                - path: File path (optional, will use document title if not provided)
        
        Returns:
            Success indicator and the path where the document was saved
        """
        if "document_id" not in parameters:
            return self._error_response("Document ID parameter is required")
        
        document_id = parameters["document_id"]
        
        # Check if the document exists
        if document_id not in self.documents:
            return self._error_response(f"Document not found: {document_id}")
        
        document = self.documents[document_id]
        
        # Determine path to save
        path = parameters.get("path")
        if not path:
            # Use document title as filename
            title = document["title"]
            # Replace invalid filename characters
            safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
            safe_title = safe_title.replace(" ", "_")
            if not safe_title:
                safe_title = "untitled"
            path = f"{safe_title}.txt"
        
        # Check for file_system connections
        file_system_cell = self._get_connected_cell_by_capability("file_system")
        
        if file_system_cell:
            try:
                logger.info(f"Saving document to file system: {path}")
                
                # Call the file_system cell's write_file capability
                result = await self.call_capability(
                    cell_id=file_system_cell,
                    capability="write_file",
                    parameters={
                        "path": path,
                        "content": document["content"],
                        "metadata": {
                            "title": document["title"],
                            "modified_at": document["modified_at"],
                            "content_type": "text/plain"
                        }
                    }
                )
                
                if result["status"] != "success":
                    return self._error_response(f"Failed to save document: {result.get('error', 'Unknown error')}")
                
                # Update document with the path
                document["path"] = path
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "path",
                            "value": path,
                            "type": "string"
                        }
                    ],
                    "performance_metrics": {
                        "execution_time_ms": 15,
                        "memory_used_mb": 0.3
                    }
                }
                
            except Exception as e:
                logger.error(f"Error saving document: {e}")
                return self._error_response(f"Error saving document: {str(e)}")
        else:
            # No file_system cell connected, save in memory only
            logger.warning("No file_system cell connected, document saved in memory only")
            document["path"] = path
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "path",
                        "value": path,
                        "type": "string"
                    },
                    {
                        "name": "warning",
                        "value": "Document saved in memory only. Connect a file_system cell for persistence.",
                        "type": "string"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 2,
                    "memory_used_mb": 0.1
                }
            }
    
    async def load_document(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load document from the file system.
        
        Args:
            parameters: Load parameters
                - path: Path to the document file
        
        Returns:
            Document ID and the loaded document
        """
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        path = parameters["path"]
        
        # Check for file_system connections
        file_system_cell = self._get_connected_cell_by_capability("file_system")
        
        if file_system_cell:
            try:
                logger.info(f"Loading document from file system: {path}")
                
                # Call the file_system cell's read_file capability
                result = await self.call_capability(
                    cell_id=file_system_cell,
                    capability="read_file",
                    parameters={
                        "path": path
                    }
                )
                
                if result["status"] != "success":
                    return self._error_response(f"Failed to load document: {result.get('error', 'Unknown error')}")
                
                # Extract content and metadata
                content_output = next((o for o in result["outputs"] if o["name"] == "content"), None)
                metadata_output = next((o for o in result["outputs"] if o["name"] == "metadata"), None)
                
                if not content_output:
                    return self._error_response("Failed to get content from file")
                
                content = content_output["value"]
                metadata = metadata_output["value"] if metadata_output else {}
                
                # Determine document title from filename or metadata
                title = metadata.get("title") if metadata else None
                if not title:
                    # Extract from path
                    title = path.split("/")[-1]
                    # Remove extension
                    if "." in title:
                        title = title.rsplit(".", 1)[0]
                    # Replace underscores with spaces
                    title = title.replace("_", " ").title()
                
                # Create a new document
                document_id = f"doc_{int(time.time())}_{len(self.documents)}"
                
                self.documents[document_id] = {
                    "title": title,
                    "content": content,
                    "path": path,
                    "created_at": metadata.get("created_at", time.time()),
                    "modified_at": metadata.get("modified_at", time.time()),
                    "last_accessed": time.time(),
                    "metadata": {
                        "word_count": len(content.split()) if content else 0,
                        "character_count": len(content),
                        "source": "file_system"
                    }
                }
                
                # Set as current document
                self.current_document_id = document_id
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "document_id",
                            "value": document_id,
                            "type": "string"
                        },
                        {
                            "name": "document",
                            "value": self.documents[document_id],
                            "type": "object"
                        }
                    ],
                    "performance_metrics": {
                        "execution_time_ms": 20,
                        "memory_used_mb": 0.5
                    }
                }
                
            except Exception as e:
                logger.error(f"Error loading document: {e}")
                return self._error_response(f"Error loading document: {str(e)}")
        else:
            return self._error_response("No file_system cell connected, cannot load document")
    
    async def text_operations(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform text operations on a document.
        
        Args:
            parameters: Operation parameters
                - operation: Operation type (search, replace, count, etc.)
                - document_id: ID of the document to operate on
                - params: Operation-specific parameters
        
        Returns:
            Success indicator and operation result
        """
        if "operation" not in parameters:
            return self._error_response("Operation parameter is required")
        
        if "document_id" not in parameters:
            return self._error_response("Document ID parameter is required")
        
        operation = parameters["operation"]
        document_id = parameters["document_id"]
        params = parameters.get("params", {})
        
        # Check if the document exists
        if document_id not in self.documents:
            return self._error_response(f"Document not found: {document_id}")
        
        document = self.documents[document_id]
        content = document["content"]
        
        # Update access time
        document["last_accessed"] = time.time()
        
        # Perform the requested operation
        result = None
        
        try:
            if operation == "search":
                # Search for text in the document
                if "query" not in params:
                    return self._error_response("Query parameter is required for search operation")
                
                query = params["query"]
                case_sensitive = params.get("case_sensitive", False)
                
                if not case_sensitive:
                    index = content.lower().find(query.lower())
                    matches = content.lower().count(query.lower())
                else:
                    index = content.find(query)
                    matches = content.count(query)
                
                result = {
                    "found": index != -1,
                    "position": index if index != -1 else -1,
                    "matches": matches
                }
                
            elif operation == "replace":
                # Replace text in the document
                if "search" not in params or "replace" not in params:
                    return self._error_response("Search and replace parameters are required for replace operation")
                
                search_text = params["search"]
                replace_text = params["replace"]
                case_sensitive = params.get("case_sensitive", False)
                replace_all = params.get("replace_all", True)
                
                if not case_sensitive:
                    if replace_all:
                        # Case-insensitive global replacement is tricky, need regex
                        import re
                        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                        new_content, count = re.subn(pattern, replace_text, content)
                    else:
                        # Replace first occurrence
                        index = content.lower().find(search_text.lower())
                        if index != -1:
                            # Get the actual case as it appears in the document
                            actual_text = content[index:index + len(search_text)]
                            new_content = content.replace(actual_text, replace_text, 1)
                            count = 1
                        else:
                            new_content = content
                            count = 0
                else:
                    if replace_all:
                        new_content = content.replace(search_text, replace_text)
                        count = (len(content) - len(new_content)) // (len(search_text) - len(replace_text)) if len(search_text) != len(replace_text) else content.count(search_text)
                    else:
                        # Replace first occurrence
                        new_content = content.replace(search_text, replace_text, 1)
                        count = 1 if new_content != content else 0
                
                # Update the document
                document["content"] = new_content
                document["modified_at"] = time.time()
                document["metadata"]["word_count"] = len(new_content.split()) if new_content else 0
                document["metadata"]["character_count"] = len(new_content)
                
                result = {
                    "replaced": count > 0,
                    "count": count
                }
                
            elif operation == "count":
                # Count words, characters, lines, etc.
                words = len(content.split()) if content else 0
                chars = len(content)
                chars_no_spaces = len(content.replace(" ", ""))
                lines = content.count("\n") + 1 if content else 0
                
                result = {
                    "words": words,
                    "characters": chars,
                    "characters_no_spaces": chars_no_spaces,
                    "lines": lines
                }
                
            elif operation == "format":
                # Format selected text (bold, italic, etc.)
                if "selection" not in params or "format_type" not in params:
                    return self._error_response("Selection and format_type parameters are required for format operation")
                
                selection = params["selection"]
                format_type = params["format_type"]
                
                if "start" not in selection or "end" not in selection:
                    return self._error_response("Selection must include start and end positions")
                
                start = selection["start"]
                end = selection["end"]
                
                if start < 0 or end > len(content) or start >= end:
                    return self._error_response("Invalid selection range")
                
                selected_text = content[start:end]
                
                if format_type == "bold":
                    formatted_text = f"**{selected_text}**"
                elif format_type == "italic":
                    formatted_text = f"*{selected_text}*"
                elif format_type == "underline":
                    formatted_text = f"_{selected_text}_"
                elif format_type == "code":
                    formatted_text = f"`{selected_text}`"
                else:
                    return self._error_response(f"Unsupported format type: {format_type}")
                
                # Replace the selected text with formatted text
                new_content = content[:start] + formatted_text + content[end:]
                
                # Update the document
                document["content"] = new_content
                document["modified_at"] = time.time()
                
                result = {
                    "formatted": True,
                    "new_position": start + len(formatted_text)
                }
                
            else:
                return self._error_response(f"Unsupported operation: {operation}")
                
        except Exception as e:
            logger.error(f"Error performing {operation} operation: {e}")
            return self._error_response(f"Error performing {operation} operation: {str(e)}")
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "success",
                    "value": True,
                    "type": "boolean"
                },
                {
                    "name": "result",
                    "value": result,
                    "type": "object"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 5,
                "memory_used_mb": 0.2
            }
        }
    
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
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "content" if capability == "read_file" else "success",
                        "value": "This is a sample document content." if capability == "read_file" else True,
                        "type": "string" if capability == "read_file" else "boolean"
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
        logger.error(f"Error in text editor cell: {message}")
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
            # Save any unsaved documents
            for doc_id, document in self.documents.items():
                if document.get("modified_at", 0) > document.get("saved_at", 0):
                    # Document has unsaved changes
                    if "path" in document:
                        # Try to save the document
                        try:
                            await self.save_document({
                                "document_id": doc_id,
                                "path": document["path"]
                            })
                            logger.debug(f"Saved document during suspension: {doc_id}")
                        except Exception as e:
                            logger.error(f"Failed to save document during suspension: {e}")
            
            # Prepare state for suspension
            state = {
                "documents": self.documents,
                "current_document_id": self.current_document_id,
                "settings": self.settings
            }
            
            result = {
                "status": "success",
                "state": "suspended",
                "saved_state": state
            }
            
            logger.info("Text editor cell suspended")
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
                
                if "documents" in saved_state:
                    self.documents = saved_state["documents"]
                
                if "current_document_id" in saved_state:
                    self.current_document_id = saved_state["current_document_id"]
                
                if "settings" in saved_state:
                    self.settings.update(saved_state["settings"])
                
                logger.info("Text editor cell resumed with saved state")
            else:
                logger.warning("Resumed without saved state")
            
            # Setup auto-save if enabled
            if self.settings.get("auto_save_enabled", False):
                self._setup_auto_save()
            
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
            # Save any unsaved documents
            for doc_id, document in self.documents.items():
                if document.get("modified_at", 0) > document.get("saved_at", 0):
                    # Document has unsaved changes
                    if "path" in document:
                        # Try to save the document
                        try:
                            await self.save_document({
                                "document_id": doc_id,
                                "path": document["path"]
                            })
                            logger.debug(f"Saved document during release: {doc_id}")
                        except Exception as e:
                            logger.error(f"Failed to save document during release: {e}")
            
            # Clear cell state
            self.documents = {}
            self.current_document_id = None
            
            logger.info("Text editor cell released")
            
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
