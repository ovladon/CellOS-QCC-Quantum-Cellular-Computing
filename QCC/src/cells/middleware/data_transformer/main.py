"""
Data Transformer cell for the QCC architecture.

This middleware cell provides data transformation capabilities,
allowing the conversion between different data formats and structures.
"""

import json
import csv
import yaml
import xml.etree.ElementTree as ET
import base64
from typing import Dict, List, Any, Optional
from io import StringIO

from qcc.cells import BaseCell

class DataTransformerCell(BaseCell):
    """
    A middleware cell that provides data transformation capabilities.
    
    This cell enables the conversion of data between different formats
    (JSON, CSV, YAML, XML) and the application of transformations to
    structured data.
    """
    
    def initialize(self, parameters):
        """Initialize the data transformer cell."""
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("convert_format", self.convert_format)
        self.register_capability("filter_data", self.filter_data)
        self.register_capability("sort_data", self.sort_data)
        self.register_capability("group_data", self.group_data)
        self.register_capability("aggregate_data", self.aggregate_data)
        self.register_capability("transform_data", self.transform_data)
        
        self.logger.info(f"Data transformer cell initialized with ID: {self.cell_id}")
        
        return self.get_initialization_result()
    
    async def convert_format(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert data between different formats.
        
        Args:
            parameters: Dictionary containing:
                - data: The data to convert
                - source_format: Source format (json, csv, yaml, xml)
                - target_format: Target format (json, csv, yaml, xml)
                - options: Optional conversion options
                
        Returns:
            Dictionary containing the converted data
        """
        # Validate parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "source_format" not in parameters:
            return self._error_response("Source format parameter is required")
        
        if "target_format" not in parameters:
            return self._error_response("Target format parameter is required")
        
        data = parameters["data"]
        source_format = parameters["source_format"].lower()
        target_format = parameters["target_format"].lower()
        options = parameters.get("options", {})
        
        # Check valid formats
        valid_formats = ["json", "csv", "yaml", "xml"]
        if source_format not in valid_formats:
            return self._error_response(f"Invalid source format: {source_format}")
        
        if target_format not in valid_formats:
            return self._error_response(f"Invalid target format: {target_format}")
            
        # Skip if source and target formats are the same
        if source_format == target_format:
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "data",
                        "value": data,
                        "type": target_format
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 1,
                    "memory_used_mb": 0.1
                }
            }
        
        try:
            # Parse input data based on source format
            parsed_data = self._parse_data(data, source_format, options)
            
            # Convert to target format
            converted_data = self._convert_data(parsed_data, target_format, options)
            
            # Log the operation
            self.logger.info(f"Converted data from {source_format} to {target_format}")
            
            # Return the converted data
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "data",
                        "value": converted_data,
                        "type": target_format
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,  # Example value
                    "memory_used_mb": 2       # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error converting data: {str(e)}")
    
    async def filter_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter data based on criteria.
        
        Args:
            parameters: Dictionary containing:
                - data: The data to filter (list of dictionaries)
                - criteria: Filter criteria
                
        Returns:
            Dictionary containing the filtered data
        """
        # Validate parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "criteria" not in parameters:
            return self._error_response("Criteria parameter is required")
        
        data = parameters["data"]
        criteria = parameters["criteria"]
        
        # Ensure data is a list
        if not isinstance(data, list):
            return self._error_response("Data must be a list of items")
        
        try:
            # Apply filters
            filtered_data = []
            for item in data:
                if self._matches_criteria(item, criteria):
                    filtered_data.append(item)
            
            # Log the operation
            self.logger.info(f"Filtered data: {len(filtered_data)} of {len(data)} items matched")
            
            # Return the filtered data
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "data",
                        "value": filtered_data,
                        "type": "array"
                    },
                    {
                        "name": "count",
                        "value": len(filtered_data),
                        "type": "number"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,  # Example value
                    "memory_used_mb": 1      # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error filtering data: {str(e)}")
    
    async def sort_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sort data based on key.
        
        Args:
            parameters: Dictionary containing:
                - data: The data to sort (list of dictionaries)
                - key: Sort key or list of keys
                - reverse: Whether to sort in reverse order (default: False)
                
        Returns:
            Dictionary containing the sorted data
        """
        # Validate parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "key" not in parameters:
            return self._error_response("Key parameter is required")
        
        data = parameters["data"]
        key = parameters["key"]
        reverse = parameters.get("reverse", False)
        
        # Ensure data is a list
        if not isinstance(data, list):
            return self._error_response("Data must be a list of items")
        
        try:
            # Convert key to list if it's a string
            keys = key if isinstance(key, list) else [key]
            
            # Sort the data
            sorted_data = sorted(
                data,
                key=lambda item: [self._get_nested_value(item, k) for k in keys],
                reverse=reverse
            )
            
            # Log the operation
            self.logger.info(f"Sorted data by {key}")
            
            # Return the sorted data
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "data",
                        "value": sorted_data,
                        "type": "array"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,  # Example value
                    "memory_used_mb": 1      # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error sorting data: {str(e)}")
    
    async def group_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Group data based on key.
        
        Args:
            parameters: Dictionary containing:
                - data: The data to group (list of dictionaries)
                - key: Grouping key or list of keys
                
        Returns:
            Dictionary containing the grouped data
        """
        # Validate parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "key" not in parameters:
            return self._error_response("Key parameter is required")
        
        data = parameters["data"]
        key = parameters["key"]
        
        # Ensure data is a list
        if not isinstance(data, list):
            return self._error_response("Data must be a list of items")
        
        try:
            # Convert key to list if it's a string
            keys = key if isinstance(key, list) else [key]
            
            # Group the data
            groups = {}
            for item in data:
                # Create group key tuple
                group_key = tuple(self._get_nested_value(item, k) for k in keys)
                
                # Initialize group if not exists
                if group_key not in groups:
                    groups[group_key] = []
                    
                # Add item to group
                groups[group_key].append(item)
            
            # Convert groups to list format
            grouped_data = [
                {
                    "key": group_key if len(keys) > 1 else group_key[0],
                    "items": items
                }
                for group_key, items in groups.items()
            ]
            
            # Log the operation
            self.logger.info(f"Grouped data by {key} into {len(grouped_data)} groups")
            
            # Return the grouped data
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "data",
                        "value": grouped_data,
                        "type": "array"
                    },
                    {
                        "name": "group_count",
                        "value": len(grouped_data),
                        "type": "number"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,  # Example value
                    "memory_used_mb": 2       # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error grouping data: {str(e)}")
    
    async def aggregate_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate data using specified functions.
        
        Args:
            parameters: Dictionary containing:
                - data: The data to aggregate (list of dictionaries)
                - group_by: Optional grouping key
                - aggregations: List of aggregation operations
                
        Returns:
            Dictionary containing the aggregated data
        """
        # Validate parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "aggregations" not in parameters:
            return self._error_response("Aggregations parameter is required")
        
        data = parameters["data"]
        group_by = parameters.get("group_by")
        aggregations = parameters["aggregations"]
        
        # Ensure data is a list
        if not isinstance(data, list):
            return self._error_response("Data must be a list of items")
        
        # Ensure aggregations is a list
        if not isinstance(aggregations, list):
            return self._error_response("Aggregations must be a list")
        
        try:
            # If group_by is specified, group the data first
            if group_by:
                # Group data
                group_result = await self.group_data({
                    "data": data,
                    "key": group_by
                })
                
                if group_result["status"] != "success":
                    return group_result
                    
                grouped_data = group_result["outputs"][0]["value"]
                
                # Apply aggregations to each group
                for group in grouped_data:
                    group["aggregations"] = self._apply_aggregations(
                        group["items"], 
                        aggregations
                    )
                    
                # Log the operation
                self.logger.info(f"Aggregated data by {group_by} with {len(aggregations)} functions")
                
                # Return the grouped and aggregated data
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "data",
                            "value": grouped_data,
                            "type": "array"
                        }
                    ],
                    "performance_metrics": {
                        "execution_time_ms": 15,  # Example value
                        "memory_used_mb": 3       # Example value
                    }
                }
            else:
                # Apply aggregations to entire dataset
                aggregated_data = self._apply_aggregations(data, aggregations)
                
                # Log the operation
                self.logger.info(f"Aggregated data with {len(aggregations)} functions")
                
                # Return the aggregated data
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "data",
                            "value": aggregated_data,
                            "type": "object"
                        }
                    ],
                    "performance_metrics": {
                        "execution_time_ms": 10,  # Example value
                        "memory_used_mb": 2       # Example value
                    }
                }
                
        except Exception as e:
            return self._error_response(f"Error aggregating data: {str(e)}")
    
    async def transform_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply transformations to data.
        
        Args:
            parameters: Dictionary containing:
                - data: The data to transform
                - transformations: List of transformation operations
                
        Returns:
            Dictionary containing the transformed data
        """
        # Validate parameters
        if "data" not in parameters:
            return self._error_response("Data parameter is required")
        
        if "transformations" not in parameters:
            return self._error_response("Transformations parameter is required")
        
        data = parameters["data"]
        transformations = parameters["transformations"]
        
        # Ensure transformations is a list
        if not isinstance(transformations, list):
            return self._error_response("Transformations must be a list")
        
        try:
            # Apply transformations sequentially
            transformed_data = data
            for transform in transformations:
                transformed_data = self._apply_transformation(transformed_data, transform)
            
            # Log the operation
            self.logger.info(f"Applied {len(transformations)} transformations to data")
            
            # Return the transformed data
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "data",
                        "value": transformed_data,
                        "type": "mixed"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 12,  # Example value
                    "memory_used_mb": 2.5     # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error transforming data: {str(e)}")
    
    def _parse_data(self, data: Any, format: str, options: Dict[str, Any] = None) -> Any:
        """
        Parse data from a specific format.
        
        Args:
            data: The data to parse
            format: Data format (json, csv, yaml, xml)
            options: Parsing options
            
        Returns:
            Parsed data
        """
        options = options or {}
        
        if format == "json":
            if isinstance(data, str):
                return json.loads(data)
            return data
            
        elif format == "csv":
            delimiter = options.get("delimiter", ",")
            has_header = options.get("has_header", True)
            
            # Parse CSV string
            csv_reader = csv.reader(StringIO(data), delimiter=delimiter)
            
            if has_header:
                header = next(csv_reader)
                rows = []
                for row in csv_reader:
                    rows.append(dict(zip(header, row)))
                return rows
            else:
                return list(csv_reader)
                
        elif format == "yaml":
            return yaml.safe_load(data)
            
        elif format == "xml":
            root = ET.fromstring(data)
            return self._xml_to_dict(root)
            
        raise ValueError(f"Unsupported format: {format}")
    
    def _convert_data(self, data: Any, format: str, options: Dict[str, Any] = None) -> str:
        """
        Convert data to a specific format.
        
        Args:
            data: The data to convert
            format: Target format (json, csv, yaml, xml)
            options: Conversion options
            
        Returns:
            Converted data string
        """
        options = options or {}
        
        if format == "json":
            indent = options.get("indent", 2)
            return json.dumps(data, indent=indent)
            
        elif format == "csv":
            delimiter = options.get("delimiter", ",")
            
            if not isinstance(data, list):
                raise ValueError("Data must be a list for CSV conversion")
                
            output = StringIO()
            
            if data and isinstance(data[0], dict):
                # Get all possible keys
                fieldnames = set()
                for item in data:
                    fieldnames.update(item.keys())
                    
                writer = csv.DictWriter(output, fieldnames=list(fieldnames), delimiter=delimiter)
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(output, delimiter=delimiter)
                writer.writerows(data)
                
            return output.getvalue()
            
        elif format == "yaml":
            return yaml.safe_dump(data)
            
        elif format == "xml":
            return self._dict_to_xml(data)
            
        raise ValueError(f"Unsupported format: {format}")
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """
        Convert XML element to dictionary.
        
        Args:
            element: XML element
            
        Returns:
            Dictionary representation
        """
        result = {}
        
        # Add attributes
        for key, value in element.attrib.items():
            result[f"@{key}"] = value
            
        # Add children
        for child in element:
            child_dict = self._xml_to_dict(child)
            
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_dict)
            else:
                result[child.tag] = child_dict
                
        # Add text
        if element.text and element.text.strip():
            if result:
                result["#text"] = element.text.strip()
            else:
                return element.text.strip()
                
        return result
    
    def _dict_to_xml(self, data: Dict[str, Any], root_name: str = "root") -> str:
        """
        Convert dictionary to XML string.
        
        Args:
            data: Dictionary to convert
            root_name: Name of the root element
            
        Returns:
            XML string
        """
        def _dict_to_element(data, element):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.startswith('@'):
                        element.set(key[1:], str(value))
                    elif key == "#text":
                        element.text = str(value)
                    else:
                        if isinstance(value, list):
                            for item in value:
                                subelement = ET.SubElement(element, key)
                                _dict_to_element(item, subelement)
                        else:
                            subelement = ET.SubElement(element, key)
                            _dict_to_element(value, subelement)
            else:
                element.text = str(data)
        
        root = ET.Element(root_name)
        _dict_to_element(data, root)
        
        return ET.tostring(root, encoding="unicode")
    
    def _matches_criteria(self, item: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """
        Check if an item matches the filter criteria.
        
        Args:
            item: Item to check
            criteria: Filter criteria
            
        Returns:
            True if the item matches, False otherwise
        """
        for key, condition in criteria.items():
            if key == "$and":
                # All conditions must match
                if not all(self._matches_criteria(item, subcriteria) for subcriteria in condition):
                    return False
            elif key == "$or":
                # At least one condition must match
                if not any(self._matches_criteria(item, subcriteria) for subcriteria in condition):
                    return False
            elif key.startswith("$"):
                # Operator not supported
                raise ValueError(f"Unsupported operator: {key}")
            else:
                # Check nested keys
                value = self._get_nested_value(item, key)
                
                if isinstance(condition, dict):
                    # Operator-based condition
                    for op, target in condition.items():
                        if not self._apply_operator(value, op, target):
                            return False
                else:
                    # Equality condition
                    if value != condition:
                        return False
        
        return True
    
    def _apply_operator(self, value: Any, op: str, target: Any) -> bool:
        """
        Apply an operator to a value and target.
        
        Args:
            value: Value to check
            op: Operator ($eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $regex)
            target: Target value
            
        Returns:
            Result of the operation
        """
        if op == "$eq":
            return value == target
        elif op == "$ne":
            return value != target
        elif op == "$gt":
            return value > target
        elif op == "$gte":
            return value >= target
        elif op == "$lt":
            return value < target
        elif op == "$lte":
            return value <= target
        elif op == "$in":
            return value in target
        elif op == "$nin":
            return value not in target
        elif op == "$regex":
            import re
            return bool(re.match(target, str(value)))
        else:
            raise ValueError(f"Unsupported operator: {op}")
    
    def _get_nested_value(self, item: Dict[str, Any], key: str) -> Any:
        """
        Get a value from a nested dictionary.
        
        Args:
            item: Dictionary to get value from
            key: Key path (e.g., "user.address.city")
            
        Returns:
            Value at the key path
        """
        if "." not in key:
            return item.get(key)
            
        keys = key.split(".")
        value = item
        
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return None
            value = value[k]
            
        return value
    
    def _apply_aggregations(self, data: List[Dict[str, Any]], aggregations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply aggregation functions to data.
        
        Args:
            data: Data to aggregate
            aggregations: List of aggregation operations
            
        Returns:
            Aggregation results
        """
        results = {}
        
        for agg in aggregations:
            if "field" not in agg or "function" not in agg:
                continue
                
            field = agg["field"]
            function = agg["function"]
            alias = agg.get("alias", f"{function}_{field}")
            
            # Get field values
            values = [self._get_nested_value(item, field) for item in data]
            values = [v for v in values if v is not None]
            
            # Apply aggregation function
            if function == "sum":
                results[alias] = sum(values)
            elif function == "avg":
                results[alias] = sum(values) / len(values) if values else None
            elif function == "min":
                results[alias] = min(values) if values else None
            elif function == "max":
                results[alias] = max(values) if values else None
            elif function == "count":
                results[alias] = len(values)
            elif function == "distinct":
                results[alias] = len(set(values))
            elif function == "first":
                results[alias] = values[0] if values else None
            elif function == "last":
                results[alias] = values[-1] if values else None
                
        return results
    
    def _apply_transformation(self, data: Any, transform: Dict[str, Any]) -> Any:
        """
        Apply a transformation to data.
        
        Args:
            data: Data to transform
            transform: Transformation specification
            
        Returns:
            Transformed data
        """
        if "type" not in transform:
            raise ValueError("Transformation must specify a type")
            
        transform_type = transform["type"]
        
        if transform_type == "select":
            # Select specific fields
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                raise ValueError("Data must be a list of dictionaries for select transformation")
                
            fields = transform.get("fields", [])
            return [
                {field: self._get_nested_value(item, field) for field in fields}
                for item in data
            ]
            
        elif transform_type == "rename":
            # Rename fields
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                raise ValueError("Data must be a list of dictionaries for rename transformation")
                
            field_map = transform.get("field_map", {})
            result = []
            
            for item in data:
                new_item = item.copy()
                for old_name, new_name in field_map.items():
                    if old_name in new_item:
                        new_item[new_name] = new_item.pop(old_name)
                result.append(new_item)
                
            return result
            
        elif transform_type == "flatten":
            # Flatten nested structures
            if not isinstance(data, list):
                raise ValueError("Data must be a list for flatten transformation")
                
            prefix = transform.get("prefix", "")
            delimiter = transform.get("delimiter", "_")
            
            result = []
            for item in data:
                flattened = self._flatten_dict(item, prefix, delimiter)
                result.append(flattened)
                
            return result
            
        elif transform_type == "compute":
            # Compute new fields
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                raise ValueError("Data must be a list of dictionaries for compute transformation")
                
            field_name = transform.get("field_name")
            expression = transform.get("expression")
            
            if not field_name or not expression:
                raise ValueError("Field name and expression are required for compute transformation")
                
            result = []
            for item in data:
                new_item = item.copy()
                new_item[field_name] = self._evaluate_expression(item, expression)
                result.append(new_item)
                
            return result
            
        else:
            raise ValueError(f"Unsupported transformation type: {transform_type}")
    
    def _flatten_dict(self, data: Dict[str, Any], prefix: str = "", delimiter: str = "_") -> Dict[str, Any]:
        """
        Flatten a nested dictionary.
        
        Args:
            data: Dictionary to flatten
            prefix: Prefix for flattened keys
            delimiter: Delimiter for nested keys
            
        Returns:
            Flattened dictionary
        """
        result = {}
        
        def _flatten(obj, current_prefix):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{current_prefix}{delimiter}{key}" if current_prefix else key
                    _flatten(value, new_prefix)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    new_prefix = f"{current_prefix}{delimiter}{i}" if current_prefix else str(i)
                    _flatten(value, new_prefix)
            else:
                result[current_prefix] = obj
        
        _flatten(data, prefix)
        return result
    
    def _evaluate_expression(self, item: Dict[str, Any], expression: str) -> Any:
        """
        Evaluate an expression in the context of an item.
        
        Args:
            item: Dictionary containing context variables
            expression: Expression to evaluate
            
        Returns:
            Result of the expression
        """
        # Create a safe evaluation environment
        env = {
            "item": item,
            "get": self._get_nested_value,
            "sum": sum,
            "min": min,
            "max": max,
            "len": len,
            "abs": abs,
            "round": round,
            "int": int,
            "float": float,
            "str": str
        }
        
        # Add item fields to environment
        for key, value in item.items():
            if isinstance(key, str) and key.isidentifier():
                env[key] = value
                
        # Evaluate the expression
        return eval(expression, {"__builtins__": {}}, env)
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
            
        Returns:
            Error response dictionary
        """
        self.logger.error(message)
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
