#!/usr/bin/python3

#NOTE: most of this code written with qwen3-coder:30b

import os
import requests
from pathlib import Path
import json
import re
import gzip
from urllib.parse import urljoin

def get_debian_release_names(cache_dir="./debian_cache"):
    """
    Get Debian release names from the README file
    """
    # Create cache directory if it doesn't exist
    Path(cache_dir).mkdir(exist_ok=True)

    # Build URL
    readme_url = "http://deb.debian.org/debian/dists/README"
    readme_path = os.path.join(cache_dir, "README")

    # Check if we already have the README file
    if os.path.exists(readme_path):
        print(f"Using cached README: {readme_path}")
        with open(readme_path, 'r') as f:
            readme_content = f.read()
    else:
        print("Downloading README...")
        response = requests.get(readme_url, timeout=30)
        response.raise_for_status()
        readme_content = response.text

        # Save to cache
        with open(readme_path, 'w') as f:
            f.write(readme_content)

    # Extract release names using regex
    # Pattern: \S+, or (\S+)\s+ - matches "oldstable, or bookworm" and captures "bookworm"
    release_pattern = r'\S+, or (\S+)\s+'

    releases = []
    for line in readme_content.split('\n'):
        if line.strip():
            match = re.search(release_pattern, line)
            if match:
                release_name = match.group(1)
                releases.append(f"debian/{release_name}")
                print(f"Found release: {release_name}")

    return releases

def get_debian_architectures(distro, release_name, cache_dir="./debian_cache"):
    """
    Get supported architectures for a Debian release from InRelease file
    """
    # Create cache directory if it doesn't exist
    Path(cache_dir).mkdir(exist_ok=True)

    # Build URLs
    match distro:
        case 'debian':
            base_url = "http://deb.debian.org/debian"
        case 'ubuntu':
            base_url = "http://archive.ubuntu.com/ubuntu"
    inrelease_url = f"{base_url}/dists/{release_name}/InRelease"
    inrelease_path = os.path.join(cache_dir, f"{release_name}_InRelease")

    # Check if we already have the file
    if os.path.exists(inrelease_path):
        #print(f"Using cached file: {inrelease_path}")
        with open(inrelease_path, 'r') as f:
            inrelease_content = f.read()
    else:
        #print(f"Downloading InRelease for {release_name}...")
        response = requests.get(inrelease_url, timeout=30)
        response.raise_for_status()
        inrelease_content = response.text

        # Save to cache
        with open(inrelease_path, 'w') as f:
            f.write(inrelease_content)

    # Extract architectures from the InRelease file
    # Look for the "Architectures:" line
    architectures = []

    # Split by lines and look for architectures
    for line in inrelease_content.split('\n'):
        if line.lower().startswith('architectures:'):
            # Extract architectures after the colon
            arch_line = line.split(':', 1)[1].strip()
            architectures = [arch.strip() for arch in arch_line.split() if arch.strip()]
            break

    if architectures:
        print(f"Supported architectures for {release_name}: {architectures}")
        if('all' in architectures):
            architectures.remove('all')
        return architectures
    else:
        print("Could not find Architectures field in InRelease file")
        return []

def get_debian_srcpkg_architecture(distro, release_name, package_name, cache_dir="./debian_cache"):
    """
    Get the synthesized package filename for a given package in a Debian release
    """
    # Create cache directory if it doesn't exist
    Path(cache_dir).mkdir(exist_ok=True)

    # Build URLs
    match distro:
        case 'debian':
            base_url = "http://deb.debian.org/debian"
        case 'ubuntu':
            #base_url = "http://archive.ubuntu.com/ubuntu"
            base_url = "http://ports.ubuntu.com/"

    sources_url = f"{base_url}/dists/{release_name}/main/source/Sources.gz"
    sources_path = os.path.join(cache_dir, f"{release_name}_Sources.gz")

    # Check if we already have the Sources.gz file
    if os.path.exists(sources_path):
        print(f"Using cached Sources.gz: {sources_path}")
    else:
        print(f"Downloading Sources.gz for {release_name}...")
        response = requests.get(sources_url, timeout=30)
        response.raise_for_status()

        # Save to cache
        with open(sources_path, 'wb') as f:
            f.write(response.content)

        # Decompress and read
    with gzip.open(sources_path, 'rt') as f:
        sources_content = f.read()

    # Parse the Sources file to find the package
    package_info = parse_sources_for_package(sources_content, package_name)

    if package_info:
        return package_info['architecture']
    else:
        raise FileNotFoundError(f"Package '{package_name}' not found in {distro}/{release_name} Sources.gz")

def parse_sources_for_package(sources_content, package_name):
    """
    Parse Sources.gz content to find package information
    """
    # Split into individual package entries
    packages = sources_content.split('\n\n')

    for package_entry in packages:
        if not package_entry.strip():
            continue

        package_info = {}
        for line in package_entry.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                package_info[key.strip().lower()] = value.strip()

        # Check if this is our package
        if package_info.get('package', '').lower() == package_name.lower():
            return package_info

    return None

def get_debian_binary_package_filename(distro, release_name, package_name, architecture='arm64', cache_dir="./debian_cache"):
    """
    Get the binary package filename for a given package in a Debian release
    This is more complex because we need to parse Packages files
    """
    # Create cache directory if it doesn't exist
    Path(cache_dir).mkdir(exist_ok=True)

    # Build URLs for Packages file
    match distro:
        case 'debian':
            if( architecture == 'loong64' ):
                base_url = "http://ftp.ports.debian.org/debian-ports/"
            else:
                base_url = "http://ftp.debian.org/debian/"
        case 'ubuntu':
            if(re.match("(i386|amd64)", architecture)): #regex as there is amd64 and amd64v3
                base_url = "http://archive.ubuntu.com/ubuntu"
            else:
                base_url = "http://ports.ubuntu.com/"
    packages_url = f"{base_url}/dists/{release_name}/main/binary-{architecture}/Packages.gz"
    packages_path = os.path.join(cache_dir, f"{release_name}_{architecture}_Packages.gz")

    # Check if we already have the Packages.gz file
    if os.path.exists(packages_path):
        print(f"Using cached Packages.gz: {packages_path}")
    else:
        print(f"Downloading Packages.gz for {release_name} ({architecture})...")
        response = requests.get(packages_url, timeout=30)
        response.raise_for_status()

        # Save to cache
        with open(packages_path, 'wb') as f:
            f.write(response.content)

        # Decompress and read
    with gzip.open(packages_path, 'rt') as f:
        packages_content = f.read()

    # Parse the Packages file to find the package
    package_info = parse_packages_for_package(packages_content, package_name)

    if package_info:
        # Synthesize the package filename
        filename = synthesize_binary_package_filename(package_info)
        #print(f"Synthesized binary package filename: {filename}")
        return filename
    else:
        print(f"Binary package '{package_name}' not found for {architecture}/Packages.gz")
        return None

def parse_packages_for_package(packages_content, package_name):
    """
    Parse Packages.gz content to find package information
    """
    # Split into individual package entries
    packages = packages_content.split('\n\n')

    for package_entry in packages:
        if not package_entry.strip():
            continue

        package_info = {}
        for line in package_entry.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                package_info[key.strip().lower()] = value.strip()

        # Check if this is our package
        if package_info.get('package', '').lower() == package_name.lower():
            return package_info

    return None

def synthesize_binary_package_filename(package_info):
    """
    Synthesize the Debian binary package filename from package info
    """
    # Extract needed fields
    package = package_info.get('package', 'unknown')
    version = package_info.get('version', '0.0.0')
    architecture = package_info.get('architecture', 'all')

    # For binary packages, the filename format is:
    # package_version_architecture.deb
    filename = f"{package}_{version}_{architecture}.deb"

    return filename

# Example usage:
if __name__ == "__main__":
    releases = get_debian_release_names()
    if('debian/rc-buggy' in releases):
        releases.remove('debian/rc-buggy')
    # FIXME: these are fetchable from changelogs.ubuntu.com/meta-release
    # filter by 'Supported: 1'.
    # Don't do this yet b/c jammy goes EOS Apr 2027, we don't know if we'll be ready.
    # also resolute isn't in changelog as of 2025Dec03
    releases += [ 'ubuntu/jammy', 'ubuntu/noble', 'ubuntu/plucky', 'ubuntu/questing', 'ubuntu/resolute' ]
    release_hash = {}
    for release in releases:
        distro, release = release.split('/')
        packages = {}

        pkg_architecture = get_debian_srcpkg_architecture(distro, release, "base-files")

        # Get architectures from InRelease
        print("\n=== Architecture List ===")
        arch_list = pkg_architecture.split()
        if( 'any' in arch_list ):
            architectures = get_debian_architectures(distro, release)
        else:
            architectures = arch_list
        if( release == 'sid' ):
            # loong64 is hidden away in /debian-ports/
            architectures += ['loong64']

        # Get binary package filename
        #print("\n=== Binary Package ===")
        # NOTE: we *cheat* here because base-files is always built for all architectures.
        # this is NOT a generic method usable for all cases. for that you have to check Sources above
        for architecture in architectures:
            binary_filename = get_debian_binary_package_filename(distro, release, "base-files", architecture)
            packages[architecture] = binary_filename
        release_hash[release] = packages

    json_content = json.dumps(release_hash)
    print(json_content)
    json_file_name = "base-files.json"
    with open(json_file_name, "w") as outfile:
        outfile.write(json_content)
