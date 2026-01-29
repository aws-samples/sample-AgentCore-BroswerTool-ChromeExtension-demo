#!/usr/bin/env python3
"""Extension setup module - download, configure, and package Chrome extension."""

import os
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Dict
import boto3
from rich.console import Console

console = Console()


class ExtensionSetup:
    """Handle Chrome extension download, configuration, and packaging."""
    
    # GitHub repository for the extension
    GITHUB_REPO = "aws-samples/amazon-bedrock-summary-client-for-chrome"
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize extension setup.
        
        Args:
            work_dir: Working directory for temporary files
        """
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="extension_"))
        self.extension_dir = self.work_dir / "extension"
        self.sts_client = boto3.client('sts')
        
    def get_temporary_credentials(self, duration_seconds: int = 3600) -> Dict[str, str]:
        """Get temporary AWS credentials using STS.
        
        Args:
            duration_seconds: Credential validity duration (default: 1 hour)
            
        Returns:
            Dict with AccessKeyId, SecretAccessKey, SessionToken
        """
        console.print(f"[cyan]Getting temporary AWS credentials (valid for {duration_seconds//60} minutes)...[/cyan]")
        
        try:
            response = self.sts_client.get_session_token(
                DurationSeconds=duration_seconds
            )
            
            credentials = response['Credentials']
            console.print("[green]✓[/green] Temporary credentials obtained")
            console.print(f"[dim]Expires at: {credentials['Expiration']}[/dim]")
            
            return {
                'AccessKeyId': credentials['AccessKeyId'],
                'SecretAccessKey': credentials['SecretAccessKey'],
                'SessionToken': credentials['SessionToken']
            }
            
        except Exception as e:
            console.print(f"[red]✗ Failed to get temporary credentials: {e}[/red]")
            raise
    
    def download_extension_from_github(self) -> Path:
        """Download extension from GitHub repository.
        
        Returns:
            Path to downloaded extension directory
        """
        console.print("[cyan]Downloading extension from GitHub...[/cyan]")
        
        # For demo purposes, we'll clone the repo and build it
        # In production, you'd download a pre-built release
        import subprocess
        
        try:
            repo_url = f"https://github.com/{self.GITHUB_REPO}.git"
            clone_dir = self.work_dir / "repo"
            
            console.print(f"[dim]Cloning {repo_url}...[/dim]")
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(clone_dir)],
                check=True,
                capture_output=True
            )
            
            console.print("[cyan]Building extension...[/cyan]")
            subprocess.run(
                ["npm", "install"],
                cwd=clone_dir,
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["npm", "run", "build"],
                cwd=clone_dir,
                check=True,
                capture_output=True
            )
            
            # Copy built extension to extension_dir
            build_dir = clone_dir / "dist"  # Assuming build output is in dist/
            if not build_dir.exists():
                build_dir = clone_dir  # Fallback to repo root
            
            shutil.copytree(build_dir, self.extension_dir, dirs_exist_ok=True)
            
            console.print("[green]✓[/green] Extension downloaded and built")
            return self.extension_dir
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Failed to build extension: {e}[/red]")
            console.print("[yellow]Tip: Make sure git and npm are installed[/yellow]")
            raise
        except Exception as e:
            console.print(f"[red]✗ Failed to download extension: {e}[/red]")
            raise
    
    def use_existing_extension(self, extension_path: Path) -> Path:
        """Use an existing extension zip or directory.
        
        Args:
            extension_path: Path to extension zip or directory
            
        Returns:
            Path to extension directory
        """
        console.print(f"[cyan]Using existing extension: {extension_path}[/cyan]")
        
        if extension_path.is_file() and extension_path.suffix == '.zip':
            # Extract zip
            console.print("[dim]Extracting zip file...[/dim]")
            with zipfile.ZipFile(extension_path, 'r') as zip_ref:
                zip_ref.extractall(self.extension_dir)
        elif extension_path.is_dir():
            # Copy directory
            console.print("[dim]Copying extension directory...[/dim]")
            shutil.copytree(extension_path, self.extension_dir, dirs_exist_ok=True)
        else:
            raise ValueError(f"Invalid extension path: {extension_path}")
        
        console.print("[green]✓[/green] Extension loaded")
        return self.extension_dir
    
    def configure_extension_credentials(self, credentials: Dict[str, str]) -> None:
        """Configure extension with AWS credentials.
        
        The Bedrock Summary Extension stores credentials in localStorage under 'keys'.
        We need to inject this into the popup.js file.
        
        Args:
            credentials: AWS credentials dict
        """
        console.print("[cyan]Configuring extension with AWS credentials...[/cyan]")
        
        # Look for manifest.json
        manifest_path = self.extension_dir / "manifest.json"
        if not manifest_path.exists():
            console.print("[yellow]⚠ manifest.json not found, extension may not work[/yellow]")
            return
        
        # Read manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        console.print(f"[dim]Extension: {manifest.get('name', 'Unknown')} v{manifest.get('version', '?')}[/dim]")
        
        # Find and modify popup.js to inject credentials
        popup_js_path = self.extension_dir / "popup.js"
        if popup_js_path.exists():
            with open(popup_js_path, 'r') as f:
                popup_js = f.read()
            
            # Inject credentials at the beginning of the file
            credentials_injection = f"""
// Auto-injected AWS credentials
(function() {{
    const credentials = {{
        accessKeyId: '{credentials['AccessKeyId']}',
        secretAccessKey: '{credentials['SecretAccessKey']}',
        sessionToken: '{credentials['SessionToken']}'
    }};
    localStorage.setItem('keys', JSON.stringify(credentials));
    console.log('AWS credentials auto-configured');
}})();

"""
            popup_js = credentials_injection + popup_js
            
            with open(popup_js_path, 'w') as f:
                f.write(popup_js)
            
            console.print("[green]✓[/green] Credentials injected into popup.js")
        
        # Also modify popup.html to inject credentials
        popup_html_path = self.extension_dir / "popup.html"
        if popup_html_path.exists():
            with open(popup_html_path, 'r') as f:
                popup_html = f.read()
            
            # Inject script at the beginning of body
            credentials_script = f"""<script>
// Auto-configure AWS credentials
(function() {{
    const credentials = {{
        accessKeyId: '{credentials['AccessKeyId']}',
        secretAccessKey: '{credentials['SecretAccessKey']}',
        sessionToken: '{credentials['SessionToken']}'
    }};
    localStorage.setItem('keys', JSON.stringify(credentials));
    console.log('AWS credentials configured from popup.html');
}})();
</script>
"""
            
            # Insert after <body> tag
            popup_html = popup_html.replace('<body>', '<body>\n' + credentials_script)
            
            with open(popup_html_path, 'w') as f:
                f.write(popup_html)
            
            console.print("[green]✓[/green] Credentials injected into popup.html")
        
        console.print("[green]✓[/green] AWS credentials configured")
        console.print(f"[dim]Credentials will be auto-loaded when extension starts[/dim]")
    
    def package_extension(self, output_path: Optional[Path] = None) -> Path:
        """Package extension directory into a zip file.
        
        Args:
            output_path: Output zip file path (auto-generated if None)
            
        Returns:
            Path to created zip file
        """
        console.print("[cyan]Packaging extension...[/cyan]")
        
        if output_path is None:
            import time
            timestamp = int(time.time())
            output_path = Path(f"bedrock-summary-extension-{timestamp}.zip")
        
        # Create zip file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.extension_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.extension_dir)
                    zipf.write(file_path, arcname)
        
        file_size = output_path.stat().st_size / 1024 / 1024  # MB
        console.print(f"[green]✓[/green] Extension packaged: {output_path}")
        console.print(f"[dim]Size: {file_size:.2f} MB[/dim]")
        
        if file_size > 10:
            console.print("[yellow]⚠ Warning: Extension size exceeds 10 MB limit[/yellow]")
        
        return output_path
    
    def prepare_extension(
        self,
        existing_extension: Optional[Path] = None,
        skip_credentials: bool = False
    ) -> Path:
        """Complete extension preparation workflow.
        
        Args:
            existing_extension: Path to existing extension (downloads if None)
            skip_credentials: Skip credential configuration
            
        Returns:
            Path to packaged extension zip
        """
        console.print("\n[bold cyan]📦 Preparing Chrome Extension[/bold cyan]\n")
        
        # Step 1: Get extension
        if existing_extension:
            self.use_existing_extension(existing_extension)
        else:
            self.download_extension_from_github()
        
        # Step 2: Get and configure credentials
        if not skip_credentials:
            credentials = self.get_temporary_credentials()
            self.configure_extension_credentials(credentials)
        else:
            console.print("[yellow]Skipping credential configuration[/yellow]")
        
        # Step 3: Package extension
        zip_path = self.package_extension()
        
        console.print("\n[green]✓ Extension preparation complete![/green]\n")
        return zip_path
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)


if __name__ == "__main__":
    # Test the extension setup
    setup = ExtensionSetup()
    try:
        zip_path = setup.prepare_extension()
        print(f"\nExtension packaged at: {zip_path}")
    finally:
        # Keep temp files for inspection
        print(f"Temp files at: {setup.work_dir}")
