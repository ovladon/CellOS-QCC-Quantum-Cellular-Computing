"""
Simple Text Editor Cell for QCC

This cell provides a basic Text Editor capability that allows users to create,
edit, and save text documents within the QCC environment.
"""

from qcc.cells import BaseCell
from typing import Dict, List, Any, Optional
import os
import time
import json
import logging

logger = logging.getLogger(__name__)

class SimpleEditorCell(BaseCell):
    """
    A cell that provides basic text editing capabilities.
    
    This cell can:
    - Create new text documents
    - Open existing documents
    - Edit document content
    - Save documents
    - List available documents
    """
    
    def initialize(self, parameters):
        """Initialize the cell with given parameters."""
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("create_document", self.create_document)
        self.register_capability("open_document", self.open_document)
        self.register_capability("edit_document", self.edit_document)
        self.register_capability("save_document", self.save_document)
        self.register_capability("list_documents", self.list_documents)
        self.register_capability("delete_document", self.delete_document)
        self.register_capability("get_editor_ui", self.get_editor_ui)
        
        # Initialize state
        self.state = {
            "current_document": None,
            "documents": {},
            "document_history": {}
        }
        
        # Set up document storage
        if "storage_path" in parameters:
            self.storage_path = parameters["storage_path"]
        else:
            # Default storage location
            self.storage_path = "./data/user_files/text_documents"
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load existing documents
        self._load_existing_documents()
        
        logger.info(f"SimpleEditorCell initialized with ID: {self.cell_id}")
        return self.get_initialization_result()
    
    def _load_existing_documents(self):
        """Load existing documents from storage."""
        try:
            # List all text files in the storage directory
            document_files = [f for f in os.listdir(self.storage_path) 
                             if f.endswith('.txt') or f.endswith('.md')]
            
            # Load basic metadata for each document
            for filename in document_files:
                doc_path = os.path.join(self.storage_path, filename)
                doc_stats = os.stat(doc_path)
                
                # Add to documents dictionary
                doc_id = filename
                self.state["documents"][doc_id] = {
                    "id": doc_id,
                    "name": filename,
                    "size_bytes": doc_stats.st_size,
                    "created_at": doc_stats.st_ctime,
                    "modified_at": doc_stats.st_mtime,
                    "path": doc_path,
                    # Content is loaded on demand when opening a document
                    "content": None
                }
            
            logger.info(f"Loaded {len(document_files)} existing documents")
        
        except Exception as e:
            logger.error(f"Error loading existing documents: {e}")
    
    async def create_document(self, parameters):
        """
        Create a new text document.
        
        Parameters:
            name (str): Name of the document
            content (str, optional): Initial content
            
        Returns:
            Document metadata
        """
        try:
            if "name" not in parameters:
                return self._error_response("Document name is required")
            
            document_name = parameters["name"]
            
            # Add extension if not present
            if not (document_name.endswith('.txt') or document_name.endswith('.md')):
                document_name += '.txt'
            
            # Check if document already exists
            doc_path = os.path.join(self.storage_path, document_name)
            if os.path.exists(doc_path):
                return self._error_response(f"Document '{document_name}' already exists")
            
            # Create document with initial content
            initial_content = parameters.get("content", "")
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(initial_content)
            
            # Create document metadata
            doc_stats = os.stat(doc_path)
            doc_id = document_name
            
            document = {
                "id": doc_id,
                "name": document_name,
                "size_bytes": doc_stats.st_size,
                "created_at": doc_stats.st_ctime,
                "modified_at": doc_stats.st_mtime,
                "path": doc_path,
                "content": initial_content
            }
            
            # Store in state
            self.state["documents"][doc_id] = document
            self.state["current_document"] = doc_id
            
            # Initialize history for this document
            self.state["document_history"][doc_id] = [{
                "timestamp": time.time(),
                "content": initial_content,
                "operation": "create"
            }]
            
            logger.info(f"Created new document: {document_name}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "document",
                        "value": {
                            "id": doc_id,
                            "name": document_name,
                            "size_bytes": doc_stats.st_size,
                            "created_at": doc_stats.st_ctime,
                            "modified_at": doc_stats.st_mtime
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
            logger.error(f"Error creating document: {e}")
            return self._error_response(f"Failed to create document: {str(e)}")
    
    async def open_document(self, parameters):
        """
        Open an existing document.
        
        Parameters:
            id (str): Document ID to open
            
        Returns:
            Document content and metadata
        """
        try:
            if "id" not in parameters:
                return self._error_response("Document ID is required")
            
            doc_id = parameters["id"]
            
            # Check if document exists
            if doc_id not in self.state["documents"]:
                return self._error_response(f"Document '{doc_id}' not found")
            
            document = self.state["documents"][doc_id]
            
            # Load content if not already loaded
            if document["content"] is None:
                doc_path = document["path"]
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                document["content"] = content
            
            # Set as current document
            self.state["current_document"] = doc_id
            
            logger.info(f"Opened document: {doc_id}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "document",
                        "value": {
                            "id": document["id"],
                            "name": document["name"],
                            "content": document["content"],
                            "size_bytes": document["size_bytes"],
                            "created_at": document["created_at"],
                            "modified_at": document["modified_at"]
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error opening document: {e}")
            return self._error_response(f"Failed to open document: {str(e)}")
    
    async def edit_document(self, parameters):
        """
        Edit document content.
        
        Parameters:
            id (str): Document ID to edit
            content (str): New document content
            position (int, optional): Position to insert/delete text
            operation (str, optional): Operation type (replace, insert, delete)
            length (int, optional): Length of text to delete
            
        Returns:
            Updated document content
        """
        try:
            if "id" not in parameters:
                return self._error_response("Document ID is required")
            
            doc_id = parameters["id"]
            
            # Check if document exists
            if doc_id not in self.state["documents"]:
                return self._error_response(f"Document '{doc_id}' not found")
            
            document = self.state["documents"][doc_id]
            
            # Load content if not already loaded
            if document["content"] is None:
                doc_path = document["path"]
                with open(doc_path, 'r', encoding='utf-8') as f:
                    document["content"] = f.read()
            
            # Handle different edit operations
            operation = parameters.get("operation", "replace")
            
            if operation == "replace" and "content" in parameters:
                # Replace entire content
                document["content"] = parameters["content"]
                
            elif operation == "insert" and "content" in parameters and "position" in parameters:
                # Insert at position
                position = parameters["position"]
                insert_text = parameters["content"]
                
                # Ensure position is valid
                if position < 0:
                    position = 0
                if position > len(document["content"]):
                    position = len(document["content"])
                
                # Insert text
                document["content"] = (
                    document["content"][:position] + 
                    insert_text + 
                    document["content"][position:]
                )
                
            elif operation == "delete" and "position" in parameters and "length" in parameters:
                # Delete text at position
                position = parameters["position"]
                length = parameters["length"]
                
                # Ensure position and length are valid
                if position < 0:
                    position = 0
                if position > len(document["content"]):
                    position = len(document["content"])
                if position + length > len(document["content"]):
                    length = len(document["content"]) - position
                
                # Delete text
                document["content"] = (
                    document["content"][:position] + 
                    document["content"][position + length:]
                )
                
            else:
                return self._error_response(
                    "Invalid edit operation. Must provide operation and required parameters."
                )
            
            # Set as current document
            self.state["current_document"] = doc_id
            
            # Add to document history
            if doc_id not in self.state["document_history"]:
                self.state["document_history"][doc_id] = []
                
            self.state["document_history"][doc_id].append({
                "timestamp": time.time(),
                "content": document["content"],
                "operation": operation
            })
            
            # Limit history length
            max_history = 20
            if len(self.state["document_history"][doc_id]) > max_history:
                self.state["document_history"][doc_id] = self.state["document_history"][doc_id][-max_history:]
            
            logger.info(f"Edited document: {doc_id} (operation: {operation})")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "document",
                        "value": {
                            "id": document["id"],
                            "name": document["name"],
                            "content": document["content"]
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 12,
                    "memory_used_mb": 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error editing document: {e}")
            return self._error_response(f"Failed to edit document: {str(e)}")
    
    async def save_document(self, parameters):
        """
        Save document content to storage.
        
        Parameters:
            id (str): Document ID to save
            
        Returns:
            Save status and updated metadata
        """
        try:
            if "id" not in parameters:
                return self._error_response("Document ID is required")
            
            doc_id = parameters["id"]
            
            # Check if document exists
            if doc_id not in self.state["documents"]:
                return self._error_response(f"Document '{doc_id}' not found")
            
            document = self.state["documents"][doc_id]
            
            # Check if content is loaded
            if document["content"] is None:
                return self._error_response(f"Document '{doc_id}' not loaded for editing")
            
            # Save to file
            doc_path = document["path"]
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(document["content"])
            
            # Update metadata
            doc_stats = os.stat(doc_path)
            document["size_bytes"] = doc_stats.st_size
            document["modified_at"] = doc_stats.st_mtime
            
            logger.info(f"Saved document: {doc_id}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "document",
                        "value": {
                            "id": document["id"],
                            "name": document["name"],
                            "size_bytes": document["size_bytes"],
                            "created_at": document["created_at"],
                            "modified_at": document["modified_at"]
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 20,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return self._error_response(f"Failed to save document: {str(e)}")
    
    async def list_documents(self, parameters=None):
        """
        List all available documents.
        
        Parameters:
            filter (str, optional): Filter documents by name
            sort (str, optional): Sort by field (name, created_at, modified_at)
            order (str, optional): Sort order (asc, desc)
            
        Returns:
            List of document metadata
        """
        try:
            # Get all documents
            documents = list(self.state["documents"].values())
            
            # Apply filter if provided
            if parameters and "filter" in parameters:
                filter_text = parameters["filter"].lower()
                documents = [
                    doc for doc in documents 
                    if filter_text in doc["name"].lower()
                ]
            
            # Apply sorting if provided
            if parameters and "sort" in parameters:
                sort_field = parameters["sort"]
                if sort_field in ["name", "created_at", "modified_at", "size_bytes"]:
                    reverse = False
                    if parameters.get("order", "asc").lower() == "desc":
                        reverse = True
                    
                    documents = sorted(
                        documents, 
                        key=lambda x: x[sort_field], 
                        reverse=reverse
                    )
            
            # Prepare document list without content
            document_list = []
            for doc in documents:
                document_list.append({
                    "id": doc["id"],
                    "name": doc["name"],
                    "size_bytes": doc["size_bytes"],
                    "created_at": doc["created_at"],
                    "modified_at": doc["modified_at"]
                })
            
            logger.info(f"Listed {len(document_list)} documents")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "documents",
                        "value": document_list,
                        "type": "array"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 8,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return self._error_response(f"Failed to list documents: {str(e)}")
    
    async def delete_document(self, parameters):
        """
        Delete a document.
        
        Parameters:
            id (str): Document ID to delete
            
        Returns:
            Delete status
        """
        try:
            if "id" not in parameters:
                return self._error_response("Document ID is required")
            
            doc_id = parameters["id"]
            
            # Check if document exists
            if doc_id not in self.state["documents"]:
                return self._error_response(f"Document '{doc_id}' not found")
            
            document = self.state["documents"][doc_id]
            
            # Delete file
            doc_path = document["path"]
            if os.path.exists(doc_path):
                os.remove(doc_path)
            
            # Remove from state
            del self.state["documents"][doc_id]
            
            # Clean up history
            if doc_id in self.state["document_history"]:
                del self.state["document_history"][doc_id]
            
            # Reset current document if it was the deleted one
            if self.state["current_document"] == doc_id:
                self.state["current_document"] = None
            
            logger.info(f"Deleted document: {doc_id}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "result",
                        "value": {
                            "id": doc_id,
                            "deleted": True
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return self._error_response(f"Failed to delete document: {str(e)}")
    
    async def get_editor_ui(self, parameters=None):
        """
        Get a simple UI for text editing.
        
        Parameters:
            document_id (str, optional): ID of document to load initially
            
        Returns:
            HTML UI for text editing
        """
        # Determine if we should load a document
        document_id = None
        if parameters and "document_id" in parameters:
            document_id = parameters["document_id"]
        elif self.state["current_document"]:
            document_id = self.state["current_document"]
        
        # Get document content if specified
        initial_content = ""
        document_name = ""
        if document_id and document_id in self.state["documents"]:
            doc = self.state["documents"][document_id]
            # Load content if not loaded
            if doc["content"] is None:
                try:
                    with open(doc["path"], 'r', encoding='utf-8') as f:
                        doc["content"] = f.read()
                except Exception as e:
                    logger.error(f"Error loading document content: {e}")
            
            if doc["content"] is not None:
                initial_content = doc["content"]
                document_name = doc["name"]
        
        # Generate HTML for the editor UI
        html = f"""
        <div class="text-editor">
            <div class="editor-toolbar">
                <div class="document-controls">
                    <button id="new-btn" onclick="createNewDocument()">New</button>
                    <button id="open-btn" onclick="openDocumentList()">Open</button>
                    <button id="save-btn" onclick="saveDocument()">Save</button>
                    <span id="document-name">{document_name}</span>
                </div>
                <div class="edit-controls">
                    <button onclick="formatText('bold')">Bold</button>
                    <button onclick="formatText('italic')">Italic</button>
                    <button onclick="formatText('heading')">Heading</button>
                    <button onclick="formatText('list')">List</button>
                </div>
            </div>
            
            <div id="editor-container">
                <textarea id="editor" placeholder="Start typing here...">{initial_content}</textarea>
            </div>
            
            <div id="document-list" class="modal hidden">
                <div class="modal-content">
                    <span class="close" onclick="closeModal()">&times;</span>
                    <h3>Open Document</h3>
                    <div id="document-items"></div>
                </div>
            </div>
            
            <div id="new-document-dialog" class="modal hidden">
                <div class="modal-content">
                    <span class="close" onclick="closeModal()">&times;</span>
                    <h3>Create New Document</h3>
                    <div>
                        <label for="new-doc-name">Document Name:</label>
                        <input type="text" id="new-doc-name" placeholder="Untitled.txt">
                        <button onclick="confirmCreateDocument()">Create</button>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .text-editor {
                display: flex;
                flex-direction: column;
                height: 500px;
                border: 1px solid #ccc;
                border-radius: 4px;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            
            .editor-toolbar {
                display: flex;
                justify-content: space-between;
                padding: 8px;
                background-color: #f5f5f5;
                border-bottom: 1px solid #ccc;
            }
            
            .document-controls, .edit-controls {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            #document-name {
                margin-left: 12px;
                font-weight: 500;
                color: #333;
            }
            
            button {
                padding: 6px 12px;
                background-color: #fff;
                border: 1px solid #ccc;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            
            button:hover {
                background-color: #e9e9e9;
            }
            
            #editor-container {
                flex: 1;
                overflow: hidden;
            }
            
            #editor {
                width: 100%;
                height: 100%;
                padding: 12px;
                font-size: 16px;
                line-height: 1.5;
                border: none;
                resize: none;
                outline: none;
                font-family: monospace;
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
            
            #document-items {
                margin-top: 16px;
                max-height: 300px;
                overflow-y: auto;
            }
            
            .document-item {
                padding: 8px 12px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
            }
            
            .document-item:hover {
                background-color: #f5f5f5;
            }
            
            input[type="text"] {
                margin: 8px 0;
                padding: 8px;
                width: 100%;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        </style>
        
        <script>
            // Current document ID
            let currentDocumentId = {f"'{document_id}'" if document_id else "null"};
            
            // Format text in the editor
            function formatText(type) {
                const editor = document.getElementById('editor');
                const selStart = editor.selectionStart;
                const selEnd = editor.selectionEnd;
                const selectedText = editor.value.substring(selStart, selEnd);
                let newText = '';
                
                switch(type) {
                    case 'bold':
                        newText = '**' + selectedText + '**';
                        break;
                    case 'italic':
                        newText = '*' + selectedText + '*';
                        break;
                    case 'heading':
                        newText = '## ' + selectedText;
                        break;
                    case 'list':
                        // Split text into lines and add list markers
                        newText = selectedText.split('\\n')
                            .map(line => '- ' + line)
                            .join('\\n');
                        break;
                }
                
                // Replace selected text with formatted text
                editor.value = editor.value.substring(0, selStart) + 
                               newText + 
                               editor.value.substring(selEnd);
                               
                // Place cursor after the inserted text
                editor.selectionStart = selStart + newText.length;
                editor.selectionEnd = selStart + newText.length;
                editor.focus();
            }
            
            // Open document list
            async function openDocumentList() {
                // Fetch document list
                const response = await callCapability('list_documents');
                
                if (response.status === 'success') {
                    const documents = response.outputs[0].value;
                    const documentItems = document.getElementById('document-items');
                    documentItems.innerHTML = '';
                    
                    documents.forEach(doc => {
                        const date = new Date(doc.modified_at * 1000).toLocaleString();
                        const item = document.createElement('div');
                        item.className = 'document-item';
                        item.innerHTML = `
                            <span>${doc.name}</span>
                            <span>${date}</span>
                        `;
                        item.onclick = () => openDocument(doc.id);
                        documentItems.appendChild(item);
                    });
                    
                    showModal('document-list');
                }
            }
            
            // Open a document
            async function openDocument(id) {
                closeModal();
                
                const response = await callCapability('open_document', {
                    id: id
                });
                
                if (response.status === 'success') {
                    const doc = response.outputs[0].value;
                    document.getElementById('editor').value = doc.content;
                    document.getElementById('document-name').textContent = doc.name;
                    currentDocumentId = doc.id;
                }
            }
            
            // Save current document
            async function saveDocument() {
                if (!currentDocumentId) {
                    showModal('new-document-dialog');
                    return;
                }
                
                // First update the content
                await callCapability('edit_document', {
                    id: currentDocumentId,
                    content: document.getElementById('editor').value
                });
                
                // Then save to storage
                await callCapability('save_document', {
                    id: currentDocumentId
                });
                
                // Show save feedback
                const saveBtn = document.getElementById('save-btn');
                const originalText = saveBtn.textContent;
                saveBtn.textContent = 'Saved!';
                setTimeout(() => {
                    saveBtn.textContent = originalText;
                }, 2000);
            }
            
            // Show dialog to create a new document
            function createNewDocument() {
                showModal('new-document-dialog');
            }
            
            // Confirm creation of new document
            async function confirmCreateDocument() {
                const name = document.getElementById('new-doc-name').value || 'Untitled.txt';
                const content = document.getElementById('editor').value;
                
                closeModal();
                
                const response = await callCapability('create_document', {
                    name: name,
                    content: content
                });
                
                if (response.status === 'success') {
                    const doc = response.outputs[0].value;
                    document.getElementById('document-name').textContent = doc.name;
                    currentDocumentId = doc.id;
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
    
    def _error_response(self, message):
        """Create an error response with the given message."""
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
        # Save any unsaved documents
        for doc_id, document in self.state["documents"].items():
            if document["content"] is not None:
                # Write to file
                try:
                    with open(document["path"], 'w', encoding='utf-8') as f:
                        f.write(document["content"])
                except Exception as e:
                    logger.error(f"Error saving document during suspension: {e}")
        
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
                # Selectively update state components
                saved_state = parameters["saved_state"]
                if "current_document" in saved_state:
                    self.state["current_document"] = saved_state["current_document"]
                if "documents" in saved_state:
                    # Update only metadata, content will be loaded when needed
                    for doc_id, doc in saved_state["documents"].items():
                        if doc_id in self.state["documents"]:
                            # Update existing document metadata
                            self.state["documents"][doc_id].update({
                                key: value for key, value in doc.items() 
                                if key != "content"  # Don't overwrite content
                            })
                        else:
                            # Add new document with content set to None
                            new_doc = dict(doc)
                            new_doc["content"] = None
                            self.state["documents"][doc_id] = new_doc
                if "document_history" in saved_state:
                    self.state["document_history"] = saved_state["document_history"]
                
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
        # Save any unsaved documents
        for doc_id, document in self.state["documents"].items():
            if document["content"] is not None:
                # Write to file
                try:
                    with open(document["path"], 'w', encoding='utf-8') as f:
                        f.write(document["content"])
                except Exception as e:
                    logger.error(f"Error saving document during release: {e}")
        
        # Clear memory
        self.state["documents"] = {}
        self.state["document_history"] = {}
        self.state["current_document"] = None
        
        return {
            "status": "success"
        }
    
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


# Create an EditorManifest to describe this cell
EditorManifest = {
    "name": "simple_editor",
    "version": "1.0.0",
    "description": "A simple text editor cell for QCC",
    "author": "QCC Team",
    "license": "MIT",
    "capabilities": [
        {
            "name": "create_document",
            "description": "Create a new text document",
            "parameters": [
                {
                    "name": "name",
                    "type": "string",
                    "description": "Name of the document",
                    "required": True
                },
                {
                    "name": "content",
                    "type": "string",
                    "description": "Initial content",
                    "required": False
                }
            ]
        },
        {
            "name": "open_document",
            "description": "Open an existing document",
            "parameters": [
                {
                    "name": "id",
                    "type": "string",
                    "description": "Document ID to open",
                    "required": True
                }
            ]
        },
        {
            "name": "edit_document",
            "description": "Edit document content",
            "parameters": [
                {
                    "name": "id",
                    "type": "string",
                    "description": "Document ID to edit",
                    "required": True
                },
                {
                    "name": "content",
                    "type": "string",
                    "description": "New document content",
                    "required": False
                },
                {
                    "name": "operation",
                    "type": "string",
                    "description": "Operation type (replace, insert, delete)",
                    "required": False
                },
                {
                    "name": "position",
                    "type": "number",
                    "description": "Position to insert/delete text",
                    "required": False
                },
                {
                    "name": "length",
                    "type": "number",
                    "description": "Length of text to delete",
                    "required": False
                }
            ]
        },
        {
            "name": "save_document",
            "description": "Save document content to storage",
            "parameters": [
                {
                    "name": "id",
                    "type": "string",
                    "description": "Document ID to save",
                    "required": True
                }
            ]
        },
        {
            "name": "list_documents",
            "description": "List all available documents",
            "parameters": [
                {
                    "name": "filter",
                    "type": "string",
                    "description": "Filter documents by name",
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
            "name": "delete_document",
            "description": "Delete a document",
            "parameters": [
                {
                    "name": "id",
                    "type": "string",
                    "description": "Document ID to delete",
                    "required": True
                }
            ]
        },
        {
            "name": "get_editor_ui",
            "description": "Get a simple UI for text editing",
            "parameters": [
                {
                    "name": "document_id",
                    "type": "string",
                    "description": "ID of document to load initially",
                    "required": False
                }
            ]
        }
    ],
    "dependencies": [],
    "resource_requirements": {
        "memory_mb": 20,
        "cpu_percent": 5,
        "storage_mb": 100
    }
}


# Example usage demonstration
async def example_usage():
    """Demonstrates how to use the SimpleEditorCell."""
    import asyncio
    
    # Create and initialize the cell
    editor_cell = SimpleEditorCell()
    await editor_cell.initialize({
        "cell_id": "demo-editor-cell",
        "quantum_signature": "demo-signature",
        "storage_path": "./example_docs"
    })
    
    # Create a new document
    create_result = await editor_cell.create_document({
        "name": "example.txt",
        "content": "Hello, this is an example document created with SimpleEditorCell."
    })
    print(f"Created document: {create_result}")
    
    # Get document ID from the result
    doc_id = create_result["outputs"][0]["value"]["id"]
    
    # Edit the document
    edit_result = await editor_cell.edit_document({
        "id": doc_id,
        "operation": "insert",
        "position": 7,
        "content": " World!"
    })
    print(f"Edited document: {edit_result}")
    
    # Save the document
    save_result = await editor_cell.save_document({
        "id": doc_id
    })
    print(f"Saved document: {save_result}")
    
    # List documents
    list_result = await editor_cell.list_documents(None)
    print(f"Document list: {list_result}")
    
    # Release the cell
    release_result = await editor_cell.release()
    print(f"Released cell: {release_result}")


# Run the example if this script is executed directly
if __name__ == "__main__":
    import asyncio
    
    # Run the example
    asyncio.run(example_usage())
