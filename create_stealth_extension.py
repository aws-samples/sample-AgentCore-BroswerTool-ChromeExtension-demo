#!/usr/bin/env python3
"""Create a stealth extension to bypass bot detection.

This extension modifies browser properties to make it appear more like a regular user browser.
"""

import json
import zipfile
from pathlib import Path
from rich.console import Console

console = Console()


def create_stealth_extension(output_dir: Path = Path("stealth_extension")):
    """Create a stealth extension to bypass bot detection.
    
    Args:
        output_dir: Directory to create extension in
    """
    console.print("[cyan]Creating stealth extension...[/cyan]")
    
    # Create directory
    output_dir.mkdir(exist_ok=True)
    
    # Create manifest.json
    manifest = {
        "manifest_version": 3,
        "name": "Stealth Mode for AgentCore Browser",
        "version": "1.0.0",
        "description": "Makes the browser appear more human-like to bypass bot detection",
        "permissions": ["webNavigation", "webRequest", "storage"],
        "host_permissions": ["<all_urls>"],
        "background": {
            "service_worker": "background.js"
        },
        "content_scripts": [
            {
                "matches": ["<all_urls>"],
                "js": ["content.js"],
                "run_at": "document_start",
                "all_frames": True
            }
        ],
        "web_accessible_resources": [
            {
                "resources": ["inject.js"],
                "matches": ["<all_urls>"]
            }
        ],
        "icons": {
            "16": "icon16.png",
            "48": "icon48.png",
            "128": "icon128.png"
        }
    }
    
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Create background.js
    background_js = """// Background script for stealth mode

// Override User-Agent for all requests
chrome.webRequest.onBeforeSendHeaders.addListener(
  function(details) {
    const headers = details.requestHeaders;
    
    // Find and modify User-Agent header
    for (let i = 0; i < headers.length; i++) {
      if (headers[i].name.toLowerCase() === 'user-agent') {
        // Use a common Chrome User-Agent
        headers[i].value = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';
      }
    }
    
    // Remove automation-related headers
    const headersToRemove = [
      'x-devtools-emulate-network-conditions-client-id',
      'x-client-data'
    ];
    
    for (let i = headers.length - 1; i >= 0; i--) {
      const headerName = headers[i].name.toLowerCase();
      if (headersToRemove.includes(headerName)) {
        headers.splice(i, 1);
      }
    }
    
    return { requestHeaders: headers };
  },
  { urls: ['<all_urls>'] },
  ['blocking', 'requestHeaders']
);

// Add random delays to make behavior more human-like
let lastRequestTime = Date.now();
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    const now = Date.now();
    const timeSinceLastRequest = now - lastRequestTime;
    
    // If requests are too fast (< 50ms), it might look automated
    // But we can't actually delay here, just log for debugging
    if (timeSinceLastRequest < 50) {
      console.log('Fast request detected:', details.url);
    }
    
    lastRequestTime = now;
  },
  { urls: ['<all_urls>'] }
);

console.log('Stealth mode background script loaded');
"""
    
    with open(output_dir / "background.js", "w") as f:
        f.write(background_js)
    
    # Create content.js
    content_js = """// Content script to inject stealth code

(function() {
  'use strict';
  
  // Inject the stealth script into the page context
  const script = document.createElement('script');
  script.src = chrome.runtime.getURL('inject.js');
  script.onload = function() {
    this.remove();
  };
  (document.head || document.documentElement).appendChild(script);
})();
"""
    
    with open(output_dir / "content.js", "w") as f:
        f.write(content_js)
    
    # Create inject.js - the main stealth code
    inject_js = """// Stealth mode injection script
// This runs in the page context to modify browser properties

(function() {
  'use strict';
  
  console.log('Stealth mode activated');
  
  // Override navigator.webdriver (most important)
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
  });
  
  // Override navigator properties to appear more human
  const navigatorProps = {
    platform: 'MacIntel',
    vendor: 'Google Inc.',
    hardwareConcurrency: 8,
    deviceMemory: 8,
    maxTouchPoints: 0
  };
  
  for (const [key, value] of Object.entries(navigatorProps)) {
    try {
      Object.defineProperty(navigator, key, {
        get: () => value,
        configurable: true
      });
    } catch (e) {
      console.warn(`Failed to override navigator.${key}:`, e);
    }
  }
  
  // Override plugins to appear more realistic
  Object.defineProperty(navigator, 'plugins', {
    get: () => {
      return [
        {
          name: 'Chrome PDF Plugin',
          description: 'Portable Document Format',
          filename: 'internal-pdf-viewer',
          length: 1
        },
        {
          name: 'Chrome PDF Viewer',
          description: '',
          filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
          length: 1
        },
        {
          name: 'Native Client',
          description: '',
          filename: 'internal-nacl-plugin',
          length: 2
        }
      ];
    },
    configurable: true
  });
  
  // Override languages
  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true
  });
  
  // Override permissions
  const originalQuery = window.navigator.permissions.query;
  window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
      Promise.resolve({ state: Notification.permission }) :
      originalQuery(parameters)
  );
  
  // Override chrome runtime to hide automation
  if (window.chrome && window.chrome.runtime) {
    try {
      Object.defineProperty(window.chrome.runtime, 'connect', {
        get: () => undefined,
        configurable: true
      });
    } catch (e) {
      // Ignore if can't override
    }
  }
  
  // Add realistic screen properties
  Object.defineProperty(screen, 'availWidth', {
    get: () => 1920,
    configurable: true
  });
  
  Object.defineProperty(screen, 'availHeight', {
    get: () => 1080,
    configurable: true
  });
  
  // Override automation-related properties
  try {
    // Hide automation flags
    delete navigator.__proto__.webdriver;
    
    // Override toString to hide modifications
    const originalToString = Function.prototype.toString;
    Function.prototype.toString = function() {
      if (this === navigator.webdriver) {
        return 'function webdriver() { [native code] }';
      }
      return originalToString.call(this);
    };
  } catch (e) {
    // Ignore errors
  }
  
  // Override Date to add slight randomness (appears more human)
  const originalDate = Date;
  Date = class extends originalDate {
    constructor(...args) {
      if (args.length === 0) {
        super();
        // Add 0-5ms random delay to appear more human
        const randomMs = Math.floor(Math.random() * 5);
        return new originalDate(super.getTime() + randomMs);
      }
      return new originalDate(...args);
    }
  };
  
  // Prevent canvas fingerprinting
  const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(type) {
    // Add slight noise to canvas to prevent fingerprinting
    const context = this.getContext('2d');
    if (context) {
      const imageData = context.getImageData(0, 0, this.width, this.height);
      for (let i = 0; i < imageData.data.length; i += 4) {
        // Add tiny random noise
        imageData.data[i] += Math.floor(Math.random() * 2);
      }
      context.putImageData(imageData, 0, 0);
    }
    return originalToDataURL.apply(this, arguments);
  };
  
  // Override WebGL fingerprinting
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // Randomize WebGL vendor and renderer
    if (parameter === 37445) {
      return 'Intel Inc.';
    }
    if (parameter === 37446) {
      return 'Intel Iris OpenGL Engine';
    }
    return getParameter.apply(this, arguments);
  };
  
  // Override Notification permission
  try {
    Object.defineProperty(Notification, 'permission', {
      get: () => 'default',
      configurable: true
    });
  } catch (e) {
    // Ignore
  }
  
  console.log('Stealth mode: All overrides applied successfully');
})();
"""
    
    with open(output_dir / "inject.js", "w") as f:
        f.write(inject_js)
    
    # Create simple icon files (1x1 PNG)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    
    for size in [16, 48, 128]:
        with open(output_dir / f"icon{size}.png", "wb") as f:
            f.write(png_data)
    
    console.print(f"[green]✓[/green] Stealth extension created in: {output_dir}")
    
    return output_dir


def package_extension(extension_dir: Path, output_zip: Path = Path("stealth-extension.zip")):
    """Package extension directory into a zip file.
    
    Args:
        extension_dir: Extension directory
        output_zip: Output zip file path
    """
    console.print(f"[cyan]Packaging extension to: {output_zip}[/cyan]")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in extension_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(extension_dir)
                zipf.write(file_path, arcname)
    
    file_size = output_zip.stat().st_size / 1024  # KB
    console.print(f"[green]✓[/green] Extension packaged: {output_zip} ({file_size:.1f} KB)")
    
    return output_zip


def main():
    """Create and package stealth extension."""
    console.print("\n[bold cyan]🕵️  Creating Stealth Extension[/bold cyan]\n")
    
    # Create extension
    extension_dir = create_stealth_extension()
    
    # Package extension
    zip_path = package_extension(extension_dir)
    
    console.print("\n[green]✓ Stealth extension ready![/green]")
    console.print(f"\n[cyan]Usage:[/cyan]")
    console.print(f"  python main.py --extension-zip {zip_path}")
    console.print(f"\n[yellow]Features:[/yellow]")
    console.print("  • Overrides navigator.webdriver")
    console.print("  • Modifies User-Agent header")
    console.print("  • Randomizes canvas fingerprinting")
    console.print("  • Overrides WebGL fingerprinting")
    console.print("  • Makes browser appear more human-like")


if __name__ == "__main__":
    main()
