#!/usr/bin/python3
import requests
from lxml import etree
import json
import sys
def get_package_info_from_upstream(distro, package_name):
    if distro == 'debian':
        distro_url = "https://packages.debian.org/search?keywords=" + package_name + "&searchon=names&suite=all&section=all"
    elif distro == 'ubuntu':
        distro_url = "https://packages.ubuntu.com/search?keywords=" + package_name + "&searchon=names&suite=all&section=all"
    else:
        print("invalid distro %s, quit" % distro)
        sys.exit(1)
    # Step 1: Fetch HTML content from the URL
    response = requests.get(distro_url)
    html_content = response.content  # Use .content for lxml to handle byte data
    # Step 2: Parse HTML with lxml
    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser)
    # Step 3: Extract data
    for h3 in tree.xpath('//h3'):
        section_title = h3.text
        ul = h3.xpath('./following-sibling::ul[1]')
        debian_all_package_info = {}
        if ul:
            list_items = ul[0].xpath('.//li')
            for li in list_items:
                debian_package_info = {}
                item_text = li.xpath('.//text()[not(parent::a)]')
                item_class = li.get("class")
                package_file_release = item_class
                package_file_version = item_text[1].split(":")[0]
                if "arm64" in item_text[1].split(":")[1]:
                    package_file_arm64_full_name = package_name + "_" + package_file_version + "_arm64.deb"
                    debian_package_info["arm64"] = package_file_arm64_full_name
                if "armhf" in item_text[1].split(":")[1]:
                    package_file_armhf_full_name = package_name + "_" + package_file_version + "_armhf.deb"
                    debian_package_info["armhf"] = package_file_armhf_full_name
                if "amd64" in item_text[1].split(":")[1]:
                    package_file_amd64_full_name = package_name + "_" + package_file_version + "_amd64.deb"
                    debian_package_info["amd64"] = package_file_amd64_full_name
                if "riscv64" in item_text[1].split(":")[1]:
                    package_file_riscv64_full_name = package_name + "_" + package_file_version + "_riscv64.deb"
                    debian_package_info["riscv64"] = package_file_riscv64_full_name
                debian_all_package_info[item_class] = debian_package_info
        return debian_all_package_info
if len(sys.argv) < 2:
    print("Usage: python parse.py <package_name>")
    sys.exit(1)
package_name = sys.argv[1]
debian_info = get_package_info_from_upstream("debian", package_name)
ubuntu_info = get_package_info_from_upstream("ubuntu", package_name)
if debian_info and ubuntu_info:
    all_info_result = {**debian_info, **ubuntu_info}
    json_file_name = package_name + ".json"
    with open(json_file_name, "w") as outfile:
        json.dump(all_info_result, outfile)
else:
    print("failed to get package info")
    sys.exit(1)
