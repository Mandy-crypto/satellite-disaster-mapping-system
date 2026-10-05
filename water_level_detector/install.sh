#!/bin/bash
# =============================================
# 📸 Water Level Detection - Installation Script
# =============================================

echo "=========================================="
echo "📸 Water Level Detection - Installing..."
echo "=========================================="

# Update system
echo "📦 Updating system..."
sudo apt update
sudo apt upgrade -y

# Install Python dependencies
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt

# Enable camera (for Raspberry Pi)
echo "📸 Configuring camera..."
sudo raspi-config nonint do_camera 0
sudo modprobe bcm2835-v4l2

# Create directories
mkdir -p logs
mkdir -p config

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Calibrate: python3 water_level_camera.py --calibrate"
echo "   2. Run: python3 water_level_camera.py"
echo ""