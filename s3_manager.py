#!/usr/bin/env python3
"""S3 bucket management for extension storage."""

import os
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from rich.console import Console

console = Console()


class S3Manager:
    """Manage S3 bucket for extension storage."""
    
    def __init__(self, bucket_name: str, region: Optional[str] = None):
        """Initialize S3 manager.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region (uses AWS_REGION env var if None)
        """
        self.bucket_name = bucket_name
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self.s3_client = boto3.client('s3', region_name=self.region)
        
    def bucket_exists(self) -> bool:
        """Check if bucket exists.
        
        Returns:
            True if bucket exists
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            elif error_code == '403':
                console.print(f"[yellow]⚠ Bucket exists but access denied: {self.bucket_name}[/yellow]")
                return True
            else:
                raise
    
    def create_bucket(self) -> bool:
        """Create S3 bucket if it doesn't exist.
        
        Returns:
            True if bucket was created or already exists
        """
        console.print(f"[cyan]Checking S3 bucket: {self.bucket_name}[/cyan]")
        
        if self.bucket_exists():
            console.print(f"[green]✓[/green] Bucket already exists: {self.bucket_name}")
            return True
        
        console.print(f"[cyan]Creating S3 bucket: {self.bucket_name}[/cyan]")
        
        try:
            # Create bucket
            if self.region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            console.print(f"[green]✓[/green] Bucket created: {self.bucket_name}")
            console.print(f"[dim]Region: {self.region}[/dim]")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyOwnedByYou':
                console.print(f"[green]✓[/green] Bucket already owned by you: {self.bucket_name}")
                return True
            elif error_code == 'BucketAlreadyExists':
                console.print(f"[red]✗[/red] Bucket name already taken: {self.bucket_name}")
                console.print("[yellow]Try a different bucket name[/yellow]")
                return False
            else:
                console.print(f"[red]✗[/red] Failed to create bucket: {e}")
                raise
    
    def upload_extension(self, extension_path: Path, key: Optional[str] = None) -> str:
        """Upload extension zip to S3.
        
        Args:
            extension_path: Path to extension zip file
            key: S3 object key (uses filename if None)
            
        Returns:
            S3 URI of uploaded extension
        """
        if key is None:
            key = f"extensions/{extension_path.name}"
        
        console.print(f"[cyan]Uploading extension to S3...[/cyan]")
        console.print(f"[dim]Bucket: {self.bucket_name}[/dim]")
        console.print(f"[dim]Key: {key}[/dim]")
        
        try:
            # Upload file
            file_size = extension_path.stat().st_size / 1024 / 1024  # MB
            console.print(f"[dim]Uploading {file_size:.2f} MB...[/dim]")
            
            self.s3_client.upload_file(
                str(extension_path),
                self.bucket_name,
                key,
                ExtraArgs={'ContentType': 'application/zip'}
            )
            
            s3_uri = f"s3://{self.bucket_name}/{key}"
            console.print(f"[green]✓[/green] Extension uploaded successfully")
            console.print(f"[dim]S3 URI: {s3_uri}[/dim]")
            
            return s3_uri
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to upload extension: {e}")
            raise
    
    def verify_access(self, s3_uri: str) -> bool:
        """Verify that we can access the uploaded extension.
        
        Args:
            s3_uri: S3 URI to verify
            
        Returns:
            True if accessible
        """
        console.print(f"[cyan]Verifying S3 access...[/cyan]")
        
        # Parse S3 URI
        if not s3_uri.startswith('s3://'):
            console.print(f"[red]✗[/red] Invalid S3 URI: {s3_uri}")
            return False
        
        parts = s3_uri[5:].split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        
        try:
            # Try to get object metadata
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            size = response['ContentLength'] / 1024 / 1024  # MB
            console.print(f"[green]✓[/green] S3 object accessible")
            console.print(f"[dim]Size: {size:.2f} MB[/dim]")
            console.print(f"[dim]Last Modified: {response['LastModified']}[/dim]")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                console.print(f"[red]✗[/red] Object not found: {s3_uri}")
            elif error_code == '403':
                console.print(f"[red]✗[/red] Access denied: {s3_uri}")
            else:
                console.print(f"[red]✗[/red] Error accessing object: {e}")
            return False
    
    def setup_and_upload(self, extension_path: Path) -> Optional[str]:
        """Complete S3 setup and upload workflow.
        
        Args:
            extension_path: Path to extension zip file
            
        Returns:
            S3 URI of uploaded extension, or None if failed
        """
        console.print("\n[bold cyan]☁️  Setting up S3 Storage[/bold cyan]\n")
        
        # Step 1: Create bucket
        if not self.create_bucket():
            return None
        
        # Step 2: Upload extension
        try:
            s3_uri = self.upload_extension(extension_path)
        except Exception:
            return None
        
        # Step 3: Verify access
        if not self.verify_access(s3_uri):
            console.print("[yellow]⚠ Upload succeeded but verification failed[/yellow]")
            console.print("[dim]This may be a temporary issue, continuing anyway...[/dim]")
        
        console.print("\n[green]✓ S3 setup complete![/green]\n")
        return s3_uri
    
    def list_extensions(self) -> list:
        """List all extensions in the bucket.
        
        Returns:
            List of extension object keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='extensions/'
            )
            
            if 'Contents' not in response:
                return []
            
            return [obj['Key'] for obj in response['Contents']]
            
        except ClientError as e:
            console.print(f"[yellow]⚠ Failed to list extensions: {e}[/yellow]")
            return []
    
    def cleanup_old_extensions(self, keep_latest: int = 5):
        """Clean up old extension versions, keeping only the latest N.
        
        Args:
            keep_latest: Number of latest versions to keep
        """
        console.print(f"[cyan]Cleaning up old extensions (keeping latest {keep_latest})...[/cyan]")
        
        extensions = self.list_extensions()
        if len(extensions) <= keep_latest:
            console.print(f"[green]✓[/green] Only {len(extensions)} extensions found, no cleanup needed")
            return
        
        # Sort by name (which includes timestamp)
        extensions.sort(reverse=True)
        to_delete = extensions[keep_latest:]
        
        console.print(f"[dim]Deleting {len(to_delete)} old extensions...[/dim]")
        
        for key in to_delete:
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                console.print(f"[dim]Deleted: {key}[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to delete {key}: {e}[/yellow]")
        
        console.print(f"[green]✓[/green] Cleanup complete")


if __name__ == "__main__":
    # Test S3 manager
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python s3_manager.py <extension.zip>")
        sys.exit(1)
    
    extension_path = Path(sys.argv[1])
    if not extension_path.exists():
        print(f"Error: File not found: {extension_path}")
        sys.exit(1)
    
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'browser-extension-demo-zihangh-20260129')
    manager = S3Manager(bucket_name)
    
    s3_uri = manager.setup_and_upload(extension_path)
    if s3_uri:
        print(f"\nSuccess! Extension uploaded to: {s3_uri}")
    else:
        print("\nFailed to upload extension")
        sys.exit(1)
