#!/bin/bash
# Cloudflare Tunnel setup script for E3 workstation (Ubuntu 24.04)
# Run this on the E3 workstation

set -e

echo "=== Broker Agents — Cloudflare Tunnel Setup ==="
echo ""

# Check if already installed
if command -v cloudflared &> /dev/null; then
    echo "cloudflared already installed: $(cloudflared --version)"
else
    echo "Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
    chmod +x cloudflared
    sudo mv cloudflared /usr/local/bin/
    echo "Installed: $(cloudflared --version)"
fi

echo ""
echo "=== One-time tunnel setup ==="
echo "1. Go to https://dash.cloudflare.com/"
echo "2. Create a Zero Trust account (free)"
echo "3. Create a tunnel under Networks > Tunnels"
echo "4. Copy the tunnel token"
echo ""
echo "=== Running the tunnel ==="
echo "cloudflared tunnel run --token YOUR_TUNNEL_TOKEN_HERE"
echo ""
echo "=== Or run as a service (systemd) ==="
echo "sudo cloudflared service install YOUR_TUNNEL_TOKEN_HERE"
echo ""
echo "=== Get a free tunnel subdomain ==="
echo "After creating tunnel in dashboard, use 'Tunnel route DNS' with your domain"
echo ""
echo "=== Dashboard URL ==="
echo "Once running, your dashboard will be at:"
echo "  https://your-subdomain.trycloudflare.com"
echo ""
echo "=== Verify connectivity ==="
echo "cloudflared tunnel run --token YOUR_TOKEN --no-autoupdate"