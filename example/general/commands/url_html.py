"""
Download HTML web page from the specified URL and print it on the standard
output or to the specified file.
"""

from .. import model
import os


def execute(url, output=None):
    if not url.startswith('http'):
        url = 'http://' + url
    html = model.load_html(url).prettify()
    if output:
        directory = os.path.dirname(output)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(output, 'w') as f:
            f.write(html)
    else:
        print(html)
