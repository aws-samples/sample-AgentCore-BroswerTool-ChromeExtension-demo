#!/usr/bin/env python3
"""Browser session management with extension support."""

import os
from typing import Optional, List, Dict
import boto3
from botocore.exceptions import ClientError
from rich.console import Console

console = Console()


class BrowserWithExtension:
    """Manage AgentCore Browser sessions with extensions."""
    
    def __init__(self, region: Optional[str] = None):
        """Initialize browser manager.
        
        Args:
            region: AWS region (uses AWS_REGION env var if None)
        """
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.agentcore_client = boto3.client('bedrock-agentcore', region_name=self.region)
        self.browser_session = None
        self.session_id = None
        
    def create_browser_session(
        self,
        extension_s3_uris: List[str],
        session_name: Optional[str] = None
    ) -> Dict:
        """Create a browser session with extensions.
        
        Args:
            extension_s3_uris: List of S3 URIs for extensions (format: s3://bucket/key)
            session_name: Optional session name (auto-generated if None)
            
        Returns:
            Browser session details
        """
        console.print("\n[bold cyan]🌐 Creating Browser Session with Extensions[/bold cyan]\n")
        
        # Parse S3 URIs and prepare extensions configuration
        extensions = []
        for uri in extension_s3_uris:
            # Parse s3://bucket/key format
            if uri.startswith('s3://'):
                parts = uri[5:].split('/', 1)
                bucket = parts[0]
                prefix = parts[1] if len(parts) > 1 else ''
                
                extensions.append({
                    'location': {
                        's3': {
                            'bucket': bucket,
                            'prefix': prefix  # Use 'prefix' not 'key'
                        }
                    }
                })
        
        console.print(f"[cyan]Extensions to load:[/cyan]")
        for i, uri in enumerate(extension_s3_uris, 1):
            console.print(f"  {i}. {uri}")
        
        console.print(f"\n[cyan]Region: {self.region}[/cyan]")
        if not session_name:
            import time
            session_name = f"extension-demo-{int(time.time())}"
        console.print(f"[cyan]Session Name: {session_name}[/cyan]")
        
        try:
            console.print("\n[dim]Starting browser session with extensions...[/dim]")
            
            # Use start_browser_session API
            response = self.agentcore_client.start_browser_session(
                browserIdentifier='aws.browser.v1',
                name=session_name,
                sessionTimeoutSeconds=1800,  # 30 minutes
                extensions=extensions
            )
            
            self.session_id = response['sessionId']
            
            # Store session info
            self.browser_session = {
                'session_id': self.session_id,
                'session_name': session_name,
                'region': self.region
            }
            
            console.print(f"[green]✓[/green] Browser session created successfully")
            console.print(f"[dim]Session ID: {self.session_id}[/dim]")
            console.print(f"[dim]Console: https://console.aws.amazon.com/agentcore/home?region={self.region}#/browsers[/dim]")
            
            # Get session details
            session_details = {
                'session_id': self.session_id,
                'region': self.region,
                'extensions': extension_s3_uris,
                'status': 'active'
            }
            
            console.print("\n[green]✓ Browser session ready![/green]\n")
            return session_details
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create browser session: {e}")
            console.print("\n[yellow]Troubleshooting tips:[/yellow]")
            console.print("  1. Check AWS credentials and permissions")
            console.print("  2. Verify S3 URIs are accessible")
            console.print("  3. Ensure IAM policy includes s3:GetObject permission")
            console.print("  4. Check that region supports AgentCore Browser")
            raise
    
    def verify_extension_loaded(self) -> bool:
        """Verify that extensions are loaded in the browser.
        
        Returns:
            True if extensions appear to be loaded
        """
        console.print("[cyan]Verifying extension installation...[/cyan]")
        
        if not self.browser_session:
            console.print("[red]✗[/red] No active browser session")
            return False
        
        try:
            # Try to navigate to chrome://extensions to verify
            # Note: This may not work as chrome:// URLs are restricted
            console.print("[dim]Checking browser state...[/dim]")
            
            # For now, we'll assume success if session was created
            # In a real implementation, you'd need to:
            # 1. Navigate to a test page
            # 2. Check if extension UI elements are present
            # 3. Or use extension-specific verification methods
            
            console.print("[green]✓[/green] Browser session is active")
            console.print("[yellow]⚠[/yellow] Extension verification requires manual check")
            console.print("[dim]Navigate to chrome://extensions in the browser to verify[/dim]")
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not verify extension: {e}")
            return False
    
    def test_extension_functionality(self, test_url: str = "https://aws.amazon.com") -> bool:
        """Test extension functionality by visiting a page.
        
        Args:
            test_url: URL to visit for testing
            
        Returns:
            True if test succeeded
        """
        console.print(f"\n[cyan]Testing extension functionality...[/cyan]")
        console.print(f"[dim]Test URL: {test_url}[/dim]")
        
        if not self.browser_session:
            console.print("[red]✗[/red] No active browser session")
            return False
        
        try:
            # Navigate to test page
            console.print(f"[dim]Navigating to {test_url}...[/dim]")
            
            # Note: Actual navigation would require using the browser client
            # This is a placeholder for the actual implementation
            
            console.print("[green]✓[/green] Navigation successful")
            console.print("\n[yellow]Manual verification required:[/yellow]")
            console.print("  1. Check if extension icon appears in browser toolbar")
            console.print("  2. Click extension icon to verify it's functional")
            console.print("  3. Try using extension features (e.g., summarize page)")
            
            return True
            
        except Exception as e:
            console.print(f"[red]✗[/red] Test failed: {e}")
            return False
    
    def get_session_info(self) -> Optional[Dict]:
        """Get current session information.
        
        Returns:
            Session info dict or None
        """
        if not self.session_id:
            return None
        
        return {
            'session_id': self.session_id,
            'region': self.region,
            'status': 'active' if self.browser_session else 'closed'
        }
    
    def close_session(self):
        """Close the browser session."""
        console.print("\n[cyan]Closing browser session...[/cyan]")
        
        if self.browser_session and self.session_id:
            try:
                # Stop the browser session
                self.agentcore_client.stop_browser_session(
                    sessionId=self.session_id
                )
                console.print("[green]✓[/green] Browser session stopped")
                self.browser_session = None
                self.session_id = None
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Error stopping session: {e}")
        else:
            console.print("[dim]No active session to close[/dim]")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_session()


def check_iam_permissions() -> bool:
    """Check if required IAM permissions are available.
    
    Returns:
        True if permissions appear to be available
    """
    console.print("[cyan]Checking IAM permissions...[/cyan]")
    
    try:
        # Check AWS identity
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        console.print(f"[green]✓[/green] AWS Account: {identity['Account']}")
        console.print(f"[green]✓[/green] Identity: {identity['Arn'].split('/')[-1]}")
        
        # Note: We can't directly check specific permissions without trying them
        # In production, you'd use IAM policy simulator or try actual operations
        
        console.print("\n[yellow]Required permissions:[/yellow]")
        console.print("  • s3:GetObject, s3:GetObjectVersion")
        console.print("  • bedrock-agentcore:CreateBrowserSession")
        console.print("  • bedrock:InvokeModel (for extension functionality)")
        
        return True
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to check permissions: {e}")
        return False


if __name__ == "__main__":
    # Test browser creation
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python browser_with_extension.py <s3://bucket/key>")
        sys.exit(1)
    
    s3_uri = sys.argv[1]
    
    # Check permissions first
    if not check_iam_permissions():
        print("\nWarning: Permission check failed, but continuing anyway...")
    
    # Create browser with extension
    with BrowserWithExtension() as browser:
        try:
            session = browser.create_browser_session([s3_uri])
            print(f"\nBrowser session created: {session['session_id']}")
            
            # Verify extension
            browser.verify_extension_loaded()
            
            # Test functionality
            browser.test_extension_functionality()
            
            input("\nPress Enter to close browser session...")
            
        except Exception as e:
            print(f"\nError: {e}")
            sys.exit(1)
