"""
GPU VRAM Management for MediOrbit Backend.

Implements semaphore-based concurrency control to prevent Out-Of-Memory errors
during concurrent medical image analysis and document processing.

This module monitors available GPU VRAM in real-time and limits the number of
concurrent model executions to maintain a safety margin.

Based on architectural recommendation:
  SEMAPHORE_SLOTS = max(
    (AVAILABLE_VRAM - VRAM_BUFFER) / VRAM_REQUIRED_PER_RUN,
    1
  )
"""

import logging
import asyncio
from typing import Optional
from threading import Semaphore
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VRAMManager:
    """
    Manages GPU VRAM allocation using semaphore-based concurrency control.
    
    Prevents out-of-memory errors by limiting concurrent model executions
    based on available GPU memory.
    """
    
    def __init__(
        self,
        vram_buffer_mb: int = 512,
        vram_per_inference_mb: int = 1024,
        check_interval_sec: int = 5
    ):
        """
        Initialize VRAM manager.
        
        Args:
            vram_buffer_mb: Safety margin to maintain (default 512 MB)
            vram_per_inference_mb: Estimated VRAM per inference (default 1024 MB)
            check_interval_sec: How often to check available VRAM
        """
        self.vram_buffer_mb = vram_buffer_mb
        self.vram_per_inference_mb = vram_per_inference_mb
        self.check_interval_sec = check_interval_sec
        
        # Initialize with conservative default (1 slot)
        self.semaphore = Semaphore(1)
        self.max_slots = 1
        
        # Try to import pynvml for GPU monitoring
        self.has_gpu = False
        self.pynvml = None
        try:
            import pynvml
            pynvml.nvmlInit()
            self.pynvml = pynvml
            self.has_gpu = True
            logger.info("✅ GPU VRAM monitoring enabled via pynvml")
        except Exception as e:
            logger.warning(f"⚠️ GPU monitoring unavailable: {e}. Using CPU-only mode.")
            self.has_gpu = False
        
        # Stats for monitoring
        self.stats = {
            "total_requests": 0,
            "current_active": 0,
            "peak_concurrent": 0,
            "last_check": datetime.now(),
            "available_vram_mb": 0
        }
        
    def get_available_vram_mb(self) -> int:
        """
        Get available GPU VRAM in MB.
        
        Returns:
            Available VRAM in MB, or 0 if GPU unavailable
        """
        if not self.has_gpu or not self.pynvml:
            return 2048  # Conservative estimate for CPU systems
        
        try:
            # Get first GPU device
            device_index = 0
            handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_index)
            
            # Get memory info
            mem_info = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
            available_mb = mem_info.free / (1024 * 1024)
            
            self.stats["available_vram_mb"] = int(available_mb)
            return int(available_mb)
        except Exception as e:
            logger.warning(f"Failed to query GPU VRAM: {e}")
            return 2048
    
    def update_semaphore_slots(self) -> int:
        """
        Update semaphore slots based on current available VRAM.
        
        Uses formula:
          slots = max(
            (available_vram - buffer) / vram_per_inference,
            1
          )
        
        Returns:
            Number of available slots
        """
        available_vram = self.get_available_vram_mb()
        
        # Calculate slots
        slots = max(
            (available_vram - self.vram_buffer_mb) // self.vram_per_inference_mb,
            1  # Always allow at least 1 request
        )
        
        # Update semaphore if needed
        old_slots = self.max_slots
        self.max_slots = slots
        
        if slots != old_slots:
            logger.info(
                f"VRAM: {available_vram}MB available | "
                f"Buffer: {self.vram_buffer_mb}MB | "
                f"Per-inference: {self.vram_per_inference_mb}MB | "
                f"Slots: {old_slots} → {slots}"
            )
        
        return slots
    
    async def acquire_slot(self, timeout_sec: float = 60.0) -> bool:
        """
        Acquire a VRAM slot for model inference.
        
        This is an async wrapper around semaphore acquire that respects timeouts.
        
        Args:
            timeout_sec: Maximum time to wait for slot availability
            
        Returns:
            True if slot acquired, False if timeout
            
        Usage:
            manager = VRAMManager()
            if await manager.acquire_slot():
                try:
                    # Do inference
                    result = model.predict(data)
                finally:
                    manager.release_slot()
            else:
                return {"error": "System under high load. Try again later"}
        """
        # Update slots before attempting to acquire
        self.update_semaphore_slots()
        
        # Try to acquire with timeout
        try:
            # Non-blocking check first
            if self.semaphore.acquire(blocking=False):
                self.stats["current_active"] += 1
                self.stats["total_requests"] += 1
                self.stats["peak_concurrent"] = max(
                    self.stats["peak_concurrent"],
                    self.stats["current_active"]
                )
                return True
            
            # If blocking, use asyncio to handle timeout
            loop = asyncio.get_event_loop()
            start = loop.time()
            
            while loop.time() - start < timeout_sec:
                if self.semaphore.acquire(blocking=False):
                    self.stats["current_active"] += 1
                    self.stats["total_requests"] += 1
                    self.stats["peak_concurrent"] = max(
                        self.stats["peak_concurrent"],
                        self.stats["current_active"]
                    )
                    logger.info(
                        f"Slot acquired | Active: {self.stats['current_active']} | "
                        f"Queue depth: {self.max_slots - self.stats['current_active']}"
                    )
                    return True
                
                # Wait 100ms before retrying
                await asyncio.sleep(0.1)
            
            # Timeout
            logger.warning(
                f"VRAM slot request timeout after {timeout_sec}s. "
                f"Active: {self.stats['current_active']}, Max: {self.max_slots}"
            )
            return False
            
        except Exception as e:
            logger.error(f"Error acquiring VRAM slot: {e}")
            return False
    
    def release_slot(self) -> None:
        """
        Release a VRAM slot after inference completes.
        
        Always call this in a try/finally block to ensure proper cleanup.
        """
        try:
            if self.stats["current_active"] > 0:
                self.semaphore.release()
                self.stats["current_active"] -= 1
        except Exception as e:
            logger.error(f"Error releasing VRAM slot: {e}")
    
    def get_stats(self) -> dict:
        """
        Get VRAM manager statistics for monitoring/debugging.
        
        Returns:
            Dictionary with current stats
        """
        return {
            "available_vram_mb": self.get_available_vram_mb(),
            "max_slots": self.max_slots,
            "current_active": self.stats["current_active"],
            "total_requests": self.stats["total_requests"],
            "peak_concurrent": self.stats["peak_concurrent"],
            "gpu_available": self.has_gpu,
            "check_interval_sec": self.check_interval_sec
        }
    
    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"VRAMManager(slots={self.max_slots}, "
            f"active={self.stats['current_active']}, "
            f"vram={self.stats['available_vram_mb']}MB)"
        )


# Global singleton instance
_vram_manager: Optional[VRAMManager] = None

def get_vram_manager() -> VRAMManager:
    """
    Get or create the global VRAM manager singleton.
    
    Returns:
        VRAMManager instance
    """
    global _vram_manager
    if _vram_manager is None:
        _vram_manager = VRAMManager()
    return _vram_manager

def init_vram_manager(
    vram_buffer_mb: int = 512,
    vram_per_inference_mb: int = 1024
) -> VRAMManager:
    """
    Initialize VRAM manager with custom settings.
    
    Args:
        vram_buffer_mb: Safety margin in MB
        vram_per_inference_mb: VRAM per model inference in MB
        
    Returns:
        Configured VRAMManager instance
    """
    global _vram_manager
    _vram_manager = VRAMManager(
        vram_buffer_mb=vram_buffer_mb,
        vram_per_inference_mb=vram_per_inference_mb
    )
    return _vram_manager
