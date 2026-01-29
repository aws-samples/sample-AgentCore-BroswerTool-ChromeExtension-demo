#!/usr/bin/env python3
"""Main demo script for AgentCore Browser with Chrome Extension.

This script demonstrates how to:
1. Download and configure a Chrome extension
2. Get temporary AWS credentials (1 hour validity)
3. Upload extension to S3
4. Create AgentCore Browser session with the extension
5. Verify extension is loaded and functional

Usage:
    # Full demo workflow
    python main.py
    
    # Use existing extension zip
    python main.py --extension-zip ./my-extension.zip
    
    # Only prepare extension (don't create browser)
    python main.py --prepare-only
    
    # Custom S3 bucket
    python main.py --bucket my-custom-bucket
    
    # Skip credential configuration
    python main.py --skip-credentials
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from setup_extension import ExtensionSetup
from s3_manager import S3Manager
from browser_with_extension import BrowserWithExtension, check_iam_permissions

console = Console()


class ExtensionDemo:
    """Main demo orchestrator."""
    
    DEFAULT_BUCKET = "browser-extension-demo-zihangh-20260129"
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        existing_extensions: Optional[list] = None,
        skip_credentials: bool = False
    ):
        """Initialize demo.
        
        Args:
            bucket_name: S3 bucket name (uses default if None)
            region: AWS region (uses AWS_REGION env var if None)
            existing_extensions: List of paths to existing extension zips
            skip_credentials: Skip AWS credential configuration
        """
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET_NAME', self.DEFAULT_BUCKET)
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.existing_extensions = existing_extensions or []
        self.skip_credentials = skip_credentials
        
        self.extension_zips = []  # List of prepared extension zips
        self.s3_uris = []  # List of S3 URIs
        self.browser = None
        
    def print_header(self):
        """Print demo header."""
        console.print(Panel.fit(
            "[bold cyan]AgentCore Browser + Chrome Extension Demo[/bold cyan]\n"
            "Load Chrome Extensions into AWS AgentCore Browser",
            border_style="cyan"
        ))
        
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met.
        
        Returns:
            True if all prerequisites are met
        """
        console.print("\n[bold cyan]🔍 Checking Prerequisites[/bold cyan]\n")
        
        # Check AWS credentials
        if not check_iam_permissions():
            console.print("\n[red]✗ AWS credentials not configured properly[/red]")
            console.print("\n[yellow]Please configure AWS credentials:[/yellow]")
            console.print("  aws configure")
            console.print("  or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY")
            return False
        
        # Check region
        console.print(f"[green]✓[/green] AWS Region: {self.region}")
        
        # Check S3 bucket name
        console.print(f"[green]✓[/green] S3 Bucket: {self.bucket_name}")
        
        # Check if using existing extensions
        if self.existing_extensions:
            for ext in self.existing_extensions:
                if not ext.exists():
                    console.print(f"[red]✗[/red] Extension file not found: {ext}")
                    return False
                console.print(f"[green]✓[/green] Using existing extension: {ext}")
        else:
            console.print("[yellow]⚠[/yellow] No extensions specified")
            console.print("[dim]Use --extension-zip to specify extensions[/dim]")
            return False
        
        console.print("\n[green]✓ Prerequisites check complete![/green]\n")
        return True
    
    def prepare_extension(self) -> bool:
        """Prepare the Chrome extensions.
        
        Returns:
            True if successful
        """
        try:
            for ext_path in self.existing_extensions:
                setup = ExtensionSetup()
                
                extension_zip = setup.prepare_extension(
                    existing_extension=ext_path,
                    skip_credentials=self.skip_credentials
                )
                
                self.extension_zips.append(extension_zip)
            
            return True
            
        except Exception as e:
            console.print(f"\n[red]✗ Extension preparation failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def upload_to_s3(self) -> bool:
        """Upload extensions to S3.
        
        Returns:
            True if successful
        """
        try:
            manager = S3Manager(self.bucket_name, self.region)
            
            for extension_zip in self.extension_zips:
                s3_uri = manager.setup_and_upload(extension_zip)
                
                if not s3_uri:
                    return False
                
                self.s3_uris.append(s3_uri)
            
            # Optional: cleanup old extensions
            if Confirm.ask("\n[cyan]Clean up old extension versions?[/cyan]", default=False):
                manager.cleanup_old_extensions(keep_latest=3)
            
            return True
            
        except Exception as e:
            console.print(f"\n[red]✗ S3 upload failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def create_browser(self) -> bool:
        """Create browser session with extensions.
        
        Returns:
            True if successful
        """
        try:
            self.browser = BrowserWithExtension(region=self.region)
            
            session = self.browser.create_browser_session(self.s3_uris)
            
            # Verify extension
            self.browser.verify_extension_loaded()
            
            return True
            
        except Exception as e:
            console.print(f"\n[red]✗ Browser creation failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def test_extension(self) -> bool:
        """Test extension functionality.
        
        Returns:
            True if successful
        """
        console.print("\n[bold cyan]🧪 Testing Extension[/bold cyan]\n")
        
        if not self.browser:
            console.print("[red]✗[/red] No active browser session")
            return False
        
        # Test with AWS homepage
        success = self.browser.test_extension_functionality("https://aws.amazon.com")
        
        if success:
            console.print("\n[green]✓ Extension test complete![/green]")
            console.print("\n[bold yellow]Next Steps:[/bold yellow]")
            console.print("  1. Open the browser session in AWS Console")
            console.print("  2. Look for the extension icon in the toolbar")
            console.print("  3. Click the extension to configure AWS credentials")
            console.print("  4. Try summarizing a web page")
            
            if not self.skip_credentials:
                console.print("\n[cyan]AWS Credentials (from aws_config.json):[/cyan]")
                console.print("  • Access Key ID: [configured]")
                console.print("  • Secret Access Key: [configured]")
                console.print("  • Session Token: [configured]")
                console.print("  • Valid for: 1 hour")
        
        return success
    
    def print_summary(self):
        """Print demo summary."""
        console.print("\n" + "="*60)
        console.print("[bold cyan]📊 Demo Summary[/bold cyan]\n")
        
        if self.extension_zips:
            console.print(f"[green]✓[/green] Extensions ({len(self.extension_zips)}):")
            for i, ext_zip in enumerate(self.extension_zips, 1):
                console.print(f"  {i}. {ext_zip}")
        
        if self.s3_uris:
            console.print(f"\n[green]✓[/green] S3 URIs ({len(self.s3_uris)}):")
            for i, s3_uri in enumerate(self.s3_uris, 1):
                console.print(f"  {i}. {s3_uri}")
        
        if self.browser and self.browser.session_id:
            console.print(f"\n[green]✓[/green] Browser Session: {self.browser.session_id}")
            console.print(f"[dim]Console: https://console.aws.amazon.com/agentcore/home?region={self.region}#/browsers[/dim]")
        
        console.print("\n" + "="*60 + "\n")
    
    def cleanup(self):
        """Clean up resources."""
        console.print("\n[cyan]🧹 Cleaning up...[/cyan]")
        
        if self.browser:
            self.browser.close_session()
        
        console.print("[green]✓ Cleanup complete[/green]\n")
    
    def run(self, prepare_only: bool = False) -> int:
        """Run the complete demo.
        
        Args:
            prepare_only: Only prepare extension, don't create browser
            
        Returns:
            Exit code (0 for success)
        """
        self.print_header()
        
        try:
            # Step 1: Check prerequisites
            if not self.check_prerequisites():
                return 1
            
            # Step 2: Prepare extension
            if not self.prepare_extension():
                return 1
            
            # Step 3: Upload to S3
            if not self.upload_to_s3():
                return 1
            
            if prepare_only:
                console.print("\n[yellow]Prepare-only mode: Skipping browser creation[/yellow]")
                console.print(f"\n[green]Extensions ready at:[/green]")
                for i, s3_uri in enumerate(self.s3_uris, 1):
                    console.print(f"  {i}. {s3_uri}")
                console.print("\nYou can now use these S3 URIs to create a browser session")
                return 0
            
            # Step 4: Create browser
            if not self.create_browser():
                return 1
            
            # Step 5: Test extension
            self.test_extension()
            
            # Print summary
            self.print_summary()
            
            # Keep browser running
            console.print("[yellow]Browser session is active[/yellow]")
            console.print("[dim]Press Ctrl+C to close and exit[/dim]\n")
            
            try:
                input("Press Enter to close browser session...")
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
            
            return 0
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            return 130
            
        except Exception as e:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
            import traceback
            traceback.print_exc()
            return 1
            
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AgentCore Browser + Chrome Extension Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with single extension
  python main.py --extension-zip stealth-extension.zip
  
  # Run with multiple extensions (Stealth + Bedrock Summary)
  python main.py --extension-zip stealth-extension.zip --extension-zip bedrock-summary-extension.zip
  
  # Prepare only (don't create browser)
  python main.py --prepare-only --extension-zip stealth-extension.zip
  
  # Custom bucket and region
  python main.py --bucket my-bucket --region us-west-2 --extension-zip stealth-extension.zip
        """
    )
    
    parser.add_argument(
        "--bucket",
        help="S3 bucket name (default: browser-extension-demo-zihangh-20260129)"
    )
    
    parser.add_argument(
        "--region",
        help="AWS region (default: from AWS_REGION env var or us-east-1)"
    )
    
    parser.add_argument(
        "--extension-zip",
        type=Path,
        action='append',
        dest='extension_zips',
        help="Path to extension zip file (can be specified multiple times for multiple extensions)"
    )
    
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only prepare and upload extension, don't create browser"
    )
    
    parser.add_argument(
        "--skip-credentials",
        action="store_true",
        help="Skip AWS credential configuration in extension"
    )
    
    args = parser.parse_args()
    
    demo = ExtensionDemo(
        bucket_name=args.bucket,
        region=args.region,
        existing_extensions=args.extension_zips,
        skip_credentials=args.skip_credentials
    )
    
    sys.exit(demo.run(prepare_only=args.prepare_only))


if __name__ == "__main__":
    main()
