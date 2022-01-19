#!/usr/bin/env python3
# Given a KB, retrieve the KB of the most recent patch this is replacing
import re
import sys
import argparse
import requests
from bs4 import BeautifulSoup


# Establish constants
WINDOWS_KB_FORMAT = re.compile(".*KB(?P<win_kb_number>\d{7}).*")
WINDOWS_KB_URL = "https://www.catalog.update.microsoft.com/Search.aspx?q="
WINDOWS_KB_DETAILS_URL = "https://www.catalog.update.microsoft.com/ScopedViewInline.aspx?updateid="


def set_up_args():
    """Parse command line input.

    :return: Input arguments
    :rtype: Namespace
    """
    parser = argparse.ArgumentParser(description="Find the KB that is replaced by the input KB.")
    parser.add_argument("knowledge_base_id", metavar="KB", type=kb_arg, 
                        help="A string representing a Microsoft Update Catalog KB id." )
    return parser.parse_args()


def kb_arg(kb_value):
    """Check the input against the WINDOWS_KB_FORMAT. 

    Raise an error if the input is an invalid format; otherwise, return the original value.

    :param kb_value: Microsoft Update Catalog KB id
    :type kb_value: string
    """
    # Regex check
    if not re.match(WINDOWS_KB_FORMAT, kb_value):
        raise argparse.ArgumentTypeError("Must be in format KB#######")

    return kb_value


def read_webpage(url):
    """Retrieve page data from a given URL.

    :param url: URL from which to retrieve data
    :type url: string
    :return: Page content at the URL
    :rtype: string
    """
    page_content = requests.get(url)

    if page_content.status_code != 200:
        print(f"HTTP Error: {page_content.status_code}\n\nURL: {url}")
        sys.exit(1)

    return page_content


def get_redirect_id(beautiful_soup):
    """Given page data for a Microsoft patch KB, find the redirect id for the details page
    for the first product listed in the table.

    :param beautiful_soup: Microsoft Update Catalog KB page data
    :type beautiful_soup: BeautifulSoup
    :return: KB details redirect ID
    :rtype: string
    """

    a_tags = beautiful_soup.find_all("a")
    for tag in a_tags:
        if "onclick" in tag.attrs.keys():
            if "goToDetails" in tag['onclick']:
                find_redirect = re.search("^goToDetails\(\"(?P<redirect_id>.*?)\"\);$", tag['onclick'])
                return find_redirect.group("redirect_id")


def get_most_recent_kb(beautiful_soup):
    """From the details page for the original KB, retrive the list of patches under the Package Details tab and
    return the last one in the list, which is the one that the current KB replaces.

    :param beautiful_soup: Beautiful Soup object containing webpage data
    :type beautiful_soup: BeautifulSoup
    :return: last KB that appears in the Package Details tab
    :rtype: string
    """
    # List to keep track of KB numbers
    kb_list = []
    div_tags = beautiful_soup.find_all("div")
    for tag in div_tags:
        if 'style' in tag.attrs.keys():
            if tag['style'] == "padding-bottom: 0.3em;" and "Cumulative Update" in tag.text:
                text = tag.text.strip()
                kb_number = re.match(WINDOWS_KB_FORMAT, text)
                if kb_number not in kb_list:
                    kb_list.append(kb_number.group("win_kb_number"))
    return f"KB{kb_list[-1]}"


def main():

    args = set_up_args()

    # Get KB page data and beautify
    kb_page_data = read_webpage(f"{WINDOWS_KB_URL}{args.knowledge_base_id}")
    kb_soup = BeautifulSoup(kb_page_data.text, "html.parser")

    # Retrieve redirect id from KB page data
    redirect_id = get_redirect_id(kb_soup)

    # Get KB Detail page data and beautify
    kb_detail_page_data = read_webpage(f"{WINDOWS_KB_DETAILS_URL}{redirect_id}")
    kb_detail_soup = BeautifulSoup(kb_detail_page_data.text, "html.parser")

    # Get last element in package details
    kb_this_replaces = get_most_recent_kb(kb_detail_soup)

    print(f"Current: {args.knowledge_base_id}\nReplaces: {kb_this_replaces}")


if __name__ == "__main__":
    main()
