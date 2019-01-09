from pip._vendor import requests


class CompilationError(Exception):
    pass


class WheelsproxyClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def compile(self, requirements_in):
        r = self.session.post(
            self.base_url + "+compile/", data=requirements_in
        )
        if r.status_code == requests.codes.bad_request:
            raise CompilationError(r.content)
        r.raise_for_status()
        return r.content

    def resolve(self, compiled_reqs):
        r = self.session.post(self.base_url + "+resolve/", data=compiled_reqs)
        r.raise_for_status()
        return r.content
