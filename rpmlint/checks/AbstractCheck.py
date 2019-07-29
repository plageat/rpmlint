#############################################################################
# File          : AbstractCheck.py
# Package       : rpmlint
# Author        : Frederic Lepied
# Created on    : Tue Sep 28 00:22:38 1999
# Purpose       : Abstract class to hold all the derived classes.
#############################################################################

import contextlib
import re
import urllib.request

from rpmlint.version import __version__

# Note: do not add any capturing parentheses here
macro_regex = re.compile(r'%+[{(]?[a-zA-Z_]\w{2,}[)}]?')


class _HeadRequest(urllib.request.Request):
    def get_method(self):
        return 'HEAD'


class _HeadRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(*args):
        res = urllib.request.HTTPRedirectHandler.redirect_request(*args)
        if res:
            res = _HeadRequest(res.get_full_url())
        return res


class AbstractCheck(object):
    def __init__(self, config, output):
        self.config = config
        self.output = output
        # FIXME: kill network from rpmlint, everything should be offline
        self.network_enabled = config.configuration['NetworkEnabled']
        self.network_timeout = config.configuration['NetworkTimeout']
        self.output.error_details.update(abstract_details_dict)

    def check(self, pkg):
        if pkg.isSource():
            return self.check_source(pkg)
        return self.check_binary(pkg)

    def check_source(self, pkg):
        return

    def check_binary(self, pkg):
        return

    def check_spec(self, pkg):
        return

    def check_url(self, pkg, tag, url):
        """
        Check that URL points to something that seems to exist.
        Return info() of the response if available.
        """
        if not self.network_enabled:
            return

        res = None
        try:
            opener = urllib.request.build_opener(_HeadRedirectHandler())
            opener.addheaders = [('User-Agent',
                                  'rpmlint/%s' % __version__)]
            res = opener.open(_HeadRequest(url), timeout=self.network_timeout)
        except Exception as e:
            errstr = str(e) or repr(e) or type(e)
            self.output.add_info('W', pkg, 'invalid-url', '%s:' % tag, url, errstr)
        else:
            if url.startswith('http://'):
                https = 'https://' + url[len('http://'):]
                try:
                    opener.open(_HeadRequest(https), timeout=self.network_timeout)
                except Exception:
                    pass
                else:
                    self.output.add_info('W', pkg, 'non-https-url', '%s:' % tag, url)
        info = None
        if res:
            with contextlib.closing(res):
                info = res.info()
        return info


class AbstractFilesCheck(AbstractCheck):
    def __init__(self, config, output, file_regexp):
        self.__files_re = re.compile(file_regexp)
        super().__init__(config, output)

    def check_binary(self, pkg):
        ghosts = pkg.ghostFiles()
        for filename in (x for x in pkg.files() if x not in ghosts):
            if self.__files_re.match(filename):
                self.check_file(pkg, filename)

    def check_file(self, pkg, filename):
        """Virtual method called for each file that match the regexp passed
        to the constructor.
        """
        raise NotImplementedError('check must be implemented in subclass')


abstract_details_dict = {
    'invalid-url':
    """The value should be a valid, public HTTP, HTTPS, or FTP URL.""",
    'network-checks-disabled':
    """Checks requiring network access have not been enabled in configuration,
    see the NetworkEnabled option.""",
    'non-https-url':
    """The URLs uses http:// while https:// appears to work,
    always prefer HTTPS URLs.""",
}