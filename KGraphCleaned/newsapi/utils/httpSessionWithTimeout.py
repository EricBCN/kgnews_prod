import requests

TIMEOUT = 5
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/50.0.2661.102 Safari/537.36'
}


class HttpSessionWithTimeout(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', TIMEOUT)
        return super(HttpSessionWithTimeout, self).request(*args, **kwargs)
