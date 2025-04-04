"""
UI Renderer Cell Implementation for QCC

This cell provides UI rendering capabilities for the QCC system,
enabling dynamic generation of user interfaces based on layout specifications.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional

from qcc.cells import BaseCell
from qcc.common.exceptions import CellError, RendererError

logger = logging.getLogger(__name__)

class UIRendererCell(BaseCell):
    """
    A middleware cell that provides UI rendering capabilities.
    
    This cell enables:
    - Rendering of HTML/CSS interfaces
    - Layout composition from multiple components
    - Responsive design adaptation
    - Theme application
    - Dynamic content injection
    """
    
    def initialize(self, parameters):
        """
        Initialize the UI renderer cell with parameters.
        
        Args:
            parameters: Initialization parameters including cell_id and context
        
        Returns:
            Initialization result with capabilities and requirements
        """
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("render_ui", self.render_ui)
        self.register_capability("render_component", self.render_component)
        self.register_capability("apply_theme", self.apply_theme)
        self.register_capability("responsive_adapt", self.responsive_adapt)
        
        # Initialize component registry
        self.component_registry = {}
        self.theme_registry = {}
        
        # Extract settings from parameters
        self.settings = parameters.get("configuration", {}).get("renderer_settings", {})
        
        # Default settings
        self.settings.setdefault("default_theme", "light")
        self.settings.setdefault("auto_responsive", True)
        self.settings.setdefault("cache_rendered", True)
        self.settings.setdefault("minify_output", True)
        self.settings.setdefault("escape_unsafe", True)
        
        # Initialize component cache
        self.component_cache = {}
        
        # Load built-in components and themes
        self._load_built_in_components()
        self._load_built_in_themes()
        
        logger.info(f"UI renderer cell initialized with ID: {self.cell_id}")
        
        return self.get_initialization_result()
    
    def get_initialization_result(self):
        """Get the initialization result with capabilities and requirements."""
        return {
            "status": "success",
            "cell_id": self.cell_id,
            "capabilities": [
                {
                    "name": "render_ui",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "layout",
                            "type": "object",
                            "required": True
                        },
                        {
                            "name": "theme",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "data",
                            "type": "object",
                            "required": False
                        },
                        {
                            "name": "options",
                            "type": "object",
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
                    "name": "render_component",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "component",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "props",
                            "type": "object",
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
                    "name": "apply_theme",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "html",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "theme",
                            "type": "string",
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "name": "themed_html",
                            "type": "string",
                            "format": "html"
                        }
                    ]
                },
                {
                    "name": "responsive_adapt",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "html",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "device_info",
                            "type": "object",
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "name": "adapted_html",
                            "type": "string",
                            "format": "html"
                        }
                    ]
                }
            ],
            "resource_usage": {
                "memory_mb": 15,
                "storage_mb": 2
            }
        }
    
    async def render_ui(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a complete user interface from a layout specification.
        
        Args:
            parameters: Rendering parameters
                - layout: Layout specification
                - theme: Optional theme to apply
                - data: Optional data to inject
                - options: Optional rendering options
        
        Returns:
            HTML representation of the user interface
        """
        if "layout" not in parameters:
            return self._error_response("Layout parameter is required")
        
        layout = parameters["layout"]
        theme = parameters.get("theme", self.settings.get("default_theme", "light"))
        data = parameters.get("data", {})
        options = parameters.get("options", {})
        
        try:
            # Extract layout sections
            sections = layout.get("sections", [])
            if not sections:
                return self._error_response("Layout must contain at least one section")
            
            # Apply global styles
            global_styles = layout.get("styles", {})
            
            # Resolve layout structure
            structure = layout.get("structure", "standard")
            
            # Render based on structure
            if structure == "standard":
                html = await self._render_standard_layout(sections, global_styles, data, theme)
            elif structure == "dashboard":
                html = await self._render_dashboard_layout(sections, global_styles, data, theme)
            elif structure == "card":
                html = await self._render_card_layout(sections, global_styles, data, theme)
            elif structure == "custom":
                html = await self._render_custom_layout(layout, data, theme)
            else:
                return self._error_response(f"Unsupported layout structure: {structure}")
            
            # Apply responsive design if enabled
            if self.settings.get("auto_responsive", True) and "device_info" in options:
                html = await self._adapt_responsive(html, options["device_info"])
            
            # Apply theme
            themed_html = await self._apply_theme(html, theme)
            
            # Minify if enabled
            if self.settings.get("minify_output", True):
                themed_html = self._minify_html(themed_html)
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "html",
                        "value": themed_html,
                        "type": "string",
                        "format": "html"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 50,
                    "memory_used_mb": 2.0
                }
            }
        except Exception as e:
            logger.error(f"Error rendering UI: {e}")
            return self._error_response(f"Error rendering UI: {str(e)}")
    
    async def _render_standard_layout(self, sections, global_styles, data, theme):
        """Render a standard layout with header, main content, and footer."""
        html = ['<!DOCTYPE html>', '<html lang="en">', '<head>']
        
        # Add meta tags
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        
        # Add title if provided
        title = next((s.get("title") for s in sections if "title" in s), "QCC Application")
        html.append(f'<title>{title}</title>')
        
        # Add global styles
        html.append('<style>')
        html.append(self._generate_css_from_styles(global_styles))
        html.append('</style>')
        
        html.append('</head>')
        html.append('<body>')
        
        # Add header section
        header_section = next((s for s in sections if s.get("type") == "header"), None)
        if header_section:
            section_id = header_section.get("id", "header")
            section_class = header_section.get("class", "")
            html.append(f'<header id="{section_id}" class="{section_class}">')
            html.append(await self._render_section_content(header_section, data))
            html.append('</header>')
        
        # Add main content
        main_section = next((s for s in sections if s.get("type") == "main"), None)
        if main_section:
            section_id = main_section.get("id", "main-content")
            section_class = main_section.get("class", "")
            html.append(f'<main id="{section_id}" class="{section_class}">')
            html.append(await self._render_section_content(main_section, data))
            html.append('</main>')
        
        # Add sidebar if present
        sidebar_section = next((s for s in sections if s.get("type") == "sidebar"), None)
        if sidebar_section:
            section_id = sidebar_section.get("id", "sidebar")
            section_class = sidebar_section.get("class", "")
            html.append(f'<aside id="{section_id}" class="{section_class}">')
            html.append(await self._render_section_content(sidebar_section, data))
            html.append('</aside>')
        
        # Add footer section
        footer_section = next((s for s in sections if s.get("type") == "footer"), None)
        if footer_section:
            section_id = footer_section.get("id", "footer")
            section_class = footer_section.get("class", "")
            html.append(f'<footer id="{section_id}" class="{section_class}">')
            html.append(await self._render_section_content(footer_section, data))
            html.append('</footer>')
        
        # Add custom scripts
        scripts_section = next((s for s in sections if s.get("type") == "scripts"), None)
        if scripts_section:
            html.append('<script>')
            html.append(scripts_section.get("content", ""))
            html.append('</script>')
        
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)
    
    async def _render_dashboard_layout(self, sections, global_styles, data, theme):
        """Render a dashboard layout with grid-based panels."""
        html = ['<!DOCTYPE html>', '<html lang="en">', '<head>']
        
        # Add meta tags
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        
        # Add title if provided
        title = next((s.get("title") for s in sections if "title" in s), "QCC Dashboard")
        html.append(f'<title>{title}</title>')
        
        # Add global styles with dashboard grid
        html.append('<style>')
        html.append(self._generate_css_from_styles(global_styles))
        html.append('''
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(12, 1fr);
                grid-gap: 16px;
                padding: 16px;
            }
            .dashboard-panel {
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 16px;
                overflow: hidden;
            }
            @media (max-width: 768px) {
                .dashboard-grid {
                    grid-template-columns: repeat(6, 1fr);
                }
                .dashboard-panel {
                    grid-column: span 6 !important;
                }
            }
            @media (max-width: 480px) {
                .dashboard-grid {
                    grid-template-columns: repeat(1, 1fr);
                    grid-gap: 12px;
                }
                .dashboard-panel {
                    grid-column: span 1 !important;
                }
            }
        ''')
        html.append('</style>')
        
        html.append('</head>')
        html.append('<body>')
        
        # Add header section
        header_section = next((s for s in sections if s.get("type") == "header"), None)
        if header_section:
            section_id = header_section.get("id", "header")
            section_class = header_section.get("class", "")
            html.append(f'<header id="{section_id}" class="{section_class}">')
            html.append(await self._render_section_content(header_section, data))
            html.append('</header>')
        
        # Create dashboard grid
        html.append('<div class="dashboard-grid">')
        
        # Add panels
        panel_sections = [s for s in sections if s.get("type") == "panel"]
        for panel in panel_sections:
            panel_id = panel.get("id", f"panel-{panel_sections.index(panel)}")
            panel_class = panel.get("class", "")
            grid_col_span = panel.get("grid_col_span", 3)
            grid_row_span = panel.get("grid_row_span", 1)
            
            html.append(f'<div id="{panel_id}" class="dashboard-panel {panel_class}" style="grid-column: span {grid_col_span}; grid-row: span {grid_row_span};">')
            if "title" in panel:
                html.append(f'<h3 class="panel-title">{panel["title"]}</h3>')
            html.append(await self._render_section_content(panel, data))
            html.append('</div>')
        
        html.append('</div>')  # Close dashboard grid
        
        # Add footer section
        footer_section = next((s for s in sections if s.get("type") == "footer"), None)
        if footer_section:
            section_id = footer_section.get("id", "footer")
            section_class = footer_section.get("class", "")
            html.append(f'<footer id="{section_id}" class="{section_class}">')
            html.append(await self._render_section_content(footer_section, data))
            html.append('</footer>')
        
        # Add custom scripts
        scripts_section = next((s for s in sections if s.get("type") == "scripts"), None)
        if scripts_section:
            html.append('<script>')
            html.append(scripts_section.get("content", ""))
            html.append('</script>')
        
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)
    
    async def _render_card_layout(self, sections, global_styles, data, theme):
        """Render a card-based layout for focused content."""
        html = ['<!DOCTYPE html>', '<html lang="en">', '<head>']
        
        # Add meta tags
        html.append('<meta charset="UTF-8">')
        html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        
        # Add title if provided
        title = next((s.get("title") for s in sections if "title" in s), "QCC Card")
        html.append(f'<title>{title}</title>')
        
        # Add global styles with card styling
        html.append('<style>')
        html.append(self._generate_css_from_styles(global_styles))
        html.append('''
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 16px;
                background-color: #f5f5f5;
                margin: 0;
            }
            .card {
                background-color: #fff;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
                width: 100%;
                max-width: 500px;
            }
            .card-header {
                padding: 16px;
                border-bottom: 1px solid #eee;
            }
            .card-body {
                padding: 24px;
            }
            .card-footer {
                padding: 16px;
                border-top: 1px solid #eee;
            }
            @media (max-width: 600px) {
                .card {
                    box-shadow: none;
                    border-radius: 0;
                }
            }
        ''')
        html.append('</style>')
        
        html.append('</head>')
        html.append('<body>')
        
        # Create card container
        html.append('<div class="card">')
        
        # Add card header
        header_section = next((s for s in sections if s.get("type") == "header"), None)
        if header_section:
            section_id = header_section.get("id", "card-header")
            section_class = header_section.get("class", "")
            html.append(f'<div id="{section_id}" class="card-header {section_class}">')
            if "title" in header_section:
                html.append(f'<h2 class="card-title">{header_section["title"]}</h2>')
            html.append(await self._render_section_content(header_section, data))
            html.append('</div>')
        
        # Add card body
        main_section = next((s for s in sections if s.get("type") == "main"), None)
        if main_section:
            section_id = main_section.get("id", "card-body")
            section_class = main_section.get("class", "")
            html.append(f'<div id="{section_id}" class="card-body {section_class}">')
            html.append(await self._render_section_content(main_section, data))
            html.append('</div>')
        
        # Add card footer
        footer_section = next((s for s in sections if s.get("type") == "footer"), None)
        if footer_section:
            section_id = footer_section.get("id", "card-footer")
            section_class = footer_section.get("class", "")
            html.append(f'<div id="{section_id}" class="card-footer {section_class}">')
            html.append(await self._render_section_content(footer_section, data))
            html.append('</div>')
        
        html.append('</div>')  # Close card
        
        # Add custom scripts
        scripts_section = next((s for s in sections if s.get("type") == "scripts"), None)
        if scripts_section:
            html.append('<script>')
            html.append(scripts_section.get("content", ""))
            html.append('</script>')
        
        html.append('</body>')
        html.append('</html>')
        
        return '\n'.join(html)
    
    async def _render_custom_layout(self, layout, data, theme):
        """Render a custom layout based on provided template."""
        template = layout.get("template", "")
        if not template:
            return self._error_response("Custom layout requires a template")
        
        # Process sections to inject
        sections = layout.get("sections", [])
        section_content = {}
        
        for section in sections:
            section_id = section.get("id")
            if section_id:
                section_content[section_id] = await self._render_section_content(section, data)
        
        # Replace section placeholders in template
        html = template
        for section_id, content in section_content.items():
            placeholder = f"{{{{section:{section_id}}}}}"
            html = html.replace(placeholder, content)
        
        # Replace data placeholders
        html = self._replace_data_placeholders(html, data)
        
        return html
    
    async def _render_section_content(self, section, data):
        """Render the content of a section."""
        content_type = section.get("content_type", "html")
        content = section.get("content", "")
        
        if content_type == "html":
            # Replace data placeholders
            return self._replace_data_placeholders(content, data)
        
        elif content_type == "markdown":
            # Convert markdown to HTML and replace data placeholders
            html_content = self._markdown_to_html(content)
            return self._replace_data_placeholders(html_content, data)
        
        elif content_type == "component":
            # Render component
            component_name = section.get("component_name")
            props = section.get("props", {})
            
            if not component_name:
                return "<div>Error: Component name not specified</div>"
            
            # Add data to props
            for key, value in props.items():
                if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                    data_key = value[2:-2].strip()
                    if data_key in data:
                        props[key] = data[data_key]
            
            result = await self.render_component({
                "component": component_name,
                "props": props
            })
            
            if result["status"] == "success":
                for output in result["outputs"]:
                    if output["name"] == "html":
                        return output["value"]
            return "<div>Error rendering component</div>"
        
        elif content_type == "template":
            # Process template with data
            return self._replace_data_placeholders(content, data)
        
        else:
            return f"<div>Unsupported content type: {content_type}</div>"
    
    async def render_component(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a specific UI component.
        
        Args:
            parameters: Component parameters
                - component: Component name
                - props: Component properties
                - theme: Optional theme to apply
        
        Returns:
            HTML representation of the component
        """
        if "component" not in parameters:
            return self._error_response("Component parameter is required")
        
        component_name = parameters["component"]
        props = parameters.get("props", {})
        theme = parameters.get("theme", self.settings.get("default_theme", "light"))
        
        # Check if component is in cache
        cache_key = None
        if self.settings.get("cache_rendered", True):
            cache_key = f"{component_name}:{json.dumps(props, sort_keys=True)}:{theme}"
            if cache_key in self.component_cache:
                cached_result = self.component_cache[cache_key]
                logger.debug(f"Using cached component: {component_name}")
                return cached_result
        
        try:
            # Check if component exists in registry
            if component_name not in self.component_registry:
                return self._error_response(f"Component not found: {component_name}")
            
            component = self.component_registry[component_name]
            
            # Check if props match required props
            required_props = component.get("required_props", [])
            for prop in required_props:
                if prop not in props:
                    return self._error_response(f"Missing required prop '{prop}' for component '{component_name}'")
            
            # Render component
            template = component.get("template", "")
            if not template:
                return self._error_response(f"Component {component_name} has no template")
            
            # Replace props in template
            html = template
            for prop_name, prop_value in props.items():
                placeholder = f"{{{{props.{prop_name}}}}}"
                
                # Handle different prop types
                if isinstance(prop_value, dict) or isinstance(prop_value, list):
                    # Convert complex types to JSON string
                    value_str = json.dumps(prop_value)
                elif prop_value is None:
                    value_str = ""
                else:
                    value_str = str(prop_value)
                
                html = html.replace(placeholder, value_str)
            
            # Replace any default props that weren't provided
            default_props = component.get("default_props", {})
            for prop_name, default_value in default_props.items():
                if prop_name not in props:
                    placeholder = f"{{{{props.{prop_name}}}}}"
                    
                    # Handle different default prop types
                    if isinstance(default_value, dict) or isinstance(default_value, list):
                        value_str = json.dumps(default_value)
                    elif default_value is None:
                        value_str = ""
                    else:
                        value_str = str(default_value)
                    
                    html = html.replace(placeholder, value_str)
            
            # Add component's CSS if available
            css = component.get("css", "")
            if css:
                html = f"<style>\n{css}\n</style>\n{html}"
            
            # Apply theme
            themed_html = await self._apply_theme(html, theme)
            
            # Store in cache if enabled
            if cache_key:
                result = {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "html",
                            "value": themed_html,
                            "type": "string",
                            "format": "html"
                        }
                    ],
                    "performance_metrics": {
                        "execution_time_ms": 10,
                        "memory_used_mb": 0.2
                    }
                }
                self.component_cache[cache_key] = result
                return result
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "html",
                        "value": themed_html,
                        "type": "string",
                        "format": "html"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error rendering component {component_name}: {e}")
            return self._error_response(f"Error rendering component {component_name}: {str(e)}")
    
    async def apply_theme(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a theme to HTML content.
        
        Args:
            parameters: Theme parameters
                - html: HTML content
                - theme: Theme to apply
        
        Returns:
            Themed HTML content
        """
        if "html" not in parameters:
            return self._error_response("HTML parameter is required")
        
        if "theme" not in parameters:
            return self._error_response("Theme parameter is required")
        
        html = parameters["html"]
        theme = parameters["theme"]
        
        try:
            # Apply theme
            themed_html = await self._apply_theme(html, theme)
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "themed_html",
                        "value": themed_html,
                        "type": "string",
                        "format": "html"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
            return self._error_response(f"Error applying theme: {str(e)}")
    
    async def _apply_theme(self, html, theme_name):
        """Apply a theme to HTML content."""
        if theme_name not in self.theme_registry:
            logger.warning(f"Theme not found: {theme_name}, using default")
            theme_name = self.settings.get("default_theme", "light")
            
            if theme_name not in self.theme_registry:
                logger.warning("Default theme not found, returning unmodified HTML")
                return html
        
        theme = self.theme_registry[theme_name]
        
        # Create theme CSS
        theme_css = []
        theme_css.append("<style>")
        theme_css.append(f"/* {theme_name} theme */")
        
        # Add theme variables
        theme_css.append(":root {")
        for var_name, var_value in theme.get("variables", {}).items():
            theme_css.append(f"    --{var_name}: {var_value};")
        theme_css.append("}")
        
        # Add theme styles
        for selector, styles in theme.get("styles", {}).items():
            theme_css.append(f"{selector} {{")
            for prop, value in styles.items():
                theme_css.append(f"    {prop}: {value};")
            theme_css.append("}")
        
        theme_css.append("</style>")
        
        # Add theme CSS to HTML
        if "</head>" in html:
            return html.replace("</head>", f"{' '.join(theme_css)}\n</head>")
        else:
            return f"{' '.join(theme_css)}\n{html}"
    
    async def responsive_adapt(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt HTML content for different devices.
        
        Args:
            parameters: Adaptation parameters
                - html: HTML content
                - device_info: Device information
        
        Returns:
            Adapted HTML content
        """
        if "html" not in parameters:
            return self._error_response("HTML parameter is required")
        
        if "device_info" not in parameters:
            return self._error_response("Device info parameter is required")
        
        html = parameters["html"]
        device_info = parameters["device_info"]
        
        try:
            # Adapt HTML for the device
            adapted_html = await self._adapt_responsive(html, device_info)
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "adapted_html",
                        "value": adapted_html,
                        "type": "string",
                        "format": "html"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error adapting HTML: {e}")
            return self._error_response(f"Error adapting HTML: {str(e)}")
    
    async def _adapt_responsive(self, html, device_info):
        """Adapt HTML for different devices."""
        # Extract device information
        screen_width = device_info.get("screen_width", 1024)
        screen_height = device_info.get("screen_height", 768)
        is_mobile = device_info.get("is_mobile", False)
        is_tablet = device_info.get("is_tablet", False)
        
        # Determine device type
        device_type = "desktop"
        if is_mobile:
            device_type = "mobile"
        elif is_tablet:
            device_type = "tablet"
        
        # Create responsive styles
        responsive_css = []
        responsive_css.append("<style>")
        responsive_css.append("/* Responsive adaptations */")
        
        if device_type == "mobile":
            responsive_css.append("""
            @media (max-width: 480px) {
                .desktop-only {
                    display: none !important;
                }
                .mobile-hidden {
                    display: none !important;
                }
                .responsive-container {
                    width: 100% !important;
                    padding: 10px !important;
                }
                .responsive-grid {
                    grid-template-columns: 1fr !important;
                }
                .responsive-text {
                    font-size: 16px !important;
                }
                .responsive-heading {
                    font-size: 20px !important;
                }
            }
            """)
        elif device_type == "tablet":
            responsive_css.append("""
            @media (min-width: 481px) and (max-width: 1024px) {
                .desktop-only {
                    display: none !important;
                }
                .tablet-hidden {
                    display: none !important;
                }
                .responsive-container {
                    width: 90% !important;
                    padding: 15px !important;
                }
                .responsive-grid {
                    grid-template-columns: repeat(2, 1fr) !important;
                }
                .responsive-text {
                    font-size: 16px !important;
                }
                .responsive-heading {
                    font-size: 24px !important;
                }
            }
            """)
        else:
            responsive_css.append("""
            @media (min-width: 1025px) {
                .mobile-only {
                    display: none !important;
                }
                .tablet-only {
                    display: none !important;
                }
                .responsive-container {
                    width: 80% !important;
                    max-width: 1200px !important;
                }
                .responsive-grid {
                    grid-template-columns: repeat(3, 1fr) !important;
                }
            }
            """)
        
        responsive_css.append("</style>")
        
        # Add responsive attributes to html tag
        html = html.replace("<html", f'<html data-device-type="{device_type}"')
        
        # Add responsive CSS to HTML
        if "</head>" in html:
            return html.replace("</head>", f"{' '.join(responsive_css)}\n</head>")
        else:
            return f"{' '.join(responsive_css)}\n{html}"
    
    def _replace_data_placeholders(self, text: str, data: Dict[str, Any]) -> str:
        """Replace data placeholders in text."""
        if not data:
            return text
        
        for key, value in data.items():
            placeholder = f"{{{{data.{key}}}}}"
            
            # Handle different value types
            if isinstance(value, dict) or isinstance(value, list):
                # Convert complex types to JSON string
                value_str = json.dumps(value)
            elif value is None:
                value_str = ""
            else:
                value_str = str(value)
            
            text = text.replace(placeholder, value_str)
        
        return text
    
    def _generate_css_from_styles(self, styles: Dict[str, Any]) -> str:
        """Generate CSS from style object."""
        css_lines = []
        
        for selector, properties in styles.items():
            css_lines.append(f"{selector} {{")
            for prop, value in properties.items():
                css_lines.append(f"    {prop}: {value};")
            css_lines.append("}")
        
        return "\n".join(css_lines)
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML."""
        # Simple markdown conversion (would use a proper library in real implementation)
        html = markdown
        
        # Headers
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
        
        # Bold and italic
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
        
        # Lists
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
        html = html.replace(/(<li>.+<\/li>\n)+/g, '<ul>$&</ul>')
        
        # Links
        html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>')
        
        # Paragraphs
        html = html.replace(/^(?!<[a-z]).+$/gm, '<p>$&</p>')
        
        return html
    
    def _minify_html(self, html: str) -> str:
        """Minify HTML content."""
        # Remove comments
        html = html.replace(/<!--[\s\S]*?-->/g, '')
        
        # Remove extra whitespace
        html = html.replace(/\s+/g, ' ')
        
        # Remove whitespace around tags
        html = html.replace(/>\s+</g, '><')
        
        return html
    
    def _load_built_in_components(self):
        """Load built-in UI components."""
        # Button component
        self.component_registry["Button"] = {
            "name": "Button",
            "description": "A clickable button component",
            "required_props": ["label"],
            "default_props": {
                "type": "button",
                "variant": "primary",
                "size": "medium",
                "disabled": False
            },
            "template": """
                <button 
                  type="{{props.type}}" 
                  class="ui-button ui-button-{{props.variant}} ui-button-{{props.size}}" 
                  {{props.disabled ? 'disabled' : ''}}
                  onclick="{{props.onClick}}"
                >
                  {{props.label}}
                </button>
            """,
            "css": """
                .ui-button {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    border: none;
                }
                .ui-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .ui-button-primary {
                    background-color: var(--primary-color, #3f51b5);
                    color: white;
                }
                .ui-button-secondary {
                    background-color: var(--secondary-color, #f50057);
                    color: white;
                }
                .ui-button-outlined {
                    background-color: transparent;
                    border: 1px solid var(--primary-color, #3f51b5);
                    color: var(--primary-color, #3f51b5);
                }
                .ui-button-text {
                    background-color: transparent;
                    color: var(--primary-color, #3f51b5);
                }
                .ui-button-small {
                    padding: 4px 8px;
                    font-size: 12px;
                }
                .ui-button-medium {
                    padding: 8px 16px;
                    font-size: 14px;
                }
                .ui-button-large {
                    padding: 12px 24px;
                    font-size: 16px;
                }
            """
        }
        
        # Card component
        self.component_registry["Card"] = {
            "name": "Card",
            "description": "A container component with a card-like appearance",
            "required_props": [],
            "default_props": {
                "title": "",
                "subtitle": "",
                "content": "",
                "footer": "",
                "elevation": 1
            },
            "template": """
                <div class="ui-card ui-card-elevation-{{props.elevation}}">
                    {{props.title ? `<div class="ui-card-header">
                        <h3 class="ui-card-title">{{props.title}}</h3>
                        ${props.subtitle ? `<div class="ui-card-subtitle">{{props.subtitle}}</div>` : ''}
                    </div>` : ''}}
                    <div class="ui-card-content">
                        {{props.content}}
                    </div>
                    {{props.footer ? `<div class="ui-card-footer">
                        {{props.footer}}
                    </div>` : ''}}
                </div>
            """,
            "css": """
                .ui-card {
                    border-radius: 8px;
                    overflow: hidden;
                    background-color: var(--card-bg-color, white);
                    margin-bottom: 16px;
                }
                .ui-card-elevation-1 {
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .ui-card-elevation-2 {
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }
                .ui-card-elevation-3 {
                    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
                }
                .ui-card-header {
                    padding: 16px;
                    border-bottom: 1px solid var(--divider-color, #eee);
                }
                .ui-card-title {
                    margin: 0;
                    font-size: 18px;
                    font-weight: 500;
                    color: var(--title-color, #333);
                }
                .ui-card-subtitle {
                    margin-top: 4px;
                    font-size: 14px;
                    color: var(--subtitle-color, #666);
                }
                .ui-card-content {
                    padding: 16px;
                }
                .ui-card-footer {
                    padding: 16px;
                    border-top: 1px solid var(--divider-color, #eee);
                }
            """
        }
        
        # Input component
        self.component_registry["Input"] = {
            "name": "Input",
            "description": "A text input component",
            "required_props": [],
            "default_props": {
                "type": "text",
                "label": "",
                "placeholder": "",
                "value": "",
                "name": "",
                "disabled": False,
                "required": False
            },
            "template": """
                <div class="ui-input-container">
                    {{props.label ? `<label class="ui-input-label" for="{{props.name}}">{{props.label}}</label>` : ''}}
                    <input 
                        type="{{props.type}}"
                        id="{{props.name}}"
                        name="{{props.name}}"
                        class="ui-input"
                        placeholder="{{props.placeholder}}"
                        value="{{props.value}}"
                        {{props.disabled ? 'disabled' : ''}}
                        {{props.required ? 'required' : ''}}
                    />
                </div>
            """,
            "css": """
                .ui-input-container {
                    margin-bottom: 16px;
                }
                .ui-input-label {
                    display: block;
                    margin-bottom: 4px;
                    font-size: 14px;
                    color: var(--label-color, #555);
                }
                .ui-input {
                    width: 100%;
                    padding: 8px 12px;
                    font-size: 14px;
                    border-radius: 4px;
                    border: 1px solid var(--border-color, #ddd);
                    background-color: var(--input-bg-color, white);
                    color: var(--input-text-color, #333);
                    transition: border-color 0.2s;
                }
                .ui-input:focus {
                    outline: none;
                    border-color: var(--primary-color, #3f51b5);
                }
                .ui-input:disabled {
                    background-color: var(--disabled-bg-color, #f5f5f5);
                    cursor: not-allowed;
                }
            """
        }
        
        # Add more built-in components as needed
        logger.info(f"Loaded {len(self.component_registry)} built-in components")
    
    def _load_built_in_themes(self):
        """Load built-in UI themes."""
        # Light theme
        self.theme_registry["light"] = {
            "name": "Light",
            "description": "A clean, light theme",
            "variables": {
                "primary-color": "#3f51b5",
                "secondary-color": "#f50057",
                "background-color": "#f5f5f5",
                "text-color": "#333333",
                "card-bg-color": "#ffffff",
                "border-color": "#e0e0e0",
                "divider-color": "#eeeeee",
                "title-color": "#212121",
                "subtitle-color": "#757575",
                "success-color": "#4caf50",
                "warning-color": "#ff9800",
                "error-color": "#f44336",
                "info-color": "#2196f3"
            },
            "styles": {
                "body": {
                    "font-family": "'Roboto', 'Segoe UI', sans-serif",
                    "line-height": "1.5",
                    "color": "var(--text-color)",
                    "background-color": "var(--background-color)",
                    "margin": "0",
                    "padding": "0"
                },
                "a": {
                    "color": "var(--primary-color)",
                    "text-decoration": "none"
                },
                "a:hover": {
                    "text-decoration": "underline"
                },
                "h1, h2, h3, h4, h5, h6": {
                    "margin-top": "0",
                    "color": "var(--title-color)"
                }
            }
        }
        
        # Dark theme
        self.theme_registry["dark"] = {
            "name": "Dark",
            "description": "A sleek, dark theme",
            "variables": {
                "primary-color": "#bb86fc",
                "secondary-color": "#03dac6",
                "background-color": "#121212",
                "text-color": "#e0e0e0",
                "card-bg-color": "#1e1e1e",
                "border-color": "#333333",
                "divider-color": "#2d2d2d",
                "title-color": "#ffffff",
                "subtitle-color": "#bbbbbb",
                "success-color": "#81c784",
                "warning-color": "#ffb74d",
                "error-color": "#e57373",
                "info-color": "#64b5f6"
            },
            "styles": {
                "body": {
                    "font-family": "'Roboto', 'Segoe UI', sans-serif",
                    "line-height": "1.5",
                    "color": "var(--text-color)",
                    "background-color": "var(--background-color)",
                    "margin": "0",
                    "padding": "0"
                },
                "a": {
                    "color": "var(--primary-color)",
                    "text-decoration": "none"
                },
                "a:hover": {
                    "text-decoration": "underline"
                },
                "h1, h2, h3, h4, h5, h6": {
                    "margin-top": "0",
                    "color": "var(--title-color)"
                }
            }
        }
        
        # Add more themes as needed
        logger.info(f"Loaded {len(self.theme_registry)} built-in themes")
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
        
        Returns:
            Error response dictionary
        """
        logger.error(f"UI renderer error: {message}")
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
                "component_registry": self.component_registry,
                "theme_registry": self.theme_registry,
                "component_cache": self.component_cache,
                "settings": self.settings
            }
            
            result = {
                "status": "success",
                "state": "suspended",
                "saved_state": state
            }
            
            logger.info("UI renderer cell suspended")
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
                
                if "component_registry" in saved_state:
                    self.component_registry = saved_state["component_registry"]
                
                if "theme_registry" in saved_state:
                    self.theme_registry = saved_state["theme_registry"]
                
                if "component_cache" in saved_state:
                    self.component_cache = saved_state["component_cache"]
                
                if "settings" in saved_state:
                    self.settings.update(saved_state["settings"])
                
                logger.info("UI renderer cell resumed with saved state")
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
            # Clear state
            self.component_cache = {}
            
            logger.info("UI renderer cell released")
            
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
