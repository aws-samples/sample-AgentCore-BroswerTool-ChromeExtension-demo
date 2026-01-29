#!/usr/bin/env python3
"""Setup script for Amazon Bedrock Summary Extension.

Downloads, builds, and prepares the real Bedrock Summary Extension from GitHub.
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

console = Console()


class BedrockSummaryExtensionSetup:
    """Setup Amazon Bedrock Summary Extension."""
    
    REPO_URL = "https://github.com/aws-samples/amazon-bedrock-summary-client-for-chrome.git"
    REPO_NAME = "amazon-bedrock-summary-client-for-chrome"
    
    def __init__(self, work_dir: Path = Path(".")):
        """Initialize setup.
        
        Args:
            work_dir: Working directory
        """
        self.work_dir = work_dir
        self.repo_dir = self.work_dir / self.REPO_NAME
        
    def check_prerequisites(self) -> bool:
        """Check if git and npm are installed.
        
        Returns:
            True if prerequisites are met
        """
        console.print("\n[bold cyan]🔍 Checking Prerequisites[/bold cyan]\n")
        
        # Check git
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            console.print(f"[green]✓[/green] Git: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]✗[/red] Git not found")
            console.print("[yellow]Please install git:[/yellow]")
            console.print("  macOS: brew install git")
            console.print("  Linux: sudo apt-get install git")
            return False
        
        # Check npm
        try:
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            console.print(f"[green]✓[/green] npm: v{result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]✗[/red] npm not found")
            console.print("[yellow]Please install Node.js and npm:[/yellow]")
            console.print("  macOS: brew install node")
            console.print("  Linux: sudo apt-get install nodejs npm")
            console.print("  Or visit: https://nodejs.org/")
            return False
        
        console.print("\n[green]✓ All prerequisites met![/green]\n")
        return True
    
    def clone_repository(self) -> bool:
        """Clone the GitHub repository.
        
        Returns:
            True if successful
        """
        console.print("[bold cyan]📥 Cloning Repository[/bold cyan]\n")
        
        if self.repo_dir.exists():
            console.print(f"[yellow]Repository already exists: {self.repo_dir}[/yellow]")
            if Confirm.ask("Delete and re-clone?", default=False):
                console.print("[dim]Removing existing repository...[/dim]")
                shutil.rmtree(self.repo_dir)
            else:
                console.print("[green]✓[/green] Using existing repository")
                return True
        
        console.print(f"[cyan]Cloning from: {self.REPO_URL}[/cyan]")
        console.print(f"[dim]Destination: {self.repo_dir}[/dim]\n")
        
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", self.REPO_URL],
                cwd=self.work_dir,
                check=True
            )
            console.print(f"\n[green]✓[/green] Repository cloned successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"\n[red]✗[/red] Failed to clone repository: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install npm dependencies.
        
        Returns:
            True if successful
        """
        console.print("\n[bold cyan]📦 Installing Dependencies[/bold cyan]\n")
        console.print("[dim]Running: npm install[/dim]")
        console.print("[yellow]This may take a few minutes...[/yellow]\n")
        
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=self.repo_dir,
                check=True
            )
            console.print("\n[green]✓[/green] Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"\n[red]✗[/red] Failed to install dependencies: {e}")
            return False
    
    def build_extension(self, credentials=None) -> bool:
        """Build the extension.
        
        Args:
            credentials: Optional AWS credentials to inject before build
        
        Returns:
            True if successful
        """
        console.print("\n[bold cyan]🔨 Building Extension[/bold cyan]\n")
        
        # Inject credentials before building if provided
        if credentials:
            self.inject_credentials_to_source(credentials)
        
        console.print("[dim]Running: npm run build[/dim]\n")
        
        try:
            subprocess.run(
                ["npm", "run", "build"],
                cwd=self.repo_dir,
                check=True
            )
            console.print("\n[green]✓[/green] Extension built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            console.print(f"\n[red]✗[/red] Failed to build extension: {e}")
            return False
    
    def inject_credentials_to_source(self, credentials):
        """Inject AWS credentials into source code before building.
        
        Args:
            credentials: AWS credentials dict
        """
        console.print("[cyan]Injecting AWS credentials, default rule, and updating model...[/cyan]")
        
        # Update sdk.js to use Claude 3 instead of Claude v2.1
        sdk_js_path = self.repo_dir / "sdk.js"
        if sdk_js_path.exists():
            with open(sdk_js_path, 'r') as f:
                sdk_js = f.read()
            
            # Replace Claude v2.1 with Claude 3 Haiku (faster and cheaper)
            sdk_js = sdk_js.replace(
                'modelId: "anthropic.claude-v2:1"',
                'modelId: "anthropic.claude-3-haiku-20240307-v1:0"'
            )
            
            # Update the prompt format for Claude 3 (uses messages API)
            # Replace the old prompt format with Claude 3 format
            old_body = """body: JSON.stringify({
      prompt,
      max_tokens_to_sample: 8000,
    })"""
            
            new_body = """body: JSON.stringify({
      anthropic_version: "bedrock-2023-05-31",
      max_tokens: 4096,
      messages: [{
        role: "user",
        content: prompt.replace(/\\n\\nHuman: |\\n\\nAssistant:/g, '')
      }]
    })"""
            
            sdk_js = sdk_js.replace(old_body, new_body)
            
            # Update response parsing for Claude 3
            old_parse = """const jsonResult = JSON.parse(result);
        callback && callback(jsonResult);"""
            
            new_parse = """const jsonResult = JSON.parse(result);
        // Claude 3 returns content in messages format
        if (jsonResult.content && jsonResult.content[0]) {
          callback && callback({ completion: jsonResult.content[0].text });
        } else {
          callback && callback(jsonResult);
        }"""
            
            sdk_js = sdk_js.replace(old_parse, new_parse)
            
            with open(sdk_js_path, 'w') as f:
                f.write(sdk_js)
            
            console.print("[green]✓[/green] Updated to Claude 3 Haiku model")
        
        popup_js_path = self.repo_dir / "popup.js"
        if not popup_js_path.exists():
            console.print("[yellow]⚠ popup.js not found, skipping credential injection[/yellow]")
            return
        
        with open(popup_js_path, 'r') as f:
            popup_js = f.read()
        
        # Strategy: Replace the line where regexp is set to include a better default value
        # Use a more comprehensive regex that captures more content
        # Original: regexp = currentSetting?.regexp || '';
        # New: Use a regex that captures paragraphs, headings, and list items
        
        default_regex = '<p>(.*?)</p>|<h[1-6]>(.*?)</h[1-6]>|<li>(.*?)</li>|<article>(.*?)</article>'
        
        popup_js = popup_js.replace(
            "regexp = currentSetting?.regexp || '';",
            f"regexp = currentSetting?.regexp || '{default_regex}';"
        )
        
        # Also set default rule in localStorage for current host
        popup_js = popup_js.replace(
            "if (currentHost) {",
            f"""if (currentHost) {{
    // Auto-inject default rule if not exists
    if (!localStorage.getItem(currentHost)) {{
      localStorage.setItem(currentHost, JSON.stringify({{ regexp: '{default_regex}' }}));
      console.log('Default rule set for: ' + currentHost);
    }}"""
        )
        
        # Inject AWS credentials at the beginning
        credentials_init = f"""
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
        
        # Insert at the beginning of the file (after imports)
        import_end = popup_js.find("let i = 0;")
        if import_end > 0:
            popup_js = popup_js[:import_end] + credentials_init + popup_js[import_end:]
        else:
            popup_js = credentials_init + popup_js
        
        with open(popup_js_path, 'w') as f:
            f.write(popup_js)
        
        console.print("[green]✓[/green] Credentials and default rule injected into popup.js source")
        console.print("[dim]Default rule: <p>|<h1-6>|<li>|<article> - captures more content[/dim]")
        console.print("[dim]Model: Claude 3 Haiku (faster and more reliable)[/dim]")
    
    def find_build_output(self) -> Path:
        """Find the build output directory.
        
        Returns:
            Path to build output
        """
        # Common build output directories
        possible_dirs = [
            self.repo_dir / "dist",
            self.repo_dir / "build",
            self.repo_dir / "out",
            self.repo_dir
        ]
        
        for dir_path in possible_dirs:
            if dir_path.exists() and (dir_path / "manifest.json").exists():
                return dir_path
        
        # If not found, return dist as default
        return self.repo_dir / "dist"
    
    def package_extension(self, output_name: str = "bedrock-summary-extension.zip") -> Path:
        """Package the extension into a zip file.
        
        Args:
            output_name: Output zip file name
            
        Returns:
            Path to created zip file
        """
        console.print("\n[bold cyan]📦 Packaging Extension[/bold cyan]\n")
        
        build_dir = self.find_build_output()
        console.print(f"[cyan]Build directory: {build_dir}[/cyan]")
        
        if not build_dir.exists():
            console.print(f"[red]✗[/red] Build directory not found: {build_dir}")
            console.print("[yellow]Trying to use repository root...[/yellow]")
            build_dir = self.repo_dir
        
        # Check for manifest.json
        manifest_path = build_dir / "manifest.json"
        if not manifest_path.exists():
            console.print(f"[red]✗[/red] manifest.json not found in {build_dir}")
            return None
        
        console.print(f"[green]✓[/green] Found manifest.json")
        
        # Create zip file
        output_path = self.work_dir / output_name
        console.print(f"[cyan]Creating zip: {output_path}[/cyan]\n")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_dir):
                # Skip node_modules and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
                
                for file in files:
                    # Skip hidden files and source maps
                    if file.startswith('.') or file.endswith('.map'):
                        continue
                    
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(build_dir)
                    zipf.write(file_path, arcname)
                    console.print(f"[dim]  Added: {arcname}[/dim]")
        
        file_size = output_path.stat().st_size / 1024 / 1024  # MB
        console.print(f"\n[green]✓[/green] Extension packaged: {output_path}")
        console.print(f"[dim]Size: {file_size:.2f} MB[/dim]")
        
        if file_size > 10:
            console.print("[yellow]⚠ Warning: Extension size exceeds 10 MB limit[/yellow]")
        
        return output_path
    
    def setup(self, credentials=None) -> Path:
        """Complete setup workflow.
        
        Args:
            credentials: Optional AWS credentials to inject
        
        Returns:
            Path to packaged extension zip, or None if failed
        """
        console.print("\n[bold cyan]🚀 Amazon Bedrock Summary Extension Setup[/bold cyan]")
        
        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            return None
        
        # Step 2: Clone repository
        if not self.clone_repository():
            return None
        
        # Step 3: Install dependencies
        if not self.install_dependencies():
            return None
        
        # Step 4: Build extension (with credentials if provided)
        if not self.build_extension(credentials):
            return None
        
        # Step 5: Package extension
        zip_path = self.package_extension()
        if not zip_path:
            return None
        
        console.print("\n[bold green]✅ Setup Complete![/bold green]\n")
        console.print("[cyan]Next steps:[/cyan]")
        console.print(f"  python main.py --extension-zip {zip_path}")
        
        return zip_path


def main():
    """Main entry point."""
    import boto3
    
    # Get temporary credentials
    console.print("\n[cyan]Getting temporary AWS credentials...[/cyan]")
    try:
        sts_client = boto3.client('sts')
        response = sts_client.get_session_token(DurationSeconds=3600)
        credentials = response['Credentials']
        console.print(f"[green]✓[/green] Temporary credentials obtained (valid for 1 hour)")
        console.print(f"[dim]Expires at: {credentials['Expiration']}[/dim]\n")
        
        creds = {
            'AccessKeyId': credentials['AccessKeyId'],
            'SecretAccessKey': credentials['SecretAccessKey'],
            'SessionToken': credentials['SessionToken']
        }
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Failed to get credentials: {e}")
        console.print("[dim]Building without credentials...[/dim]\n")
        creds = None
    
    setup = BedrockSummaryExtensionSetup()
    
    try:
        zip_path = setup.setup(credentials=creds)
        
        if zip_path:
            console.print(f"\n[bold green]Success![/bold green]")
            console.print(f"Extension ready at: {zip_path}")
            if creds:
                console.print("\n[cyan]AWS credentials have been injected into the extension[/cyan]")
                console.print("[dim]No manual configuration needed in browser![/dim]")
            sys.exit(0)
        else:
            console.print(f"\n[bold red]Setup failed[/bold red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
