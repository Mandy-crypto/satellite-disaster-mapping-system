"""
Visualization module for satellite processing results.

Creates visual outputs including:
- Original image
- NDWI heatmap
- Flood mask
- Change detection (if applicable)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)


class Visualizer:
    """
    Create visualizations from satellite processing results.
    """
    
    def __init__(self, output_dir: str = "./output", save_plots: bool = True):
        """
        Initialize visualizer.
        
        Args:
            output_dir: Directory to save visualizations
            save_plots: Whether to save plots to disk
        """
        self.output_dir = output_dir
        self.save_plots = save_plots
        
        if save_plots:
            os.makedirs(output_dir, exist_ok=True)
    
    def create_visualization_package(self,
                                    image_data: Dict[str, Any],
                                    ndwi: np.ndarray,
                                    flood_mask: np.ndarray,
                                    before_ndwi: Optional[np.ndarray] = None,
                                    change_map: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Create complete visualization package.
        
        Args:
            image_data: Original image data
            ndwi: NDWI array
            flood_mask: Binary flood mask
            before_ndwi: NDWI from before image (optional)
            change_map: Change detection map (optional)
            
        Returns:
            Dictionary with visualization paths and base64 images
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"satellite_{timestamp}"
        
        visualizations = {
            'timestamp': datetime.now().isoformat(),
            'plots': [],
            'files': []
        }
        
        # Get original image
        original = image_data['data']
        if len(original.shape) == 3 and original.shape[0] >= 3:
            # RGB image (bands, height, width)
            rgb = np.transpose(original[:3], (1, 2, 0))
            rgb = np.clip(rgb, 0, 1)
        else:
            # Grayscale or single band
            if len(original.shape) == 3:
                rgb = original[0]
            else:
                rgb = original
            rgb = np.clip(rgb, 0, 1)
        
        # Plot 1: Original image
        fig1 = self._plot_original(rgb)
        visualizations['plots'].append(self._save_plot(fig1, f"{base_name}_original"))
        
        # Plot 2: NDWI heatmap
        fig2 = self._plot_ndwi_heatmap(ndwi)
        visualizations['plots'].append(self._save_plot(fig2, f"{base_name}_ndwi"))
        
        # Plot 3: Flood mask
        fig3 = self._plot_flood_mask(rgb, ndwi, flood_mask)
        visualizations['plots'].append(self._save_plot(fig3, f"{base_name}_flood"))
        
        # Plot 4: Change detection (if available)
        if before_ndwi is not None and change_map is not None:
            fig4 = self._plot_change_detection(ndwi, before_ndwi, change_map)
            visualizations['plots'].append(self._save_plot(fig4, f"{base_name}_change"))
        
        # Create composite visualization
        if before_ndwi is not None:
            fig5 = self._create_composite_visualization(
                rgb, ndwi, flood_mask, before_ndwi, change_map
            )
            visualizations['plots'].append(
                self._save_plot(fig5, f"{base_name}_composite")
            )
        
        # Generate summary
        summary = self._generate_summary_text(ndwi, flood_mask, before_ndwi)
        visualizations['summary'] = summary
        
        return visualizations
    
    def _plot_original(self, rgb: np.ndarray) -> Figure:
        """Plot original image."""
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(rgb)
        ax.set_title("Satellite Image")
        ax.axis('off')
        plt.tight_layout()
        return fig
    
    def _plot_ndwi_heatmap(self, ndwi: np.ndarray) -> Figure:
        """Plot NDWI heatmap."""
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(ndwi, cmap='RdYlBu_r', vmin=-0.5, vmax=0.5)
        ax.set_title("NDWI Heatmap")
        ax.axis('off')
        plt.colorbar(im, ax=ax, label="NDWI Value")
        plt.tight_layout()
        return fig
    
    def _plot_flood_mask(self, 
                        rgb: np.ndarray, 
                        ndwi: np.ndarray, 
                        flood_mask: np.ndarray) -> Figure:
        """Plot flood mask overlay."""
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
        
        # Original
        ax1.imshow(rgb)
        ax1.set_title("Original")
        ax1.axis('off')
        
        # NDWI
        im2 = ax2.imshow(ndwi, cmap='RdYlBu_r', vmin=-0.5, vmax=0.5)
        ax2.set_title("NDWI")
        ax2.axis('off')
        
        # Flood mask overlay
        ax3.imshow(rgb)
        overlay = np.zeros((*flood_mask.shape, 4))
        overlay[:, :, 0] = 1  # Red channel
        overlay[:, :, 1] = 0
        overlay[:, :, 2] = 0
        overlay[:, :, 3] = flood_mask * 0.5  # 50% transparency
        ax3.imshow(overlay)
        ax3.set_title(f"Flood Mask (Area: {np.sum(flood_mask)} pixels)")
        ax3.axis('off')
        
        plt.tight_layout()
        return fig
    
    def _plot_change_detection(self,
                              ndwi_after: np.ndarray,
                              ndwi_before: np.ndarray,
                              change_map: np.ndarray) -> Figure:
        """Plot change detection visualization."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 12))
        
        # Before NDWI
        im1 = ax1.imshow(ndwi_before, cmap='RdYlBu_r', vmin=-0.5, vmax=0.5)
        ax1.set_title("Before NDWI")
        ax1.axis('off')
        plt.colorbar(im1, ax=ax1, label="NDWI Value")
        
        # After NDWI
        im2 = ax2.imshow(ndwi_after, cmap='RdYlBu_r', vmin=-0.5, vmax=0.5)
        ax2.set_title("After NDWI")
        ax2.axis('off')
        plt.colorbar(im2, ax=ax2, label="NDWI Value")
        
        # Difference
        diff = ndwi_after - ndwi_before
        im3 = ax3.imshow(diff, cmap='RdBu', vmin=-0.5, vmax=0.5)
        ax3.set_title("NDWI Change")
        ax3.axis('off')
        plt.colorbar(im3, ax=ax3, label="Change Value")
        
        # Change map
        ax4.imshow(change_map, cmap='RdYlGn')
        ax4.set_title(f"Change Map (Significant)")
        ax4.axis('off')
        
        plt.tight_layout()
        return fig
    
    def _create_composite_visualization(self,
                                       rgb: np.ndarray,
                                       ndwi: np.ndarray,
                                       flood_mask: np.ndarray,
                                       before_ndwi: Optional[np.ndarray],
                                       change_map: Optional[np.ndarray]) -> Figure:
        """Create composite visualization with multiple panels."""
        n_cols = 2 if before_ndwi is not None else 1
        n_rows = 3 if before_ndwi is not None else 2
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 12))
        
        # Flatten axes for easier indexing
        if n_rows == 1:
            axes = axes.reshape(1, -1)
        
        idx = 0
        
        # Original
        ax = axes[idx // n_cols, idx % n_cols]
        ax.imshow(rgb)
        ax.set_title("Original Image")
        ax.axis('off')
        idx += 1
        
        # NDWI
        ax = axes[idx // n_cols, idx % n_cols]
        im = ax.imshow(ndwi, cmap='RdYlBu_r', vmin=-0.5, vmax=0.5)
        ax.set_title("NDWI")
        ax.axis('off')
        plt.colorbar(im, ax=ax, label="NDWI")
        idx += 1
        
        # Flood overlay
        if n_cols > 1:
            ax = axes[idx // n_cols, idx % n_cols]
            ax.imshow(rgb)
            overlay = np.zeros((*flood_mask.shape, 4))
            overlay[:, :, 0] = 1
            overlay[:, :, 3] = flood_mask * 0.4
            ax.imshow(overlay)
            ax.set_title("Flood Overlay")
            ax.axis('off')
            idx += 1
        
        # Change detection (if available)
        if before_ndwi is not None and change_map is not None:
            ax = axes[idx // n_cols, idx % n_cols]
            diff = ndwi - before_ndwi
            im = ax.imshow(diff, cmap='RdBu', vmin=-0.3, vmax=0.3)
            ax.set_title("NDWI Change (After - Before)")
            ax.axis('off')
            plt.colorbar(im, ax=ax, label="Change")
            idx += 1
        
        plt.tight_layout()
        return fig
    
    def _save_plot(self, fig: Figure, name: str) -> Dict[str, str]:
        """
        Save plot to file and convert to base64.
        
        Returns:
            Dictionary with file path and base64 data
        """
        result = {}
        
        if self.save_plots:
            file_path = os.path.join(self.output_dir, f"{name}.png")
            fig.savefig(file_path, dpi=150, bbox_inches='tight')
            result['file_path'] = file_path
            
            # Also save as PDF for high quality
            pdf_path = os.path.join(self.output_dir, f"{name}.pdf")
            fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
            result['pdf_path'] = pdf_path
        
        # Convert to base64 for API responses
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        result['base64'] = base64.b64encode(buf.read()).decode('utf-8')
        result['name'] = name
        
        plt.close(fig)
        
        return result
    
    def _generate_summary_text(self,
                              ndwi: np.ndarray,
                              flood_mask: np.ndarray,
                              before_ndwi: Optional[np.ndarray]) -> str:
        """Generate summary text for visualizations."""
        total_pixels = flood_mask.size
        flood_pixels = np.sum(flood_mask)
        flood_percentage = (flood_pixels / total_pixels) * 100
        
        summary = f"""
Satellite Processing Summary
============================
Total Pixels: {total_pixels:,}
Flood Pixels: {flood_pixels:,}
Flood Percentage: {flood_percentage:.2f}%

NDWI Statistics:
  - Min: {ndwi.min():.3f}
  - Max: {ndwi.max():.3f}
  - Mean: {ndwi.mean():.3f}
  - Std: {ndwi.std():.3f}
        """
        
        if before_ndwi is not None:
            diff = ndwi - before_ndwi
            summary += f"""
Change Detection:
  - NDWI Change (Mean): {diff.mean():.3f}
  - Max Increase: {diff.max():.3f}
  - Max Decrease: {diff.min():.3f}
            """
        
        return summary.strip()