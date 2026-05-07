#!/bin/bash
# Tailscale setup script for E3 workstation (Ubuntu 24.04)
# Run this on the E3 workstation

set -e

echo "=== Broker Agents — Tailscale Setup ==="
echo ""

# Check if already installed
if command -v tailscale &> /dev/null; then
    echo "Tailscale already installed: $(tailscale version)"
else
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "Installed: $(tailscale version)"
fi

echo ""
echo "=== First-time setup ==="
echo "1. Sign up at https://login.tailscale.com/ using your email"
echo "2. Run the following command on this machine:"
echo ""
echo "   sudo tailscale up --operator=\$USER"
echo ""
echo "3. Authorize the device in your Tailscale admin console"
echo ""
echo "=== Getting your device name ==="
echo "After connecting, run:"
echo "   tailscale status"
echo "Your device name will be: broker-agents.<your-tailnet>.ts.net"
echo ""
echo "=== Accessing the dashboard ==="
echo "From any device with Tailscale installed:"
echo "   http://broker-agents.<your-tailnet>.ts.net:8000"
echo ""
echo "=== (Optional) Access from browser without Tailscale app ==="
echo "Enable Tailscale Funnel for public HTTPS access:"
echo "   sudo tailscale funnel 8000"
echo "   tailscale funnel status"
echo "Warning: This exposes port 8000 publicly. Add auth below."
echo ""
echo "=== Adding password protection (recommended if using Funnel) ==="
echo "In dashboard/backend/main.py, add middleware for HTTP Basic Auth"
echo "when running with Tailscale Funnel enabled."
