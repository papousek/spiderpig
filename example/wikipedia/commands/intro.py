"""
Download and print the first paragraph from Wikipedia for the given keyword.
"""

from general.model import load_html
from html2text import HTML2Text


def execute(text, lang='en'):
    h = HTML2Text()
    h.ignore_links = True
    print(h.handle(load_html('https://en.wikipedia.org/w/index.php?search={}'.format(text.lower())).find('p').prettify()).strip())
