from interfaces.scrapper import Scrapper

__all__ = [
    'BeautifulSoupScrapper'
]


class BeautifulSoupScrapper(Scrapper):
    def allocate_entries(self):
        return list()

    def process_entries(self, entries):
        return list()
