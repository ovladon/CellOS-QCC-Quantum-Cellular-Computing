"""
Data Visualization Cell Implementation for QCC

This cell provides data visualization capabilities for the QCC system,
enabling the creation of various charts, graphs, and visual representations
of data.
"""

import logging
import time
import json
import math
import hashlib
import random
from typing import Dict, List, Any, Optional, Tuple, Union

from qcc.cells import BaseCell
from qcc.common.exceptions import CellError, DataError, VisualizationError

logger = logging.getLogger(__name__)

class DataVisualizationCell(BaseCell):
    """
    A middleware cell that provides data visualization capabilities.
    
    This cell enables:
    - Creation of various charts and graphs (bar, line, pie, scatter, etc.)
    - Interactive visualizations
    - Dashboard layouts
    - Data transformations for visualization
    - Color theming and styling
    
    It serves as a bridge between data processing cells and UI rendering,
    focusing on the transformation of data into visual representations.
    """
    
    def initialize(self, parameters):
        """
        Initialize the data visualization cell with parameters.
        
        Args:
            parameters: Initialization parameters including cell_id and context
        
        Returns:
            Initialization result with capabilities and requirements
        """
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("create_chart", self.create_chart)
        self.register_capability("create_dashboard", self.create_dashboard)
        self.register_capability("transform_data", self.transform_data)
        self.register_capability("visualization_themes", self.visualization_themes)
        
        # Initialize cache for rendered visualizations
        self.visualization_cache = {}
        
        # Extract settings from parameters
        self.visualization_settings = parameters.get("configuration", {}).get("visualization_settings", {})
        
        # Default settings
        self.visualization_settings.setdefault("max_data_points", 10000)
        self.visualization_settings.setdefault("default_theme", "light")
        self.visualization_settings.setdefault("default_chart_width", 800)
        self.visualization_settings.setdefault("default_chart_height", 500)
        self.visualization_settings.setdefault("enable_animations", True)
        self.visualization_settings.setdefault("color_palette", [
            "#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f",
            "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab"
        ])
        
        # Set up dependency relationships
        self.required_connections = []  # No hard dependencies, works with any data source
        
        logger.info(f"Data visualization cell initialized with ID: {self.cell_id}")
        
        return self.get_initialization_result()
    
    def get_initialization_result(self):
        """Get the initialization result with capabilities and requirements."""
        return {
            "status": "success",
            "cell_id": self.cell_id,
            "capabilities": [
                {
                    "name": "create_chart",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "chart_type",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "data",
                            "type": "any",
                            "required": True
                        },
                        {
                            "name": "options",
                            "type": "object",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "chart_id",
                            "type": "string"
                        },
                        {
                            "name": "html",
                            "type": "string"
                        }
                    ]
                },
                {
                    "name": "create_dashboard",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "layout",
                            "type": "object",
                            "required": True
                        },
                        {
                            "name": "charts",
                            "type": "array",
                            "required": True
                        },
                        {
                            "name": "options",
                            "type": "object",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "dashboard_id",
                            "type": "string"
                        },
                        {
                            "name": "html",
                            "type": "string"
                        }
                    ]
                },
                {
                    "name": "transform_data",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "data",
                            "type": "any",
                            "required": True
                        },
                        {
                            "name": "transformations",
                            "type": "array",
                            "required": True
                        }
                    ],
                    "outputs": [
                        {
                            "name": "transformed_data",
                            "type": "any"
                        }
                    ]
                },
                {
                    "name": "visualization_themes",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "action",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "theme_name",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "theme_config",
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
                            "name": "themes",
                            "type": "array"
                        }
                    ]
                }
            ],
            "resource_usage": {
                "memory_mb": 30,
                "storage_mb": 5
            }
        }
    
    async def create_chart(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a chart visualization from data.
        
        Args:
            parameters: Chart parameters
                - chart_type: Type of chart (bar, line, pie, scatter, etc.)
                - data: Data to visualize
                - options: Chart-specific options
        
        Returns:
            Chart ID and HTML for the chart
        """
        # Validate required parameters
        if "chart_type" not in parameters:
            return self._error_response("Chart type parameter is required")
        
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        chart_type = parameters["chart_type"].lower()
        data = parameters["data"]
        options = parameters.get("options", {})
        
        # Validate chart type
        supported_chart_types = [
            "bar", "line", "pie", "scatter", "area", "bubble",
            "radar", "polar", "heatmap", "candlestick", "gauge",
            "treemap", "sankey", "boxplot", "histogram"
        ]
        
        if chart_type not in supported_chart_types:
            return self._error_response(f"Unsupported chart type: {chart_type}. Supported types: {', '.join(supported_chart_types)}")
        
        # Validate data
        try:
            self._validate_data_for_chart(chart_type, data)
        except DataError as e:
            return self._error_response(f"Invalid data for {chart_type} chart: {str(e)}")
        
        # Check data size
        data_points = self._count_data_points(data)
        max_points = self.visualization_settings.get("max_data_points", 10000)
        
        if data_points > max_points:
            return self._error_response(f"Data size exceeds maximum allowed ({data_points} > {max_points} points)")
        
        # Process chart-specific options
        processed_options = self._process_chart_options(chart_type, options)
        
        # Create a unique chart ID
        chart_id = f"chart_{int(time.time())}_{self._hash_data(data)[:8]}"
        
        try:
            # Generate HTML for the chart
            html = self._generate_chart_html(chart_type, data, processed_options)
            
            # Store in cache
            self.visualization_cache[chart_id] = {
                "type": chart_type,
                "data": data,
                "options": processed_options,
                "created_at": time.time()
            }
            
            logger.info(f"Created {chart_type} chart: {chart_id}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "chart_id",
                        "value": chart_id,
                        "type": "string"
                    },
                    {
                        "name": "html",
                        "value": html,
                        "type": "string"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 50,
                    "memory_used_mb": 2.0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return self._error_response(f"Error creating chart: {str(e)}")
    
    async def create_dashboard(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a dashboard with multiple charts.
        
        Args:
            parameters: Dashboard parameters
                - layout: Dashboard layout configuration
                - charts: List of charts to include
                - options: Dashboard-specific options
        
        Returns:
            Dashboard ID and HTML for the dashboard
        """
        # Validate required parameters
        if "layout" not in parameters:
            return self._error_response("Layout parameter is required")
        
        if "charts" not in parameters:
            return self._error_response("Charts parameter is required")
        
        layout = parameters["layout"]
        charts = parameters["charts"]
        options = parameters.get("options", {})
        
        # Validate charts
        if not isinstance(charts, list):
            return self._error_response("Charts parameter must be an array")
        
        if len(charts) == 0:
            return self._error_response("At least one chart is required")
        
        # Process each chart
        processed_charts = []
        
        for i, chart in enumerate(charts):
            if not isinstance(chart, dict):
                return self._error_response(f"Chart {i} must be an object")
            
            # Chart can be defined inline or referenced by ID
            if "chart_id" in chart:
                # Reference to existing chart
                chart_id = chart["chart_id"]
                
                if chart_id not in self.visualization_cache:
                    return self._error_response(f"Chart not found: {chart_id}")
                
                # Get chart from cache
                cached_chart = self.visualization_cache[chart_id]
                
                # Generate HTML for the chart
                chart_html = self._generate_chart_html(
                    cached_chart["type"],
                    cached_chart["data"],
                    cached_chart["options"]
                )
                
                processed_charts.append({
                    "id": chart_id,
                    "type": cached_chart["type"],
                    "html": chart_html,
                    "position": chart.get("position", {})
                })
                
            elif "chart_type" in chart and "data" in chart:
                # Inline chart definition
                try:
                    # Create a temporary chart
                    temp_chart_result = await self.create_chart({
                        "chart_type": chart["chart_type"],
                        "data": chart["data"],
                        "options": chart.get("options", {})
                    })
                    
                    if temp_chart_result["status"] != "success":
                        return self._error_response(f"Failed to create chart {i}: {temp_chart_result.get('error', 'Unknown error')}")
                    
                    # Extract chart info
                    chart_id = next((o["value"] for o in temp_chart_result["outputs"] if o["name"] == "chart_id"), None)
                    chart_html = next((o["value"] for o in temp_chart_result["outputs"] if o["name"] == "html"), None)
                    
                    if not chart_id or not chart_html:
                        return self._error_response(f"Invalid chart result for chart {i}")
                    
                    processed_charts.append({
                        "id": chart_id,
                        "type": chart["chart_type"],
                        "html": chart_html,
                        "position": chart.get("position", {})
                    })
                    
                except Exception as e:
                    return self._error_response(f"Error creating chart {i}: {str(e)}")
                
            else:
                return self._error_response(f"Chart {i} must have either chart_id or (chart_type and data)")
        
        # Create dashboard ID
        dashboard_id = f"dashboard_{int(time.time())}_{len(processed_charts)}"
        
        try:
            # Generate HTML for the dashboard
            html = self._generate_dashboard_html(layout, processed_charts, options)
            
            # Store in cache (only the structure, not all the HTML)
            self.visualization_cache[dashboard_id] = {
                "type": "dashboard",
                "layout": layout,
                "charts": [{"id": chart["id"], "position": chart["position"]} for chart in processed_charts],
                "options": options,
                "created_at": time.time()
            }
            
            logger.info(f"Created dashboard: {dashboard_id} with {len(processed_charts)} charts")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "dashboard_id",
                        "value": dashboard_id,
                        "type": "string"
                    },
                    {
                        "name": "html",
                        "value": html,
                        "type": "string"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 100 + (50 * len(processed_charts)),
                    "memory_used_mb": 5.0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            return self._error_response(f"Error creating dashboard: {str(e)}")
    
    async def transform_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform data for visualization.
        
        Args:
            parameters: Transformation parameters
                - data: Data to transform
                - transformations: List of transformations to apply
        
        Returns:
            Transformed data
        """
        # Validate required parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "transformations" not in parameters:
            return self._error_response("Transformations parameter is required")
        
        data = parameters["data"]
        transformations = parameters["transformations"]
        
        # Validate transformations
        if not isinstance(transformations, list):
            return self._error_response("Transformations parameter must be an array")
        
        # Process each transformation
        transformed_data = data
        
        for i, transformation in enumerate(transformations):
            if not isinstance(transformation, dict):
                return self._error_response(f"Transformation {i} must be an object")
            
            if "type" not in transformation:
                return self._error_response(f"Transformation {i} must have a type")
            
            try:
                transformed_data = self._apply_transformation(
                    transformed_data,
                    transformation["type"],
                    transformation.get("options", {})
                )
            except Exception as e:
                return self._error_response(f"Error applying transformation {i}: {str(e)}")
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "transformed_data",
                    "value": transformed_data,
                    "type": "any"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 30,
                "memory_used_mb": 1.0
            }
        }
    
    async def visualization_themes(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage visualization themes.
        
        Args:
            parameters: Theme parameters
                - action: Action to perform (get, set, list)
                - theme_name: Name of the theme (for get, set)
                - theme_config: Theme configuration (for set)
        
        Returns:
            Success indicator and theme information
        """
        # Validate required parameters
        if "action" not in parameters:
            return self._error_response("Action parameter is required")
        
        action = parameters["action"].lower()
        
        # Built-in themes
        built_in_themes = {
            "light": {
                "colors": ["#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f", "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab"],
                "background": "#ffffff",
                "text": "#333333",
                "grid": "#dddddd",
                "axis": "#999999"
            },
            "dark": {
                "colors": ["#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f", "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab"],
                "background": "#333333",
                "text": "#ffffff",
                "grid": "#555555",
                "axis": "#888888"
            },
            "pastel": {
                "colors": ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"],
                "background": "#f5f5f5",
                "text": "#333333",
                "grid": "#dddddd",
                "axis": "#999999"
            },
            "highcontrast": {
                "colors": ["#fafa6e", "#2A4858", "#f77f00", "#0077b6", "#d62828", "#007f5f", "#e9c46a", "#9c6ea5"],
                "background": "#000000",
                "text": "#ffffff",
                "grid": "#555555",
                "axis": "#888888"
            }
        }
        
        # Custom themes (would be stored in the cell's state)
        custom_themes = {}
        
        if action == "list":
            # List all available themes
            all_themes = {}
            all_themes.update(built_in_themes)
            all_themes.update(custom_themes)
            
            theme_list = [{"name": name, "built_in": name in built_in_themes} for name in all_themes.keys()]
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "themes",
                        "value": theme_list,
                        "type": "array"
                    }
                ]
            }
            
        elif action == "get":
            # Get a specific theme
            if "theme_name" not in parameters:
                return self._error_response("Theme name parameter is required for get action")
            
            theme_name = parameters["theme_name"]
            
            # Check built-in themes first, then custom themes
            if theme_name in built_in_themes:
                theme = built_in_themes[theme_name]
                is_built_in = True
            elif theme_name in custom_themes:
                theme = custom_themes[theme_name]
                is_built_in = False
            else:
                return self._error_response(f"Theme not found: {theme_name}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "themes",
                        "value": [{
                            "name": theme_name,
                            "built_in": is_built_in,
                            "config": theme
                        }],
                        "type": "array"
                    }
                ]
            }
            
        elif action == "set":
            # Set a custom theme
            if "theme_name" not in parameters:
                return self._error_response("Theme name parameter is required for set action")
            
            if "theme_config" not in parameters:
                return self._error_response("Theme configuration parameter is required for set action")
            
            theme_name = parameters["theme_name"]
            theme_config = parameters["theme_config"]
            
            # Validate theme configuration
            required_fields = ["colors", "background", "text", "grid", "axis"]
            for field in required_fields:
                if field not in theme_config:
                    return self._error_response(f"Theme configuration must include {field}")
            
            # Check if attempting to override a built-in theme
            if theme_name in built_in_themes:
                return self._error_response(f"Cannot override built-in theme: {theme_name}")
            
            # Store the custom theme
            custom_themes[theme_name] = theme_config
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "success",
                        "value": True,
                        "type": "boolean"
                    },
                    {
                        "name": "themes",
                        "value": [{
                            "name": theme_name,
                            "built_in": False,
                            "config": theme_config
                        }],
                        "type": "array"
                    }
                ]
            }
            
        else:
            return self._error_response(f"Unsupported action: {action}")
    
    def _validate_data_for_chart(self, chart_type: str, data: Any) -> None:
        """
        Validate data for a specific chart type.
        
        Args:
            chart_type: Type of chart
            data: Data to validate
            
        Raises:
            DataError: If the data is invalid for the chart type
        """
        # Basic validations
        if data is None:
            raise DataError("Data cannot be None")
        
        if chart_type in ["bar", "line", "area"]:
            # These charts require data with labels and datasets
            if not isinstance(data, dict):
                raise DataError("Data must be an object with labels and datasets")
            
            if "labels" not in data:
                raise DataError("Data must include labels array")
            
            if "datasets" not in data:
                raise DataError("Data must include datasets array")
            
            if not isinstance(data["labels"], list):
                raise DataError("Labels must be an array")
            
            if not isinstance(data["datasets"], list) or len(data["datasets"]) == 0:
                raise DataError("Datasets must be a non-empty array")
            
            for i, dataset in enumerate(data["datasets"]):
                if not isinstance(dataset, dict):
                    raise DataError(f"Dataset {i} must be an object")
                
                if "data" not in dataset:
                    raise DataError(f"Dataset {i} must include data array")
                
                if not isinstance(dataset["data"], list):
                    raise DataError(f"Dataset {i} data must be an array")
                
                if len(dataset["data"]) != len(data["labels"]):
                    raise DataError(f"Dataset {i} data length must match labels length")
        
        elif chart_type in ["pie", "doughnut", "radar", "polarArea"]:
            # These charts require data with labels and values
            if not isinstance(data, dict):
                raise DataError("Data must be an object with labels and data")
            
            if "labels" not in data:
                raise DataError("Data must include labels array")
            
            if "data" not in data:
                raise DataError("Data must include data array")
            
            if not isinstance(data["labels"], list):
                raise DataError("Labels must be an array")
            
            if not isinstance(data["data"], list):
                raise DataError("Data must be an array")
            
            if len(data["data"]) != len(data["labels"]):
                raise DataError("Data length must match labels length")
        
        elif chart_type in ["scatter", "bubble"]:
            # These charts require data with x and y coordinates
            if not isinstance(data, dict) or "datasets" not in data:
                raise DataError("Data must be an object with datasets array")
            
            if not isinstance(data["datasets"], list) or len(data["datasets"]) == 0:
                raise DataError("Datasets must be a non-empty array")
            
            for i, dataset in enumerate(data["datasets"]):
                if not isinstance(dataset, dict):
                    raise DataError(f"Dataset {i} must be an object")
                
                if "data" not in dataset:
                    raise DataError(f"Dataset {i} must include data array")
                
                if not isinstance(dataset["data"], list):
                    raise DataError(f"Dataset {i} data must be an array")
                
                for j, point in enumerate(dataset["data"]):
                    if not isinstance(point, dict):
                        raise DataError(f"Dataset {i} point {j} must be an object")
                    
                    if "x" not in point or "y" not in point:
                        raise DataError(f"Dataset {i} point {j} must include x and y coordinates")
        
        elif chart_type == "heatmap":
            # Heatmap requires matrix data
            if not isinstance(data, dict):
                raise DataError("Data must be an object with x, y, and values")
            
            if "x" not in data or "y" not in data or "values" not in data:
                raise DataError("Data must include x, y, and values arrays")
            
            if not isinstance(data["x"], list) or not isinstance(data["y"], list) or not isinstance(data["values"], list):
                raise DataError("x, y, and values must be arrays")
            
            if len(data["values"]) != len(data["y"]):
                raise DataError("Values must have the same number of rows as y labels")
            
            for row in data["values"]:
                if not isinstance(row, list) or len(row) != len(data["x"]):
                    raise DataError("Each row in values must be an array with the same length as x labels")
        
        elif chart_type == "candlestick":
            # Candlestick requires OHLC data
            if not isinstance(data, dict) or "data" not in data:
                raise DataError("Data must be an object with data array")
            
            if not isinstance(data["data"], list) or len(data["data"]) == 0:
                raise DataError("Data must be a non-empty array")
            
            for i, point in enumerate(data["data"]):
                if not isinstance(point, dict):
                    raise DataError(f"Point {i} must be an object")
                
                if not all(k in point for k in ["time", "open", "high", "low", "close"]):
                    raise DataError(f"Point {i} must include time, open, high, low, and close values")
    
    def _count_data_points(self, data: Any) -> int:
        """
        Count the number of data points in a dataset.
        
        Args:
            data: Data to count
            
        Returns:
            Number of data points
        """
        if isinstance(data, dict):
            if "datasets" in data and isinstance(data["datasets"], list):
                # Bar, line, area charts
                count = 0
                for dataset in data["datasets"]:
                    if isinstance(dataset, dict) and "data" in dataset and isinstance(dataset["data"], list):
                        count += len(dataset["data"])
                return count
            
            elif "data" in data and isinstance(data["data"], list):
                # Pie, doughnut charts
                if all(isinstance(x, dict) for x in data["data"]):
                    # Candlestick, complex data
                    return len(data["data"])
                else:
                    # Simple data
                    return len(data["data"])
            
            elif "values" in data and isinstance(data["values"], list):
                # Heatmap
                count = 0
                for row in data["values"]:
                    if isinstance(row, list):
                        count += len(row)
                return count
            
            return 0
        
        elif isinstance(data, list):
            return len(data)
        
        return 0
    
    def _process_chart_options(self, chart_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate chart options.
        
        Args:
            chart_type: Type of chart
            options: Chart options
            
        Returns:
            Processed options
        """
        # Start with default options
        processed_options = {
            "title": options.get("title", ""),
            "width": options.get("width", self.visualization_settings.get("default_chart_width", 800)),
            "height": options.get("height", self.visualization_settings.get("default_chart_height", 500)),
            "theme": options.get("theme", self.visualization_settings.get("default_theme", "light")),
            "animation": options.get("animation", self.visualization_settings.get("enable_animations", True)),
            "responsive": options.get("responsive", True),
            "maintainAspectRatio": options.get("maintainAspectRatio", True),
            "plugins": options.get("plugins", {}),
            "layout": options.get("layout", {}),
            "scales": options.get("scales", {})
        }
        
        # Add chart type specific defaults
        if chart_type in ["bar"]:
            processed_options.setdefault("indexAxis", options.get("indexAxis", "x"))
            processed_options.setdefault("barPercentage", options.get("barPercentage", 0.9))
            processed_options.setdefault("categoryPercentage", options.get("categoryPercentage", 0.8))
        
        elif chart_type in ["line", "area"]:
            processed_options.setdefault("tension", options.get("tension", 0.4))
            processed_options.setdefault("fill", options.get("fill", chart_type == "area"))
            processed_options.setdefault("borderWidth", options.get("borderWidth", 2))
            processed_options.setdefault("pointRadius", options.get("pointRadius", 3))
        
        elif chart_type in ["pie", "doughnut"]:
            processed_options.setdefault("cutout", options.get("cutout", chart_type == "doughnut" ? "50%" : "0%"))
            processed_options.setdefault("radius", options.get("radius", "100%"))
        
        elif chart_type in ["scatter", "bubble"]:
            processed_options.setdefault("showLine", options.get("showLine", False))
            processed_options.setdefault("pointRadius", options.get("pointRadius", chart_type == "bubble" ? 15 : 5))
            processed_options.setdefault("pointStyle", options.get("pointStyle", "circle"))
        
        elif chart_type == "heatmap":
            processed_options.setdefault("radius", options.get("radius", 0))
            processed_options.setdefault("colorScale", options.get("colorScale", "viridis"))
        
        # Ensure valid dimensions
        if processed_options["width"] <= 0:
            processed_options["width"] = self.visualization_settings.get("default_chart_width", 800)
        
        if processed_options["height"] <= 0:
            processed_options["height"] = self.visualization_settings.get("default_chart_height", 500)
        
        # Max dimensions
        max_width = 2000
        max_height = 2000
        
        if processed_options["width"] > max_width:
            processed_options["width"] = max_width
        
        if processed_options["height"] > max_height:
            processed_options["height"] = max_height
        
        return processed_options
    
    def _generate_chart_html(self, chart_type: str, data: Any, options: Dict[str, Any]) -> str:
        """
        Generate HTML for a chart.
        
        Args:
            chart_type: Type of chart
            data: Chart data
            options: Chart options
            
        Returns:
            HTML string for the chart
        """
        # Create a unique chart element ID
        chart_element_id = f"chart_{self._hash_data(data)[:8]}_{int(time.time())}"
        
        # Convert data to JSON string (safely)
        data_json = json.dumps(data)
        
        # Convert options to JSON string (safely)
        options_json = json.dumps(options)
        
        # Choose the right Chart.js initialization based on chart type
        chart_init = {
            "bar": "new Chart(ctx, { type: 'bar', data: chartData, options: chartOptions });",
            "line": "new Chart(ctx, { type: 'line', data: chartData, options: chartOptions });",
            "pie": "new Chart(ctx, { type: 'pie', data: { labels: chartData.labels, datasets: [{ data: chartData.data, backgroundColor: colorPalette }] }, options: chartOptions });",
            "doughnut": "new Chart(ctx, { type: 'doughnut', data: { labels: chartData.labels, datasets: [{ data: chartData.data, backgroundColor: colorPalette }] }, options: chartOptions });",
            "scatter": "new Chart(ctx, { type: 'scatter', data: chartData, options: chartOptions });",
            "area": "new Chart(ctx, { type: 'line', data: chartData, options: Object.assign({}, chartOptions, { elements: { line: { fill: true } } }) });",
            "bubble": "new Chart(ctx, { type: 'bubble', data: chartData, options: chartOptions });",
            "radar": "new Chart(ctx, { type: 'radar', data: { labels: chartData.labels, datasets: [{ data: chartData.data, backgroundColor: 'rgba(78, 121, 167, 0.2)', borderColor: colorPalette[0] }] }, options: chartOptions });",
            "polar": "new Chart(ctx, { type: 'polarArea', data: { labels: chartData.labels, datasets: [{ data: chartData.data, backgroundColor: colorPalette }] }, options: chartOptions });",
            "heatmap": self._generate_heatmap_code(chart_element_id, "chartData", "chartOptions"),
            "candlestick": self._generate_candlestick_code(chart_element_id, "chartData", "chartOptions"),
            "gauge": self._generate_gauge_code(chart_element_id, "chartData", "chartOptions"),
            "treemap": self._generate_treemap_code(chart_element_id, "chartData", "chartOptions"),
            "sankey": self._generate_sankey_code(chart_element_id, "chartData", "chartOptions"),
            "boxplot": self._generate_boxplot_code(chart_element_id, "chartData", "chartOptions"),
            "histogram": "new Chart(ctx, { type: 'bar', data: chartData, options: Object.assign({}, chartOptions, { scales: { x: { type: 'linear', offset: false, grid: { offset: false } } } }) });"
        }.get(chart_type)
        
        if not chart_init:
            chart_init = f"console.error('Unsupported chart type: {chart_type}');"
        
        # Set color palette based on theme
        theme = options.get("theme", "light")
        color_palette = self.visualization_settings.get("color_palette", [
            "#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f",
            "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab"
        ])
        
        # Generate the HTML
        html = f"""
        <div class="qcc-chart-container" style="width: {options['width']}px; height: {options['height']}px;">
            <canvas id="{chart_element_id}" width="{options['width']}" height="{options['height']}"></canvas>
        </div>
        
        <script>
        (function() {{
            // Get the canvas context
            const canvas = document.getElementById('{chart_element_id}');
            const ctx = canvas.getContext('2d');
            
            // Chart data
            const chartData = {data_json};
            
            // Chart options
            const chartOptions = {options_json};
            
            // Color palette
            const colorPalette = {json.dumps(color_palette)};
            
            // Apply colors to datasets if they don't have colors
            if (chartData.datasets) {{
                chartData.datasets.forEach((dataset, index) => {{
                    if (!dataset.backgroundColor) {{
                        dataset.backgroundColor = colorPalette[index % colorPalette.length];
                    }}
                    if (!dataset.borderColor && chartOptions.showLine !== false) {{
                        dataset.borderColor = colorPalette[index % colorPalette.length];
                    }}
                }});
            }}
            
            // Create the chart
            {chart_init}
        }})();
        </script>
        
        <style>
        .qcc-chart-container {{
            position: relative;
            margin: 0 auto;
            max-width: 100%;
        }}
        </style>
        """
        
        return html
    
    def _generate_dashboard_html(self, layout: Dict[str, Any], charts: List[Dict[str, Any]], options: Dict[str, Any]) -> str:
        """
        Generate HTML for a dashboard.
        
        Args:
            layout: Dashboard layout
            charts: List of charts
            options: Dashboard options
            
        Returns:
            HTML string for the dashboard
        """
        # Create a unique dashboard element ID
        dashboard_id = f"dashboard_{int(time.time())}_{len(charts)}"
        
        # Process layout options
        layout_type = layout.get("type", "grid")
        
        if layout_type == "grid":
            rows = layout.get("rows", 2)
            columns = layout.get("columns", 2)
            gap = layout.get("gap", 16)
            
            # Generate grid layout CSS
            grid_css = f"""
            .qcc-dashboard-grid {{
                display: grid;
                grid-template-columns: repeat({columns}, 1fr);
                grid-template-rows: repeat({rows}, 1fr);
                gap: {gap}px;
                width: 100%;
                height: 100%;
                padding: 16px;
            }}
            """
            
            # Position charts in the grid
            chart_html = ""
            for chart in charts:
                # Get position from chart or assign default
                position = chart.get("position", {})
                grid_row = position.get("row", 1)
                grid_column = position.get("column", 1)
                grid_row_span = position.get("row_span", 1)
                grid_column_span = position.get("column_span", 1)
                
                # Ensure valid values
                grid_row = max(1, min(grid_row, rows))
                grid_column = max(1, min(grid_column, columns))
                grid_row_span = max(1, min(grid_row_span, rows - grid_row + 1))
                grid_column_span = max(1, min(grid_column_span, columns - grid_column + 1))
                
                # Add chart to layout
                chart_html += f"""
                <div class="qcc-dashboard-item" style="grid-row: {grid_row} / span {grid_row_span}; grid-column: {grid_column} / span {grid_column_span};">
                    <div class="qcc-dashboard-chart">
                        {chart["html"]}
                    </div>
                </div>
                """
            
            # Complete grid layout
            layout_html = f"""
            <div class="qcc-dashboard-grid">
                {chart_html}
            </div>
            """
            
        elif layout_type == "flex":
            direction = layout.get("direction", "row")
            wrap = layout.get("wrap", True)
            justify = layout.get("justify", "space-between")
            align = layout.get("align", "flex-start")
            gap = layout.get("gap", 16)
            
            # Generate flex layout CSS
            flex_css = f"""
            .qcc-dashboard-flex {{
                display: flex;
                flex-direction: {direction};
                flex-wrap: {wrap and 'wrap' or 'nowrap'};
                justify-content: {justify};
                align-items: {align};
                gap: {gap}px;
                width: 100%;
                padding: 16px;
            }}
            """
            
            # Position charts in the flex container
            chart_html = ""
            for chart in charts:
                # Get position from chart or assign default
                position = chart.get("position", {})
                flex_basis = position.get("basis", "0")
                flex_grow = position.get("grow", 1)
                flex_shrink = position.get("shrink", 1)
                align_self = position.get("align", "auto")
                
                # Add chart to layout
                chart_html += f"""
                <div class="qcc-dashboard-item" style="flex: {flex_grow} {flex_shrink} {flex_basis}; align-self: {align_self};">
                    <div class="qcc-dashboard-chart">
                        {chart["html"]}
                    </div>
                </div>
                """
            
            # Complete flex layout
            layout_html = f"""
            <div class="qcc-dashboard-flex">
                {chart_html}
            </div>
            """
            
        else:
            # Fallback to simple stack layout
            chart_html = ""
            for chart in charts:
                chart_html += f"""
                <div class="qcc-dashboard-item">
                    <div class="qcc-dashboard-chart">
                        {chart["html"]}
                    </div>
                </div>
                """
            
            # Complete stack layout
            layout_html = f"""
            <div class="qcc-dashboard-stack">
                {chart_html}
            </div>
            """
            
            # Simple stack layout CSS
            grid_css = """
            .qcc-dashboard-stack {
                display: flex;
                flex-direction: column;
                gap: 16px;
                width: 100%;
                padding: 16px;
            }
            """
        
        # Process theme
        theme = options.get("theme", "light")
        theme_css = ".qcc-dashboard { background-color: #ffffff; color: #333333; }"
        if theme == "dark":
            theme_css = ".qcc-dashboard { background-color: #333333; color: #ffffff; }"
        
        # Generate the complete dashboard HTML
        dashboard_html = f"""
        <div id="{dashboard_id}" class="qcc-dashboard qcc-dashboard-{theme}">
            <div class="qcc-dashboard-header">
                <h2 class="qcc-dashboard-title">{options.get('title', 'Dashboard')}</h2>
                {f'<div class="qcc-dashboard-description">{options.get("description", "")}</div>' if options.get("description") else ''}
            </div>
            
            {layout_html}
            
            {f'<div class="qcc-dashboard-footer">{options.get("footer", "")}</div>' if options.get("footer") else ''}
        </div>
        
        <style>
        .qcc-dashboard {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
        }
        
        .qcc-dashboard-header {
            padding: 16px;
            border-bottom: 1px solid #ddd;
        }
        
        .qcc-dashboard-title {
            margin: 0 0 8px 0;
            font-size: 24px;
            font-weight: 500;
        }
        
        .qcc-dashboard-description {
            margin: 0;
            font-size: 14px;
            color: #666;
        }
        
        .qcc-dashboard-item {
            background-color: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .qcc-dashboard-dark .qcc-dashboard-item {
            background-color: #444;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
        }
        
        .qcc-dashboard-chart {
            padding: 8px;
        }
        
        .qcc-dashboard-footer {
            padding: 16px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
            text-align: center;
        }
        
        /* Theme specific styles */
        {theme_css}
        
        /* Layout specific styles */
        {grid_css if layout_type == "grid" else flex_css if layout_type == "flex" else ""}
        </style>
        """
        
        return dashboard_html
    
    def _apply_transformation(self, data: Any, transformation_type: str, options: Dict[str, Any]) -> Any:
        """
        Apply a data transformation.
        
        Args:
            data: Data to transform
            transformation_type: Type of transformation
            options: Transformation options
            
        Returns:
            Transformed data
        """
        if transformation_type == "filter":
            # Filter data based on condition
            field = options.get("field")
            operator = options.get("operator", "eq")
            value = options.get("value")
            
            if field is None or value is None:
                return data
            
            # Handle different data structures
            if isinstance(data, list):
                return self._filter_list(data, field, operator, value)
            
            elif isinstance(data, dict):
                if "datasets" in data and isinstance(data["datasets"], list):
                    # Filter dataset values
                    return {
                        **data,
                        "datasets": [
                            {
                                **dataset,
                                "data": self._filter_list(dataset["data"], field, operator, value)
                            }
                            for dataset in data["datasets"]
                        ]
                    }
                
                elif "data" in data and isinstance(data["data"], list):
                    # Filter data array
                    return {
                        **data,
                        "data": self._filter_list(data["data"], field, operator, value)
                    }
            
            return data
        
        elif transformation_type == "sort":
            # Sort data
            field = options.get("field")
            order = options.get("order", "asc")
            
            if field is None:
                return data
            
            # Handle different data structures
            if isinstance(data, list):
                return self._sort_list(data, field, order)
            
            elif isinstance(data, dict):
                if "datasets" in data and isinstance(data["datasets"], list):
                    # Sort dataset values (note: this only sorts within each dataset)
                    return {
                        **data,
                        "datasets": [
                            {
                                **dataset,
                                "data": self._sort_list(dataset["data"], field, order)
                            }
                            for dataset in data["datasets"]
                        ]
                    }
                
                elif "data" in data and isinstance(data["data"], list):
                    # Sort data array
                    return {
                        **data,
                        "data": self._sort_list(data["data"], field, order)
                    }
            
            return data
        
        elif transformation_type == "aggregate":
            # Aggregate data
            group_by = options.get("group_by")
            aggregation = options.get("aggregation", "sum")
            target_field = options.get("target_field")
            
            if group_by is None or target_field is None:
                return data
            
            # Only handle list of objects for aggregation
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return self._aggregate_data(data, group_by, aggregation, target_field)
            
            return data
        
        elif transformation_type == "limit":
            # Limit number of items
            count = options.get("count", 10)
            
            if count <= 0:
                return data
            
            # Handle different data structures
            if isinstance(data, list):
                return data[:count]
            
            elif isinstance(data, dict):
                if "labels" in data and "datasets" in data:
                    # Limit bar/line chart data
                    labels = data["labels"][:count]
                    datasets = [
                        {
                            **dataset,
                            "data": dataset["data"][:count]
                        }
                        for dataset in data["datasets"]
                    ]
                    
                    return {
                        **data,
                        "labels": labels,
                        "datasets": datasets
                    }
                
                elif "labels" in data and "data" in data:
                    # Limit pie/doughnut chart data
                    return {
                        **data,
                        "labels": data["labels"][:count],
                        "data": data["data"][:count]
                    }
            
            return data
        
        elif transformation_type == "math":
            # Apply mathematical operation
            operation = options.get("operation")
            fields = options.get("fields", [])
            result_field = options.get("result_field", "result")
            
            if operation is None or not fields:
                return data
            
            # Only handle list of objects for math operations
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return self._apply_math_operation(data, operation, fields, result_field)
            
            return data
        
        elif transformation_type == "format":
            # Format data values
            format_type = options.get("format_type")
            field = options.get("field")
            format_options = options.get("format_options", {})
            
            if format_type is None or field is None:
                return data
            
            # Handle different data structures
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return self._format_values(data, field, format_type, format_options)
            
            return data
        
        elif transformation_type == "restructure":
            # Restructure data format (e.g., array to chart data)
            target_format = options.get("target_format")
            mappings = options.get("mappings", {})
            
            if target_format is None:
                return data
            
            # Convert to various chart data formats
            if target_format == "bar" or target_format == "line":
                return self._convert_to_bar_line_format(data, mappings)
            
            elif target_format == "pie":
                return self._convert_to_pie_format(data, mappings)
            
            elif target_format == "scatter":
                return self._convert_to_scatter_format(data, mappings)
            
            return data
        
        # Default: return data unchanged
        return data
    
    def _filter_list(self, data_list: List, field: str, operator: str, value: Any) -> List:
        """
        Filter a list based on a condition.
        
        Args:
            data_list: List to filter
            field: Field to filter on
            operator: Operator to use
            value: Value to compare against
            
        Returns:
            Filtered list
        """
        operators = {
            "eq": lambda x, y: x == y,
            "ne": lambda x, y: x != y,
            "gt": lambda x, y: x > y,
            "lt": lambda x, y: x < y,
            "gte": lambda x, y: x >= y,
            "lte": lambda x, y: x <= y,
            "in": lambda x, y: x in y if isinstance(y, list) else False,
            "contains": lambda x, y: y in x if isinstance(x, (str, list)) else False
        }
        
        # Use the correct comparison function
        compare = operators.get(operator, operators["eq"])
        
        # Handle different data structures
        if all(isinstance(item, dict) for item in data_list):
            # List of objects
            return [
                item for item in data_list
                if field in item and compare(item[field], value)
            ]
        
        # Simple list of values
        return [
            item for item in data_list
            if compare(item, value)
        ]
    
    def _sort_list(self, data_list: List, field: str, order: str) -> List:
        """
        Sort a list.
        
        Args:
            data_list: List to sort
            field: Field to sort by
            order: Sort order (asc or desc)
            
        Returns:
            Sorted list
        """
        reverse = order.lower() == "desc"
        
        # Handle different data structures
        if all(isinstance(item, dict) for item in data_list):
            # List of objects
            return sorted(
                data_list,
                key=lambda item: item.get(field, 0),
                reverse=reverse
            )
        
        # Simple list of values
        return sorted(data_list, reverse=reverse)
    
    def _aggregate_data(self, data_list: List[Dict], group_by: str, aggregation: str, target_field: str) -> List[Dict]:
        """
        Aggregate data by a field.
        
        Args:
            data_list: Data to aggregate
            group_by: Field to group by
            aggregation: Aggregation function
            target_field: Field to aggregate
            
        Returns:
            Aggregated data
        """
        # Group data
        groups = {}
        
        for item in data_list:
            if group_by not in item:
                continue
            
            group_key = item[group_by]
            
            if group_key not in groups:
                groups[group_key] = []
            
            groups[group_key].append(item)
        
        # Aggregate each group
        result = []
        
        for group_key, group_items in groups.items():
            if aggregation == "sum":
                value = sum(item.get(target_field, 0) for item in group_items)
            elif aggregation == "avg":
                values = [item.get(target_field, 0) for item in group_items]
                value = sum(values) / len(values) if values else 0
            elif aggregation == "min":
                value = min((item.get(target_field, float('inf')) for item in group_items), default=0)
            elif aggregation == "max":
                value = max((item.get(target_field, float('-inf')) for item in group_items), default=0)
            elif aggregation == "count":
                value = len(group_items)
            else:
                value = 0
            
            result.append({
                group_by: group_key,
                target_field: value,
                "count": len(group_items)
            })
        
        return result
    
    def _apply_math_operation(self, data_list: List[Dict], operation: str, fields: List[str], result_field: str) -> List[Dict]:
        """
        Apply a mathematical operation to fields.
        
        Args:
            data_list: Data to process
            operation: Operation to apply
            fields: Fields to operate on
            result_field: Field to store result
            
        Returns:
            Processed data
        """
        return [
            {
                **item,
                result_field: self._calculate_math_operation(item, operation, fields)
            }
            for item in data_list
        ]
    
    def _calculate_math_operation(self, item: Dict, operation: str, fields: List[str]) -> float:
        """
        Calculate a mathematical operation on an item.
        
        Args:
            item: Data item
            operation: Operation to apply
            fields: Fields to operate on
            
        Returns:
            Result of operation
        """
        # Get values from fields
        values = [item.get(field, 0) for field in fields]
        
        # Apply operation
        if operation == "sum":
            return sum(values)
        elif operation == "avg":
            return sum(values) / len(values) if values else 0
        elif operation == "min":
            return min(values) if values else 0
        elif operation == "max":
            return max(values) if values else 0
        elif operation == "product":
            result = 1
            for value in values:
                result *= value
            return result
        elif operation == "diff":
            if len(values) >= 2:
                return values[0] - sum(values[1:])
            return 0
        
        return 0
    
    def _format_values(self, data_list: List[Dict], field: str, format_type: str, format_options: Dict[str, Any]) -> List[Dict]:
        """
        Format values in a field.
        
        Args:
            data_list: Data to process
            field: Field to format
            format_type: Type of formatting
            format_options: Formatting options
            
        Returns:
            Processed data
        """
        return [
            {
                **item,
                field: self._format_value(item.get(field), format_type, format_options)
            }
            for item in data_list
        ]
    
    def _format_value(self, value: Any, format_type: str, format_options: Dict[str, Any]) -> Any:
        """
        Format a single value.
        
        Args:
            value: Value to format
            format_type: Type of formatting
            format_options: Formatting options
            
        Returns:
            Formatted value
        """
        if format_type == "number":
            # Format number
            try:
                decimal_places = format_options.get("decimal_places", 2)
                thousands_separator = format_options.get("thousands_separator", ",")
                
                if not isinstance(value, (int, float)):
                    return value
                
                # Format number with specified decimal places
                formatted = format(value, f",.{decimal_places}f")
                
                # Replace default separator with specified separator
                if thousands_separator != ",":
                    formatted = formatted.replace(",", thousands_separator)
                
                return formatted
            
            except Exception:
                return value
        
        elif format_type == "percentage":
            # Format as percentage
            try:
                if not isinstance(value, (int, float)):
                    return value
                
                decimal_places = format_options.get("decimal_places", 2)
                multiply = format_options.get("multiply", True)
                
                if multiply:
                    value = value * 100
                
                return f"{value:.{decimal_places}f}%"
            
            except Exception:
                return value
        
        elif format_type == "date":
            # Format date
            try:
                # In a real implementation, we would use a date formatting library
                # For simplicity, we'll just return the value
                return value
            
            except Exception:
                return value
        
        elif format_type == "currency":
            # Format as currency
            try:
                if not isinstance(value, (int, float)):
                    return value
                
                currency_symbol = format_options.get("currency_symbol", "$")
                decimal_places = format_options.get("decimal_places", 2)
                
                return f"{currency_symbol}{value:.{decimal_places}f}"
            
            except Exception:
                return value
        
        # Default: return unchanged
        return value
    
    def _convert_to_bar_line_format(self, data: List[Dict], mappings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data to bar/line chart format.
        
        Args:
            data: Data to convert
            mappings: Field mappings
            
        Returns:
            Converted data
        """
        # Validate mappings
        if "labels" not in mappings:
            raise DataError("labels field mapping is required")
        
        if "values" not in mappings:
            raise DataError("values field mapping is required")
        
        # Get labels and values fields
        labels_field = mappings["labels"]
        values_field = mappings["values"]
        series_field = mappings.get("series")
        
        # Simple case: no series field
        if not series_field:
            # Extract labels and values
            labels = []
            values = []
            
            for item in data:
                if labels_field in item and values_field in item:
                    labels.append(item[labels_field])
                    values.append(item[values_field])
            
            return {
                "labels": labels,
                "datasets": [
                    {
                        "label": mappings.get("datasetLabel", "Data"),
                        "data": values
                    }
                ]
            }
        
        # Series case: group by series field
        else:
            # Group data by series
            series_groups = {}
            all_labels = set()
            
            for item in data:
                if labels_field in item and values_field in item and series_field in item:
                    series_value = item[series_field]
                    label_value = item[labels_field]
                    
                    if series_value not in series_groups:
                        series_groups[series_value] = {}
                    
                    series_groups[series_value][label_value] = item[values_field]
                    all_labels.add(label_value)
            
            # Sort labels
            sorted_labels = sorted(all_labels)
            
            # Create datasets
            datasets = []
            
            for series_value, series_data in series_groups.items():
                # Get values for each label
                values = [series_data.get(label, 0) for label in sorted_labels]
                
                datasets.append({
                    "label": str(series_value),
                    "data": values
                })
            
            return {
                "labels": sorted_labels,
                "datasets": datasets
            }
    
    def _convert_to_pie_format(self, data: List[Dict], mappings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data to pie chart format.
        
        Args:
            data: Data to convert
            mappings: Field mappings
            
        Returns:
            Converted data
        """
        # Validate mappings
        if "labels" not in mappings:
            raise DataError("labels field mapping is required")
        
        if "values" not in mappings:
            raise DataError("values field mapping is required")
        
        # Get labels and values fields
        labels_field = mappings["labels"]
        values_field = mappings["values"]
        
        # Extract labels and values
        labels = []
        values = []
        
        for item in data:
            if labels_field in item and values_field in item:
                labels.append(item[labels_field])
                values.append(item[values_field])
        
        return {
            "labels": labels,
            "data": values
        }
    
    def _convert_to_scatter_format(self, data: List[Dict], mappings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data to scatter chart format.
        
        Args:
            data: Data to convert
            mappings: Field mappings
            
        Returns:
            Converted data
        """
        # Validate mappings
        if "x" not in mappings:
            raise DataError("x field mapping is required")
        
        if "y" not in mappings:
            raise DataError("y field mapping is required")
        
        # Get field mappings
        x_field = mappings["x"]
        y_field = mappings["y"]
        series_field = mappings.get("series")
        r_field = mappings.get("r")  # For bubble charts
        
        # Simple case: no series field
        if not series_field:
            # Extract points
            points = []
            
            for item in data:
                if x_field in item and y_field in item:
                    point = {
                        "x": item[x_field],
                        "y": item[y_field]
                    }
                    
                    # Add radius for bubble charts
                    if r_field and r_field in item:
                        point["r"] = item[r_field]
                    
                    points.append(point)
            
            return {
                "datasets": [
                    {
                        "label": mappings.get("datasetLabel", "Data"),
                        "data": points
                    }
                ]
            }
        
        # Series case: group by series field
        else:
            # Group data by series
            series_groups = {}
            
            for item in data:
                if x_field in item and y_field in item and series_field in item:
                    series_value = item[series_field]
                    
                    if series_value not in series_groups:
                        series_groups[series_value] = []
                    
                    point = {
                        "x": item[x_field],
                        "y": item[y_field]
                    }
                    
                    # Add radius for bubble charts
                    if r_field and r_field in item:
                        point["r"] = item[r_field]
                    
                    series_groups[series_value].append(point)
            
            # Create datasets
            datasets = []
            
            for series_value, points in series_groups.items():
                datasets.append({
                    "label": str(series_value),
                    "data": points
                })
            
            return {
                "datasets": datasets
            }
    
    def _generate_heatmap_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate code for heatmap chart.
        
        Args:
            chart_id: Chart element ID
            data_var: Data variable name
            options_var: Options variable name
            
        Returns:
            JavaScript code
        """
        return f"""
        // Create custom heatmap chart
        (() => {{
            const ctx = document.getElementById('{chart_id}').getContext('2d');
            
            // Get x, y, and values from data
            const x = {data_var}.x;
            const y = {data_var}.y;
            const values = {data_var}.values;
            
            // Calculate min and max values
            let min = Infinity;
            let max = -Infinity;
            
            for (const row of values) {{
                for (const value of row) {{
                    if (value < min) min = value;
                    if (value > max) max = value;
                }}
            }}
            
            // Create a color scale function
            const colorScale = value => {{
                const normalizedValue = (value - min) / (max - min);
                const r = Math.round(normalizedValue * 255);
                const b = Math.round(255 - normalizedValue * 255);
                return `rgba(${{r}}, 0, ${{b}}, 0.8)`;
            }};
            
            // Create heatmap dataset
            const datasets = [];
            
            for (let i = 0; i < y.length; i++) {{
                for (let j = 0; j < x.length; j++) {{
                    datasets.push({{
                        label: `${{y[i]}}, ${{x[j]}}: ${{values[i][j]}}`,
                        data: [{{
                            x: j,
                            y: i,
                            r: 15,
                            v: values[i][j]
                        }}],
                        backgroundColor: colorScale(values[i][j])
                    }});
                }}
            }}
            
            // Create heatmap chart
            new Chart(ctx, {{
                type: 'bubble',
                data: {{
                    datasets
                }},
                options: {{
                    ...(({options_var}) || {{}}),
                    scales: {{
                        x: {{
                            type: 'category',
                            labels: x,
                            grid: {{
                                display: false
                            }}
                        }},
                        y: {{
                            type: 'category',
                            labels: y,
                            grid: {{
                                display: false
                            }},
                            ticks: {{
                                reverse: true
                            }}
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const v = context.raw.v;
                                    return `Value: ${{v}}`;
                                }}
                            }}
                        }},
                        legend: {{
                            display: false
                        }}
                    }}
                }}
            }});
        }})();
        """
    
    def _generate_candlestick_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate code for candlestick chart.
        
        Args:
            chart_id: Chart element ID
            data_var: Data variable name
            options_var: Options variable name
            
        Returns:
            JavaScript code
        """
        return f"""
        // Create custom candlestick chart
        (() => {{
            const ctx = document.getElementById('{chart_id}').getContext('2d');
            
            // Get data points
            const dataPoints = {data_var}.data;
            
            // Process data for candlestick chart
            const labels = dataPoints.map(point => point.time);
            const ohlc = dataPoints.map(point => ({{
                o: point.open,
                h: point.high,
                l: point.low,
                c: point.close
            }}));
            
            // Create dataset
            const up = (ctx, value) => value.o <= value.c ? 'rgba(75, 192, 192, 1)' : 'rgba(255, 99, 132, 1)';
            const down = (ctx, value) => value.o > value.c ? 'rgba(75, 192, 192, 1)' : 'rgba(255, 99, 132, 1)';
            
            // Create candlestick chart
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels,
                    datasets: [
                        {{
                            label: 'OHLC',
                            data: ohlc,
                            backgroundColor: up,
                            borderColor: down,
                            borderWidth: 2
                        }}
                    ]
                }},
                options: {{
                    ...(({options_var}) || {{}}),
                    parsing: {{
                        xAxisKey: 'time',
                        yAxisKey: 'o'
                    }},
                    scales: {{
                        y: {{
                            grace: '10%',
                            grid: {{
                                color: 'rgba(0, 0, 0, 0.1)'
                            }}
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const value = context.raw;
                                    return [
                                        `Open: ${{value.o}}`,
                                        `High: ${{value.h}}`,
                                        `Low: ${{value.l}}`,
                                        `Close: ${{value.c}}`
                                    ];
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }})();
        """
    
    def _generate_gauge_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate code for gauge chart.
        
        Args:
            chart_id: Chart element ID
            data_var: Data variable name
            options_var: Options variable name
            
        Returns:
            JavaScript code
        """
        return f"""
        // Create custom gauge chart
        (() => {{
            const ctx = document.getElementById('{chart_id}').getContext('2d');
            
            // Get value and options
            const value = {data_var}.value || 0;
            const min = {data_var}.min || 0;
            const max = {data_var}.max || 100;
            const title = {data_var}.title || 'Gauge';
            
            // Calculate percentage
            const percentage = (value - min) / (max - min) * 100;
            
            // Define colors based on value
            const getColor = pct => {{
                if (pct < 30) return '#4CAF50';  // Green
                if (pct < 70) return '#FFC107';  // Amber
                return '#F44336';                // Red
            }};
            
            const color = getColor(percentage);
            
            // Create gauge chart using doughnut chart
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    datasets: [{{
                        data: [percentage, 100 - percentage],
                        backgroundColor: [color, '#ECEFF1'],
                        borderWidth: 0,
                        circumference: 180,
                        rotation: -90
                    }}]
                }},
                options: {{
                    ...(({options_var}) || {{}}),
                    cutout: '80%',
                    plugins: {{
                        tooltip: {{ enabled: false }},
                        legend: {{ display: false }},
                        title: {{
                            display: true,
                            text: title,
                            position: 'bottom',
                            font: {{
                                size: 16
                            }}
                        }}
                    }}
                }}
            }});
            
            // Add needle and value
            Chart.register({{
                id: 'gaugeNeedle',
                afterDatasetDraw(chart) {{
                    const {{ctx, data, chartArea}} = chart;
                    
                    ctx.save();
                    
                    // Draw value text
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = 'bold 24px Arial';
                    ctx.fillStyle = '#333';
                    ctx.fillText(value, chartArea.left + chartArea.width / 2, chartArea.top + chartArea.height * 0.6);
                    
                    // Draw min, max values
                    ctx.font = '12px Arial';
                    ctx.fillText(min, chartArea.left + chartArea.width * 0.1, chartArea.top + chartArea.height * 0.85);
                    ctx.fillText(max, chartArea.left + chartArea.width * 0.9, chartArea.top + chartArea.height * 0.85);
                    
                    // Draw needle
                    const needleLength = chartArea.height * 0.35;
                    const needleWidth = 5;
                    const angle = Math.PI * (1 - percentage / 100);
                    
                    const cx = chartArea.left + chartArea.width / 2;
                    const cy = chartArea.top + chartArea.height * 0.7;
                    
                    const x = cx + needleLength * Math.cos(angle);
                    const y = cy - needleLength * Math.sin(angle);
                    
                    ctx.beginPath();
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(x, y);
                    ctx.strokeStyle = '#666';
                    ctx.lineWidth = needleWidth;
                    ctx.stroke();
                    
                    // Draw needle center
                    ctx.beginPath();
                    ctx.arc(cx, cy, needleWidth * 2, 0, Math.PI * 2);
                    ctx.fillStyle = '#666';
                    ctx.fill();
                    
                    ctx.restore();
                }}
            }});
        }})();
        """
    
    def _generate_treemap_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate code for treemap chart.
        
        Args:
            chart_id: Chart element ID
            data_var: Data variable name
            options_var: Options variable name
            
        Returns:
            JavaScript code
        """
        return f"""
        // Create custom treemap chart
        (() => {{
            const canvas = document.getElementById('{chart_id}');
            const ctx = canvas.getContext('2d');
            
            // Get hierarchical data
            const data = {data_var}.data || [];
            
            // Create treemap layout algorithm
            function createTreemap(data, width, height) {{
                // Sort data by value descending
                const sortedData = [...data].sort((a, b) => b.value - a.value);
                
                // Normalize values to fit canvas
                const totalValue = sortedData.reduce((sum, item) => sum + item.value, 0);
                const normalizedData = sortedData.map(item => ({{
                    ...item,
                    normalizedValue: item.value / totalValue * width * height
                }}));
                
                // Simple treemap algorithm (not optimal but works for simple cases)
                const rects = [];
                let currentX = 0;
                let currentY = 0;
                let rowHeight = 0;
                let remainingWidth = width;
                
                for (const item of normalizedData) {{
                    const rectWidth = Math.floor(item.normalizedValue / height);
                    const rectHeight = Math.floor(item.normalizedValue / rectWidth);
                    
                    if (rectWidth > remainingWidth) {{
                        // Move to next row
                        currentX = 0;
                        currentY += rowHeight;
                        rowHeight = 0;
                        remainingWidth = width;
                    }}
                    
                    // Add rectangle
                    rects.push({{
                        x: currentX,
                        y: currentY,
                        width: Math.min(rectWidth, remainingWidth),
                        height: rectHeight,
                        name: item.name,
                        value: item.value,
                        color: item.color || getRandomColor()
                    }});
                    
                    // Update position
                    currentX += rectWidth;
                    remainingWidth -= rectWidth;
                    rowHeight = Math.max(rowHeight, rectHeight);
                }}
                
                return rects;
            }}
            
            // Helper to get random color
            function getRandomColor() {{
                const letters = '0123456789ABCDEF';
                let color = '#';
                for (let i = 0; i < 6; i++) {{
                    color += letters[Math.floor(Math.random() * 16)];
                }}
                return color;
            }}
            
            // Draw treemap
            function drawTreemap() {{
                // Clear canvas
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Create treemap layout
                const rects = createTreemap(data, canvas.width, canvas.height);
                
                // Draw rectangles
                for (const rect of rects) {{
                    // Draw rectangle
                    ctx.beginPath();
                    ctx.rect(rect.x, rect.y, rect.width, rect.height);
                    ctx.fillStyle = rect.color;
                    ctx.fill();
                    ctx.strokeStyle = '#fff';
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    
                    // Draw text
                    ctx.fillStyle = '#fff';
                    ctx.font = '12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    // Only draw text if rectangle is big enough
                    if (rect.width > 40 && rect.height > 30) {{
                        ctx.fillText(
                            rect.name,
                            rect.x + rect.width / 2,
                            rect.y + rect.height / 2 - 6
                        );
                        
                        ctx.fillText(
                            rect.value,
                            rect.x + rect.width / 2,
                            rect.y + rect.height / 2 + 10
                        );
                    }}
                }}
                
                // Add tooltip handling
                canvas.onmousemove = event => {{
                    const rect = canvas.getBoundingClientRect();
                    const x = event.clientX - rect.left;
                    const y = event.clientY - rect.top;
                    
                    // Find rectangle under cursor
                    for (const r of rects) {{
                        if (x >= r.x && x <= r.x + r.width && y >= r.y && y <= r.y + r.height) {{
                            canvas.title = `${{r.name}}: ${{r.value}}`;
                            return;
                        }}
                    }}
                    
                    canvas.title = '';
                }};
            }}
            
            // Initial draw
            drawTreemap();
            
            // Handle resize
            window.addEventListener('resize', drawTreemap);
        }})();
        """
    
    def _generate_sankey_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a Sankey diagram.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the Sankey diagram
        """
        code = f"""
        google.charts.load("current", {{packages:["sankey"]}});
        google.charts.setOnLoadCallback(drawChart);

        function drawChart() {{
            var data = new google.visualization.DataTable();
            data.addColumn('string', 'From');
            data.addColumn('string', 'To');
            data.addColumn('number', 'Weight');
            data.addRows({data_var});

            var chart = new google.visualization.Sankey(document.getElementById('{chart_id}'));
            chart.draw(data, {options_var});
        }}
        """
        return code
    
    def _generate_treemap_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a treemap visualization.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the treemap
        """
        code = f"""
        google.charts.load('current', {{'packages':['treemap']}});
        google.charts.setOnLoadCallback(drawChart);

        function drawChart() {{
            var data = new google.visualization.DataTable();
            data.addColumn('string', 'ID');
            data.addColumn('string', 'Parent');
            data.addColumn('number', 'Value');
            data.addRows({data_var});

            var tree = new google.visualization.TreeMap(document.getElementById('{chart_id}'));
            tree.draw(data, {options_var});
        }}
        """
        return code
    
    def _generate_timeline_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a timeline visualization.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the timeline
        """
        code = f"""
        google.charts.load('current', {{'packages':['timeline']}});
        google.charts.setOnLoadCallback(drawChart);

        function drawChart() {{
            var container = document.getElementById('{chart_id}');
            var chart = new google.visualization.Timeline(container);
            var dataTable = new google.visualization.DataTable();

            dataTable.addColumn({{ type: 'string', id: 'RowLabel' }});
            dataTable.addColumn({{ type: 'string', id: 'Name' }});
            dataTable.addColumn({{ type: 'date', id: 'Start' }});
            dataTable.addColumn({{ type: 'date', id: 'End' }});
            dataTable.addRows({data_var});

            chart.draw(dataTable, {options_var});
        }}
        """
        return code
    
    def _generate_calendar_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a calendar visualization.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the calendar
        """
        code = f"""
        google.charts.load("current", {{packages:["calendar"]}});
        google.charts.setOnLoadCallback(drawChart);

        function drawChart() {{
            var dataTable = new google.visualization.DataTable();
            dataTable.addColumn({{ type: 'date', id: 'Date' }});
            dataTable.addColumn({{ type: 'number', id: 'Value' }});
            dataTable.addRows({data_var});

            var chart = new google.visualization.Calendar(document.getElementById('{chart_id}'));
            chart.draw(dataTable, {options_var});
        }}
        """
        return code
    
    def _generate_network_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a network visualization.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the network diagram
        """
        code = f"""
        var container = document.getElementById('{chart_id}');
        var nodes = new vis.DataSet({data_var}.nodes);
        var edges = new vis.DataSet({data_var}.edges);
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var network = new vis.Network(container, data, {options_var});
        
        // Handle selection events
        network.on("selectNode", function(params) {{
            if (params.nodes.length > 0) {{
                var selectedNodeId = params.nodes[0];
                if (window.onNodeSelected) {{
                    window.onNodeSelected(selectedNodeId);
                }}
            }}
        }});
        """
        return code
    
    def _generate_heatmap_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a heatmap visualization.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the heatmap
        """
        code = f"""
        var data = {{
            z: {data_var}.values,
            x: {data_var}.x,
            y: {data_var}.y,
            type: 'heatmap',
            colorscale: {data_var}.colorscale || 'Viridis'
        }};

        var layout = {options_var};
        
        Plotly.newPlot('{chart_id}', [data], layout);
        """
        return code
    
    def _generate_word_cloud_code(self, chart_id: str, data_var: str, options_var: str) -> str:
        """
        Generate the JavaScript code for a word cloud visualization.
        
        Args:
            chart_id: Unique ID for the chart container
            data_var: JavaScript variable name containing the data
            options_var: JavaScript variable name containing options
            
        Returns:
            JavaScript code to render the word cloud
        """
        code = f"""
        var layout = d3.layout.cloud()
            .size([{options_var}.width || 500, {options_var}.height || 500])
            .words({data_var})
            .padding(5)
            .rotate(function() {{ return ~~(Math.random() * 2) * 90; }})
            .font({options_var}.font || "Arial")
            .fontSize(function(d) {{ return d.size; }})
            .on("end", draw);

        layout.start();

        function draw(words) {{
            d3.select("#{chart_id}")
                .append("svg")
                .attr("width", layout.size()[0])
                .attr("height", layout.size()[1])
                .append("g")
                .attr("transform", "translate(" + layout.size()[0] / 2 + "," + layout.size()[1] / 2 + ")")
                .selectAll("text")
                .data(words)
                .enter().append("text")
                .style("font-size", function(d) {{ return d.size + "px"; }})
                .style("font-family", {options_var}.font || "Arial")
                .style("fill", function(d, i) {{ 
                    return {options_var}.colors ? {options_var}.colors[i % {options_var}.colors.length] : d3.schemeCategory10[i % 10]; 
                }})
                .attr("text-anchor", "middle")
                .attr("transform", function(d) {{
                    return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
                }})
                .text(function(d) {{ return d.text; }});
        }}
        """
        return code

    async def _transform_data_for_visualization(self, data: Any, viz_type: str) -> Dict[str, Any]:
        """
        Transform data into the format required by the visualization type.
        
        Args:
            data: Input data in various formats
            viz_type: Type of visualization
            
        Returns:
            Transformed data suitable for the visualization
        """
        # Check if a data_transformer cell is connected
        transformer_cell = self._get_connected_cell_by_capability("data_transform")
        
        if transformer_cell:
            try:
                # Use data transformer if available
                result = await self.call_capability(
                    cell_id=transformer_cell,
                    capability="transform_data",
                    parameters={
                        "data": data,
                        "target_format": f"visualization_{viz_type}",
                        "options": {}
                    }
                )
                
                if result["status"] == "success":
                    transformed_data = next((o["value"] for o in result["outputs"] if o["name"] == "transformed_data"), None)
                    if transformed_data:
                        return transformed_data
            except Exception as e:
                logger.warning(f"Error using data transformer: {e}")
                # Fall back to built-in transformation
        
        # Built-in transformation logic
        if viz_type == "pie":
            return self._transform_for_pie(data)
        elif viz_type == "bar":
            return self._transform_for_bar(data)
        elif viz_type == "line":
            return self._transform_for_line(data)
        elif viz_type == "scatter":
            return self._transform_for_scatter(data)
        elif viz_type == "bubble":
            return self._transform_for_bubble(data)
        elif viz_type == "histogram":
            return self._transform_for_histogram(data)
        elif viz_type == "sankey":
            return self._transform_for_sankey(data)
        elif viz_type == "tree":
            return self._transform_for_tree(data)
        elif viz_type == "treemap":
            return self._transform_for_treemap(data)
        elif viz_type == "heatmap":
            return self._transform_for_heatmap(data)
        elif viz_type == "network":
            return self._transform_for_network(data)
        elif viz_type == "wordcloud":
            return self._transform_for_wordcloud(data)
        elif viz_type == "calendar":
            return self._transform_for_calendar(data)
        elif viz_type == "timeline":
            return self._transform_for_timeline(data)
        else:
            # Default to table transformation
            return self._transform_for_table(data)
    
    def _transform_for_pie(self, data: Any) -> Dict[str, Any]:
        """Transform data for pie chart format."""
        rows = []
        
        if isinstance(data, dict):
            # Convert dict to [label, value] rows
            for label, value in data.items():
                rows.append([str(label), self._ensure_numeric(value)])
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # Assume list of dicts with label and value fields
                label_field = next((k for k in data[0] if "label" in k.lower() or "name" in k.lower()), next(iter(data[0])))
                value_field = next((k for k in data[0] if "value" in k.lower() or "count" in k.lower() or "amount" in k.lower()), 
                                  next(k for k in data[0] if isinstance(data[0][k], (int, float))), 
                                  next(iter(data[0].keys())))
                
                for item in data:
                    rows.append([str(item.get(label_field, "")), self._ensure_numeric(item.get(value_field, 0))])
            else:
                # Try to interpret as [label, value] pairs or single values
                for i, item in enumerate(data):
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        rows.append([str(item[0]), self._ensure_numeric(item[1])])
                    else:
                        rows.append([f"Item {i+1}", self._ensure_numeric(item)])
        
        return {
            "formatted_data": rows,
            "labels": [row[0] for row in rows],
            "values": [row[1] for row in rows]
        }
    
    def _transform_for_bar(self, data: Any) -> Dict[str, Any]:
        """Transform data for bar chart format."""
        categories = []
        series = []
        series_names = []
        
        if isinstance(data, dict):
            # Simple dictionary becomes a single series
            categories = list(data.keys())
            series.append([self._ensure_numeric(v) for v in data.values()])
            series_names.append("Value")
        
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # List of dictionaries
                # First, determine category and value fields
                first_item = data[0]
                cat_field = next((k for k in first_item if k.lower() in ['category', 'name', 'label', 'group']), 
                                next(iter(first_item.keys())))
                
                # Extract all potential value fields (numeric fields)
                value_fields = [k for k in first_item if isinstance(first_item[k], (int, float)) and k != cat_field]
                
                if value_fields:
                    # Multiple series bar chart
                    categories = [item[cat_field] for item in data]
                    series_names = value_fields
                    
                    for field in value_fields:
                        series.append([self._ensure_numeric(item.get(field, 0)) for item in data])
                else:
                    # Try to see if this is a list of records with a common category field
                    # and different value fields per record
                    categories = list(set(item[cat_field] for item in data))
                    categories.sort()
                    
                    value_field = next((k for k in first_item if k.lower() in ['value', 'amount', 'count']), 
                                    next((k for k in first_item if isinstance(first_item[k], (int, float)) and k != cat_field), 
                                         next(k for k in first_item if k != cat_field)))
                    
                    # Check if there's a series field
                    series_field = next((k for k in first_item if k.lower() in ['series', 'group', 'type']), None)
                    
                    if series_field:
                        # Data has explicit series
                        series_values = list(set(item[series_field] for item in data))
                        series_values.sort()
                        series_names = series_values
                        
                        # Create a matrix of values
                        for series_val in series_values:
                            series_data = []
                            for cat in categories:
                                # Find matching items
                                matches = [item for item in data if item[cat_field] == cat and item[series_field] == series_val]
                                if matches:
                                    series_data.append(self._ensure_numeric(matches[0].get(value_field, 0)))
                                else:
                                    series_data.append(0)
                            series.append(series_data)
                    else:
                        # Single series with categories
                        series_names = ["Value"]
                        series_data = []
                        for cat in categories:
                            matches = [item for item in data if item[cat_field] == cat]
                            if matches:
                                series_data.append(self._ensure_numeric(matches[0].get(value_field, 0)))
                            else:
                                series_data.append(0)
                        series.append(series_data)
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of lists/tuples
                if data and len(data[0]) >= 2:
                    # First element of each is category, rest are series values
                    categories = [item[0] for item in data]
                    
                    # Determine how many series
                    max_length = max(len(item) for item in data)
                    
                    for i in range(1, max_length):
                        series_names.append(f"Series {i}")
                        series.append([self._ensure_numeric(item[i]) if i < len(item) else 0 for item in data])
                else:
                    # Single list of values
                    categories = [f"Item {i+1}" for i in range(len(data))]
                    series.append([self._ensure_numeric(item) for item in data])
                    series_names.append("Value")
            else:
                # Single list of values
                categories = [f"Item {i+1}" for i in range(len(data))]
                series.append([self._ensure_numeric(item) for item in data])
                series_names.append("Value")
        
        # Convert all categories to strings
        categories = [str(cat) for cat in categories]
        
        return {
            "categories": categories,
            "series": series,
            "series_names": series_names
        }
    
    def _transform_for_line(self, data: Any) -> Dict[str, Any]:
        """Transform data for line chart format."""
        # Line charts use the same basic structure as bar charts
        return self._transform_for_bar(data)
    
    def _transform_for_scatter(self, data: Any) -> Dict[str, Any]:
        """Transform data for scatter plot format."""
        # Scatter plots need x,y points
        series = []
        series_names = []
        
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # List of dicts
                
                # Try to find x and y fields
                first_item = data[0]
                x_field = next((k for k in first_item if k.lower() in ['x', 'xaxis', 'xvalue']), 
                             next((k for k in first_item if isinstance(first_item[k], (int, float))), 
                                 next(iter(first_item.keys()))))
                
                remaining_fields = [k for k in first_item if k != x_field]
                y_fields = []
                
                # Find numeric fields for y-axis
                for field in remaining_fields:
                    if any(isinstance(item.get(field), (int, float)) for item in data):
                        y_fields.append(field)
                
                # If no numeric y_fields found, use the first field that's not x
                if not y_fields and remaining_fields:
                    y_fields = [remaining_fields[0]]
                
                # Create series for each y field
                for y_field in y_fields:
                    points = []
                    for item in data:
                        if x_field in item and y_field in item:
                            x_val = item[x_field]
                            y_val = item[y_field]
                            
                            # Make sure x and y are numeric
                            if isinstance(x_val, (int, float)) and isinstance(y_val, (int, float)):
                                points.append([x_val, y_val])
                    
                    if points:
                        series.append(points)
                        series_names.append(y_field)
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of lists/tuples
                if data and len(data[0]) >= 2:
                    # Simple x,y pairs
                    points = []
                    for item in data:
                        if len(item) >= 2:
                            x_val = item[0]
                            y_val = item[1]
                            
                            # Make sure x and y are numeric
                            if isinstance(x_val, (int, float)) and isinstance(y_val, (int, float)):
                                points.append([x_val, y_val])
                    
                    if points:
                        series.append(points)
                        series_names.append("Series 1")
        
        return {
            "series": series,
            "series_names": series_names
        }
    
    def _transform_for_bubble(self, data: Any) -> Dict[str, Any]:
        """Transform data for bubble chart format."""
        # Bubble charts need x,y,size points
        series = []
        series_names = []
        
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # List of dicts
                
                # Try to find x, y, and size fields
                first_item = data[0]
                x_field = next((k for k in first_item if k.lower() in ['x', 'xaxis', 'xvalue']), 
                             next((k for k in first_item if isinstance(first_item[k], (int, float))), 
                                 next(iter(first_item.keys()))))
                
                remaining_fields = [k for k in first_item if k != x_field]
                y_field = next((k for k in remaining_fields if k.lower() in ['y', 'yaxis', 'yvalue']), 
                             next((k for k in remaining_fields if isinstance(first_item[k], (int, float))), 
                                 remaining_fields[0] if remaining_fields else None))
                
                if y_field:
                    remaining_fields = [k for k in remaining_fields if k != y_field]
                    
                    size_field = next((k for k in remaining_fields if k.lower() in ['size', 'value', 'weight', 'amount']), 
                                    next((k for k in remaining_fields if isinstance(first_item[k], (int, float))), 
                                        remaining_fields[0] if remaining_fields else None))
                    
                    # Try to find a label field
                    label_field = next((k for k in first_item if k.lower() in ['name', 'label', 'title', 'id']), None)
                    
                    # Try to find a color/category field
                    color_field = next((k for k in first_item if k.lower() in ['color', 'category', 'group', 'type']), None)
                    
                    if size_field:
                        if color_field:
                            # Group by color field
                            categories = list(set(item.get(color_field) for item in data if color_field in item))
                            categories.sort()
                            
                            for category in categories:
                                points = []
                                for item in data:
                                    if (x_field in item and y_field in item and size_field in item and 
                                            color_field in item and item[color_field] == category):
                                        x_val = self._ensure_numeric(item[x_field])
                                        y_val = self._ensure_numeric(item[y_field])
                                        size_val = self._ensure_numeric(item[size_field])
                                        label = str(item.get(label_field, "")) if label_field else ""
                                        
                                        if label:
                                            points.append([x_val, y_val, size_val, label])
                                        else:
                                            points.append([x_val, y_val, size_val])
                                
                                if points:
                                    series.append(points)
                                    series_names.append(str(category))
                        else:
                            # Single series
                            points = []
                            for item in data:
                                if x_field in item and y_field in item and size_field in item:
                                    x_val = self._ensure_numeric(item[x_field])
                                    y_val = self._ensure_numeric(item[y_field])
                                    size_val = self._ensure_numeric(item[size_field])
                                    label = str(item.get(label_field, "")) if label_field else ""
                                    
                                    if label:
                                        points.append([x_val, y_val, size_val, label])
                                    else:
                                        points.append([x_val, y_val, size_val])
                            
                            if points:
                                series.append(points)
                                series_names.append("Series 1")
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of lists/tuples
                if data and len(data[0]) >= 3:
                    # Simple x,y,size tuples
                    points = []
                    for item in data:
                        if len(item) >= 3:
                            x_val = self._ensure_numeric(item[0])
                            y_val = self._ensure_numeric(item[1])
                            size_val = self._ensure_numeric(item[2])
                            
                            if len(item) >= 4:
                                label = str(item[3])
                                points.append([x_val, y_val, size_val, label])
                            else:
                                points.append([x_val, y_val, size_val])
                    
                    if points:
                        series.append(points)
                        series_names.append("Series 1")
        
        return {
            "series": series,
            "series_names": series_names
        }
    
    def _transform_for_histogram(self, data: Any) -> Dict[str, Any]:
        """Transform data for histogram format."""
        values = []
        
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # Try to find a value field
                first_item = data[0]
                value_field = next((k for k in first_item if k.lower() in ['value', 'amount', 'count']), 
                                 next((k for k in first_item if isinstance(first_item[k], (int, float))), 
                                     next(iter(first_item.keys()))))
                
                values = [self._ensure_numeric(item.get(value_field, 0)) for item in data]
            elif all(isinstance(item, (list, tuple)) for item in data):
                # If lists/tuples, take first element of each
                values = [self._ensure_numeric(item[0]) if item else 0 for item in data]
            else:
                # Use values directly
                values = [self._ensure_numeric(item) for item in data]
        
        return {
            "values": values
        }
    
    def _transform_for_sankey(self, data: Any) -> Dict[str, Any]:
        """Transform data for Sankey diagram format."""
        links = []
        
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # Try to find source, target, and value fields
                first_item = data[0]
                source_field = next((k for k in first_item if k.lower() in ['source', 'from', 'start']), None)
                target_field = next((k for k in first_item if k.lower() in ['target', 'to', 'end', 'dest']), None)
                value_field = next((k for k in first_item if k.lower() in ['value', 'weight', 'amount', 'count']), 
                                 next((k for k in first_item if isinstance(first_item[k], (int, float)) and 
                                      k not in [source_field, target_field]), None))
                
                if source_field and target_field:
                    for item in data:
                        if source_field in item and target_field in item:
                            source = str(item[source_field])
                            target = str(item[target_field])
                            value = self._ensure_numeric(item.get(value_field, 1))
                            
                            links.append([source, target, value])
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # Expect [source, target, value] format
                for item in data:
                    if len(item) >= 3:
                        source = str(item[0])
                        target = str(item[1])
                        value = self._ensure_numeric(item[2])
                        
                        links.append([source, target, value])
                    elif len(item) >= 2:
                        source = str(item[0])
                        target = str(item[1])
                        value = 1  # Default value
                        
                        links.append([source, target, value])
        
        return {
            "links": links
        }
    
    def _transform_for_tree(self, data: Any) -> Dict[str, Any]:
        """Transform data for tree diagram format."""
        nodes = []
        
        if isinstance(data, dict):
            # Recursively convert nested dictionary to tree nodes
            nodes = self._dict_to_tree_nodes(data)
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # Look for parent-child relationships
                id_field = next((k for k in data[0] if k.lower() in ['id', 'name', 'label']), 
                               next(iter(data[0].keys())))
                
                parent_field = next((k for k in data[0] if k.lower() in ['parent', 'parent_id', 'parentid']), None)
                
                if parent_field:
                    # Classic parent-child representation
                    for item in data:
                        node = {
                            "id": str(item.get(id_field, "")),
                            "parent": str(item.get(parent_field, "")) if item.get(parent_field) else ""
                        }
                        
                        # Add other fields as attributes
                        for k, v in item.items():
                            if k not in [id_field, parent_field]:
                                node[k] = v
                        
                        nodes.append(node)
                else:
                    # Check for children array
                    children_field = next((k for k in data[0] if k.lower() in ['children', 'items', 'nodes']), None)
                    
                    if children_field and isinstance(data[0].get(children_field), list):
                        # Hierarchical representation with children arrays
                        nodes = self._hierarchical_to_tree_nodes(data)
        
        return {
            "nodes": nodes
        }
    
    def _dict_to_tree_nodes(self, data: Dict, parent: str = "", level: int = 0) -> List[Dict]:
        """
        Recursively convert a nested dictionary to tree nodes.
        
        Args:
            data: Dictionary or value
            parent: Parent node ID
            level: Current nesting level
            
        Returns:
            List of node objects
        """
        nodes = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                node_id = key if level == 0 else f"{parent}.{key}"
                
                # Add current node
                nodes.append({
                    "id": node_id,
                    "parent": parent,
                    "name": key
                })
                
                # Process children
                if isinstance(value, (dict, list)):
                    child_nodes = self._dict_to_tree_nodes(value, node_id, level + 1)
                    nodes.extend(child_nodes)
                else:
                    # Leaf node with value
                    value_node_id = f"{node_id}.value"
                    nodes.append({
                        "id": value_node_id,
                        "parent": node_id,
                        "name": str(value)
                    })
        elif isinstance(data, list):
            for i, item in enumerate(data):
                node_id = f"{parent}.{i}" if parent else str(i)
                
                # Add this item
                nodes.append({
                    "id": node_id,
                    "parent": parent,
                    "name": f"Item {i+1}"
                })
                
                # Process the item
                child_nodes = self._dict_to_tree_nodes(item, node_id, level + 1)
                nodes.extend(child_nodes)
        
        return nodes
    
    def _hierarchical_to_tree_nodes(self, data: List[Dict], parent: str = "") -> List[Dict]:
        """
        Convert hierarchical data (with children arrays) to flat tree nodes.
        
        Args:
            data: List of node objects with children arrays
            parent: Parent node ID
            
        Returns:
            List of node objects in flat structure
        """
        nodes = []
        
        for item in data:
            # Find id field
            id_field = next((k for k in item if k.lower() in ['id', 'name', 'label']), 
                           next(iter(item.keys())))
            children_field = next((k for k in item if k.lower() in ['children', 'items', 'nodes']), None)
            
            node_id = str(item.get(id_field, ""))
            
            # Add current node
            node = {
                "id": node_id,
                "parent": parent,
                "name": node_id
            }
            
            # Add other fields as attributes
            for k, v in item.items():
                if k not in [id_field, children_field]:
                    node[k] = v
            
            nodes.append(node)
            
            # Process children if present
            if children_field and isinstance(item.get(children_field), list):
                child_nodes = self._hierarchical_to_tree_nodes(item[children_field], node_id)
                nodes.extend(child_nodes)
        
        return nodes
    
    def _transform_for_treemap(self, data: Any) -> Dict[str, Any]:
        """Transform data for treemap format."""
        # Treemaps use the same hierarchical structure as trees
        tree_data = self._transform_for_tree(data)
        
        # Add value field to leaf nodes if not present
        nodes = tree_data["nodes"]
        
        # Find all nodes that are parents
        parent_nodes = set(node["id"] for node in nodes if node["parent"])
        
        # Add default value to leaf nodes
        for node in nodes:
            if node["id"] not in parent_nodes and "value" not in node:
                node["value"] = 1
        
        return {"nodes": nodes}
    
    def _transform_for_heatmap(self, data: Any) -> Dict[str, Any]:
        """Transform data for heatmap format."""
        x_labels = []
        y_labels = []
        values = []
        
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # Try to find x, y, and value fields
                first_item = data[0]
                x_field = next((k for k in first_item if k.lower() in ['x', 'xaxis', 'xvalue', 'column']), 
                             next(iter(first_item.keys())))
                
                remaining_fields = [k for k in first_item if k != x_field]
                y_field = next((k for k in remaining_fields if k.lower() in ['y', 'yaxis', 'yvalue', 'row']), 
                             remaining_fields[0] if remaining_fields else None)
                
                if y_field:
                    remaining_fields = [k for k in remaining_fields if k != y_field]
                    value_field = next((k for k in remaining_fields if k.lower() in ['value', 'weight', 'amount', 'count', 'z']), 
                                     next((k for k in remaining_fields if isinstance(first_item[k], (int, float))), 
                                         remaining_fields[0] if remaining_fields else None))
                    
                    # Extract unique x and y values to form the grid
                    x_values = list(set(item.get(x_field) for item in data if x_field in item))
                    y_values = list(set(item.get(y_field) for item in data if y_field in item))
                    
                    # Sort the labels
                    x_values.sort()
                    y_values.sort()
                    
                    x_labels = [str(x) for x in x_values]
                    y_labels = [str(y) for y in y_values]
                    
                    # Create the value matrix
                    values = []
                    for y in y_values:
                        row = []
                        for x in x_values:
                            # Find the matching data point
                            matches = [item for item in data if item.get(x_field) == x and item.get(y_field) == y]
                            if matches and value_field in matches[0]:
                                row.append(self._ensure_numeric(matches[0][value_field]))
                            else:
                                row.append(0)  # Default for missing values
                        values.append(row)
            
            elif all(isinstance(row, list) for row in data):
                # Assume it's already in matrix form
                values = [[self._ensure_numeric(cell) for cell in row] for row in data]
                
                # Generate default labels
                x_labels = [f"Column {i+1}" for i in range(len(data[0]))]
                y_labels = [f"Row {i+1}" for i in range(len(data))]
        
        return {
            "x": x_labels,
            "y": y_labels,
            "values": values
        }
    
    def _transform_for_network(self, data: Any) -> Dict[str, Any]:
        """Transform data for network diagram format."""
        nodes = []
        edges = []
        
        if isinstance(data, dict) and "nodes" in data and "edges" in data:
            # Already in the right format
            if isinstance(data["nodes"], list) and isinstance(data["edges"], list):
                return {
                    "nodes": data["nodes"],
                    "edges": data["edges"]
                }
        
        elif isinstance(data, dict) and "nodes" in data and "links" in data:
            # Common alternative format
            nodes = data["nodes"]
            
            # Convert links to edges
            for link in data["links"]:
                edge = dict(link)
                
                # Rename fields if needed
                if "source" in edge and "from" not in edge:
                    edge["from"] = edge["source"]
                
                if "target" in edge and "to" not in edge:
                    edge["to"] = edge["target"]
                
                edges.append(edge)
            
            return {
                "nodes": nodes,
                "edges": edges
            }
        
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # Check if this is a list of edges with implicit nodes
                from_field = next((k for k in data[0] if k.lower() in ['from', 'source', 'start']), None)
                to_field = next((k for k in data[0] if k.lower() in ['to', 'target', 'end', 'dest']), None)
                
                if from_field and to_field:
                    # This is a list of edges
                    node_ids = set()
                    
                    # Process edges and collect unique nodes
                    for item in data:
                        if from_field in item and to_field in item:
                            from_id = str(item[from_field])
                            to_id = str(item[to_field])
                            
                            # Create edge
                            edge = {
                                "from": from_id,
                                "to": to_id
                            }
                            
                            # Copy other properties
                            for k, v in item.items():
                                if k not in [from_field, to_field]:
                                    edge[k] = v
                            
                            edges.append(edge)
                            
                            # Track nodes
                            node_ids.add(from_id)
                            node_ids.add(to_id)
                    
                    # Create nodes for each unique ID
                    for node_id in node_ids:
                        nodes.append({
                            "id": node_id,
                            "label": node_id
                        })
                else:
                    # Check if this is a list of nodes
                    id_field = next((k for k in data[0] if k.lower() in ['id', 'name', 'label']), None)
                    
                    if id_field:
                        # This is a list of nodes
                        nodes = data.copy()
                        
                        # Ensure all nodes have an id field
                        for node in nodes:
                            if "id" not in node and id_field in node:
                                node["id"] = str(node[id_field])
                            
                            if "label" not in node and id_field in node:
                                node["label"] = str(node[id_field])
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # Assume pairs of [from, to] or triples [from, to, weight]
                node_ids = set()
                
                for item in data:
                    if len(item) >= 2:
                        from_id = str(item[0])
                        to_id = str(item[1])
                        
                        edge = {
                            "from": from_id,
                            "to": to_id
                        }
                        
                        if len(item) >= 3:
                            edge["value"] = self._ensure_numeric(item[2])
                            edge["width"] = self._ensure_numeric(item[2])
                        
                        if len(item) >= 4:
                            edge["label"] = str(item[3])
                        
                        edges.append(edge)
                        
                        # Track nodes
                        node_ids.add(from_id)
                        node_ids.add(to_id)
                
                # Create nodes for each unique ID
                for node_id in node_ids:
                    nodes.append({
                        "id": node_id,
                        "label": node_id
                    })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _transform_for_wordcloud(self, data: Any) -> Dict[str, Any]:
        """Transform data for word cloud format."""
        words = []
        
        if isinstance(data, dict):
            # Dictionary of word -> weight
            for word, weight in data.items():
                words.append({
                    "text": str(word),
                    "size": self._ensure_numeric(weight)
                })
        
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # List of dict objects
                text_field = next((k for k in data[0] if k.lower() in ['text', 'word', 'term', 'name', 'label']), 
                                next(iter(data[0].keys())))
                
                size_field = next((k for k in data[0] if k.lower() in ['size', 'weight', 'value', 'count', 'frequency']), 
                                next((k for k in data[0] if isinstance(data[0][k], (int, float)) and k != text_field), 
                                    None))
                
                if size_field:
                    for item in data:
                        if text_field in item and size_field in item:
                            words.append({
                                "text": str(item[text_field]),
                                "size": self._ensure_numeric(item[size_field])
                            })
                else:
                    # No explicit size field, use count
                    word_counts = {}
                    for item in data:
                        if text_field in item:
                            word = str(item[text_field])
                            word_counts[word] = word_counts.get(word, 0) + 1
                    
                    for word, count in word_counts.items():
                        words.append({
                            "text": word,
                            "size": count
                        })
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of [word, size] pairs
                for item in data:
                    if len(item) >= 2:
                        words.append({
                            "text": str(item[0]),
                            "size": self._ensure_numeric(item[1])
                        })
            
            elif all(isinstance(item, str) for item in data):
                # List of words, count occurrences
                word_counts = {}
                for word in data:
                    word_counts[word] = word_counts.get(word, 0) + 1
                
                for word, count in word_counts.items():
                    words.append({
                        "text": word,
                        "size": count
                    })
        
        return {
            "words": words
        }
    
    def _transform_for_calendar(self, data: Any) -> Dict[str, Any]:
        """Transform data for calendar visualization format."""
        date_values = []
        
        if isinstance(data, dict):
            # Dictionary of date -> value
            for date_str, value in data.items():
                try:
                    # Try to parse date
                    date_obj = self._parse_date(date_str)
                    if date_obj:
                        date_values.append([date_obj, self._ensure_numeric(value)])
                except Exception:
                    pass
        
        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # List of dict objects
                date_field = next((k for k in data[0] if k.lower() in ['date', 'day', 'timestamp']), None)
                value_field = next((k for k in data[0] if k.lower() in ['value', 'count', 'amount']), 
                                 next((k for k in data[0] if isinstance(data[0][k], (int, float)) and k != date_field), 
                                     None))
                
                if date_field and value_field:
                    for item in data:
                        if date_field in item and value_field in item:
                            try:
                                date_obj = self._parse_date(item[date_field])
                                if date_obj:
                                    date_values.append([date_obj, self._ensure_numeric(item[value_field])])
                            except Exception:
                                pass
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of [date, value] pairs
                for item in data:
                    if len(item) >= 2:
                        try:
                            date_obj = self._parse_date(item[0])
                            if date_obj:
                                date_values.append([date_obj, self._ensure_numeric(item[1])])
                        except Exception:
                            pass
        
        return {
            "date_values": date_values
        }
    
    def _transform_for_timeline(self, data: Any) -> Dict[str, Any]:
        """Transform data for timeline visualization format."""
        timeline_rows = []
        
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                # List of dict objects
                # Look for key fields
                row_field = next((k for k in data[0] if k.lower() in ['row', 'category', 'group', 'track']), None)
                label_field = next((k for k in data[0] if k.lower() in ['label', 'name', 'title', 'event']), None)
                start_field = next((k for k in data[0] if k.lower() in ['start', 'start_date', 'startdate', 'begin']), None)
                end_field = next((k for k in data[0] if k.lower() in ['end', 'end_date', 'enddate', 'finish']), None)
                
                if start_field:
                    for item in data:
                        if start_field in item:
                            try:
                                # Get row label
                                row_label = str(item.get(row_field, "Default")) if row_field else "Default"
                                
                                # Get event label
                                event_label = str(item.get(label_field, "Event")) if label_field else "Event"
                                
                                # Parse dates
                                start_date = self._parse_date(item[start_field])
                                
                                end_date = None
                                if end_field and end_field in item:
                                    end_date = self._parse_date(item[end_field])
                                
                                if not end_date and start_date:
                                    # Default to 1 day duration if no end date
                                    from datetime import timedelta
                                    end_date = start_date + timedelta(days=1)
                                
                                if start_date and end_date:
                                    timeline_rows.append([row_label, event_label, start_date, end_date])
                            except Exception as e:
                                logger.warning(f"Error parsing timeline data: {e}")
            
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of [row, label, start, end] tuples
                for item in data:
                    if len(item) >= 4:
                        try:
                            row_label = str(item[0])
                            event_label = str(item[1])
                            start_date = self._parse_date(item[2])
                            end_date = self._parse_date(item[3])
                            
                            if start_date and end_date:
                                timeline_rows.append([row_label, event_label, start_date, end_date])
                        except Exception:
                            pass
        
        return {
            "timeline_rows": timeline_rows
        }
    
    def _transform_for_table(self, data: Any) -> Dict[str, Any]:
        """Transform data for table format."""
        columns = []
        rows = []
        
        if isinstance(data, dict):
            # Single row with column keys
            columns = list(data.keys())
            rows = [list(data.values())]
        
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                # List of dictionaries
                # Use keys from first row as columns
                columns = list(data[0].keys())
                
                # Extract values for each row
                for item in data:
                    row = [item.get(col, "") for col in columns]
                    rows.append(row)
            
            elif data and isinstance(data[0], (list, tuple)):
                # List of lists
                # If first row contains strings and rest are same length, use as header
                if all(isinstance(x, str) for x in data[0]) and all(len(row) == len(data[0]) for row in data[1:]):
                    columns = list(data[0])
                    rows = data[1:]
                else:
                    # Generate column names and use all rows
                    columns = [f"Column {i+1}" for i in range(len(data[0]))]
                    rows = data
            
            else:
                # Single column of values
                columns = ["Value"]
                rows = [[x] for x in data]
        
        return {
            "columns": columns,
            "rows": rows
        }
    
    def _parse_date(self, date_value) -> Optional[str]:
        """
        Parse a date value in various formats.
        
        Args:
            date_value: Date string, timestamp, or datetime object
            
        Returns:
            Parsed date string or None if parsing fails
        """
        from datetime import datetime
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, (int, float)):
            # Assume unix timestamp
            try:
                return datetime.fromtimestamp(date_value)
            except Exception:
                pass
        
        if isinstance(date_value, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%d-%b-%Y",
                "%B %d, %Y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _ensure_numeric(self, value) -> Union[int, float]:
        """
        Ensure a value is numeric, converting strings if needed.
        
        Args:
            value: Value to convert
            
        Returns:
            Numeric version of the value
        """
        if isinstance(value, (int, float)):
            return value
        
        try:
            # Try converting to int first
            return int(value)
        except (TypeError, ValueError):
            try:
                # Try converting to float
                return float(value)
            except (TypeError, ValueError):
                # Default to 0 if cannot convert
                return 0
    
    def _get_connected_cell_by_capability(self, capability: str) -> Optional[str]:
        """
        Find a connected cell with the specified capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            Cell ID of connected cell or None if not found
        """
        for connection in self.connections:
            if capability in connection.capabilities:
                return connection.id
        return None
    
    async def call_capability(self, cell_id: str, capability: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a capability on a connected cell.
        
        Args:
            cell_id: ID of the cell to call
            capability: Capability to invoke
            parameters: Parameters for the capability
            
        Returns:
            Result of the capability call
        """
        # In a real implementation, this would use the cell runtime messaging system
        # For this example, we'll just return a mock response
        logger.debug(f"Calling capability {capability} on cell {cell_id}")
        
        if capability == "data_transform":
            # Mock data transformer response
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "transformed_data",
                        "value": parameters.get("data", {}),
                        "type": "object"
                    }
                ]
            }
        
        return {
            "status": "error",
            "error": f"Capability {capability} not found on cell {cell_id}"
        }
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
            
        Returns:
            Error response dictionary
        """
        logger.error(f"Data visualization error: {message}")
        return {
            "status": "error",
            "error": message,
            "outputs": [
                {
                    "name": "error",
                    "value": message,
                    "type": "string"
                }
            ]
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
                "settings": self.settings,
                "chart_counter": self.chart_counter
            }
            
            result = {
                "status": "success",
                "state": "suspended",
                "saved_state": state
            }
            
            logger.info("Data visualization cell suspended")
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
                
                if "settings" in saved_state:
                    self.settings.update(saved_state["settings"])
                
                if "chart_counter" in saved_state:
                    self.chart_counter = saved_state["chart_counter"]
                
                logger.info("Data visualization cell resumed with saved state")
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
            self.chart_counter = 0
            
            logger.info("Data visualization cell released")
            
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
