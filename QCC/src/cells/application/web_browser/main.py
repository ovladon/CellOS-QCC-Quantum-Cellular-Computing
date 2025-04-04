{
                    "name": "browser_settings",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "action",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "settings",
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
                            "name": "settings",
                            "type": "object"
                        }
                    ]
                }
            ],
            "required_connections": self.required_connections,
            "resource_usage": {
                "memory_mb": 75,
                "storage_mb": 30
            }
        }
    
    async def browser_interface(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate the web browser user interface.
        
        Args:
            parameters: Optional parameters for UI customization
                - url: URL to load initially
                - theme: UI theme (light or dark)
        
        Returns:
            HTML interface for the web browser
        """
        parameters = parameters or {}
        theme = parameters.get("theme", "light")
        
        # If URL is provided, navigate to it
        if "url" in parameters:
            url = parameters["url"]
            await self.navigate({
                "url": url,
                "tab_id": self.active_tab_id
            })
        
        # Get the current active tab
        active_tab = self.tabs.get(self.active_tab_id, {})
        
        # Get URL for address bar
        current_url = active_tab.get("url", self.settings["default_home_page"])
        
        # Get page title
        page_title = active_tab.get("title", "New Tab")
        
        # Get page content
        page_content = active_tab.get("content", "")
        page_loading = active_tab.get("loading", False)
        
        # Generate tabs HTML
        tabs_html = ""
        for tab_id, tab in self.tabs.items():
            tab_title = tab.get("title", "New Tab")
            if len(tab_title) > 20:
                tab_title = tab_title[:20] + "..."
            
            tab_url = tab.get("url", "")
            tab_favicon = tab.get("favicon", "")
            
            # Set active class if this is the active tab
            active_class = "active" if tab_id == self.active_tab_id else ""
            
            tabs_html += f"""
            <div class="browser-tab {active_class}" data-tab-id="{tab_id}" onclick="switchTab('{tab_id}')">
                <span class="tab-title">{tab_title}</span>
                <button class="tab-close" onclick="closeTab('{tab_id}', event)">×</button>
            </div>
            """
        
        # Add new tab button
        tabs_html += """
        <div class="browser-tab-new" onclick="newTab()">
            <span>+</span>
        </div>
        """
        
        # Generate bookmarks HTML
        bookmarks_html = ""
        for bookmark in self.bookmarks:
            bookmark_id = bookmark.get("id", "")
            bookmark_title = bookmark.get("title", "Bookmark")
            bookmark_url = bookmark.get("url", "#")
            
            if len(bookmark_title) > 20:
                bookmark_title = bookmark_title[:20] + "..."
            
            bookmarks_html += f"""
            <div class="bookmark-item" title="{bookmark_url}">
                <a href="javascript:void(0)" onclick="navigateTo('{bookmark_url}')">{bookmark_title}</a>
                <button class="bookmark-remove" onclick="removeBookmark('{bookmark_id}', event)">×</button>
            </div>
            """
        
        # Get CSS for the selected theme
        theme_css = self._get_theme_css(theme)
        
        # Generate the full browser HTML
        html = f"""
        <div id="browser-container" class="browser-container {theme}-theme">
            <div class="browser-toolbar">
                <div class="navigation-buttons">
                    <button id="back-button" onclick="navigateBack()" title="Back">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" fill="currentColor"/></svg>
                    </button>
                    <button id="forward-button" onclick="navigateForward()" title="Forward">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z" fill="currentColor"/></svg>
                    </button>
                    <button id="reload-button" onclick="reloadPage()" title="Reload">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 9h7V2l-2.35 4.35z" fill="currentColor"/></svg>
                    </button>
                    <button id="home-button" onclick="navigateHome()" title="Home">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" fill="currentColor"/></svg>
                    </button>
                </div>
                <div class="address-bar">
                    <input type="text" id="url-input" value="{current_url}" placeholder="Enter URL or search term" onkeypress="handleUrlKeyPress(event)">
                    <button id="go-button" onclick="navigateToUrl()" title="Go">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" fill="currentColor"/></svg>
                    </button>
                </div>
                <div class="browser-controls">
                    <button id="bookmark-button" onclick="toggleBookmark()" title="Bookmark">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M17 3H7c-1.1 0-1.99.9-1.99 2L5 21l7-3 7 3V5c0-1.1-.9-2-2-2z" fill="currentColor"/></svg>
                    </button>
                    <button id="history-button" onclick="showHistory()" title="History">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" fill="currentColor"/></svg>
                    </button>
                    <button id="settings-button" onclick="showSettings()" title="Settings">
                        <svg viewBox="0 0 24 24" width="24" height="24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="currentColor"/></svg>
                    </button>
                </div>
            </div>
            
            <div class="browser-tabs-container">
                {tabs_html}
            </div>
            
            <div class="bookmarks-bar" id="bookmarks-bar">
                {bookmarks_html}
            </div>
            
            <div class="browser-content" id="browser-content">
                {f'<div class="loading-indicator" id="loading-indicator">Loading...</div>' if page_loading else ''}
                
                <iframe id="browser-frame" 
                        sandbox="allow-same-origin allow-scripts allow-forms allow-popups" 
                        style="display: {'' if not page_loading else 'none'}"
                        src="about:blank"></iframe>
            </div>
            
            <div class="browser-statusbar">
                <div class="status-text" id="status-text">Ready</div>
                <div class="page-info">
                    <span id="page-security">Secure</span> | 
                    <span id="page-resources">0 resources</span> | 
                    <span id="page-load-time">0 ms</span>
                </div>
            </div>
        </div>
        
        <style>
            /* Base Styles */
            .browser-container {
                display: flex;
                flex-direction: column;
                width: 100%;
                height: 700px;
                border-radius: 8px;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                background-color: #f5f5f5;
            }
            
            /* Theme-specific styles */
            {theme_css}
            
            /* Toolbar Styles */
            .browser-toolbar {
                display: flex;
                align-items: center;
                padding: 8px 16px;
                border-bottom: 1px solid #ddd;
                gap: 16px;
            }
            
            .navigation-buttons {
                display: flex;
                gap: 8px;
            }
            
            .address-bar {
                flex-grow: 1;
                display: flex;
                align-items: center;
                background-color: #fff;
                border-radius: 20px;
                padding: 0 12px;
                border: 1px solid #ddd;
            }
            
            .dark-theme .address-bar {
                background-color: #444;
                border-color: #555;
            }
            
            #url-input {
                flex-grow: 1;
                border: none;
                outline: none;
                padding: 8px 12px;
                font-size: 14px;
                background: transparent;
                color: inherit;
            }
            
            #go-button {
                background: none;
                border: none;
                cursor: pointer;
                color: #5f6368;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 4px;
            }
            
            .dark-theme #go-button {
                color: #aaa;
            }
            
            .browser-controls {
                display: flex;
                gap: 8px;
            }
            
            button {
                background: none;
                border: none;
                cursor: pointer;
                color: #5f6368;
                border-radius: 50%;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.2s;
            }
            
            button:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            .dark-theme button {
                color: #aaa;
            }
            
            .dark-theme button:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            /* Tab Styles */
            .browser-tabs-container {
                display: flex;
                padding: 0 16px;
                border-bottom: 1px solid #ddd;
                background-color: #f5f5f5;
                overflow-x: auto;
                scrollbar-width: thin;
            }
            
            .dark-theme .browser-tabs-container {
                background-color: #333;
                border-color: #444;
            }
            
            .browser-tab {
                padding: 8px 16px;
                border-radius: 8px 8px 0 0;
                background-color: #e0e0e0;
                margin-right: 4px;
                margin-top: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                min-width: 100px;
                max-width: 200px;
                position: relative;
                height: 36px;
                overflow: hidden;
                transition: background-color 0.2s;
            }
            
            .browser-tab.active {
                background-color: #fff;
                border: 1px solid #ddd;
                border-bottom: none;
            }
            
            .dark-theme .browser-tab {
                background-color: #444;
            }
            
            .dark-theme .browser-tab.active {
                background-color: #555;
                border-color: #666;
            }
            
            .tab-title {
                flex-grow: 1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                font-size: 13px;
            }
            
            .tab-close {
                border-radius: 50%;
                width: 16px;
                height: 16px;
                font-size: 14px;
                line-height: 14px;
                text-align: center;
                margin-left: 8px;
                opacity: 0.7;
                transition: opacity 0.2s;
            }
            
            .tab-close:hover {
                opacity: 1;
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            .browser-tab-new {
                padding: 8px 12px;
                margin-top: 4px;
                cursor: pointer;
                border-radius: 8px 8px 0 0;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.2s;
            }
            
            .browser-tab-new:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            .dark-theme .browser-tab-new:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            /* Bookmarks Bar */
            .bookmarks-bar {
                display: flex;
                padding: 4px 16px;
                border-bottom: 1px solid #ddd;
                background-color: #f9f9f9;
                overflow-x: auto;
                scrollbar-width: thin;
            }
            
            .dark-theme .bookmarks-bar {
                background-color: #383838;
                border-color: #444;
            }
            
            .bookmark-item {
                padding: 4px 8px;
                margin-right: 8px;
                border-radius: 4px;
                font-size: 13px;
                white-space: nowrap;
                display: flex;
                align-items: center;
                transition: background-color 0.2s;
            }
            
            .bookmark-item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            .dark-theme .bookmark-item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            .bookmark-item a {
                text-decoration: none;
                color: inherit;
            }
            
            .bookmark-remove {
                border-radius: 50%;
                width: 16px;
                height: 16px;
                font-size: 14px;
                line-height: 14px;
                text-align: center;
                margin-left: 4px;
                opacity: 0;
                transition: opacity 0.2s;
            }
            
            .bookmark-item:hover .bookmark-remove {
                opacity: 0.7;
            }
            
            .bookmark-remove:hover {
                opacity: 1 !important;
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            /* Browser Content */
            .browser-content {
                flex-grow: 1;
                position: relative;
                background-color: #fff;
            }
            
            .dark-theme .browser-content {
                background-color: #333;
            }
            
            #browser-frame {
                width: 100%;
                height: 100%;
                border: none;
            }
            
            .loading-indicator {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                color: #666;
                background-color: #fff;
            }
            
            .dark-theme .loading-indicator {
                color: #ccc;
                background-color: #333;
            }
            
            /* Status Bar */
            .browser-statusbar {
                display: flex;
                justify-content: space-between;
                padding: 4px 16px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
                background-color: #f5f5f5;
            }
            
            .dark-theme .browser-statusbar {
                color: #aaa;
                background-color: #333;
                border-color: #444;
            }
            
            .page-info {
                display: flex;
                gap: 8px;
            }
        </style>
        
        <script>
            // Initializing browser state
            const cellId = '{self.cell_id}';
            const activeTabId = '{self.active_tab_id}';
            let currentUrl = '{current_url}';
            
            // Initialize iframe with content if available
            const browserFrame = document.getElementById('browser-frame');
            {f'browserFrame.srcdoc = `{self._sanitize_html(page_content)}`;' if page_content else ''}
            
            // Function to navigate to a URL
            async function navigateTo(url) {{
                try {{
                    document.getElementById('status-text').textContent = 'Navigating...';
                    document.getElementById('loading-indicator').style.display = 'flex';
                    document.getElementById('browser-frame').style.display = 'none';
                    
                    // Update the address bar
                    document.getElementById('url-input').value = url;
                    
                    // Call the navigate capability
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/navigate`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            url: url,
                            tab_id: activeTabId
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Update the current URL
                        currentUrl = url;
                        
                        // Reload the page after navigation
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Navigation error: ${{result.error || 'Unknown error'}}`;
                        document.getElementById('loading-indicator').style.display = 'none';
                        document.getElementById('browser-frame').style.display = 'block';
                    }}
                }} catch (error) {{
                    console.error('Navigation failed:', error);
                    document.getElementById('status-text').textContent = `Navigation error: ${{error.message}}`;
                    document.getElementById('loading-indicator').style.display = 'none';
                    document.getElementById('browser-frame').style.display = 'block';
                }}
            }}
            
            // Function to navigate to URL from address bar
            function navigateToUrl() {{
                const url = document.getElementById('url-input').value.trim();
                if (url) {{
                    navigateTo(url);
                }}
            }}
            
            // Handle Enter key in address bar
            function handleUrlKeyPress(event) {{
                if (event.key === 'Enter') {{
                    navigateToUrl();
                }}
            }}
            
            // Navigate back function
            async function navigateBack() {{
                try {{
                    document.getElementById('status-text').textContent = 'Navigating back...';
                    
                    // Call the manage_tabs capability with back action
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_tabs`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'back',
                            tab_id: activeTabId
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the page after navigation
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Navigation error: ${{result.error || 'Cannot go back'}}`;
                    }}
                }} catch (error) {{
                    console.error('Back navigation failed:', error);
                    document.getElementById('status-text').textContent = `Navigation error: ${{error.message}}`;
                }}
            }}
            
            // Navigate forward function
            async function navigateForward() {{
                try {{
                    document.getElementById('status-text').textContent = 'Navigating forward...';
                    
                    // Call the manage_tabs capability with forward action
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_tabs`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'forward',
                            tab_id: activeTabId
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the page after navigation
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Navigation error: ${{result.error || 'Cannot go forward'}}`;
                    }}
                }} catch (error) {{
                    console.error('Forward navigation failed:', error);
                    document.getElementById('status-text').textContent = `Navigation error: ${{error.message}}`;
                }}
            }}
            
            // Reload page function
            function reloadPage() {{
                document.getElementById('loading-indicator').style.display = 'flex';
                document.getElementById('browser-frame').style.display = 'none';
                document.getElementById('status-text').textContent = 'Reloading...';
                
                // Reload current page
                navigateTo(currentUrl);
            }}
            
            // Navigate home function
            function navigateHome() {{
                navigateTo('{self.settings["default_home_page"]}');
            }}
            
            // Function to reload the browser content
            function reloadBrowserContent() {{
                // Reload the entire browser interface to get the latest content
                window.location.reload();
            }}
            
            // New tab function
            async function newTab() {{
                try {{
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_tabs`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'new'
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the browser interface
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Error creating tab: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Tab creation failed:', error);
                    document.getElementById('status-text').textContent = `Error creating tab: ${{error.message}}`;
                }}
            }}
            
            // Close tab function
            async function closeTab(tabId, event) {{
                // Prevent the click from also triggering switchTab
                event.stopPropagation();
                
                try {{
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_tabs`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'close',
                            tab_id: tabId
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the browser interface
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Error closing tab: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Tab closing failed:', error);
                    document.getElementById('status-text').textContent = `Error closing tab: ${{error.message}}`;
                }}
            }}
            
            // Switch tab function
            async function switchTab(tabId) {{
                try {{
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_tabs`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'switch',
                            tab_id: tabId
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the browser interface
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Error switching tab: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Tab switching failed:', error);
                    document.getElementById('status-text').textContent = `Error switching tab: ${{error.message}}`;
                }}
            }}
            
            // Toggle bookmark function
            async function toggleBookmark() {{
                try {{
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_bookmarks`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'add',
                            url: currentUrl,
                            title: document.title || currentUrl
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the browser interface
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Error adding bookmark: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Bookmark action failed:', error);
                    document.getElementById('status-text').textContent = `Error adding bookmark: ${{error.message}}`;
                }}
            }}
            
            // Remove bookmark function
            async function removeBookmark(bookmarkId, event) {{
                // Prevent the click from also triggering the bookmark navigation
                event.stopPropagation();
                
                try {{
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/manage_bookmarks`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'remove',
                            bookmark_id: bookmarkId
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Reload the browser interface
                        reloadBrowserContent();
                    }} else {{
                        document.getElementById('status-text').textContent = `Error removing bookmark: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Bookmark removal failed:', error);
                    document.getElementById('status-text').textContent = `Error removing bookmark: ${{error.message}}`;
                }}
            }}
            
            // Show history function
            async function showHistory() {{
                try {{
                    document.getElementById('status-text').textContent = 'Loading history...';
                    
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/browser_history`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'get',
                            limit: 10
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Create a history popup
                        const historyItems = result.outputs.find(o => o.name === 'history_items')?.value || [];
                        
                        // Build HTML for history popup
                        let historyHtml = `
                            <div class="popup-header">
                                <h3>Browser History</h3>
                                <button onclick="closePopup()">×</button>
                            </div>
                            <div class="popup-content">
                        `;
                        
                        if (historyItems.length === 0) {{
                            historyHtml += '<p>No history items found</p>';
                        }} else {{
                            historyHtml += '<ul class="history-list">';
                            
                            historyItems.forEach(item => {{
                                historyHtml += `
                                    <li class="history-item">
                                        <div class="history-item-time">${{new Date(item.timestamp).toLocaleString()}}</div>
                                        <a href="javascript:void(0)" onclick="navigateTo('${{item.url}}')" class="history-item-link">
                                            <div class="history-item-title">${{item.title || item.url}}</div>
                                            <div class="history-item-url">${{item.url}}</div>
                                        </a>
                                    </li>
                                `;
                            }});
                            
                            historyHtml += '</ul>';
                        }}
                        
                        historyHtml += `
                                <div class="popup-footer">
                                    <button onclick="clearHistory()">Clear History</button>
                                </div>
                            </div>
                        `;
                        
                        // Show popup
                        showPopup(historyHtml);
                        
                        document.getElementById('status-text').textContent = 'History loaded';
                    }} else {{
                        document.getElementById('status-text').textContent = `Error loading history: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('History retrieval failed:', error);
                    document.getElementById('status-text').textContent = `Error loading history: ${{error.message}}`;
                }}
            }}
            
            // Clear history function
            async function clearHistory() {{
                try {{
                    document.getElementById('status-text').textContent = 'Clearing history...';
                    
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/browser_history`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'clear'
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        document.getElementById('status-text').textContent = 'History cleared';
                        closePopup();
                    }} else {{
                        document.getElementById('status-text').textContent = `Error clearing history: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('History clearing failed:', error);
                    document.getElementById('status-text').textContent = `Error clearing history: ${{error.message}}`;
                }}
            }}
            
            // Show settings function
            async function showSettings() {{
                try {{
                    document.getElementById('status-text').textContent = 'Loading settings...';
                    
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/browser_settings`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'get'
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        // Get settings
                        const settings = result.outputs.find(o => o.name === 'settings')?.value || {{}};
                        
                        // Build HTML for settings popup
                        let settingsHtml = `
                            <div class="popup-header">
                                <h3>Browser Settings</h3>
                                <button onclick="closePopup()">×</button>
                            </div>
                            <div class="popup-content">
                                <form id="settings-form">
                                    <div class="settings-group">
                                        <label for="default_home_page">Home Page</label>
                                        <input type="text" id="default_home_page" name="default_home_page" value="${{settings.default_home_page || ''}}">
                                    </div>
                                    
                                    <div class="settings-group">
                                        <label for="search_engine">Search Engine</label>
                                        <input type="text" id="search_engine" name="search_engine" value="${{settings.search_engine || ''}}">
                                    </div>
                                    
                                    <div class="settings-group">
                                        <label for="download_directory">Download Directory</label>
                                        <input type="text" id="download_directory" name="download_directory" value="${{settings.download_directory || ''}}">
                                    </div>
                                    
                                    <div class="settings-group">
                                        <label>
                                            <input type="checkbox" name="enable_cookies" ${{settings.enable_cookies ? 'checked' : ''}}>
                                            Enable Cookies
                                        </label>
                                    </div>
                                    
                                    <div class="settings-group">
                                        <label>
                                            <input type="checkbox" name="enable_javascript" ${{settings.enable_javascript ? 'checked' : ''}}>
                                            Enable JavaScript
                                        </label>
                                    </div>
                                    
                                    <div class="settings-group">
                                        <label>
                                            <input type="checkbox" name="enable_plugins" ${{settings.enable_plugins ? 'checked' : ''}}>
                                            Enable Plugins
                                        </label>
                                    </div>
                                    
                                    <div class="settings-group">
                                        <label for="max_tabs">Maximum Tabs</label>
                                        <input type="number" id="max_tabs" name="max_tabs" value="${{settings.max_tabs || 10}}" min="1" max="20">
                                    </div>
                                </form>
                            </div>
                            <div class="popup-footer">
                                <button onclick="saveSettings()">Save Settings</button>
                            </div>
                        `;
                        
                        // Show popup
                        showPopup(settingsHtml);
                        
                        document.getElementById('status-text').textContent = 'Settings loaded';
                    }} else {{
                        document.getElementById('status-text').textContent = `Error loading settings: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Settings retrieval failed:', error);
                    document.getElementById('status-text').textContent = `Error loading settings: ${{error.message}}`;
                }}
            }}
            
            // Save settings function
            async function saveSettings() {{
                try {{
                    document.getElementById('status-text').textContent = 'Saving settings...';
                    
                    // Get form data
                    const form = document.getElementById('settings-form');
                    const formData = new FormData(form);
                    
                    // Convert to object
                    const settings = {{}};
                    for (const [key, value] of formData.entries()) {{
                        if (key === 'enable_cookies' || key === 'enable_javascript' || key === 'enable_plugins') {{
                            settings[key] = true;  // Checkbox is checked
                        }} else if (key === 'max_tabs') {{
                            settings[key] = parseInt(value);
                        }} else {{
                            settings[key] = value;
                        }}
                    }}
                    
                    // Add unchecked checkboxes (they don't appear in FormData)
                    if (!formData.has('enable_cookies')) settings['enable_cookies'] = false;
                    if (!formData.has('enable_javascript')) settings['enable_javascript'] = false;
                    if (!formData.has('enable_plugins')) settings['enable_plugins'] = false;
                    
                    const response = await fetch(`/api/cells/${{cellId}}/capabilities/browser_settings`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            action: 'set',
                            settings: settings
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {{
                        document.getElementById('status-text').textContent = 'Settings saved';
                        closePopup();
                        
                        // Reload browser interface after a brief delay
                        setTimeout(reloadBrowserContent, 500);
                    }} else {{
                        document.getElementById('status-text').textContent = `Error saving settings: ${{result.error || 'Unknown error'}}`;
                    }}
                }} catch (error) {{
                    console.error('Settings save failed:', error);
                    document.getElementById('status-text').textContent = `Error saving settings: ${{error.message}}`;
                }}
            }}
            
            // Popup management
            function showPopup(content) {{
                // Create popup if it doesn't exist
                let popup = document.getElementById('browser-popup');
                if (!popup) {{
                    popup = document.createElement('div');
                    popup.id = 'browser-popup';
                    popup.className = 'browser-popup';
                    document.body.appendChild(popup);
                    
                    // Add styles for popup
                    const style = document.createElement('style');
                    style.textContent = `
                        .browser-popup {{
                            position: fixed;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            width: 80%;
                            max-width: 600px;
                            max-height: 80vh;
                            background-color: #fff;
                            border-radius: 8px;
                            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                            z-index: 1000;
                            display: flex;
                            flex-direction: column;
                        }}
                        
                        .dark-theme .browser-popup {{
                            background-color: #444;
                            color: #fff;
                        }}
                        
                        .popup-overlay {{
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background-color: rgba(0, 0, 0, 0.5);
                            z-index: 999;
                        }}
                        
                        .popup-header {{
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 16px;
                            border-bottom: 1px solid #ddd;
                        }}
                        
                        .dark-theme .popup-header {{
                            border-color: #555;
                        }}
                        
                        .popup-header h3 {{
                            margin: 0;
                            font-size: 18px;
                        }}
                        
                        .popup-header button {{
                            background: none;
                            border: none;
                            font-size: 24px;
                            cursor: pointer;
                            color: #666;
                        }}
                        
                        .dark-theme .popup-header button {{
                            color: #ccc;
                        }}
                        
                        .popup-content {{
                            flex-grow: 1;
                            overflow-y: auto;
                            padding: 16px;
                        }}
                        
                        .popup-footer {{
                            padding: 16px;
                            border-top: 1px solid #ddd;
                            display: flex;
                            justify-content: flex-end;
                        }}
                        
                        .dark-theme .popup-footer {{
                            border-color: #555;
                        }}
                        
                        .popup-footer button {{
                            padding: 8px 16px;
                            background-color: #f0f0f0;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                            cursor: pointer;
                        }}
                        
                        .dark-theme .popup-footer button {{
                            background-color: #555;
                            border-color: #666;
                            color: #fff;
                        }}
                        
                        .history-list {{
                            list-style: none;
                            padding: 0;
                            margin: 0;
                        }}
                        
                        .history-item {{
                            padding: 8px 0;
                            border-bottom: 1px solid #eee;
                        }}
                        
                        .dark-theme .history-item {{
                            border-color: #555;
                        }}
                        
                        .history-item-time {{
                            font-size: 12px;
                            color: #999;
                            margin-bottom: 4px;
                        }}
                        
                        .dark-theme .history-item-time {{
                            color: #aaa;
                        }}
                        
                        .history-item-link {{
                            text-decoration: none;
                            color: inherit;
                            display: block;
                        }}
                        
                        .history-item-title {{
                            font-weight: 500;
                        }}
                        
                        .history-item-url {{
                            font-size: 12px;
                            color: #666;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                        }}
                        
                        .dark-theme .history-item-url {{
                            color: #aaa;
                        }}
                        
                        .settings-group {{
                            margin-bottom: 16px;
                        }}
                        
                        .settings-group label {{
                            display: block;
                            margin-bottom: 4px;
                        }}
                        
                        .settings-group input[type="text"],
                        .settings-group input[type="number"] {{
                            width: 100%;
                            padding: 8px;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                        }}
                        
                        .dark-theme .settings-group input[type="text"],
                        .dark-theme .settings-group input[type="number"] {{
                            background-color: #555;
                            border-color: #666;
                            color: #fff;
                        }}
                    `;
                    document.head.appendChild(style);
                }}
                
                // Create overlay
                let overlay = document.getElementById('popup-overlay');
                if (!overlay) {{
                    overlay = document.createElement('div');
                    overlay.id = 'popup-overlay';
                    overlay.className = 'popup-overlay';
                    overlay.onclick = closePopup;
                    document.body.appendChild(overlay);
                }}
                
                // Set popup content
                popup.innerHTML = content;
                
                // Show popup and overlay
                popup.style.display = 'flex';
                overlay.style.display = 'block';
            }}
            
            function closePopup() {{
                const popup = document.getElementById('browser-popup');
                const overlay = document.getElementById('popup-overlay');
                
                if (popup) popup.style.display = 'none';
                if (overlay) overlay.style.display = 'none';
            }}
            
            // Initialize iframe content once it's loaded
            browserFrame.addEventListener('load', function() {{
                document.getElementById('loading-indicator').style.display = 'none';
                browserFrame.style.display = 'block';
                document.getElementById('status-text').textContent = 'Page loaded';
            }});
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
                "execution_time_ms": 50,
                "memory_used_mb": 2.0
            }
        }
    
    async def navigate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to a URL.
        
        Args:
            parameters: Navigation parameters
                - url: URL to navigate to
                - tab_id: ID of tab to navigate in (uses active tab if not provided)
        
        Returns:
            Success indicator and page information
        """
        # Validate required parameters
        if "url" not in parameters:
            return self._error_response("URL parameter is required")
        
        url = parameters["url"]
        tab_id = parameters.get("tab_id", self.active_tab_id)
        
        # Validate URL
        if not url:
            return self._error_response("URL cannot be empty")
        
        # Check if tab exists
        if tab_id not in self.tabs:
            return self._error_response(f"Tab with ID {tab_id} not found")
        
        # Process the URL (e.g., handle search terms)
        url = self._process_url(url)
        
        try:
            # Mark tab as loading
            self.tabs[tab_id]["loading"] = True
            
            # Get network interface cell
            network_cell = self._get_network_cell()
            if not network_cell:
                return self._error_response("Network interface cell not available")
            
            # Track timing
            start_time = time.time()
            
            # Make HTTP request through network interface cell
            response = await self.call_capability(
                cell_id=network_cell,
                capability="http_request",
                parameters={
                    "method": "GET",
                    "url": url,
                    "headers": {
                        "User-Agent": self.settings.get("user_agent", "QCC Web Browser/1.0.0")
                    }
                }
            )
            
            # Check for errors
            if response.get("status") != "success":
                error_message = next((o["value"] for o in response.get("outputs", []) if o["name"] == "error"), "Unknown error")
                
                # Update tab with error page
                self.tabs[tab_id]["url"] = url
                self.tabs[tab_id]["title"] = f"Error: {url}"
                self.tabs[tab_id]["content"] = self._generate_error_page(url, error_message)
                self.tabs[tab_id]["loading"] = False
                
                # Add to history
                self._add_to_history(url, f"Error: {url}")
                
                return self._error_response(f"Navigation failed: {error_message}")
            
            # Get response data
            status_code = next((o["value"] for o in response["outputs"] if o["name"] == "status_code"), 0)
            headers = next((o["value"] for o in response["outputs"] if o["name"] == "headers"), {})
            body = next((o["value"] for o in response["outputs"] if o["name"] == "body"), "")
            timing = next((o["value"] for o in response["outputs"] if o["name"] == "timing"), {})
            
            # Calculate load time
            load_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse HTML to extract title
            title = self._extract_title(body) or url
            
            # Extract favicon
            favicon = self._extract_favicon(body, url)
            
            # Update tab info
            self.tabs[tab_id]["url"] = url
            self.tabs[tab_id]["title"] = title
            self.tabs[tab_id]["content"] = body
            self.tabs[tab_id]["status_code"] = status_code
            self.tabs[tab_id]["headers"] = headers
            self.tabs[tab_id]["favicon"] = favicon
            self.tabs[tab_id]["load_time_ms"] = load_time_ms
            self.tabs[tab_id]["loading"] = False
            
            # Add current URL to history
            self._add_to_history(url, title)
            
            # Add to tab history
            if "history" not in self.tabs[tab_id]:
                self.tabs[tab_id]["history"] = []
                self.tabs[tab_id]["history_position"] = -1
            
            # Check if we're navigating within history
            current_position = self.tabs[tab_id]["history_position"]
            if current_position >= 0 and current_position < len(self.tabs[tab_id]["history"]) - 1:
                # Truncate history at current position
                self.tabs[tab_id]["history"] = self.tabs[tab_id]["history"][:current_position + 1]
            
            # Add new URL to history
            self.tabs[tab_id]["history"].append(url)
            self.tabs[tab_id]["history_position"] = len(self.tabs[tab_id]["history"]) - 1
            
            # Create page info
            page_info = {
                "url": url,
                "title": title,
                "status_code": status_code,
                "content_type": headers.get("Content-Type", ""),
                "load_time_ms": load_time_ms,
                "favicon": favicon
            }
            
            logger.info(f"Navigated to {url} in tab {tab_id}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "page_info",
                        "value": page_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": load_time_ms,
                    "memory_used_mb": 5.0
                }
            }
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            
            # Update tab with error page
            self.tabs[tab_id]["url"] = url
            self.tabs[tab_id]["title"] = f"Error: {url}"
            self.tabs[tab_id]["content"] = self._generate_error_page(url, str(e))
            self.tabs[tab_id]["loading"] = False
            
            # Add to history
            self._add_to_history(url, f"Error: {url}")
            
            return self._error_response(f"Navigation failed: {str(e)}")
    
    async def manage_tabs(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage browser tabs.
        
        Args:
            parameters: Tab management parameters
                - action: Action to perform (new, close, switch, back, forward)
                - tab_id: Tab identifier for close, switch, back, and forward actions
                - url: Initial URL for new tab
        
        Returns:
            Success indicator, active tab, and tab list
        """
        # Validate required parameters
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"].lower()
        
        try:
            if action == "new":
                # Create a new tab
                url = parameters.get("url", self.settings["default_home_page"])
                new_tab_id = self._create_new_tab(url)
                
                # Make it the active tab
                self.active_tab_id = new_tab_id
                
                # Navigate to the URL
                await self.navigate({
                    "url": url,
                    "tab_id": new_tab_id
                })
                
            elif action == "close":
                # Close a tab
                tab_id = parameters.get("tab_id")
                
                if not tab_id:
                    return self._error_response("Tab ID parameter is required for close action")
                
                if tab_id not in self.tabs:
                    return self._error_response(f"Tab with ID {tab_id} not found")
                
                # Check if it's the only tab
                if len(self.tabs) <= 1:
                    return self._error_response("Cannot close the only tab")
                
                # Remove the tab
                del self.tabs[tab_id]
                
                # If the active tab was closed, make another tab active
                if tab_id == self.active_tab_id:
                    self.active_tab_id = next(iter(self.tabs.keys()))
                
            elif action == "switch":
                # Switch to a tab
                tab_id = parameters.get("tab_id")
                
                if not tab_id:
                    return self._error_response("Tab ID parameter is required for switch action")
                
                if tab_id not in self.tabs:
                    return self._error_response(f"Tab with ID {tab_id} not found")
                
                # Set as active tab
                self.active_tab_id = tab_id
                
            elif action == "back":
                # Go back in tab history
                tab_id = parameters.get("tab_id", self.active_tab_id)
                
                if tab_id not in self.tabs:
                    return self._error_response(f"Tab with ID {tab_id} not found")
                
                tab = self.tabs[tab_id]
                
                if "history" not in tab or "history_position" not in tab:
                    return self._error_response("No browsing history available")
                
                if tab["history_position"] <= 0:
                    return self._error_response("Cannot go back (already at the oldest entry)")
                
                # Update position and navigate
                tab["history_position"] -= 1
                url = tab["history"][tab["history_position"]]
                
                # Navigate without updating history
                await self._navigate_without_history(url, tab_id)
                
            elif action == "forward":
                # Go forward in tab history
                tab_id = parameters.get("tab_id", self.active_tab_id)
                
                if tab_id not in self.tabs:
                    return self._error_response(f"Tab with ID {tab_id} not found")
                
                tab = self.tabs[tab_id]
                
                if "history" not in tab or "history_position" not in tab:
                    return self._error_response("No browsing history available")
                
                if tab["history_position"] >= len(tab["history"]) - 1:
                    return self._error_response("Cannot go forward (already at the newest entry)")
                
                # Update position and navigate
                tab["history_position"] += 1
                url = tab["history"][tab["history_position"]]
                
                # Navigate without updating history
                await self._navigate_without_history(url, tab_id)
                
            else:
                return self._error_response(f"Unsupported action: {action}")
            
            # Get active tab info
            active_tab = self.tabs.get(self.active_tab_id, {})
            
            # Prepare tab list
            tab_list = [
                {
                    "id": tab_id,
                    "url": tab.get("url", ""),
                    "title": tab.get("title", "New Tab"),
                    "favicon": tab.get("favicon", ""),
                    "active": tab_id == self.active_tab_id
                }
                for tab_id, tab in self.tabs.items()
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
                        "name": "active_tab",
                        "value": {
                            "id": self.active_tab_id,
                            "url": active_tab.get("url", ""),
                            "title": active_tab.get("title", "New Tab"),
                            "favicon": active_tab.get("favicon", "")
                        },
                        "type": "object"
                    },
                    {
                        "name": "tab_list",
                        "value": tab_list,
                        "type": "array"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,
                    "memory_used_mb": 0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Tab management error: {e}")
            return self._error_response(f"Tab management failed: {str(e)}")
    
    async def manage_bookmarks(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage browser bookmarks.
        
        Args:
            parameters: Bookmark management parameters
                - action: Action to perform (add, remove, list)
                - url: URL for add action
                - title: Title for add action
                - bookmark_id: Bookmark identifier for remove action
        
        Returns:
            Success indicator and bookmarks list
        """
        # Validate required parameters
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"].lower()
        
        try:
            if action == "add":
                # Add a bookmark
                if "url" not in parameters:
                    return self._error_response("URL parameter is required for add action")
                
                url = parameters["url"]
                title = parameters.get("title", url)
                
                # Check if bookmark already exists
                for bookmark in self.bookmarks:
                    if bookmark["url"] == url:
                        return self._error_response("Bookmark already exists")
                
                # Generate bookmark ID
                bookmark_id = f"bookmark_{int(time.time())}_{self._get_hash(url)}"
                
                # Add bookmark
                self.bookmarks.append({
                    "id": bookmark_id,
                    "url": url,
                    "title": title,
                    "created_at": time.time()
                })
                
                # Sort bookmarks by title
                self.bookmarks.sort(key=lambda b: b["title"])
                
            elif action == "remove":
                # Remove a bookmark
                bookmark_id = parameters.get("bookmark_id")
                
                if not bookmark_id:
                    return self._error_response("Bookmark ID parameter is required for remove action")
                
                # Find and remove bookmark
                matching_bookmark = None
                for i, bookmark in enumerate(self.bookmarks):
                    if bookmark["id"] == bookmark_id:
                        matching_bookmark = bookmark
                        self.bookmarks.pop(i)
                        break
                
                if not matching_bookmark:
                    return self._error_response(f"Bookmark with ID {bookmark_id} not found")
                
            elif action == "list":
                # Nothing to do, just return the bookmarks
                pass
                
            else:
                return self._error_response(f"Unsupported action: {action}")
            
            # Persist bookmarks if file_system cell is available
            await self._persist_bookmarks()
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "bookmarks",
                        "value": self.bookmarks,
                        "type": "array"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Bookmark management error: {e}")
            return self._error_response(f"Bookmark management failed: {str(e)}")
    
    async def browser_history(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage and query browser history.
        
        Args:
            parameters: History parameters
                - action: Action to perform (get, clear, search)
                - query: Search query for search action
                - limit: Maximum number of history items to return
        
        Returns:
            Success indicator and history items
        """
        # Validate required parameters
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"].lower()
        
        try:
            if action == "get":
                # Get history items
                limit = parameters.get("limit", 50)
                
                # Get limited number of most recent history items
                history_items = sorted(
                    self.history,
                    key=lambda h: h["timestamp"],
                    reverse=True
                )[:limit]
                
            elif action == "clear":
                # Clear history
                self.history = []
                history_items = []
                
                # Persist empty history if file_system cell is available
                await self._persist_history()
                
            elif action == "search":
                # Search history
                if "query" not in parameters:
                    return self._error_response("Query parameter is required for search action")
                
                query = parameters["query"].lower()
                limit = parameters.get("limit", 50)
                
                # Search history by URL and title
                history_items = [
                    item for item in self.history
                    if query in item["url"].lower() or query in item.get("title", "").lower()
                ]
                
                # Sort by timestamp (newest first) and limit results
                history_items = sorted(
                    history_items,
                    key=lambda h: h["timestamp"],
                    reverse=True
                )[:limit]
                
            else:
                return self._error_response(f"Unsupported action: {action}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "history_items",
                        "value": history_items,
                        "type": "array"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"History operation error: {e}")
            return self._error_response(f"History operation failed: {str(e)}")
    
    async def browser_settings(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage browser settings.
        
        Args:
            parameters: Settings parameters
                - action: Action to perform (get, set)
                - settings: Settings to update for set action
        
        Returns:
            Success indicator and current settings
        """
        # Validate required parameters
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"].lower()
        
        try:
            if action == "get":
                # Return current settings
                pass
                
            elif action == "set":
                # Update settings
                if "settings" not in parameters:
                    return self._error_response("Settings parameter is required for set action")
                
                settings = parameters["settings"]
                
                # Validate and update settings
                if not isinstance(settings, dict):
                    return self._error_response("Settings must be an object")
                
                # Update settings
                for key, value in settings.items():
                    if key in self.settings:
                        self.settings[key] = value
                
            else:
                return self._error_response(f"Unsupported action: {action}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "settings",
                        "value": self.settings,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Settings operation error: {e}")
            return self._error_response(f"Settings operation failed: {str(e)}")
    
    def _create_new_tab(self, url: str = None) -> str:
        """
        Create a new browser tab.
        
        Args:
            url: Initial URL for the tab (uses home page if not provided)
        
        Returns:
            ID of the new tab
        """
        # Check if we've reached the maximum number of tabs
        max_tabs = self.settings.get("max_tabs", 10)
        if len(self.tabs) >= max_tabs:
            raise TabError(f"Maximum number of tabs ({max_tabs}) reached")
        
        # Generate a unique tab ID
        tab_id = f"tab_{int(time.time())}_{len(self.tabs) + 1}"
        
        # Set initial URL
        if not url:
            url = self.settings["default_home_page"]
        
        # Create the tab
        self.tabs[tab_id] = {
            "url": url,
            "title": "New Tab",
            "content": "",
            "created_at": time.time(),
            "history": [url],
            "history_position": 0,
            "loading": False
        }
        
        # If this is the first tab, make it active
        if len(self.tabs) == 1:
            self.active_tab_id = tab_id
        
        logger.info(f"Created new tab with ID: {tab_id}")
        
        return tab_id
    
    async def _navigate_without_history(self, url: str, tab_id: str) -> None:
        """
        Navigate to a URL without updating the browsing history.
        
        Args:
            url: URL to navigate to
            tab_id: ID of tab to navigate in
        """
        # Mark tab as loading
        self.tabs[tab_id]["loading"] = True
        
        # Get network interface cell
        network_cell = self._get_network_cell()
        if not network_cell:
            self.tabs[tab_id]["loading"] = False
            self.tabs[tab_id]["content"] = self._generate_error_page(url, "Network interface cell not available")
            return
        
        try:
            # Make HTTP request through network interface cell
            response = await self.call_capability(
                cell_id=network_cell,
                capability="http_request",
                parameters={
                    "method": "GET",
                    "url": url,
                    "headers": {
                        "User-Agent": self.settings.get("user_agent", "QCC Web Browser/1.0.0")
                    }
                }
            )
            
            # Check for errors
            if response.get("status") != "success":
                error_message = next((o["value"] for o in response.get("outputs", []) if o["name"] == "error"), "Unknown error")
                
                # Update tab with error page
                self.tabs[tab_id]["url"] = url
                self.tabs[tab_id]["title"] = f"Error: {url}"
                self.tabs[tab_id]["content"] = self._generate_error_page(url, error_message)
                self.tabs[tab_id]["loading"] = False
                return
            
            # Get response data
            status_code = next((o["value"] for o in response["outputs"] if o["name"] == "status_code"), 0)
            headers = next((o["value"] for o in response["outputs"] if o["name"] == "headers"), {})
            body = next((o["value"] for o in response["outputs"] if o["name"] == "body"), "")
            
            # Parse HTML to extract title
            title = self._extract_title(body) or url
            
            # Extract favicon
            favicon = self._extract_favicon(body, url)
            
            # Update tab info
            self.tabs[tab_id]["url"] = url
            self.tabs[tab_id]["title"] = title
            self.tabs[tab_id]["content"] = body
            self.tabs[tab_id]["status_code"] = status_code
            self.tabs[tab_id]["headers"] = headers
            self.tabs[tab_id]["favicon"] = favicon
            self.tabs[tab_id]["loading"] = False
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            
            # Update tab with error page
            self.tabs[tab_id]["url"] = url
            self.tabs[tab_id]["title"] = f"Error: {url}"
            self.tabs[tab_id]["content"] = self._generate_error_page(url, str(e))
            self.tabs[tab_id]["loading"] = False
    
    def _process_url(self, url: str) -> str:
        """
        Process a URL, handling search terms and defaults.
        
        Args:
            url: URL or search term
            
        Returns:
            Processed URL
        """
        # Check if it's a valid URL
        if url.startswith("http://") or url.startswith("https://"):
            return url
        
        # Check if it's a domain name (e.g., example.com)
        if "." in url and " " not in url:
            return f"https://{url}"
        
        # Treat as search query
        search_engine = self.settings.get("search_engine", "https://www.google.com/search?q=")
        return f"{search_engine}{urllib.parse.quote(url)}"
    
    def _extract_title(self, html: str) -> Optional[str]:
        """
        Extract page title from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Page title or None if not found
        """
        if not html:
            return None
        
        # Simple regex to extract title
        import re
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        
        if title_match:
            return title_match.group(1).strip()
        
        return None
    
    def _extract_favicon(self, html: str, url: str) -> str:
        """
        Extract favicon URL from HTML.
        
        Args:
            html: HTML content
            url: Page URL for relative links
            
        Returns:
            Favicon URL or empty string if not found
        """
        if not html:
            return ""
        
        # Simple regex to extract favicon link
        import re
        
        # Look for link rel="icon" or rel="shortcut icon"
        favicon_match = re.search(r'<link[^>]*rel=["\'](icon|shortcut icon)["\'][^>]*href=["\'](.*?)["\']', html, re.IGNORECASE)
        
        if favicon_match:
            favicon_url = favicon_match.group(2).strip()
            
            # Handle relative URLs
            if favicon_url.startswith("/"):
                # Get base URL
                parsed_url = urllib.parse.urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                favicon_url = f"{base_url}{favicon_url}"
            elif not favicon_url.startswith("http"):
                # Get directory URL
                directory_url = url.rsplit("/", 1)[0]
                favicon_url = f"{directory_url}/{favicon_url}"
            
            return favicon_url
        
        # If no explicit favicon, try the default /favicon.ico
        parsed_url = urllib.parse.urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return f"{base_url}/favicon.ico"
    
    def _generate_error_page(self, url: str, error_message: str) -> str:
        """
        Generate an error page for failed navigation.
        
        Args:
            url: URL that caused the error
            error_message: Error message
            
        Returns:
            HTML for the error page
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error: {url}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                }}
                
                h1 {{
                    color: #d32f2f;
                    margin-bottom: 20px;
                }}
                
                .url {{
                    font-family: monospace;
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 4px;
                    word-break: break-all;
                }}
                
                .error-message {{
                    background-color: #ffebee;
                    border-left: 4px solid #d32f2f;
                    padding: 15px;
                    margin: 20px 0;
                }}
                
                .suggestions {{
                    background-color: #e8f5e9;
                    border-left: 4px solid #4caf50;
                    padding: 15px;
                    margin: 20px 0;
                }}
                
                .button {{
                    display: inline-block;
                    padding: 10px 15px;
                    background-color: #2196f3;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-right: 10px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>Page could not be loaded</h1>
            
            <p>The browser could not load the following address:</p>
            <div class="url">{url}</div>
            
            <div class="error-message">
                <strong>Error:</strong> {error_message}
            </div>
            
            <div class="suggestions">
                <strong>Suggestions:</strong>
                <ul>
                    <li>Check if the URL is correct</li>
                    <li>Check your internet connection</li>
                    <li>Try again later</li>
                </ul>
            </div>
            
            <a href="#" class="button" onclick="window.history.back();">Go back</a>
            <a href="{self.settings['default_home_page']}" class="button">Go to homepage</a>
        </body>
        </html>
        """
    
    def _add_to_history(self, url: str, title: str) -> None:
        """
        Add a URL to the browsing history.
        
        Args:
            url: URL to add
            title: Page title
        """
        # Check if URL is already in history
        for item in self.history:
            if item["url"] == url:
                # Update timestamp and title
                item["timestamp"] = time.time()
                item["title"] = title
                return
        
        # Add new history item
        self.history.append({
            "url": url,
            "title": title,
            "timestamp": time.time()
        })
        
        # Limit history size
        if len(self.history) > 1000:
            # Remove oldest entries
            self.history = sorted(
                self.history,
                key=lambda h: h["timestamp"],
                reverse=True
            )[:1000]
        
        # Persist history if file_system cell is available
        asyncio.create_task(self._persist_history())
    
    async def _persist_history(self) -> None:
        """Persist browsing history using file_system cell."""
        # Check if file_system cell is available
        file_system_cell = self._get_file_system_cell()
        if not file_system_cell:
            return
        
        try:
            # Convert history to JSON
            history_json = json.dumps(self.history)
            
            # Write to file
            await self.call_capability(
                cell_id=file_system_cell,
                capability="write_file",
                parameters={
                    "path": "browser_history.json",
                    "content": history_json
                }
            )
            
            logger.debug("Browser history saved to file")
            
        except Exception as e:
            logger.error(f"Failed to persist history: {e}")
    
    async def _persist_bookmarks(self) -> None:
        """Persist bookmarks using file_system cell."""
        # Check if file_system cell is available
        file_system_cell = self._get_file_system_cell()
        if not file_system_cell:
            return
        
        try:
            # Convert bookmarks to JSON
            bookmarks_json = json.dumps(self.bookmarks)
            
            # Write to file
            await self.call_capability(
                cell_id=file_system_cell,
                capability="write_file",
                parameters={
                    "path": "browser_bookmarks.json",
                    "content": bookmarks_json
                }
            )
            
            logger.debug("Browser bookmarks saved to file")
            
        except Exception as e:
            logger.error(f"Failed to persist bookmarks: {e}")
    
    async def _load_history(self) -> None:
        """Load browsing history from file_system cell."""
        # Check if file_system cell is available
        file_system_cell = self._get_file_system_cell()
        if not file_system_cell:
            return
        
        try:
            # Read from file
            response = await self.call_capability(
                cell_id=file_system_cell,
                capability="read_file",
                parameters={
                    "path": "browser_history.json"
                }
            )
            
            if response.get("status") == "success":
                content = next((o["value"] for o in response["outputs"] if o["name"] == "content"), "")
                
                if content:
                    # Parse JSON
                    self.history = json.loads(content)
                    logger.debug(f"Loaded {len(self.history)} browsing history items")
            
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
    
    async def _load_bookmarks(self) -> None:
        """Load bookmarks from file_system cell."""
        # Check if file_system cell is available
        file_system_cell = self._get_file_system_cell()
        if not file_system_cell:
            return
        
        try:
            # Read from file
            response = await self.call_capability(
                cell_id=file_system_cell,
                capability="read_file",
                parameters={
                    "path": "browser_bookmarks.json"
                }
            )
            
            if response.get("status") == "success":
                content = next((o["value"] for o in response["outputs"] if o["name"] == "content"), "")
                
                if content:
                    # Parse JSON
                    self.bookmarks = json.loads(content)
                    logger.debug(f"Loaded {len(self.bookmarks)} bookmarks")
            
        except Exception as e:
            logger.error(f"Failed to load bookmarks: {e}")
    
    def _get_network_cell(self) -> Optional[str]:
        """
        Get the ID of a connected network_interface cell.
        
        Returns:
            Cell ID or None if not found
        """
        for connection in self.connections:
            if hasattr(connection, 'capabilities') and "network_interface" in connection.capabilities:
                return connection.id
                
            if hasattr(connection, 'capability') and connection.capability == "network_interface":
                return connection.id
        
        return None
    
    def _get_file_system_cell(self) -> Optional[str]:
        """
        Get the ID of a connected file_system cell.
        
        Returns:
            Cell ID or None if not found
        """
        for connection in self.connections:
            if hasattr(connection, 'capabilities') and "file_system" in connection.capabilities:
                return connection.id
                
            if hasattr(connection, 'capability') and connection.capability == "file_system":
                return connection.id
        
        return None
    
    def _get_theme_css(self, theme: str) -> str:
        """
        Get CSS for the selected theme.
        
        Args:
            theme: Theme name (light or dark)
            
        Returns:
            CSS for the theme
        """
        if theme == "dark":
            return """
            .dark-theme {
                background-color: #333;
                color: #fff;
            }
            
            .dark-theme .browser-toolbar {
                background-color: #444;
                border-color: #555;
            }
            
            .dark-theme button {
                color: #ccc;
            }
            
            .dark-theme button:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            """
        
        # Default to light theme
        return """
        .light-theme {
            background-color: #f5f5f5;
            color: #333;
        }
        
        .light-theme .browser-toolbar {
            background-color: #fff;
            border-color: #ddd;
        }
        
        .light-theme button {
            color: #5f6368;
        }
        
        .light-theme button:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        """
    
    def _sanitize_html(self, html: str) -> str:
        """
        Sanitize HTML for safe display in an iframe.
        
        Args:
            html: HTML content
            
        Returns:
            Sanitized HTML
        """
        # In a real implementation, we would use a proper HTML sanitizer
        # For this example, we'll just escape double quotes
        return html.replace('"', '&quot;')
    
    def _get_hash(self, text: str) -> str:
        """
        Generate a hash for a text string.
        
        Args:
            text: Text to hash
            
        Returns:
            Hash string
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
        
        Returns:
            Error response dictionary
        """
        logger.error(f"Web browser error: {message}")
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
                "tabs": self.tabs,
                "active_tab_id": self.active_tab_id,
                "bookmarks": self.bookmarks,
                "history": self.history,
                "settings": self.settings
            }
            
            result = {
                "status": "success",
                "state": "suspended",
                "saved_state": state
            }
            
            logger.info("Web browser cell suspended")
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
                
                if "tabs" in saved_state:
                    self.tabs = saved_state["tabs"]
                
                if "active_tab_id" in saved_state:
                    self.active_tab_id = saved_state["active_tab_id"]
                
                if "bookmarks" in saved_state:
                    self.bookmarks = saved_state["bookmarks"]
                
                if "history" in saved_state:
                    self.history = saved_state["history"]
                
                if "settings" in saved_state:
                    self.settings = saved_state["settings"]
                
                logger.info("Web browser cell resumed with saved state")
            else:
                logger.warning("Resumed without saved state")
                
                # Create a new tab if none exist
                if not self.tabs:
                    self._create_new_tab(self.settings["default_home_page"])
            
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
            # Save bookmarks and history before release
            await self._persist_bookmarks()
            await self._persist_history()
            
            # Clear state
            self.tabs = {}
            self.active_tab_id = None
            self.bookmarks = []
            self.history = []
            
            logger.info("Web browser cell released")
            
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
