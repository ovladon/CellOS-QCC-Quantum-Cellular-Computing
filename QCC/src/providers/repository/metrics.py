"""
Metrics collection system for Quantum Cellular Computing repository.

This module provides functionality for collecting, storing, and analyzing
metrics about the repository's usage and performance, enabling monitoring
and optimization of the repository service.
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from qcc.providers.repository.storage import StorageManager

logger = logging.getLogger(__name__)

@dataclass
class MetricSample:
    """
    Represents a single metric sample.
    
    Attributes:
        name: Metric name
        value: Metric value
        timestamp: Sample timestamp
        labels: Additional metric labels
    """
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricSample':
        """Create MetricSample from dictionary."""
        # Convert ISO format string back to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            name=data.get("name", ""),
            value=data.get("value", 0.0),
            timestamp=data.get("timestamp", datetime.now()),
            labels=data.get("labels", {})
        )


class MetricsCollector:
    """
    Collects and stores metrics about the repository.
    
    This class provides functionality for collecting various metrics about
    repository usage, performance, and health, and storing them for later
    analysis.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Initialize the metrics collector.
        
        Args:
            storage_manager: Storage manager for storing metrics
        """
        self.storage_manager = storage_manager
        self.metrics_cache = {}  # name -> [recent samples]
        self.max_cached_samples = 1000  # Maximum samples to keep in memory per metric
        self.retention_days = 30  # Number of days to retain metrics
        self.flush_interval = 300  # Seconds between automatic flushes
        self.last_flush = time.time()
        
        # Start background flush task
        self._background_task = None
    
    async def start_background_flush(self):
        """Start the background metrics flush task."""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._background_flush())
    
    async def stop_background_flush(self):
        """Stop the background metrics flush task."""
        if self._background_task is not None:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
    
    async def _background_flush(self):
        """Periodically flush metrics in the background."""
        try:
            while True:
                await asyncio.sleep(self.flush_interval)
                await self.flush_metrics()
        except asyncio.CancelledError:
            # Final flush before shutting down
            await self.flush_metrics()
            raise
        except Exception as e:
            logger.error(f"Error in background metrics flush: {e}")
    
    async def record_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        Record a metric sample.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Additional metric labels
        """
        # Create metric sample
        sample = MetricSample(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        
        # Add to cache
        if name not in self.metrics_cache:
            self.metrics_cache[name] = []
        
        self.metrics_cache[name].append(sample)
        
        # Trim cache if it exceeds the limit
        if len(self.metrics_cache[name]) > self.max_cached_samples:
            self.metrics_cache[name] = self.metrics_cache[name][-self.max_cached_samples:]
        
        # Auto-flush if it's been too long
        if time.time() - self.last_flush > self.flush_interval:
            await self.flush_metrics()
    
    async def flush_metrics(self) -> bool:
        """
        Flush cached metrics to storage.
        
        Returns:
            True if flush was successful, False otherwise
        """
        if not self.metrics_cache:
            return True
        
        try:
            # Group samples by date for storage
            date_samples = {}
            
            for name, samples in self.metrics_cache.items():
                for sample in samples:
                    date_str = sample.timestamp.strftime("%Y-%m-%d")
                    if date_str not in date_samples:
                        date_samples[date_str] = []
                    
                    date_samples[date_str].append(sample.to_dict())
            
            # Store samples by date
            for date_str, samples in date_samples.items():
                # Merge with existing samples if any
                metrics_path = os.path.join("metrics", f"{date_str}.json")
                
                if await self.storage_manager.exists(metrics_path):
                    existing_samples = await self.storage_manager.read_json(metrics_path) or []
                    samples.extend(existing_samples)
                
                # Write combined samples
                await self.storage_manager.write_json(metrics_path, samples)
                
                logger.debug(f"Flushed {len(samples)} metric samples for {date_str}")
            
            # Clear cache
            self.metrics_cache.clear()
            self.last_flush = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
            return False
    
    async def get_metrics(
        self, 
        name: str, 
        start_time: datetime = None, 
        end_time: datetime = None,
        labels: Dict[str, str] = None
    ) -> List[MetricSample]:
        """
        Get metric samples for a specific metric.
        
        Args:
            name: Metric name
            start_time: Start time for samples
            end_time: End time for samples
            labels: Filter samples by labels
            
        Returns:
            List of metric samples
        """
        try:
            # Set default time range if not specified
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(days=1)
            
            # Generate list of dates in range
            date_range = []
            current_date = start_time.date()
            while current_date <= end_time.date():
                date_range.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)
            
            # Collect samples from each date
            all_samples = []
            
            # Add cached samples
            if name in self.metrics_cache:
                for sample in self.metrics_cache[name]:
                    if start_time <= sample.timestamp <= end_time:
                        if labels is None or self._match_labels(sample.labels, labels):
                            all_samples.append(sample)
            
            # Add samples from storage
            for date_str in date_range:
                metrics_path = os.path.join("metrics", f"{date_str}.json")
                
                if await self.storage_manager.exists(metrics_path):
                    samples_data = await self.storage_manager.read_json(metrics_path) or []
                    
                    for sample_data in samples_data:
                        # Check if sample matches metric name
                        if sample_data.get("name") == name:
                            # Parse timestamp
                            sample_timestamp = datetime.fromisoformat(sample_data.get("timestamp"))
                            
                            # Check if sample is in time range
                            if start_time <= sample_timestamp <= end_time:
                                # Check if sample matches labels
                                sample_labels = sample_data.get("labels", {})
                                if labels is None or self._match_labels(sample_labels, labels):
                                    all_samples.append(MetricSample.from_dict(sample_data))
            
            # Sort samples by timestamp
            all_samples.sort(key=lambda s: s.timestamp)
            
            return all_samples
            
        except Exception as e:
            logger.error(f"Error getting metrics for {name}: {e}")
            return []
    
    def _match_labels(self, sample_labels: Dict[str, str], query_labels: Dict[str, str]) -> bool:
        """
        Check if sample labels match query labels.
        
        Args:
            sample_labels: Labels from sample
            query_labels: Labels to match
            
        Returns:
            True if all query labels match sample labels
        """
        for key, value in query_labels.items():
            if key not in sample_labels or sample_labels[key] != value:
                return False
        return True
    
    async def get_metric_statistics(
        self, 
        name: str, 
        start_time: datetime = None, 
        end_time: datetime = None,
        labels: Dict[str, str] = None,
        interval: str = "hour"
    ) -> Dict[str, Any]:
        """
        Get statistics for a metric.
        
        Args:
            name: Metric name
            start_time: Start time for samples
            end_time: End time for samples
            labels: Filter samples by labels
            interval: Aggregation interval ('minute', 'hour', 'day')
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Get raw samples
            samples = await self.get_metrics(name, start_time, end_time, labels)
            
            if not samples:
                return {
                    "name": name,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "count": 0,
                    "min": None,
                    "max": None,
                    "avg": None,
                    "sum": None,
                    "points": []
                }
            
            # Group samples by interval
            interval_samples = {}
            
            for sample in samples:
                interval_key = self._get_interval_key(sample.timestamp, interval)
                
                if interval_key not in interval_samples:
                    interval_samples[interval_key] = []
                
                interval_samples[interval_key].append(sample.value)
            
            # Calculate statistics for each interval
            points = []
            
            for interval_key, values in sorted(interval_samples.items()):
                point = {
                    "timestamp": interval_key,
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "sum": sum(values)
                }
                points.append(point)
            
            # Calculate overall statistics
            all_values = [sample.value for sample in samples]
            
            return {
                "name": name,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "count": len(samples),
                "min": min(all_values),
                "max": max(all_values),
                "avg": sum(all_values) / len(all_values),
                "sum": sum(all_values),
                "points": points
            }
            
        except Exception as e:
            logger.error(f"Error getting metric statistics for {name}: {e}")
            return {
                "name": name,
                "error": str(e)
            }
    
    def _get_interval_key(self, timestamp: datetime, interval: str) -> str:
        """
        Get key for a time interval.
        
        Args:
            timestamp: Sample timestamp
            interval: Interval type ('minute', 'hour', 'day')
            
        Returns:
            Interval key as ISO string
        """
        if interval == "minute":
            return datetime(
                timestamp.year, timestamp.month, timestamp.day,
                timestamp.hour, timestamp.minute
            ).isoformat()
        elif interval == "hour":
            return datetime(
                timestamp.year, timestamp.month, timestamp.day,
                timestamp.hour
            ).isoformat()
        elif interval == "day":
            return datetime(
                timestamp.year, timestamp.month, timestamp.day
            ).isoformat()
        else:
            return timestamp.isoformat()
    
    async def purge_old_metrics(self) -> int:
        """
        Purge metrics older than retention period.
        
        Returns:
            Number of days purged
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            
            # List all metric files
            metrics_dir = "metrics"
            metric_files = await self.storage_manager.list_files(metrics_dir)
            
            # Filter files older than cutoff
            old_files = []
            for file_path in metric_files:
                file_name = os.path.basename(file_path)
                if file_name.endswith(".json") and file_name[:-5] < cutoff_str:
                    old_files.append(file_path)
            
            # Delete old files
            purged_count = 0
            for file_path in old_files:
                success = await self.storage_manager.delete_file(file_path)
                if success:
                    purged_count += 1
            
            logger.info(f"Purged {purged_count} days of metrics older than {cutoff_str}")
            return purged_count
            
        except Exception as e:
            logger.error(f"Error purging old metrics: {e}")
            return 0
    
    async def get_metric_summary(self) -> Dict[str, Any]:
        """
        Get a summary of available metrics.
        
        Returns:
            Dictionary with metric summary
        """
        try:
            # List all metric files
            metrics_dir = "metrics"
            metric_files = await self.storage_manager.list_files(metrics_dir)
            
            # Extract dates from file names
            dates = []
            for file_path in metric_files:
                file_name = os.path.basename(file_path)
                if file_name.endswith(".json"):
                    dates.append(file_name[:-5])
            
            # Sort dates
            dates.sort()
            
            # Get all unique metric names
            metric_names = set()
            
            # Check the latest file for metric names
            if dates:
                latest_file = os.path.join(metrics_dir, f"{dates[-1]}.json")
                samples_data = await self.storage_manager.read_json(latest_file) or []
                
                for sample_data in samples_data:
                    metric_names.add(sample_data.get("name"))
            
            # Add cached metric names
            for name in self.metrics_cache.keys():
                metric_names.add(name)
            
            return {
                "metric_count": len(metric_names),
                "metrics": sorted(list(metric_names)),
                "earliest_date": dates[0] if dates else None,
                "latest_date": dates[-1] if dates else None,
                "date_count": len(dates)
            }
            
        except Exception as e:
            logger.error(f"Error getting metric summary: {e}")
            return {
                "error": str(e)
            }
