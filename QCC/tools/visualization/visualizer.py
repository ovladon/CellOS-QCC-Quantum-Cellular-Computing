"""
QCC Visualization Tool

This module provides visualization capabilities for the Quantum Cellular Computing system,
making it easier to understand the system state, cell relationships, and performance metrics.

Features include:
- Interactive visualization of cell assemblies and connections
- Quantum trail pattern visualization
- Performance metrics dashboards
- Cell state and activity monitoring
- Recording playback and analysis
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.ticker import MaxNLocator
import networkx as nx
import numpy as np
import pandas as pd
from aiohttp import web
import aiohttp_cors
import yaml
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("qcc.visualizer")

# Constants
DEFAULT_PORT = 8083
DEFAULT_HOST = "localhost"
DEFAULT_RECORDINGS_DIR = os.path.join(os.getcwd(), "recordings")
DEFAULT_SCENARIOS_DIR = os.path.join(os.getcwd(), "scenarios")
DEFAULT_OUTPUT_DIR = os.path.join(os.getcwd(), "visualization_output")

class CellAssemblyVisualizer:
    """
    Visualizes cell assemblies and their connections.
    
    Attributes:
        solution (Dict): Solution data containing cells and connections
        output_dir (str): Directory to save visualization outputs
        interactive (bool): Whether to display interactive visualizations
    """
    
    def __init__(
        self, 
        solution: Dict[str, Any] = None, 
        output_dir: str = DEFAULT_OUTPUT_DIR,
        interactive: bool = True
    ):
        """
        Initialize the cell assembly visualizer.
        
        Args:
            solution: Solution data containing cells and connections
            output_dir: Directory to save visualization outputs
            interactive: Whether to display interactive visualizations
        """
        self.solution = solution
        self.output_dir = output_dir
        self.interactive = interactive
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.debug("Initialized CellAssemblyVisualizer")
    
    def set_solution(self, solution: Dict[str, Any]) -> None:
        """
        Set the solution to visualize.
        
        Args:
            solution: Solution data containing cells and connections
        """
        self.solution = solution
    
    def visualize_assembly(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> Optional[nx.Graph]:
        """
        Visualize the cell assembly as a network graph.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Returns:
            The NetworkX graph object if created, None otherwise
            
        Raises:
            ValueError: If no solution is set
        """
        if not self.solution:
            raise ValueError("No solution set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Create graph
            G = nx.DiGraph()
            
            # Add cells as nodes
            cells = self.solution.get("cells", {})
            for cell_id, cell_data in cells.items():
                G.add_node(
                    cell_id, 
                    type=cell_data.get("cell_type", "unknown"),
                    capability=cell_data.get("capability", "unknown"),
                    status=cell_data.get("status", "unknown")
                )
            
            # Add connections as edges
            connection_map = self.solution.get("connection_map", {})
            for source, targets in connection_map.items():
                for target in targets:
                    G.add_edge(source, target)
            
            # Create figure
            plt.figure(figsize=(12, 8))
            
            # Create positions
            pos = nx.spring_layout(G, seed=42)
            
            # Node colors based on capabilities
            capabilities = {
                data.get("capability", "unknown") 
                for _, data in cells.items()
            }
            capability_colors = {}
            colormap = plt.cm.get_cmap('tab10', len(capabilities))
            
            for i, capability in enumerate(sorted(capabilities)):
                capability_colors[capability] = colormap(i)
            
            node_colors = [
                capability_colors[cells[node].get("capability", "unknown")] 
                for node in G.nodes()
            ]
            
            # Draw nodes
            nx.draw_networkx_nodes(
                G, pos, 
                node_color=node_colors, 
                node_size=700, 
                alpha=0.8
            )
            
            # Draw edges
            nx.draw_networkx_edges(
                G, pos, 
                arrowstyle='->', 
                arrowsize=15, 
                edge_color='gray', 
                width=1.5
            )
            
            # Draw labels
            nx.draw_networkx_labels(
                G, pos, 
                labels={node: cells[node].get("cell_type", "unknown") for node in G.nodes()},
                font_size=10
            )
            
            # Draw capability legend
            legend_elements = [
                plt.Line2D(
                    [0], [0], 
                    marker='o', 
                    color='w', 
                    markerfacecolor=color, 
                    markersize=10, 
                    label=capability
                )
                for capability, color in capability_colors.items()
            ]
            plt.legend(handles=legend_elements, title="Capabilities")
            
            # Set title
            plt.title(
                f"Cell Assembly for Solution {self.solution.get('id', 'Unknown')}\n"
                f"{len(cells)} cells, {sum(len(targets) for targets in connection_map.values())} connections"
            )
            
            # Remove axis
            plt.axis('off')
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved assembly visualization to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
            return G
            
        except Exception as e:
            logger.error(f"Error visualizing cell assembly: {e}")
            plt.close()
            return None
    
    def visualize_capabilities(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Visualize the distribution of capabilities in the solution.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no solution is set
        """
        if not self.solution:
            raise ValueError("No solution set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Count capabilities
            cells = self.solution.get("cells", {})
            capabilities = {}
            
            for cell_id, cell_data in cells.items():
                capability = cell_data.get("capability", "unknown")
                if capability not in capabilities:
                    capabilities[capability] = 0
                capabilities[capability] += 1
            
            # Create figure
            plt.figure(figsize=(10, 6))
            
            # Plot bar chart
            plt.bar(capabilities.keys(), capabilities.values(), color='skyblue')
            
            # Add labels and title
            plt.xlabel('Capability')
            plt.ylabel('Number of Cells')
            plt.title(f"Capability Distribution in Solution {self.solution.get('id', 'Unknown')}")
            
            # Rotate x-axis labels if needed
            plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved capabilities visualization to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing capabilities: {e}")
            plt.close()
    
    def visualize_solution_summary(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Create a summary visualization of the solution with multiple charts.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no solution is set
        """
        if not self.solution:
            raise ValueError("No solution set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Create figure with subplots
            fig, axs = plt.subplots(2, 2, figsize=(15, 10))
            
            # Extract data
            cells = self.solution.get("cells", {})
            connection_map = self.solution.get("connection_map", {})
            
            # 1. Capability Distribution (top left)
            capabilities = {}
            for cell_id, cell_data in cells.items():
                capability = cell_data.get("capability", "unknown")
                if capability not in capabilities:
                    capabilities[capability] = 0
                capabilities[capability] += 1
            
            axs[0, 0].bar(capabilities.keys(), capabilities.values(), color='skyblue')
            axs[0, 0].set_title('Capability Distribution')
            axs[0, 0].set_xlabel('Capability')
            axs[0, 0].set_ylabel('Count')
            axs[0, 0].tick_params(axis='x', rotation=45)
            
            # 2. Cell Types (top right)
            cell_types = {}
            for cell_id, cell_data in cells.items():
                cell_type = cell_data.get("cell_type", "unknown")
                if cell_type not in cell_types:
                    cell_types[cell_type] = 0
                cell_types[cell_type] += 1
            
            axs[0, 1].pie(
                cell_types.values(), 
                labels=cell_types.keys(), 
                autopct='%1.1f%%',
                startangle=90
            )
            axs[0, 1].set_title('Cell Types')
            
            # 3. Connection Distribution (bottom left)
            outgoing_connections = {}
            for source, targets in connection_map.items():
                outgoing_connections[source] = len(targets)
            
            # Sort by number of connections
            sorted_cells = sorted(
                outgoing_connections.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]  # Top 10
            
            if sorted_cells:
                cell_ids, connection_counts = zip(*sorted_cells)
                # Shorten cell IDs for display
                short_ids = [f"{cid[:8]}..." for cid in cell_ids]
                
                axs[1, 0].bar(short_ids, connection_counts, color='lightgreen')
                axs[1, 0].set_title('Top Cells by Outgoing Connections')
                axs[1, 0].set_xlabel('Cell ID')
                axs[1, 0].set_ylabel('Connections')
                axs[1, 0].tick_params(axis='x', rotation=45)
            else:
                axs[1, 0].text(
                    0.5, 0.5, 
                    "No connections found", 
                    horizontalalignment='center',
                    verticalalignment='center'
                )
                axs[1, 0].set_title('Connection Distribution')
            
            # 4. Status Distribution (bottom right)
            statuses = {}
            for cell_id, cell_data in cells.items():
                status = cell_data.get("status", "unknown")
                if status not in statuses:
                    statuses[status] = 0
                statuses[status] += 1
            
            status_colors = {
                'active': 'green',
                'initialized': 'blue',
                'deactivated': 'orange',
                'released': 'red',
                'suspended': 'purple',
                'unknown': 'gray'
            }
            
            colors = [
                status_colors.get(status, 'gray') 
                for status in statuses.keys()
            ]
            
            axs[1, 1].bar(statuses.keys(), statuses.values(), color=colors)
            axs[1, 1].set_title('Cell Status Distribution')
            axs[1, 1].set_xlabel('Status')
            axs[1, 1].set_ylabel('Count')
            
            # Add solution ID as figure title
            solution_id = self.solution.get('id', 'Unknown')
            fig.suptitle(
                f"Solution Summary - ID: {solution_id}\n"
                f"Created: {self.solution.get('created_at', 'Unknown')} - "
                f"Cells: {len(cells)} - "
                f"Connections: {sum(len(targets) for targets in connection_map.values())}",
                fontsize=16
            )
            
            plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust for suptitle
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved solution summary to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing solution summary: {e}")
            plt.close()


class QuantumTrailVisualizer:
    """
    Visualizes quantum trail patterns and relationships.
    
    Attributes:
        trail_data (Dict): Quantum trail data containing patterns and relationships
        output_dir (str): Directory to save visualization outputs
        interactive (bool): Whether to display interactive visualizations
    """
    
    def __init__(
        self, 
        trail_data: Dict[str, Any] = None,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        interactive: bool = True
    ):
        """
        Initialize the quantum trail visualizer.
        
        Args:
            trail_data: Quantum trail data
            output_dir: Directory to save visualization outputs
            interactive: Whether to display interactive visualizations
        """
        self.trail_data = trail_data
        self.output_dir = output_dir
        self.interactive = interactive
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.debug("Initialized QuantumTrailVisualizer")
    
    def set_trail_data(self, trail_data: Dict[str, Any]) -> None:
        """
        Set the quantum trail data to visualize.
        
        Args:
            trail_data: Quantum trail data
        """
        self.trail_data = trail_data
    
    def visualize_pattern_graph(
        self, 
        filename: str = None, 
        show: bool = None,
        max_nodes: int = 50
    ) -> Optional[nx.Graph]:
        """
        Visualize the quantum trail as a pattern graph.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            max_nodes: Maximum number of nodes to display for readability
            
        Returns:
            The NetworkX graph object if created, None otherwise
            
        Raises:
            ValueError: If no trail data is set
        """
        if not self.trail_data:
            raise ValueError("No quantum trail data set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Create graph
            G = nx.Graph()
            
            # Process trail data
            assemblies = self.trail_data.get("assemblies", {})
            
            # Limit to max_nodes for readability
            if len(assemblies) > max_nodes:
                logger.warning(
                    f"Trail data contains {len(assemblies)} assemblies, "
                    f"limiting visualization to {max_nodes} for readability"
                )
                # Take the most recent entries
                sorted_assemblies = sorted(
                    assemblies.items(),
                    key=lambda x: x[1].get("timestamp", ""),
                    reverse=True
                )[:max_nodes]
                assemblies = dict(sorted_assemblies)
            
            # Add assembly nodes
            for signature, assembly_data in assemblies.items():
                # Truncate signature for readability
                short_sig = signature[:8] + "..." if len(signature) > 8 else signature
                
                G.add_node(
                    signature,
                    type="assembly",
                    label=short_sig,
                    solution_id=assembly_data.get("solution_id", "unknown"),
                    cell_count=len(assembly_data.get("cell_ids", [])),
                    timestamp=assembly_data.get("timestamp", "")
                )
            
            # Add pattern relationships
            patterns = self.trail_data.get("patterns", {})
            
            for pattern_type, pattern_data in patterns.items():
                # Add pattern node
                pattern_id = f"pattern_{pattern_type}"
                G.add_node(
                    pattern_id,
                    type="pattern",
                    label=f"Pattern {pattern_type}",
                    pattern_type=pattern_type
                )
                
                # Connect assemblies to pattern
                for cell_count, cell_sets in pattern_data.items():
                    for cell_set, signatures in cell_sets.items():
                        for signature in signatures:
                            if signature in G:  # Only connect existing nodes
                                G.add_edge(signature, pattern_id, weight=1)
            
            # Create figure
            plt.figure(figsize=(15, 10))
            
            # Create positions
            pos = nx.spring_layout(G, seed=42)
            
            # Node colors and sizes based on type
            node_colors = []
            node_sizes = []
            
            for node in G.nodes():
                node_type = G.nodes[node].get("type", "unknown")
                if node_type == "assembly":
                    node_colors.append('skyblue')
                    node_sizes.append(300)
                elif node_type == "pattern":
                    node_colors.append('orange')
                    node_sizes.append(800)
                else:
                    node_colors.append('gray')
                    node_sizes.append(300)
            
            # Draw nodes
            nx.draw_networkx_nodes(
                G, pos, 
                node_color=node_colors, 
                node_size=node_sizes, 
                alpha=0.8
            )
            
            # Draw edges
            nx.draw_networkx_edges(
                G, pos, 
                edge_color='gray', 
                width=0.5,
                alpha=0.5
            )
            
            # Draw labels
            nx.draw_networkx_labels(
                G, pos, 
                labels={
                    node: G.nodes[node].get("label", str(node)) 
                    for node in G.nodes()
                },
                font_size=8
            )
            
            # Draw legend
            legend_elements = [
                plt.Line2D(
                    [0], [0], 
                    marker='o', 
                    color='w', 
                    markerfacecolor='skyblue', 
                    markersize=10, 
                    label='Assembly'
                ),
                plt.Line2D(
                    [0], [0], 
                    marker='o', 
                    color='w', 
                    markerfacecolor='orange', 
                    markersize=15, 
                    label='Pattern'
                )
            ]
            plt.legend(handles=legend_elements, title="Node Types")
            
            # Set title
            plt.title(
                f"Quantum Trail Pattern Graph\n"
                f"{len([n for n in G.nodes() if G.nodes[n].get('type') == 'assembly'])} assemblies, "
                f"{len([n for n in G.nodes() if G.nodes[n].get('type') == 'pattern'])} patterns"
            )
            
            # Remove axis
            plt.axis('off')
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved quantum trail pattern graph to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
            return G
            
        except Exception as e:
            logger.error(f"Error visualizing quantum trail pattern graph: {e}")
            plt.close()
            return None
    
    def visualize_assembly_timeline(
        self, 
        filename: str = None, 
        show: bool = None,
        max_assemblies: int = 50
    ) -> None:
        """
        Visualize the timeline of assemblies in the quantum trail.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            max_assemblies: Maximum number of assemblies to display for readability
            
        Raises:
            ValueError: If no trail data is set
        """
        if not self.trail_data:
            raise ValueError("No quantum trail data set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Extract assembly data
            assemblies = self.trail_data.get("assemblies", {})
            
            # Create timeline data
            timeline_data = []
            
            for signature, assembly_data in assemblies.items():
                try:
                    timestamp = datetime.fromisoformat(assembly_data.get("timestamp", ""))
                    cell_count = len(assembly_data.get("cell_ids", []))
                    status = assembly_data.get("status", "unknown")
                    solution_id = assembly_data.get("solution_id", "unknown")
                    
                    timeline_data.append({
                        "signature": signature,
                        "timestamp": timestamp,
                        "cell_count": cell_count,
                        "status": status,
                        "solution_id": solution_id
                    })
                except Exception as e:
                    logger.warning(f"Error processing assembly {signature}: {e}")
            
            # Sort by timestamp
            timeline_data.sort(key=lambda x: x["timestamp"])
            
            # Limit to max_assemblies for readability
            if len(timeline_data) > max_assemblies:
                logger.warning(
                    f"Trail data contains {len(timeline_data)} assemblies, "
                    f"limiting visualization to {max_assemblies} for readability"
                )
                # Take the most recent entries
                timeline_data = timeline_data[-max_assemblies:]
            
            # Extract data for plotting
            timestamps = [item["timestamp"] for item in timeline_data]
            cell_counts = [item["cell_count"] for item in timeline_data]
            statuses = [item["status"] for item in timeline_data]
            
            # Create status color map
            status_colors = {
                'active': 'green',
                'released': 'red',
                'error': 'darkred',
                'unknown': 'gray'
            }
            
            colors = [status_colors.get(status, 'blue') for status in statuses]
            
            # Create figure
            plt.figure(figsize=(15, 8))
            
            # Plot timeline
            scatter = plt.scatter(
                timestamps, 
                cell_counts, 
                c=colors, 
                s=100, 
                alpha=0.7
            )
            
            # Add connecting line
            plt.plot(
                timestamps, 
                cell_counts, 
                'gray', 
                alpha=0.3
            )
            
            # Add labels and title
            plt.xlabel('Time')
            plt.ylabel('Cell Count')
            plt.title('Quantum Trail Assembly Timeline')
            
            # Format time axis
            plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.xticks(rotation=45)
            
            # Add status legend
            unique_statuses = set(statuses)
            legend_elements = [
                plt.Line2D(
                    [0], [0], 
                    marker='o', 
                    color='w', 
                    markerfacecolor=status_colors.get(status, 'blue'), 
                    markersize=10, 
                    label=status
                )
                for status in unique_statuses
            ]
            plt.legend(handles=legend_elements, title="Status")
            
            plt.tight_layout()
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved assembly timeline to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing assembly timeline: {e}")
            plt.close()
    
    def visualize_pattern_heatmap(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Visualize the pattern frequency as a heatmap.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no trail data is set
        """
        if not self.trail_data:
            raise ValueError("No quantum trail data set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Extract pattern data
            patterns = self.trail_data.get("patterns", {})
            
            # Prepare heatmap data
            pattern_types = list(patterns.keys())
            cell_counts = set()
            
            for pattern_type, pattern_data in patterns.items():
                for cell_count in pattern_data.keys():
                    cell_counts.add(int(cell_count))
            
            cell_counts = sorted(cell_counts)
            
            # Create the matrix
            matrix = np.zeros((len(pattern_types), len(cell_counts)))
            
            for i, pattern_type in enumerate(pattern_types):
                pattern_data = patterns[pattern_type]
                for j, cell_count in enumerate(cell_counts):
                    cell_count_str = str(cell_count)
                    if cell_count_str in pattern_data:
                        # Count the total number of signatures for this pattern and cell count
                        total_signatures = sum(
                            len(signatures) 
                            for signatures in pattern_data[cell_count_str].values()
                        )
                        matrix[i, j] = total_signatures
            
            # Create figure
            plt.figure(figsize=(12, 8))
            
            # Create heatmap
            im = plt.imshow(matrix, cmap='YlOrRd')
            
            # Add colorbar
            cbar = plt.colorbar(im)
            cbar.set_label('Number of Assemblies')
            
            # Add labels and title
            plt.xlabel('Cell Count')
            plt.ylabel('Pattern Type')
            plt.title('Quantum Trail Pattern Frequency Heatmap')
            
            # Set ticks
            plt.xticks(range(len(cell_counts)), cell_counts)
            plt.yticks(range(len(pattern_types)), pattern_types)
            
            # Add text annotations
            for i in range(len(pattern_types)):
                for j in range(len(cell_counts)):
                    value = matrix[i, j]
                    if value > 0:
                        text_color = 'white' if value > matrix.max() / 2 else 'black'
                        plt.text(
                            j, i, 
                            int(value), 
                            ha="center", 
                            va="center", 
                            color=text_color
                        )
            
            plt.tight_layout()
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved pattern heatmap to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing pattern heatmap: {e}")
            plt.close()


class PerformanceVisualizer:
    """
    Visualizes performance metrics from simulation recordings.
    
    Attributes:
        recording_data (Dict): Simulation recording data with events and metrics
        output_dir (str): Directory to save visualization outputs
        interactive (bool): Whether to display interactive visualizations
    """
    
    def __init__(
        self, 
        recording_data: Dict[str, Any] = None,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        interactive: bool = True
    ):
        """
        Initialize the performance visualizer.
        
        Args:
            recording_data: Simulation recording data
            output_dir: Directory to save visualization outputs
            interactive: Whether to display interactive visualizations
        """
        self.recording_data = recording_data
        self.output_dir = output_dir
        self.interactive = interactive
        
        # Extracted metrics
        self.metrics = {
            "solution_assembly_times": [],
            "cell_initialization_times": [],
            "capability_execution_times": [],
            "memory_usage": [],
            "cpu_usage": []
        }
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.debug("Initialized PerformanceVisualizer")
    
    def set_recording_data(self, recording_data: Dict[str, Any]) -> None:
        """
        Set the recording data to visualize.
        
        Args:
            recording_data: Simulation recording data
        """
        self.recording_data = recording_data
        self._extract_metrics()
    
    def _extract_metrics(self) -> None:
        """Extract performance metrics from the recording data."""
        if not self.recording_data:
            logger.warning("No recording data to extract metrics from")
            return
        
        # Reset metrics
        self.metrics = {
            "solution_assembly_times": [],
            "cell_initialization_times": [],
            "capability_execution_times": [],
            "memory_usage": [],
            "cpu_usage": []
        }
        
        # Extract events
        events = self.recording_data.get("events", [])
        
        for event in events:
            event_type = event.get("event_type", "")
            component = event.get("component", "")
            action = event.get("action", "")
            
            if component == "assembler" and action == "assemble_solution":
                # Assembly time metrics
                if event.get("result") and "performance_metrics" in event.get("result", {}):
                    metrics = event["result"]["performance_metrics"]
                    if "assembly_time_ms" in metrics:
                        self.metrics["solution_assembly_times"].append({
                            "timestamp": event.get("timestamp", ""),
                            "value": metrics["assembly_time_ms"]
                        })
            
            elif component == "cell" and action == "initialize":
                # Cell initialization metrics
                if event.get("result") and "performance_metrics" in event.get("result", {}):
                    metrics = event["result"]["performance_metrics"]
                    if "initialization_time_ms" in metrics:
                        self.metrics["cell_initialization_times"].append({
                            "timestamp": event.get("timestamp", ""),
                            "value": metrics["initialization_time_ms"]
                        })
            
            elif component == "cell" and action == "execute_capability":
                # Capability execution metrics
                if event.get("result") and "performance_metrics" in event.get("result", {}):
                    metrics = event["result"]["performance_metrics"]
                    if "execution_time_ms" in metrics:
                        capability = event.get("data", {}).get("capability", "unknown")
                        self.metrics["capability_execution_times"].append({
                            "timestamp": event.get("timestamp", ""),
                            "value": metrics["execution_time_ms"],
                            "capability": capability
                        })
            
            # Resource metrics
            if "resource_usage" in event.get("data", {}):
                resources = event["data"]["resource_usage"]
                if "memory_mb" in resources:
                    self.metrics["memory_usage"].append({
                        "timestamp": event.get("timestamp", ""),
                        "value": resources["memory_mb"]
                    })
                if "cpu_percent" in resources:
                    self.metrics["cpu_usage"].append({
                        "timestamp": event.get("timestamp", ""),
                        "value": resources["cpu_percent"]
                    })
    
    def visualize_assembly_times(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Visualize solution assembly times over the course of the simulation.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no metrics are available
        """
        if not self.metrics["solution_assembly_times"]:
            raise ValueError("No assembly time metrics available")
        
        show = self.interactive if show is None else show
        
        try:
            # Extract data
            timestamps = []
            values = []
            
            for item in self.metrics["solution_assembly_times"]:
                try:
                    timestamp = datetime.fromisoformat(item["timestamp"])
                    timestamps.append(timestamp)
                    values.append(item["value"])
                except Exception as e:
                    logger.warning(f"Error processing metric: {e}")
            
            # Create figure
            plt.figure(figsize=(12, 6))
            
            # Plot line chart
            plt.plot(timestamps, values, 'b-', marker='o')
            
            # Calculate moving average if enough points
            if len(values) > 5:
                window_size = min(5, len(values) // 2)
                moving_avg = np.convolve(values, np.ones(window_size)/window_size, mode='valid')
                # Adjust timestamps for the moving average
                ma_timestamps = timestamps[window_size-1:]
                plt.plot(ma_timestamps, moving_avg, 'r--', label=f'{window_size}-point Moving Average')
                plt.legend()
            
            # Add labels and title
            plt.xlabel('Time')
            plt.ylabel('Assembly Time (ms)')
            plt.title('Solution Assembly Times')
            
            # Format time axis
            plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))
            plt.xticks(rotation=45)
            
            # Add grid
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Add average line
            avg_time = sum(values) / len(values)
            plt.axhline(y=avg_time, color='g', linestyle='-', alpha=0.5)
            plt.text(
                timestamps[0], 
                avg_time * 1.05, 
                f'Average: {avg_time:.2f} ms', 
                color='g'
            )
            
            plt.tight_layout()
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved assembly times visualization to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing assembly times: {e}")
            plt.close()
    
    def visualize_capability_execution_times(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Visualize capability execution times by capability type.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no metrics are available
        """
        if not self.metrics["capability_execution_times"]:
            raise ValueError("No capability execution time metrics available")
        
        show = self.interactive if show is None else show
        
        try:
            # Group by capability
            capability_times = {}
            
            for item in self.metrics["capability_execution_times"]:
                capability = item.get("capability", "unknown")
                if capability not in capability_times:
                    capability_times[capability] = []
                capability_times[capability].append(item["value"])
            
            # Calculate statistics
            capabilities = []
            avg_times = []
            min_times = []
            max_times = []
            
            for capability, times in capability_times.items():
                capabilities.append(capability)
                avg_times.append(sum(times) / len(times))
                min_times.append(min(times))
                max_times.append(max(times))
            
            # Sort by average time
            sorted_indices = np.argsort(avg_times)[::-1]  # Descending
            capabilities = [capabilities[i] for i in sorted_indices]
            avg_times = [avg_times[i] for i in sorted_indices]
            min_times = [min_times[i] for i in sorted_indices]
            max_times = [max_times[i] for i in sorted_indices]
            
            # Create figure
            plt.figure(figsize=(12, 6))
            
            # Create positions
            positions = np.arange(len(capabilities))
            
            # Plot bars for average times
            plt.bar(
                positions, 
                avg_times, 
                color='skyblue', 
                label='Average Time'
            )
            
            # Add error bars for min/max
            plt.errorbar(
                positions, 
                avg_times, 
                yerr=[
                    [avg - min_val for avg, min_val in zip(avg_times, min_times)],
                    [max_val - avg for avg, max_val in zip(avg_times, max_times)]
                ],
                fmt='none', 
                color='black', 
                capsize=5
            )
            
            # Add labels and title
            plt.xlabel('Capability')
            plt.ylabel('Execution Time (ms)')
            plt.title('Capability Execution Times by Type')
            
            # Set x-ticks
            plt.xticks(positions, capabilities, rotation=45, ha='right')
            
            # Add grid
            plt.grid(True, linestyle='--', alpha=0.7, axis='y')
            
            # Add legend
            plt.legend()
            
            plt.tight_layout()
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved capability execution times visualization to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing capability execution times: {e}")
            plt.close()
    
    def visualize_resource_usage(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Visualize memory and CPU usage over time.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no metrics are available
        """
        if not self.metrics["memory_usage"] and not self.metrics["cpu_usage"]:
            raise ValueError("No resource usage metrics available")
        
        show = self.interactive if show is None else show
        
        try:
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
            
            # Process memory usage data
            if self.metrics["memory_usage"]:
                mem_timestamps = []
                mem_values = []
                
                for item in self.metrics["memory_usage"]:
                    try:
                        timestamp = datetime.fromisoformat(item["timestamp"])
                        mem_timestamps.append(timestamp)
                        mem_values.append(item["value"])
                    except Exception as e:
                        logger.warning(f"Error processing memory metric: {e}")
                
                # Plot memory usage
                ax1.plot(mem_timestamps, mem_values, 'b-', marker='o', label='Memory Usage')
                ax1.set_ylabel('Memory (MB)')
                ax1.set_title('Memory Usage Over Time')
                ax1.grid(True, linestyle='--', alpha=0.7)
                
                if mem_values:
                    # Add average line
                    avg_mem = sum(mem_values) / len(mem_values)
                    ax1.axhline(y=avg_mem, color='g', linestyle='-', alpha=0.5)
                    ax1.text(
                        mem_timestamps[0], 
                        avg_mem * 1.05, 
                        f'Average: {avg_mem:.2f} MB', 
                        color='g'
                    )
            
            # Process CPU usage data
            if self.metrics["cpu_usage"]:
                cpu_timestamps = []
                cpu_values = []
                
                for item in self.metrics["cpu_usage"]:
                    try:
                        timestamp = datetime.fromisoformat(item["timestamp"])
                        cpu_timestamps.append(timestamp)
                        cpu_values.append(item["value"])
                    except Exception as e:
                        logger.warning(f"Error processing CPU metric: {e}")
                
                # Plot CPU usage
                ax2.plot(cpu_timestamps, cpu_values, 'r-', marker='o', label='CPU Usage')
                ax2.set_xlabel('Time')
                ax2.set_ylabel('CPU (%)')
                ax2.set_title('CPU Usage Over Time')
                ax2.grid(True, linestyle='--', alpha=0.7)
                
                if cpu_values:
                    # Add average line
                    avg_cpu = sum(cpu_values) / len(cpu_values)
                    ax2.axhline(y=avg_cpu, color='g', linestyle='-', alpha=0.5)
                    ax2.text(
                        cpu_timestamps[0], 
                        avg_cpu * 1.05, 
                        f'Average: {avg_cpu:.2f}%', 
                        color='g'
                    )
            
            # Format time axis
            plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved resource usage visualization to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error visualizing resource usage: {e}")
            plt.close()
    
    def visualize_performance_dashboard(
        self, 
        filename: str = None, 
        show: bool = None
    ) -> None:
        """
        Create a comprehensive performance dashboard with multiple charts.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
        """
        if not self.recording_data:
            raise ValueError("No recording data set for visualization")
        
        show = self.interactive if show is None else show
        
        try:
            # Create figure with subplots
            fig = plt.figure(figsize=(15, 12))
            grid = plt.GridSpec(3, 2, figure=fig, hspace=0.4, wspace=0.3)
            
            # 1. Assembly Times Plot (top left)
            ax1 = fig.add_subplot(grid[0, 0])
            
            if self.metrics["solution_assembly_times"]:
                timestamps = []
                values = []
                
                for item in self.metrics["solution_assembly_times"]:
                    try:
                        timestamp = datetime.fromisoformat(item["timestamp"])
                        timestamps.append(timestamp)
                        values.append(item["value"])
                    except Exception:
                        pass
                
                if timestamps and values:
                    ax1.plot(timestamps, values, 'b-', marker='o')
                    ax1.set_ylabel('Time (ms)')
                    ax1.set_title('Solution Assembly Times')
                    ax1.grid(True, linestyle='--', alpha=0.7)
                    ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
                    ax1.tick_params(axis='x', rotation=45)
                    
                    # Add average line
                    avg_time = sum(values) / len(values)
                    ax1.axhline(y=avg_time, color='g', linestyle='-', alpha=0.5)
                    ax1.text(
                        timestamps[0], 
                        avg_time * 1.05, 
                        f'Avg: {avg_time:.2f} ms', 
                        color='g'
                    )
                else:
                    ax1.text(
                        0.5, 0.5,
                        "No assembly time data available",
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax1.transAxes
                    )
                    ax1.set_title('Solution Assembly Times')
            else:
                ax1.text(
                    0.5, 0.5,
                    "No assembly time data available",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax1.transAxes
                )
                ax1.set_title('Solution Assembly Times')
            
            # 2. Capability Execution Times (top right)
            ax2 = fig.add_subplot(grid[0, 1])
            
            if self.metrics["capability_execution_times"]:
                # Group by capability
                capability_times = {}
                
                for item in self.metrics["capability_execution_times"]:
                    capability = item.get("capability", "unknown")
                    if capability not in capability_times:
                        capability_times[capability] = []
                    capability_times[capability].append(item["value"])
                
                # Calculate statistics
                capabilities = []
                avg_times = []
                
                for capability, times in capability_times.items():
                    capabilities.append(capability)
                    avg_times.append(sum(times) / len(times))
                
                # Sort by average time
                sorted_indices = np.argsort(avg_times)[::-1]  # Descending
                capabilities = [capabilities[i] for i in sorted_indices]
                avg_times = [avg_times[i] for i in sorted_indices]
                
                # Plot bars
                positions = np.arange(len(capabilities))
                ax2.bar(positions, avg_times, color='skyblue')
                ax2.set_ylabel('Time (ms)')
                ax2.set_title('Average Capability Execution Times')
                ax2.set_xticks(positions)
                ax2.set_xticklabels(capabilities, rotation=45, ha='right')
                ax2.grid(True, linestyle='--', alpha=0.7, axis='y')
            else:
                ax2.text(
                    0.5, 0.5,
                    "No capability execution data available",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax2.transAxes
                )
                ax2.set_title('Average Capability Execution Times')
            
            # 3. Memory Usage (middle left)
            ax3 = fig.add_subplot(grid[1, 0])
            
            if self.metrics["memory_usage"]:
                timestamps = []
                values = []
                
                for item in self.metrics["memory_usage"]:
                    try:
                        timestamp = datetime.fromisoformat(item["timestamp"])
                        timestamps.append(timestamp)
                        values.append(item["value"])
                    except Exception:
                        pass
                
                if timestamps and values:
                    ax3.plot(timestamps, values, 'g-', marker='o')
                    ax3.set_ylabel('Memory (MB)')
                    ax3.set_title('Memory Usage Over Time')
                    ax3.grid(True, linestyle='--', alpha=0.7)
                    ax3.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
                    ax3.tick_params(axis='x', rotation=45)
                else:
                    ax3.text(
                        0.5, 0.5,
                        "No memory usage data available",
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax3.transAxes
                    )
                    ax3.set_title('Memory Usage Over Time')
            else:
                ax3.text(
                    0.5, 0.5,
                    "No memory usage data available",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax3.transAxes
                )
                ax3.set_title('Memory Usage Over Time')
            
            # 4. CPU Usage (middle right)
            ax4 = fig.add_subplot(grid[1, 1])
            
            if self.metrics["cpu_usage"]:
                timestamps = []
                values = []
                
                for item in self.metrics["cpu_usage"]:
                    try:
                        timestamp = datetime.fromisoformat(item["timestamp"])
                        timestamps.append(timestamp)
                        values.append(item["value"])
                    except Exception:
                        pass
                
                if timestamps and values:
                    ax4.plot(timestamps, values, 'r-', marker='o')
                    ax4.set_ylabel('CPU (%)')
                    ax4.set_title('CPU Usage Over Time')
                    ax4.grid(True, linestyle='--', alpha=0.7)
                    ax4.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
                    ax4.tick_params(axis='x', rotation=45)
                else:
                    ax4.text(
                        0.5, 0.5,
                        "No CPU usage data available",
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax4.transAxes
                    )
                    ax4.set_title('CPU Usage Over Time')
            else:
                ax4.text(
                    0.5, 0.5,
                    "No CPU usage data available",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax4.transAxes
                )
                ax4.set_title('CPU Usage Over Time')
            
            # 5. Event Distribution (bottom left)
            ax5 = fig.add_subplot(grid[2, 0])
            
            # Count events by type
            events = self.recording_data.get("events", [])
            event_types = {}
            
            for event in events:
                event_type = event.get("event_type", "unknown")
                if event_type not in event_types:
                    event_types[event_type] = 0
                event_types[event_type] += 1
            
            if event_types:
                # Plot pie chart
                labels = list(event_types.keys())
                sizes = list(event_types.values())
                ax5.pie(
                    sizes, 
                    labels=labels, 
                    autopct='%1.1f%%',
                    shadow=True, 
                    startangle=90
                )
                ax5.axis('equal')
                ax5.set_title('Event Type Distribution')
            else:
                ax5.text(
                    0.5, 0.5,
                    "No event data available",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax5.transAxes
                )
                ax5.set_title('Event Type Distribution')
            
            # 6. Error Rate Over Time (bottom right)
            ax6 = fig.add_subplot(grid[2, 1])
            
            # Analyze errors over time
            error_events = []
            total_events = []
            
            # Group events by time intervals (10 minute buckets)
            event_times = {}
            
            for event in events:
                try:
                    timestamp = datetime.fromisoformat(event.get("timestamp", ""))
                    # Create a 10-minute bucket key
                    bucket_key = timestamp.replace(
                        minute=timestamp.minute // 10 * 10,
                        second=0,
                        microsecond=0
                    )
                    
                    if bucket_key not in event_times:
                        event_times[bucket_key] = {"total": 0, "errors": 0}
                    
                    event_times[bucket_key]["total"] += 1
                    
                    if event.get("event_type") == "error" or event.get("error"):
                        event_times[bucket_key]["errors"] += 1
                except Exception:
                    pass
            
            if event_times:
                # Sort by time
                sorted_times = sorted(event_times.items())
                timestamps = [t[0] for t in sorted_times]
                error_rates = [
                    (t[1]["errors"] / t[1]["total"]) * 100 if t[1]["total"] > 0 else 0 
                    for t in sorted_times
                ]
                
                # Plot error rate
                ax6.plot(timestamps, error_rates, 'm-', marker='o')
                ax6.set_ylabel('Error Rate (%)')
                ax6.set_title('Error Rate Over Time')
                ax6.grid(True, linestyle='--', alpha=0.7)
                ax6.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
                ax6.tick_params(axis='x', rotation=45)
                
                # Set y-axis to start at 0 and max at 100%
                ax6.set_ylim(0, max(100, max(error_rates) * 1.1))
            else:
                ax6.text(
                    0.5, 0.5,
                    "No error data available",
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax6.transAxes
                )
                ax6.set_title('Error Rate Over Time')
            
            # Add title for the entire dashboard
            plt.suptitle(
                f"Performance Dashboard - {self.recording_data.get('scenario_name', 'Unknown Scenario')}",
                fontsize=16
            )
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved performance dashboard to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error creating performance dashboard: {e}")
            plt.close()


class RecordingPlaybackVisualizer:
    """
    Visualizes the playback of a simulation recording, showing the evolution 
    of the system state over time.
    
    Attributes:
        recording_data (Dict): Simulation recording data with events and metrics
        output_dir (str): Directory to save visualization outputs
        interactive (bool): Whether to display interactive visualizations
    """
    
    def __init__(
        self, 
        recording_data: Dict[str, Any] = None,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        interactive: bool = True
    ):
        """
        Initialize the recording playback visualizer.
        
        Args:
            recording_data: Simulation recording data
            output_dir: Directory to save visualization outputs
            interactive: Whether to display interactive visualizations
        """
        self.recording_data = recording_data
        self.output_dir = output_dir
        self.interactive = interactive
        
        # Processed state for animation
        self.states = []
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.debug("Initialized RecordingPlaybackVisualizer")
    
    def set_recording_data(self, recording_data: Dict[str, Any]) -> None:
        """
        Set the recording data to visualize.
        
        Args:
            recording_data: Simulation recording data
        """
        self.recording_data = recording_data
        self._process_states()
    
    def _process_states(self) -> None:
        """Process the recording data into a series of system states for animation."""
        if not self.recording_data:
            logger.warning("No recording data to process states from")
            return
        
        # Reset states
        self.states = []
        
        # Extract events
        events = self.recording_data.get("events", [])
        
        # Track the current state
        current_state = {
            "solutions": {},  # Map of solution IDs to solution data
            "cells": {},      # Map of cell IDs to cell data
            "connections": {},  # Map of source cell IDs to target cell IDs
            "timestamp": None,
            "event_count": 0
        }
        
        # Process events in chronological order
        for event in events:
            # Clone the current state
            new_state = {
                "solutions": current_state["solutions"].copy(),
                "cells": current_state["cells"].copy(),
                "connections": current_state["connections"].copy(),
                "timestamp": event.get("timestamp", "unknown"),
                "event_count": current_state["event_count"] + 1,
                "event_type": event.get("event_type", "unknown"),
                "component": event.get("component", "unknown"),
                "action": event.get("action", "unknown")
            }
            
            # Update state based on event
            event_type = event.get("event_type", "")
            component = event.get("component", "")
            action = event.get("action", "")
            
            if component == "assembler" and action == "assemble_solution":
                # New solution created
                if event.get("result"):
                    solution = event["result"]
                    solution_id = solution.get("id", "unknown")
                    
                    # Add to solutions
                    new_state["solutions"][solution_id] = solution
                    
                    # Add cells
                    for cell_id, cell_data in solution.get("cells", {}).items():
                        new_state["cells"][cell_id] = {
                            "id": cell_id,
                            "solution_id": solution_id,
                            "type": cell_data.get("cell_type", "unknown"),
                            "capability": cell_data.get("capability", "unknown"),
                            "status": cell_data.get("status", "unknown")
                        }
                    
                    # Add connections
                    for source, targets in solution.get("connection_map", {}).items():
                        new_state["connections"][source] = targets
            
            elif component == "assembler" and action == "release_solution":
                # Solution released
                if event.get("data"):
                    solution_id = event["data"].get("solution_id", "")
                    
                    if solution_id in new_state["solutions"]:
                        # Remove solution
                        del new_state["solutions"][solution_id]
                        
                        # Remove associated cells
                        cells_to_remove = [
                            cell_id 
                            for cell_id, cell_data in new_state["cells"].items() 
                            if cell_data.get("solution_id") == solution_id
                        ]
                        for cell_id in cells_to_remove:
                            del new_state["cells"][cell_id]
                        
                        # Remove associated connections
                        connections_to_remove = [
                            source 
                            for source in new_state["connections"] 
                            if source in cells_to_remove
                        ]
                        for source in connections_to_remove:
                            del new_state["connections"][source]
            
            elif component == "cell" and action == "activate":
                # Cell activated
                if event.get("data"):
                    cell_id = event["data"].get("cell_id", "")
                    
                    if cell_id in new_state["cells"]:
                        new_state["cells"][cell_id]["status"] = "active"
            
            elif component == "cell" and action == "deactivate":
                # Cell deactivated
                if event.get("data"):
                    cell_id = event["data"].get("cell_id", "")
                    
                    if cell_id in new_state["cells"]:
                        new_state["cells"][cell_id]["status"] = "deactivated"
            
            elif component == "cell" and action == "suspend":
                # Cell suspended
                if event.get("data"):
                    cell_id = event["data"].get("cell_id", "")
                    
                    if cell_id in new_state["cells"]:
                        new_state["cells"][cell_id]["status"] = "suspended"
            
            elif component == "cell" and action == "resume":
                # Cell resumed
                if event.get("data"):
                    cell_id = event["data"].get("cell_id", "")
                    
                    if cell_id in new_state["cells"]:
                        new_state["cells"][cell_id]["status"] = "active"
            
            elif component == "cell" and action == "release":
                # Cell released
                if event.get("data"):
                    cell_id = event["data"].get("cell_id", "")
                    
                    if cell_id in new_state["cells"]:
                        new_state["cells"][cell_id]["status"] = "released"
            
            elif component == "cell" and action == "connect_to":
                # Connection established
                if event.get("data"):
                    source_id = event["data"].get("source_id", "")
                    target_id = event["data"].get("target_id", "")
                    
                    if source_id and target_id:
                        if source_id not in new_state["connections"]:
                            new_state["connections"][source_id] = []
                        if target_id not in new_state["connections"][source_id]:
                            new_state["connections"][source_id].append(target_id)
            
            # Add the new state to the list
            self.states.append(new_state)
            
            # Update the current state
            current_state = new_state
    
    def create_animation(
        self, 
        filename: str = None,
        fps: int = 5,
        show: bool = None
    ) -> None:
        """
        Create an animation of the system state evolution.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            fps: Frames per second for the animation
            show: Whether to display the animation (defaults to self.interactive)
            
        Raises:
            ValueError: If no states are available
        """
        if not self.states:
            raise ValueError("No states available to animate")
        
        show = self.interactive if show is None else show
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 8))
            
            def update(frame):
                """Update function for animation."""
                ax.clear()
                
                state = self.states[frame]
                
                # Create a graph from the current state
                G = nx.DiGraph()
                
                # Add cells as nodes
                for cell_id, cell_data in state["cells"].items():
                    G.add_node(
                        cell_id, 
                        type=cell_data.get("type", "unknown"),
                        capability=cell_data.get("capability", "unknown"),
                        status=cell_data.get("status", "unknown"),
                        solution_id=cell_data.get("solution_id", "unknown")
                    )
                
                # Add connections as edges
                for source, targets in state["connections"].items():
                    for target in targets:
                        if source in G.nodes() and target in G.nodes():
                            G.add_edge(source, target)
                
                # Check if graph is empty
                if not G.nodes():
                    ax.text(
                        0.5, 0.5,
                        "No cells in current state",
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=ax.transAxes
                    )
                    ax.set_title(f"System State - Event {frame+1}/{len(self.states)}")
                    return
                
                # Create positions
                pos = nx.spring_layout(G, seed=42)
                
                # Node colors based on status
                status_colors = {
                    'active': 'green',
                    'initialized': 'blue',
                    'deactivated': 'orange',
                    'released': 'red',
                    'suspended': 'purple',
                    'unknown': 'gray'
                }
                
                node_colors = [
                    status_colors.get(G.nodes[node]["status"], "gray")
                    for node in G.nodes()
                ]
                
                # Node sizes based on solution
                solution_groups = {}
                for node in G.nodes():
                    solution_id = G.nodes[node]["solution_id"]
                    if solution_id not in solution_groups:
                        solution_groups[solution_id] = []
                    solution_groups[solution_id].append(node)
                
                # Draw nodes by solution group
                for solution_id, nodes in solution_groups.items():
                    nx.draw_networkx_nodes(
                        G, pos,
                        nodelist=nodes,
                        node_color=[status_colors.get(G.nodes[node]["status"], "gray") for node in nodes],
                        node_size=300,
                        alpha=0.8,
                        label=f"Solution {solution_id[:6]}..."
                    )
                
                # Draw edges
                nx.draw_networkx_edges(
                    G, pos,
                    edgelist=G.edges(),
                    arrows=True,
                    arrowsize=15,
                    edge_color='gray',
                    width=1.0,
                    alpha=0.6
                )
                
                # Draw labels
                nx.draw_networkx_labels(
                    G, pos,
                    labels={
                        node: f"{G.nodes[node]['type']}\n{G.nodes[node]['capability'][:8]}"
                        for node in G.nodes()
                    },
                    font_size=8,
                    font_color='black'
                )
                
                # Add event info
                event_str = f"Event {frame+1}/{len(self.states)}: "
                event_str += f"{state.get('component', 'unknown')}.{state.get('action', 'unknown')}"
                if state.get('event_type') == 'error':
                    event_str += " (ERROR)"
                
                ax.text(
                    0.5, 0.02,
                    event_str,
                    horizontalalignment='center',
                    verticalalignment='bottom',
                    transform=ax.transAxes,
                    bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5')
                )
                
                # Add timestamp
                timestamp = state.get("timestamp", "unknown")
                ax.text(
                    0.98, 0.98,
                    f"Time: {timestamp}",
                    horizontalalignment='right',
                    verticalalignment='top',
                    transform=ax.transAxes,
                    fontsize=8
                )
                
                # Add status legend
                status_patches = [
                    plt.Line2D(
                        [0], [0],
                        marker='o',
                        color='w',
                        markerfacecolor=color,
                        markersize=8,
                        label=status
                    )
                    for status, color in status_colors.items()
                    if any(G.nodes[node]["status"] == status for node in G.nodes())
                ]
                
                if status_patches:
                    status_legend = ax.legend(
                        handles=status_patches,
                        title="Cell Status",
                        loc='upper right',
                        fontsize=8
                    )
                    ax.add_artist(status_legend)
                
                # Add solution legend if more than one solution
                if len(solution_groups) > 1:
                    solution_patches = [
                        plt.Line2D(
                            [0], [0],
                            marker='o',
                            color='w',
                            markerfacecolor='gray',
                            markersize=8,
                            label=f"Solution {sol_id[:6]}..."
                        )
                        for sol_id in solution_groups.keys()
                    ]
                    
                    solution_legend = ax.legend(
                        handles=solution_patches,
                        title="Solutions",
                        loc='upper left',
                        fontsize=8
                    )
                    ax.add_artist(solution_legend)
                
                # Set title
                cells_count = len(G.nodes())
                connections_count = len(G.edges())
                solutions_count = len(solution_groups)
                
                ax.set_title(
                    f"System State Evolution\n"
                    f"Cells: {cells_count}, Connections: {connections_count}, Solutions: {solutions_count}"
                )
                
                # Remove axis
                ax.axis('off')
            
            # Create animation
            ani = animation.FuncAnimation(
                fig, 
                update, 
                frames=len(self.states),
                interval=1000/fps,  # milliseconds
                repeat=True
            )
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                writer = animation.FFMpegWriter(fps=fps, bitrate=1800)
                ani.save(full_path, writer=writer)
                logger.info(f"Saved animation to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error creating animation: {e}")
            plt.close()
    
    def create_event_timeline(
        self, 
        filename: str = None,
        show: bool = None
    ) -> None:
        """
        Create a timeline visualization of events in the recording.
        
        Args:
            filename: Output filename (if None, a default name is generated)
            show: Whether to display the visualization (defaults to self.interactive)
            
        Raises:
            ValueError: If no states are available
        """
        if not self.states:
            raise ValueError("No states available to visualize")
        
        show = self.interactive if show is None else show
        
        try:
            # Extract event data
            events = []
            for i, state in enumerate(self.states):
                try:
                    timestamp = datetime.fromisoformat(state.get("timestamp", ""))
                    events.append({
                        "index": i,
                        "timestamp": timestamp,
                        "component": state.get("component", "unknown"),
                        "action": state.get("action", "unknown"),
                        "type": state.get("event_type", "unknown"),
                        "solutions_count": len(state.get("solutions", {})),
                        "cells_count": len(state.get("cells", {}))
                    })
                except Exception as e:
                    logger.warning(f"Error processing event state: {e}")
            
            if not events:
                raise ValueError("No valid events to visualize")
            
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True, gridspec_kw={'height_ratios': [1, 3]})
            
            # Extract data for plotting
            timestamps = [event["timestamp"] for event in events]
            component_actions = [f"{event['component']}.{event['action']}" for event in events]
            cells_counts = [event["cells_count"] for event in events]
            solutions_counts = [event["solutions_count"] for event in events]
            
            # Create colors based on event type
            event_colors = {
                'request': 'blue',
                'response': 'green',
                'error': 'red',
                'unknown': 'gray'
            }
            
            colors = [event_colors.get(event["type"], "gray") for event in events]
            
            # Plot 1: Count of solutions and cells over time
            ax1.plot(timestamps, cells_counts, 'b-', marker='o', label='Cells')
            ax1.plot(timestamps, solutions_counts, 'r-', marker='s', label='Solutions')
            ax1.set_ylabel('Count')
            ax1.set_title('System Size Evolution')
            ax1.legend()
            ax1.grid(True, linestyle='--', alpha=0.7)
            
            # Plot 2: Events timeline
            y_positions = np.arange(len(events))
            ax2.scatter(timestamps, y_positions, c=colors, s=100, alpha=0.8)
            
            # Add event labels
            for i, txt in enumerate(component_actions):
                ax2.annotate(
                    txt,
                    (timestamps[i], y_positions[i]),
                    xytext=(5, 0),
                    textcoords="offset points",
                    fontsize=8,
                    va='center'
                )
            
            # Customize plot
            ax2.set_yticks(y_positions)
            ax2.set_yticklabels([f"Event {i+1}" for i in y_positions])
            ax2.set_xlabel('Time')
            ax2.set_title('Event Timeline')
            ax2.grid(True, linestyle='--', alpha=0.7)
            
            # Add event type legend
            legend_elements = [
                plt.Line2D(
                    [0], [0],
                    marker='o',
                    color='w',
                    markerfacecolor=color,
                    markersize=10,
                    label=event_type
                )
                for event_type, color in event_colors.items()
                if any(event["type"] == event_type for event in events)
            ]
            ax2.legend(handles=legend_elements, title="Event Types")
            
            # Format time axis
            plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))
            plt.xticks(rotation=45)
            
            # Add main title
            recording_name = self.recording_data.get("scenario_name", "Unknown Recording")
            plt.suptitle(f"Event Timeline - {recording_name}", fontsize=16)
            
            plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for suptitle
            
            # Save if filename provided
            if filename:
                full_path = os.path.join(self.output_dir, filename)
                plt.savefig(full_path, bbox_inches='tight')
                logger.info(f"Saved event timeline to {full_path}")
            
            # Show if requested
            if show:
                plt.show()
            else:
                plt.close()
            
        except Exception as e:
            logger.error(f"Error creating event timeline: {e}")
            plt.close()


class DashboardServer:
    """
    Provides a web-based dashboard for visualizing QCC systems.
    
    The dashboard server serves interactive visualizations through
    a web interface, allowing real-time monitoring and analysis.
    
    Attributes:
        host (str): Host address to bind the server
        port (int): Port to bind the server
        recordings_dir (str): Directory containing recording files
        scenarios_dir (str): Directory containing scenario files
        app (web.Application): AIOHTTP web application instance
    """
    
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        recordings_dir: str = DEFAULT_RECORDINGS_DIR,
        scenarios_dir: str = DEFAULT_SCENARIOS_DIR
    ):
        """
        Initialize the dashboard server.
        
        Args:
            host: Host address to bind the server
            port: Port to bind the server
            recordings_dir: Directory containing recording files
            scenarios_dir: Directory containing scenario files
        """
        self.host = host
        self.port = port
        self.recordings_dir = recordings_dir
        self.scenarios_dir = scenarios_dir
        
        # Create AIOHTTP application
        self.app = web.Application()
        
        # Setup routes
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/recordings', self.handle_get_recordings)
        self.app.router.add_get('/api/scenarios', self.handle_get_scenarios)
        self.app.router.add_get('/api/recording/{recording_id}', self.handle_get_recording)
        self.app.router.add_get('/api/recording/{recording_id}/analysis', self.handle_get_recording_analysis)
        self.app.router.add_get('/api/recording/{recording_id}/visualize/{vis_type}', self.handle_visualize_recording)
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        
        # Apply CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        logger.info(f"Initialized dashboard server on {host}:{port}")
    
    async def handle_index(self, request: web.Request) -> web.Response:
        """
        Handle requests to the index page.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with the dashboard HTML
        """
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>QCC Visualization Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {
                    padding-top: 2rem;
                    background-color: #f5f5f5;
                }
                .header {
                    margin-bottom: 2rem;
                }
                .card {
                    margin-bottom: 1.5rem;
                    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
                }
                .chart-container {
                    height: 400px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>QCC Visualization Dashboard</h1>
                    <p class="lead">View and analyze Quantum Cellular Computing simulations</p>
                </div>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                Recordings
                            </div>
                            <div class="card-body">
                                <select id="recordingSelect" class="form-select mb-3">
                                    <option value="">Select a recording...</option>
                                </select>
                                <button id="loadRecordingBtn" class="btn btn-primary" disabled>Load Recording</button>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="card-header">
                                Visualization Options
                            </div>
                            <div class="card-body">
                                <div class="d-grid gap-2">
                                    <button id="performanceDashboardBtn" class="btn btn-outline-primary" disabled>Performance Dashboard</button>
                                    <button id="cellAssemblyBtn" class="btn btn-outline-primary" disabled>Cell Assembly</button>
                                    <button id="eventTimelineBtn" class="btn btn-outline-primary" disabled>Event Timeline</button>
                                    <button id="resourceUsageBtn" class="btn btn-outline-primary" disabled>Resource Usage</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-header">
                                <span id="visualizationTitle">Visualization</span>
                            </div>
                            <div class="card-body">
                                <div id="visualization" class="chart-container">
                                    <div class="d-flex justify-content-center align-items-center h-100">
                                        <p class="text-muted">Select a recording to visualize</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card">
                            <div class="card-header">
                                Recording Information
                            </div>
                            <div class="card-body">
                                <div id="recordingInfo">
                                    <p class="text-muted">No recording selected</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                // Global variables
                let currentRecording = null;
                let recordingData = null;
                
                // Load recordings on page load
                document.addEventListener('DOMContentLoaded', async () => {
                    try {
                        const response = await fetch('/api/recordings');
                        const recordings = await response.json();
                        
                        const select = document.getElementById('recordingSelect');
                        recordings.forEach(rec => {
                            const option = document.createElement('option');
                            option.value = rec.id;
                            option.textContent = `${rec.scenario_name} (${rec.timestamp})`;
                            select.appendChild(option);
                        });
                        
                        // Enable load button when a recording is selected
                        select.addEventListener('change', () => {
                            document.getElementById('loadRecordingBtn').disabled = !select.value;
                        });
                        
                        // Load recording when button is clicked
                        document.getElementById('loadRecordingBtn').addEventListener('click', loadRecording);
                        
                        // Setup visualization buttons
                        document.getElementById('performanceDashboardBtn').addEventListener('click', () => {
                            visualizeRecording('performance_dashboard');
                        });
                        
                        document.getElementById('cellAssemblyBtn').addEventListener('click', () => {
                            visualizeRecording('cell_assembly');
                        });
                        
                        document.getElementById('eventTimelineBtn').addEventListener('click', () => {
                            visualizeRecording('event_timeline');
                        });
                        
                        document.getElementById('resourceUsageBtn').addEventListener('click', () => {
                            visualizeRecording('resource_usage');
                        });
                        
                    } catch (error) {
                        console.error('Error loading recordings:', error);
                        alert('Failed to load recordings. See console for details.');
                    }
                });
                
                // Load recording function
                async function loadRecording() {
                    const recordingId = document.getElementById('recordingSelect').value;
                    if (!recordingId) return;
                    
                    try {
                        // Fetch recording data
                        const response = await fetch(`/api/recording/${recordingId}`);
                        recordingData = await response.json();
                        currentRecording = recordingId;
                        
                        // Update recording info
                        const infoDiv = document.getElementById('recordingInfo');
                        infoDiv.innerHTML = `
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Scenario:</strong> ${recordingData.scenario_name}</p>
                                    <p><strong>Duration:</strong> ${recordingData.duration_seconds.toFixed(2)} seconds</p>
                                    <p><strong>Events:</strong> ${recordingData.event_count}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Start Time:</strong> ${recordingData.start_time}</p>
                                    <p><strong>End Time:</strong> ${recordingData.end_time}</p>
                                    <p><strong>ID:</strong> ${recordingData.id}</p>
                                </div>
                            </div>
                        `;
                        
                        // Enable visualization buttons
                        document.querySelectorAll('.btn-outline-primary').forEach(btn => {
                            btn.disabled = false;
                        });
                        
                        // Load performance dashboard by default
                        visualizeRecording('performance_dashboard');
                        
                    } catch (error) {
                        console.error('Error loading recording:', error);
                        alert('Failed to load recording. See console for details.');
                    }
                }
                
                // Visualize recording function
                async function visualizeRecording(visType) {
                    if (!currentRecording) return;
                    
                    try {
                        // Update visualization title
                        const titleMap = {
                            'performance_dashboard': 'Performance Dashboard',
                            'cell_assembly': 'Cell Assembly',
                            'event_timeline': 'Event Timeline',
                            'resource_usage': 'Resource Usage'
                        };
                        
                        document.getElementById('visualizationTitle').textContent = 
                            titleMap[visType] || 'Visualization';
                        
                        // Fetch visualization
                        const response = await fetch(`/api/recording/${currentRecording}/visualize/${visType}`);
                        const data = await response.json();
                        
                        // Display visualization
                        const visDiv = document.getElementById('visualization');
                        
                        if (data.error) {
                            visDiv.innerHTML = `
                                <div class="alert alert-danger" role="alert">
                                    ${data.error}
                                </div>
                            `;
                            return;
                        }
                        
                        // Clear previous visualization
                        visDiv.innerHTML = '';
                        
                        // Render the visualization based on the type
                        if (data.plot_data) {
                            Plotly.newPlot(visDiv, 
                                JSON.parse(data.plot_data.data), 
                                JSON.parse(data.plot_data.layout), 
                                {responsive: true}
                            );
                        } else if (data.image_data) {
                            const img = document.createElement('img');
                            img.src = `data:image/png;base64,${data.image_data}`;
                            img.className = 'img-fluid';
                            visDiv.appendChild(img);
                        } else {
                            visDiv.innerHTML = `
                                <div class="alert alert-warning" role="alert">
                                    No visualization data available
                                </div>
                            `;
                        }
                        
                    } catch (error) {
                        console.error('Error visualizing recording:', error);
                        alert('Failed to visualize recording. See console for details.');
                    }
                }
            </script>
        </body>
        </html>
        """
        
        return web.Response(text=html, content_type='text/html')
    
    async def handle_get_recordings(self, request: web.Request) -> web.Response:
        """
        Handle requests for the list of available recordings.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with recording information
        """
        recordings = []
        
        try:
            for filename in os.listdir(self.recordings_dir):
                if filename.endswith('.json'):
                    path = os.path.join(self.recordings_dir, filename)
                    with open(path, 'r') as f:
                        data = json.load(f)
                    
                    recordings.append({
                        "id": os.path.splitext(filename)[0],
                        "scenario_name": data.get("scenario_name", "Unknown"),
                        "timestamp": data.get("start_time", "Unknown"),
                        "duration_seconds": data.get("duration_seconds", 0),
                        "event_count": data.get("event_count", 0)
                    })
        except Exception as e:
            logger.error(f"Error listing recordings: {e}")
            return web.json_response({"error": str(e)}, status=500)
        
        # Sort by timestamp (newest first)
        recordings.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return web.json_response(recordings)
    
    async def handle_get_scenarios(self, request: web.Request) -> web.Response:
        """
        Handle requests for the list of available scenarios.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with scenario information
        """
        scenarios = []
        
        try:
            for filename in os.listdir(self.scenarios_dir):
                if filename.endswith(('.yaml', '.yml', '.json')):
                    path = os.path.join(self.scenarios_dir, filename)
                    
                    try:
                        if filename.endswith('.json'):
                            with open(path, 'r') as f:
                                data = json.load(f)
                        else:
                            with open(path, 'r') as f:
                                data = yaml.safe_load(f)
                        
                        scenarios.append({
                            "id": os.path.splitext(filename)[0],
                            "name": data.get("name", "Unknown"),
                            "description": data.get("description", ""),
                            "request_count": len(data.get("requests", [])),
                            "file_path": path
                        })
                    except Exception as e:
                        logger.warning(f"Error loading scenario {filename}: {e}")
                        scenarios.append({
                            "id": os.path.splitext(filename)[0],
                            "name": filename,
                            "description": "Error loading scenario",
                            "request_count": 0,
                            "file_path": path,
                            "error": str(e)
                        })
        except Exception as e:
            logger.error(f"Error listing scenarios: {e}")
            return web.json_response({"error": str(e)}, status=500)
        
        # Sort by name
        scenarios.sort(key=lambda x: x["name"])
        
        return web.json_response(scenarios)
    
    async def handle_get_recording(self, request: web.Request) -> web.Response:
        """
        Handle requests for a specific recording.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with recording data
        """
        recording_id = request.match_info.get('recording_id')
        
        try:
            # Find the recording file
            for filename in os.listdir(self.recordings_dir):
                if filename.startswith(recording_id) and filename.endswith('.json'):
                    path = os.path.join(self.recordings_dir, filename)
                    with open(path, 'r') as f:
                        data = json.load(f)
                    return web.json_response(data)
            
            return web.json_response(
                {"error": f"Recording not found: {recording_id}"}, 
                status=404
            )
        except Exception as e:
            logger.error(f"Error retrieving recording: {e}", exc_info=True)
            return web.json_response(
                {"error": f"Error retrieving recording: {str(e)}"},
                status=500
            )
    
    async def handle_get_cell_graph(self, request: web.Request) -> web.Response:
        """
        Handle requests for cell graph visualization data.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with graph data
        """
        solution_id = request.query.get('solution_id')
        if not solution_id:
            return web.json_response(
                {"error": "Missing solution_id parameter"},
                status=400
            )
        
        try:
            # Get solution details from the assembler
            solution_details = await self.get_solution_details(solution_id)
            if not solution_details:
                return web.json_response(
                    {"error": f"Solution not found: {solution_id}"},
                    status=404
                )
            
            # Generate graph visualization data
            graph_data = self.generate_cell_graph(solution_details)
            return web.json_response(graph_data)
            
        except Exception as e:
            logger.error(f"Error generating cell graph: {e}", exc_info=True)
            return web.json_response(
                {"error": f"Error generating cell graph: {str(e)}"},
                status=500
            )
    
    async def handle_get_quantum_trail(self, request: web.Request) -> web.Response:
        """
        Handle requests for quantum trail visualization data.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with quantum trail data
        """
        user_id = request.query.get('user_id', 'anonymous')
        limit = int(request.query.get('limit', 100))
        
        try:
            # Get quantum trail data from the quantum trail manager
            trail_data = await self.get_quantum_trail_data(user_id, limit)
            return web.json_response(trail_data)
            
        except Exception as e:
            logger.error(f"Error retrieving quantum trail: {e}", exc_info=True)
            return web.json_response(
                {"error": f"Error retrieving quantum trail: {str(e)}"},
                status=500
            )
    
    async def handle_get_resource_metrics(self, request: web.Request) -> web.Response:
        """
        Handle requests for resource metrics visualization data.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with resource metrics data
        """
        solution_id = request.query.get('solution_id')
        timeframe = request.query.get('timeframe', '1h')
        
        try:
            # Get resource metrics from the assembler
            metrics_data = await self.get_resource_metrics(solution_id, timeframe)
            return web.json_response(metrics_data)
            
        except Exception as e:
            logger.error(f"Error retrieving resource metrics: {e}", exc_info=True)
            return web.json_response(
                {"error": f"Error retrieving resource metrics: {str(e)}"},
                status=500
            )
    
    async def get_solution_details(self, solution_id: str) -> Dict[str, Any]:
        """
        Get solution details from the assembler.
        
        Args:
            solution_id: Solution ID
            
        Returns:
            Solution details
        """
        url = f"{self.assembler_url}/api/v1/solutions/{solution_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to get solution details: {response.status}")
                    return None
    
    async def get_quantum_trail_data(self, user_id: str, limit: int) -> Dict[str, Any]:
        """
        Get quantum trail data from the quantum trail manager.
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            
        Returns:
            Quantum trail data
        """
        url = f"{self.assembler_url}/api/v1/quantum_trail"
        params = {
            "user_id": user_id,
            "limit": limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to get quantum trail data: {response.status}")
                    return {"nodes": [], "links": [], "error": f"Status: {response.status}"}
    
    async def get_resource_metrics(self, solution_id: str, timeframe: str) -> Dict[str, Any]:
        """
        Get resource metrics from the assembler.
        
        Args:
            solution_id: Solution ID (optional)
            timeframe: Time frame for metrics (e.g., "1h", "24h", "7d")
            
        Returns:
            Resource metrics data
        """
        url = f"{self.assembler_url}/api/v1/metrics/resources"
        params = {"timeframe": timeframe}
        
        if solution_id:
            params["solution_id"] = solution_id
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to get resource metrics: {response.status}")
                    return {"timestamps": [], "metrics": {}, "error": f"Status: {response.status}"}
    
    def generate_cell_graph(self, solution_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate graph visualization data for a solution.
        
        Args:
            solution_details: Solution details from the assembler
            
        Returns:
            Graph visualization data
        """
        nodes = []
        links = []
        
        # Extract cells
        cells = solution_details.get("cells", {})
        
        # Create nodes for each cell
        for cell_id, cell_info in cells.items():
            node = {
                "id": cell_id,
                "name": cell_info.get("cell_type", "Unknown"),
                "capability": cell_info.get("capability", "Unknown"),
                "status": cell_info.get("status", "Unknown"),
                "type": self._get_node_type(cell_info),
                "metrics": {
                    "memory_mb": cell_info.get("resource_usage", {}).get("memory_mb", 0),
                    "cpu_percent": cell_info.get("resource_usage", {}).get("cpu_percent", 0)
                }
            }
            nodes.append(node)
        
        # Create links from connection map
        connection_map = solution_details.get("connection_map", {})
        for source_id, targets in connection_map.items():
            for target_id in targets:
                link = {
                    "source": source_id,
                    "target": target_id,
                    "value": 1  # Weight/value for the connection
                }
                links.append(link)
        
        # Add assembler as a central node
        assembler_node = {
            "id": "assembler",
            "name": "Assembler",
            "capability": "orchestration",
            "status": "active",
            "type": "assembler"
        }
        nodes.append(assembler_node)
        
        # Connect assembler to all cells
        for cell_id in cells:
            links.append({
                "source": "assembler",
                "target": cell_id,
                "value": 0.5  # Lower weight for assembler connections
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "solution_id": solution_details.get("id", "unknown"),
            "created_at": solution_details.get("created_at", "unknown"),
            "status": solution_details.get("status", "unknown")
        }
    
    def _get_node_type(self, cell_info: Dict[str, Any]) -> str:
        """
        Determine the node type for visualization based on cell info.
        
        Args:
            cell_info: Cell information
            
        Returns:
            Node type string
        """
        capability = cell_info.get("capability", "").lower()
        
        if "file_system" in capability:
            return "system"
        elif "network" in capability:
            return "system"
        elif "data" in capability or "visualization" in capability:
            return "middleware"
        elif "ui" in capability or "rendering" in capability:
            return "middleware"
        elif "text" in capability or "editor" in capability:
            return "application"
        elif "media" in capability or "player" in capability:
            return "application"
        else:
            return "general"
    
    async def handle_get_dashboard(self, request: web.Request) -> web.Response:
        """
        Serve the main dashboard HTML.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with dashboard HTML
        """
        dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QCC Visualization Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            margin: 0;
            padding: 0;
        }
        .navbar {
            background-color: #1E1B4B;
        }
        .navbar-brand {
            font-weight: 700;
            color: white !important;
        }
        .nav-link {
            color: rgba(255, 255, 255, 0.8) !important;
        }
        .nav-link:hover {
            color: white !important;
        }
        .card {
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }
        .card-header {
            font-weight: 600;
            background-color: #f8fafc;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        }
        #cell-graph {
            width: 100%;
            height: 500px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background-color: #fff;
        }
        .node {
            cursor: pointer;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
        .tooltip {
            position: absolute;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }
        .top-panels {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-panel {
            flex: 1;
            min-width: 200px;
            border-radius: 8px;
            padding: 15px;
            background-color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }
        .metric-label {
            color: #64748b;
            font-size: 14px;
        }
        #quantum-trail-visualization {
            width: 100%;
            height: 400px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background-color: #fff;
        }
        .node-system { fill: #4F46E5; }
        .node-middleware { fill: #14B8A6; }
        .node-application { fill: #F59E0B; }
        .node-general { fill: #94A3B8; }
        .node-assembler { fill: #EF4444; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="#">QCC Visualization Dashboard</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="#" id="refresh-link">Refresh Data</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#" data-bs-toggle="modal" data-bs-target="#settingsModal">Settings</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        <div class="row mb-4">
            <div class="col">
                <h2>System Overview</h2>
                <div class="top-panels">
                    <div class="metric-panel">
                        <div class="metric-label">Active Solutions</div>
                        <div class="metric-value" id="active-solutions">-</div>
                    </div>
                    <div class="metric-panel">
                        <div class="metric-label">Total Cells</div>
                        <div class="metric-value" id="total-cells">-</div>
                    </div>
                    <div class="metric-panel">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-value" id="cpu-usage">-</div>
                    </div>
                    <div class="metric-panel">
                        <div class="metric-label">Memory Usage</div>
                        <div class="metric-value" id="memory-usage">-</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Cell Graph Visualization</span>
                        <select id="solution-selector" class="form-select" style="width: auto;">
                            <option value="">Select a solution...</option>
                        </select>
                    </div>
                    <div class="card-body">
                        <div id="cell-graph"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">Resource Usage</div>
                    <div class="card-body">
                        <canvas id="resource-chart"></canvas>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">Selected Cell Details</div>
                    <div class="card-body">
                        <div id="cell-details">
                            <p class="text-muted">Select a cell in the graph to view details</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">Quantum Trail Visualization</div>
                    <div class="card-body">
                        <div id="quantum-trail-visualization"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Settings Modal -->
    <div class="modal fade" id="settingsModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Dashboard Settings</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="refresh-interval" class="form-label">Auto-refresh Interval (seconds)</label>
                        <input type="number" class="form-control" id="refresh-interval" value="10" min="5" max="60">
                    </div>
                    <div class="mb-3">
                        <label for="graph-layout" class="form-label">Cell Graph Layout</label>
                        <select class="form-select" id="graph-layout">
                            <option value="force">Force-directed</option>
                            <option value="radial">Radial</option>
                            <option value="tree">Tree</option>
                        </select>
                    </div>
                    <div class="mb-3 form-check">
                        <input type="checkbox" class="form-check-input" id="show-animations" checked>
                        <label class="form-check-label" for="show-animations">Show Animations</label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" id="save-settings">Save changes</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Dashboard state
        let activeSolutions = [];
        let currentSolutionId = null;
        let refreshInterval = 10000; // 10 seconds
        let refreshTimerId = null;
        let showAnimations = true;
        let graphLayout = 'force';
        
        // Initialize D3 visualizations
        let cellGraph = null;
        let quantumTrailVisualization = null;
        
        // Initialize resource chart
        let resourceChart = null;
        
        // Initialize the dashboard
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize the dashboard
            initDashboard();
            
            // Set up event listeners
            document.getElementById('refresh-link').addEventListener('click', refreshData);
            document.getElementById('solution-selector').addEventListener('change', function() {
                currentSolutionId = this.value;
                updateCellGraph();
            });
            document.getElementById('save-settings').addEventListener('click', saveSettings);
            
            // Start auto-refresh
            startAutoRefresh();
        });
        
        function initDashboard() {
            // Initialize the cell graph
            initCellGraph();
            
            // Initialize the quantum trail visualization
            initQuantumTrailVisualization();
            
            // Initialize the resource chart
            initResourceChart();
            
            // Load initial data
            refreshData();
        }
        
        function refreshData() {
            // Fetch system status
            fetchSystemStatus();
            
            // Fetch active solutions
            fetchActiveSolutions();
            
            // Fetch and update quantum trail
            updateQuantumTrail();
            
            // Fetch and update resource metrics
            updateResourceMetrics();
        }
        
        function fetchSystemStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('active-solutions').textContent = data.active_solutions || '-';
                    document.getElementById('total-cells').textContent = data.total_cells || '-';
                    document.getElementById('cpu-usage').textContent = (data.cpu_usage_percent || '-') + '%';
                    document.getElementById('memory-usage').textContent = (data.memory_usage_mb || '-') + ' MB';
                })
                .catch(error => console.error('Error fetching system status:', error));
        }
        
        function fetchActiveSolutions() {
            fetch('/api/solutions')
                .then(response => response.json())
                .then(data => {
                    activeSolutions = data.solutions || [];
                    
                    // Update solution selector
                    const selector = document.getElementById('solution-selector');
                    selector.innerHTML = '<option value="">Select a solution...</option>';
                    
                    activeSolutions.forEach(solution => {
                        const option = document.createElement('option');
                        option.value = solution.id;
                        option.textContent = `${solution.id.substring(0, 8)}... (${solution.intent_summary || 'No summary'})`;
                        selector.appendChild(option);
                    });
                    
                    // If no solution is selected and there are solutions available, select the first one
                    if (!currentSolutionId && activeSolutions.length > 0) {
                        currentSolutionId = activeSolutions[0].id;
                        selector.value = currentSolutionId;
                    }
                    
                    // Update cell graph if a solution is selected
                    if (currentSolutionId) {
                        updateCellGraph();
                    }
                })
                .catch(error => console.error('Error fetching active solutions:', error));
        }
        
        function initCellGraph() {
            const width = document.getElementById('cell-graph').clientWidth;
            const height = document.getElementById('cell-graph').clientHeight;
            
            // Create SVG container
            const svg = d3.select('#cell-graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
                
            // Create tooltip
            const tooltip = d3.select('body')
                .append('div')
                .attr('class', 'tooltip');
                
            // Initialize force simulation
            const simulation = d3.forceSimulation()
                .force('link', d3.forceLink().id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));
                
            // Store references for later update
            cellGraph = {
                svg: svg,
                tooltip: tooltip,
                simulation: simulation,
                width: width,
                height: height,
                nodes: [],
                links: []
            };
        }
        
        function updateCellGraph() {
            if (!currentSolutionId) return;
            
            fetch(`/api/cell-graph?solution_id=${currentSolutionId}`)
                .then(response => response.json())
                .then(data => {
                    const svg = cellGraph.svg;
                    const tooltip = cellGraph.tooltip;
                    const simulation = cellGraph.simulation;
                    
                    // Clear previous graph
                    svg.selectAll('*').remove();
                    
                    // Update stored data
                    cellGraph.nodes = data.nodes;
                    cellGraph.links = data.links;
                    
                    // Create arrow marker for links
                    svg.append('defs').append('marker')
                        .attr('id', 'arrowhead')
                        .attr('viewBox', '-0 -5 10 10')
                        .attr('refX', 20)
                        .attr('refY', 0)
                        .attr('orient', 'auto')
                        .attr('markerWidth', 6)
                        .attr('markerHeight', 6)
                        .attr('xoverflow', 'visible')
                        .append('svg:path')
                        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
                        .attr('fill', '#999')
                        .style('stroke', 'none');
                    
                    // Draw links
                    const link = svg.append('g')
                        .selectAll('line')
                        .data(data.links)
                        .enter()
                        .append('line')
                        .attr('class', 'link')
                        .attr('marker-end', 'url(#arrowhead)')
                        .style('stroke-width', d => Math.sqrt(d.value) * 2);
                    
                    // Draw nodes
                    const node = svg.append('g')
                        .selectAll('circle')
                        .data(data.nodes)
                        .enter()
                        .append('circle')
                        .attr('class', d => `node node-${d.type}`)
                        .attr('r', 10)
                        .call(d3.drag()
                            .on('start', dragstarted)
                            .on('drag', dragged)
                            .on('end', dragended));
                    
                    // Add labels
                    const label = svg.append('g')
                        .selectAll('text')
                        .data(data.nodes)
                        .enter()
                        .append('text')
                        .attr('dx', 12)
                        .attr('dy', '.35em')
                        .text(d => d.name);
                    
                    // Add tooltips
                    node.on('mouseover', function(event, d) {
                            tooltip.transition()
                                .duration(200)
                                .style('opacity', .9);
                            tooltip.html(`
                                <strong>${d.name}</strong><br>
                                Capability: ${d.capability}<br>
                                Status: ${d.status}<br>
                                Memory: ${d.metrics?.memory_mb || 0} MB<br>
                                CPU: ${d.metrics?.cpu_percent || 0}%
                            `)
                                .style('left', (event.pageX + 10) + 'px')
                                .style('top', (event.pageY - 28) + 'px');
                        })
                        .on('mouseout', function() {
                            tooltip.transition()
                                .duration(500)
                                .style('opacity', 0);
                        })
                        .on('click', function(event, d) {
                            displayCellDetails(d);
                        });
                    
                    // Update simulation
                    simulation
                        .nodes(data.nodes)
                        .on('tick', ticked);
                    
                    simulation.force('link')
                        .links(data.links);
                    
                    // Reset simulation
                    simulation.alpha(1).restart();
                    
                    function ticked() {
                        link
                            .attr('x1', d => d.source.x)
                            .attr('y1', d => d.source.y)
                            .attr('x2', d => d.target.x)
                            .attr('y2', d => d.target.y);
                        
                        node
                            .attr('cx', d => d.x = Math.max(10, Math.min(cellGraph.width - 10, d.x)))
                            .attr('cy', d => d.y = Math.max(10, Math.min(cellGraph.height - 10, d.y)));
                        
                        label
                            .attr('x', d => d.x)
                            .attr('y', d => d.y);
                    }
                    
                    function dragstarted(event, d) {
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    }
                    
                    function dragged(event, d) {
                        d.fx = event.x;
                        d.fy = event.y;
                    }
                    
                    function dragended(event, d) {
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    }
                })
                .catch(error => console.error('Error fetching cell graph data:', error));
        }
        
        function displayCellDetails(cell) {
            const detailsContainer = document.getElementById('cell-details');
            detailsContainer.innerHTML = `
                <h5>${cell.name}</h5>
                <table class="table table-sm">
                    <tr>
                        <th>ID</th>
                        <td>${cell.id}</td>
                    </tr>
                    <tr>
                        <th>Capability</th>
                        <td>${cell.capability}</td>
                    </tr>
                    <tr>
                        <th>Status</th>
                        <td>${cell.status}</td>
                    </tr>
                    <tr>
                        <th>Memory Usage</th>
                        <td>${cell.metrics?.memory_mb || 0} MB</td>
                    </tr>
                    <tr>
                        <th>CPU Usage</th>
                        <td>${cell.metrics?.cpu_percent || 0}%</td>
                    </tr>
                </table>
            `;
        }
        
        function initQuantumTrailVisualization() {
            const width = document.getElementById('quantum-trail-visualization').clientWidth;
            const height = document.getElementById('quantum-trail-visualization').clientHeight;
            
            // Create SVG container
            const svg = d3.select('#quantum-trail-visualization')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
                
            // Initialize force simulation
            const simulation = d3.forceSimulation()
                .force('link', d3.forceLink().id(d => d.id).distance(50))
                .force('charge', d3.forceManyBody().strength(-100))
                .force('center', d3.forceCenter(width / 2, height / 2));
                
            // Store references for later update
            quantumTrailVisualization = {
                svg: svg,
                simulation: simulation,
                width: width,
                height: height
            };
            
            // Initial update
            updateQuantumTrail();
        }
        
        function updateQuantumTrail() {
            fetch('/api/quantum-trail')
                .then(response => response.json())
                .then(data => {
                    const svg = quantumTrailVisualization.svg;
                    const simulation = quantumTrailVisualization.simulation;
                    
                    // Clear previous visualization
                    svg.selectAll('*').remove();
                    
                    // Draw links
                    const link = svg.append('g')
                        .selectAll('line')
                        .data(data.links)
                        .enter()
                        .append('line')
                        .attr('stroke', '#999')
                        .attr('stroke-opacity', 0.6)
                        .attr('stroke-width', d => Math.sqrt(d.value));
                    
                    // Draw nodes
                    const node = svg.append('g')
                        .selectAll('circle')
                        .data(data.nodes)
                        .enter()
                        .append('circle')
                        .attr('r', d => 5 + d.value * 3)
                        .attr('fill', d => d.color || '#4F46E5')
                        .call(d3.drag()
                            .on('start', dragstarted)
                            .on('drag', dragged)
                            .on('end', dragended));
                    
                    // Add labels
                    const label = svg.append('g')
                        .selectAll('text')
                        .data(data.nodes)
                        .enter()
                        .append('text')
                        .attr('dx', 12)
                        .attr('dy', '.35em')
                        .text(d => d.label)
                        .attr('font-size', '10px');
                    
                    // Update simulation
                    simulation
                        .nodes(data.nodes)
                        .on('tick', ticked);
                    
                    simulation.force('link')
                        .links(data.links);
                    
                    // Reset simulation
                    simulation.alpha(1).restart();
                    
                    function ticked() {
                        link
                            .attr('x1', d => d.source.x)
                            .attr('y1', d => d.source.y)
                            .attr('x2', d => d.target.x)
                            .attr('y2', d => d.target.y);
                        
                        node
                            .attr('cx', d => d.x = Math.max(5, Math.min(quantumTrailVisualization.width - 5, d.x)))
                            .attr('cy', d => d.y = Math.max(5, Math.min(quantumTrailVisualization.height - 5, d.y)));
                        
                        label
                            .attr('x', d => d.x)
                            .attr('y', d => d.y);
                    }
                    
                    function dragstarted(event, d) {
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    }
                    
                    function dragged(event, d) {
                        d.fx = event.x;
                        d.fy = event.y;
                    }
                    
                    function dragended(event, d) {
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    }
                })
                .catch(error => console.error('Error fetching quantum trail data:', error));
        }
        
        function initResourceChart() {
            const ctx = document.getElementById('resource-chart').getContext('2d');
            resourceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'CPU Usage (%)',
                            data: [],
                            borderColor: '#4F46E5',
                            backgroundColor: 'rgba(79, 70, 229, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Memory Usage (MB)',
                            data: [],
                            borderColor: '#14B8A6',
                            backgroundColor: 'rgba(20, 184, 166, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Value'
                            }
                        }
                    }
                }
            });
        }
        
        function updateResourceMetrics() {
            const params = new URLSearchParams();
            if (currentSolutionId) {
                params.append('solution_id', currentSolutionId);
            }
            params.append('timeframe', '1h');
            
            fetch(`/api/resource-metrics?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    // Update chart data
                    resourceChart.data.labels = data.timestamps.map(ts => {
                        const date = new Date(ts);
                        return date.toLocaleTimeString();
                    });
                    
                    // Update CPU dataset
                    resourceChart.data.datasets[0].data = data.metrics.cpu_percent || [];
                    
                    // Update Memory dataset
                    resourceChart.data.datasets[1].data = data.metrics.memory_mb || [];
                    
                    // Update chart
                    resourceChart.update();
                })
                .catch(error => console.error('Error fetching resource metrics:', error));
        }
        
        function startAutoRefresh() {
            // Clear existing timer if any
            if (refreshTimerId) {
                clearInterval(refreshTimerId);
            }
            
            // Start new timer
            refreshTimerId = setInterval(refreshData, refreshInterval);
        }
        
        function saveSettings() {
            // Get settings values
            const newInterval = parseInt(document.getElementById('refresh-interval').value) * 1000;
            const newLayout = document.getElementById('graph-layout').value;
            const newShowAnimations = document.getElementById('show-animations').checked;
            
            // Update settings
            refreshInterval = newInterval;
            graphLayout = newLayout;
            showAnimations = newShowAnimations;
            
            // Restart auto-refresh
            startAutoRefresh();
            
            // Apply layout change
            if (cellGraph && cellGraph.simulation) {
                updateCellGraph();
            }
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('settingsModal')).hide();
        }
    </script>
</body>
</html>
        """
        return web.Response(text=dashboard_html, content_type='text/html')
    
    async def handle_get_static(self, request: web.Request) -> web.Response:
        """
        Serve static files from the static directory.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with static file content
        """
        static_file = request.match_info.get('file')
        static_path = os.path.join(self.static_dir, static_file)
        
        if not os.path.exists(static_path) or not os.path.isfile(static_path):
            return web.Response(text="File not found", status=404)
        
        # Determine content type
        content_type = 'application/octet-stream'
        if static_file.endswith('.css'):
            content_type = 'text/css'
        elif static_file.endswith('.js'):
            content_type = 'application/javascript'
        elif static_file.endswith('.html'):
            content_type = 'text/html'
        elif static_file.endswith('.json'):
            content_type = 'application/json'
        elif static_file.endswith('.png'):
            content_type = 'image/png'
        elif static_file.endswith('.jpg') or static_file.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif static_file.endswith('.svg'):
            content_type = 'image/svg+xml'
        
        try:
            with open(static_path, 'rb') as f:
                return web.Response(body=f.read(), content_type=content_type)
        except Exception as e:
            logger.error(f"Error serving static file {static_file}: {e}")
            return web.Response(text=f"Error reading file: {str(e)}", status=500)
    
    async def start(self):
        """Start the visualization server."""
        app = web.Application()
        
        # Setup routes
        app.router.add_get('/', self.handle_get_dashboard)
        app.router.add_get('/static/{file}', self.handle_get_static)
        app.router.add_get('/api/status', self.handle_get_status)
        app.router.add_get('/api/solutions', self.handle_get_solutions)
        app.router.add_get('/api/solution/{solution_id}', self.handle_get_solution)
        app.router.add_get('/api/cell-graph', self.handle_get_cell_graph)
        app.router.add_get('/api/quantum-trail', self.handle_get_quantum_trail)
        app.router.add_get('/api/resource-metrics', self.handle_get_resource_metrics)
        app.router.add_get('/api/recordings', self.handle_get_recordings)
        app.router.add_get('/api/recording/{recording_id}', self.handle_get_recording)
        
        # Configure CORS
        if self.config.get('cors_enabled', True):
            import aiohttp_cors
            cors = aiohttp_cors.setup(app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=["GET", "POST", "OPTIONS"]
                )
            })
            
            # Apply CORS to all routes
            for route in list(app.router.routes()):
                cors.add(route)
        
        # Start the server
        host = self.config.get('host', 'localhost')
        port = self.config.get('port', 8083)
        
        logger.info(f"Starting visualization server at http://{host}:{port}")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        self.runner = runner
        self.site = site
        
        logger.info(f"Visualization server running at http://{host}:{port}")
    
    async def stop(self):
        """Stop the visualization server."""
        if hasattr(self, 'runner'):
            logger.info("Stopping visualization server")
            await self.runner.cleanup()


async def create_visualizer(config_path: str = None) -> QCCVisualizer:
    """
    Create and start a QCC Visualizer instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Running QCCVisualizer instance
    """
    # Load configuration
    config = {}
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            logger.warning("Using default configuration")
    
    # Create visualizer
    visualizer = QCCVisualizer(config)
    
    # Start visualizer
    await visualizer.start()
    
    return visualizer


if __name__ == "__main__":
    import argparse
    
    # Configure argument parser
    parser = argparse.ArgumentParser(description='QCC Visualization Server')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--host', type=str, default='localhost', help='Host address to bind')
    parser.add_argument('--port', type=int, default=8083, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration from {args.config}: {e}")
            logger.warning("Using default configuration")
    
    # Override config with command line arguments
    if args.host:
        config['host'] = args.host
    if args.port:
        config['port'] = args.port
    
    # Run the visualizer
    async def main():
        visualizer = QCCVisualizer(config)
        await visualizer.start()
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping server")
        finally:
            await visualizer.stop()
    
    # Run the main function
    asyncio.run(main())
