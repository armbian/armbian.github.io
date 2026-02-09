#!/usr/bin/env python3
"""
Generate Raspberry Pi Imager JSON from Armbian all-images.json

This script fetches the Armbian images JSON from github.armbian.com,
filters for Raspberry Pi images, and generates a JSON file compatible
with the Raspberry Pi Imager format.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Optional

import requests


class RpiImagerGenerator:
    """Generate Raspberry Pi Imager JSON from Armbian images JSON"""

    # Source URL for all Armbian images
    ALL_IMAGES_URL = "https://github.armbian.com/armbian-images.json"

    # Ubuntu releases
    UBUNTU_RELEASES = {"jammy", "noble", "plucky"}

    # Raspberry Pi boards to filter (board_slug values)
    RPI_BOARDS = {
        "rpi4b"
    }

    # Map Armbian board names to RPi imager device names
    RPI_DEVICES = ["pi5-64bit", "pi4-64bit", "pi3-64bit"]

    # Exclude patterns
    EXCLUDE_PATTERNS = [
        "homeassistant", "openhab", "kali", "omv", "trunk"
    ]

    # Only include these file extensions
    IMAGE_EXTENSIONS = {".img.xz", ".img"}

    # Variant display name mapping
    VARIANT_DISPLAY_NAMES = {
        "gnome": "Gnome Desktop",
        "minimal": "Minimal",
        "xfce": "Xfce Desktop",
        "kde-neon": "KDE Neon Desktop",
        "cinnamon": "Cinnamon Desktop",
        "mate": "Mate Desktop",
        "i3-wm": "I3 Window Manager",
        "server": "Server",
    }

    def __init__(
        self,
        all_images_url: str = ALL_IMAGES_URL,
        output_file: str = "rpi-imager.json",
        dry_run: bool = False,
        use_cached_json: Optional[str] = None,
        verbose: bool = False
    ):
        self.all_images_url = all_images_url
        self.output_file = output_file
        self.dry_run = dry_run
        self.use_cached_json = use_cached_json
        self.verbose = verbose
        self.entries = []

    def log(self, message: str):
        """Print message if verbose mode is enabled"""
        if self.verbose:
            print(message)

    def fetch_images_json(self) -> dict:
        """Fetch the all-images.json from Armbian"""
        if self.use_cached_json:
            print(f"Using cached JSON from: {self.use_cached_json}")
            with open(self.use_cached_json, 'r') as f:
                return json.load(f)

        print(f"Fetching images from: {self.all_images_url}")
        response = requests.get(self.all_images_url, timeout=60)
        response.raise_for_status()
        return response.json()

    def is_rpi_board(self, board_slug: str) -> bool:
        """Check if board is a Raspberry Pi variant"""
        board_lower = board_slug.lower()
        return any(rpi in board_lower for rpi in self.RPI_BOARDS)

    def should_exclude_image(self, asset: dict) -> bool:
        """Check if image should be excluded based on patterns"""
        name = asset.get("preinstalled_application", "").lower()
        return any(pattern in name for pattern in self.EXCLUDE_PATTERNS)

    def get_variant_display_name(self, variant: str) -> str:
        """Get display name for an image variant"""
        return self.VARIANT_DISPLAY_NAMES.get(variant.lower(), variant.capitalize())

    def get_release_type(self, distro_release: str) -> str:
        """Determine if release is Ubuntu or Debian"""
        return "Ubuntu" if distro_release in self.UBUNTU_RELEASES else "Debian"

    def parse_file_size(self, size_str: str) -> int:
        """Parse file size string to integer bytes"""
        try:
            return int(size_str) if size_str else 0
        except ValueError:
            return 0

    def extract_image_info(self, asset: dict) -> Optional[dict]:
        """Extract relevant information from an asset entry"""
        try:
            board_slug = asset.get("board_slug", "")
            file_url = asset.get("file_url", "")

            if not file_url:
                self.log(f"Skipping: no file_url for {board_slug}")
                return None

            # Check if this is an RPi image
            if not self.is_rpi_board(board_slug):
                self.log(f"Skipping: {board_slug} is not an RPi board")
                return None

            # Check exclusions
            if self.should_exclude_image(asset):
                self.log(f"Skipping: {board_slug} matches exclusion pattern")
                return None

            # Parse filename
            filename = file_url.split('/')[-1]

            # Check file extension - only include image files
            if not any(filename.endswith(ext) for ext in self.IMAGE_EXTENSIONS):
                self.log(f"Skipping: {filename} - not an image file")
                return None

            # Check if filename contains excluded patterns
            filename_lower = filename.lower()
            if any(pattern in filename_lower for pattern in self.EXCLUDE_PATTERNS):
                self.log(f"Skipping: {filename} - matches exclusion pattern in filename")
                return None

            self.log(f"Processing: {filename}")

            # Extract metadata from asset
            armbian_version = asset.get("armbian_version", "unknown")
            distro_release = asset.get("distro", "unknown")
            kernel_branch = asset.get("branch", "current")
            image_variant = asset.get("variant", "server")
            file_size = self.parse_file_size(asset.get("file_size", "0"))
            file_updated = asset.get("file_date", "")

            # Map kernel branch to expected format
            # current -> current, legacy -> legacy
            kernel_branch_name = kernel_branch

            # Get release type
            release_type = self.get_release_type(distro_release)

            # Format date to YYYY-MM-DD
            created_date = ""
            if file_updated:
                try:
                    dt = datetime.fromisoformat(file_updated.replace('Z', '+00:00'))
                    created_date = dt.strftime('%Y-%m-%d')
                except:
                    created_date = file_updated[:10]

            return {
                'filename': filename,
                'file_url': file_url,
                'board_slug': board_slug,
                'armbian_version': armbian_version,
                'distro_release': distro_release,
                'release_type': release_type,
                'kernel_branch': kernel_branch_name,
                'image_variant': image_variant,
                'created_date': created_date,
                'file_size': file_size,
            }

        except Exception as e:
            print(f"Error extracting image info: {e}", file=sys.stderr)
            return None

    def fetch_sha256_from_url(self, sha_url: str) -> Optional[str]:
        """Fetch SHA256 hash from .sha file"""
        try:
            response = requests.get(sha_url, timeout=30)
            response.raise_for_status()
            # .sha file format: "hash filename"
            sha256 = response.text.split()[0].strip()
            return sha256
        except Exception as e:
            self.log(f"Warning: Could not fetch SHA256 from {sha_url}: {e}")
            return None

    def decompress_and_compute(self, xz_file_path: str) -> tuple[int, str]:
        """Decompress .xz file and compute SHA256 and size of extracted image"""
        sha256_hash = hashlib.sha256()

        # Use xz command to decompress
        result = subprocess.run(
            ['xz', '-d', '-k', xz_file_path],
            capture_output=True,
            timeout=300
        )
        if result.returncode != 0:
            raise Exception(f"Failed to decompress: {result.stderr.decode()}")

        # Get the decompressed filename (same as input but without .xz)
        decompressed_path = xz_file_path[:-3] if xz_file_path.endswith('.xz') else xz_file_path

        try:
            # Get file size
            extracted_size = os.path.getsize(decompressed_path)

            # Compute SHA256
            with open(decompressed_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)

            return extracted_size, sha256_hash.hexdigest()
        finally:
            # Clean up decompressed file
            if os.path.exists(decompressed_path):
                os.remove(decompressed_path)

    def process_image(self, asset: dict) -> Optional[dict]:
        """Process a single image asset"""
        info = self.extract_image_info(asset)
        if not info:
            return None

        if self.dry_run:
            print(f"[DRY RUN] Would process: {info['filename']}")
            return self._create_entry(
                info,
                extract_size=0,
                extract_sha256="",
                download_sha256=""
            )

        # Get the .sha URL from the asset
        sha_url = asset.get("file_url_sha", "")
        download_sha256 = ""
        if sha_url:
            download_sha256 = self.fetch_sha256_from_url(sha_url) or ""

        # For extract_size and extract_sha256, we need to download and decompress
        extract_size = 0
        extract_sha256 = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = info['filename']
            filepath = os.path.join(tmpdir, filename)

            # Download the image
            print(f"Downloading: {info['file_url']}")
            try:
                response = requests.get(info['file_url'], stream=True, timeout=600)
                response.raise_for_status()

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Decompress and compute if it's .xz
                if filename.endswith('.xz'):
                    extract_size, extract_sha256 = self.decompress_and_compute(filepath)
                else:
                    # For uncompressed images, compute size and hash directly
                    extract_size = os.path.getsize(filepath)
                    sha256_hash = hashlib.sha256()
                    with open(filepath, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            sha256_hash.update(chunk)
                    extract_sha256 = sha256_hash.hexdigest()

                print(f"  Extracted size: {extract_size} bytes")
                print(f"  Extracted SHA256: {extract_sha256}")

            except Exception as e:
                print(f"Error processing {filename}: {e}", file=sys.stderr)
                return None

        return self._create_entry(
            info,
            extract_size=extract_size,
            extract_sha256=extract_sha256,
            download_sha256=download_sha256
        )

    def _create_entry(self, info: dict, extract_size: int, extract_sha256: str, download_sha256: str) -> dict:
        """Create a JSON entry for the Raspberry Pi Imager"""
        # Build name: Armbian <Release> <Variant> <Version>
        release_title = info['distro_release'].capitalize()
        variant_display = self.get_variant_display_name(info['image_variant'])
        version = info['armbian_version']

        # image_download_size is the compressed file size
        image_download_size = info.get('file_size', extract_size)

        return {
            "name": f"Armbian {release_title} {variant_display} {version}",
            "description": f"Ultralight custom {info['release_type']} OS for single board computers",
            "url": info['file_url'],
            "icon": "https://www.armbian.com/armbian-logo-40x40.png",
            "website": "https://www.armbian.com",
            "release_date": info['created_date'],
            "extract_size": extract_size,
            "extract_sha256": extract_sha256,
            "image_download_size": image_download_size,  # Compressed size
            "image_download_sha256": download_sha256,
            "devices": self.RPI_DEVICES,
            "init_format": "systemd"
        }

    def generate(self) -> list[dict]:
        """Generate the full JSON list"""
        images_data = self.fetch_images_json()

        # Get assets list
        assets = []
        if isinstance(images_data, dict):
            assets = images_data.get("assets", [])
        elif isinstance(images_data, list):
            assets = images_data

        print(f"Found {len(assets)} total images")

        for asset in assets:
            entry = self.process_image(asset)
            if entry:
                self.entries.append(entry)

        print(f"Generated {len(self.entries)} RPi imager entries")
        return self.entries

    def save(self):
        """Save the generated JSON to file"""
        output = {"os_list": self.entries}

        with open(self.output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Saved {len(self.entries)} entries to {self.output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Raspberry Pi Imager JSON from Armbian images"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't download images, just show what would be processed"
    )
    parser.add_argument(
        "--cached-json",
        type=str,
        help="Use cached all-images.json file instead of fetching from URL"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="rpi-imager.json",
        help="Output JSON file path (default: rpi-imager.json)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://github.armbian.com/armbian-images.json",
        help="URL to fetch armbian-images.json from"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    generator = RpiImagerGenerator(
        all_images_url=args.url,
        output_file=args.output,
        dry_run=args.dry_run,
        use_cached_json=args.cached_json,
        verbose=args.verbose
    )

    generator.generate()
    generator.save()


if __name__ == "__main__":
    main()
