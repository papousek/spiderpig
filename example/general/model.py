from bs4 import BeautifulSoup
from spiderpig.msg import Verbosity, print_debug
from urllib.request import urlopen
import spiderpig as sp


@sp.cached()
def load_page_content(url, verbosity=Verbosity.INFO):
    if verbosity > Verbosity.INFO:
        print_debug('Downloading {}'.format(url))
    return urlopen(url).read()


def load_html(url):
    return BeautifulSoup(load_page_content(url), 'html.parser')
