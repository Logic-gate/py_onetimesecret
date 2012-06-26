# -*- coding: UTF-8 -*-

__author__ = 'Step'
import urllib2
import json
from urllib import urlencode
from functools import wraps

def server_check(func):
    """
    Decorator that checks, whether server is ready to process our requests or not.
    Able to wrap only instance of OneTimeSecret class (or any other, that provides .status method, which
    returns True if all is OK, else False).
    """
    @wraps(func)
    def checked_func(self, *args, **kwargs):
        if self.status():
            return func(self, *args, **kwargs)
        else:
            raise Exception("Server is not ready")
    return checked_func

def create_opener(url, username, password):
    """
    Creates opener for the OTS site with given credentials.

    @param url: url of the site (don't think that it would differ from default, but..)

    @type url:      string
    @type username: string
    @type password: string
    """
    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm='OTS',
                              uri=url,
                              user=username,
                              passwd=password)
    opener = urllib2.build_opener(auth_handler)
    return opener

class OneTimeSecret(object):
    def __init__(self, username, api_key, api_ver=None, url=None):
        """
        Creates entity to work with OTS using given credentials.

        @param username: your API username, usually your e-mail.
        @param api_key:  your API key
        @param api_ver:  version of the API to work with. Currently it's "v1"
        @param url:      url of the OTS domain. Maybe will be useful for the clients with "Agency" account

        @type username: string
        @type api_key:  string
        @type api_ver:  string
        @type url:      string
        """
        if api_ver is None:
            self.api_ver = "v1"
        if url is None:
            url = "onetimesecret.com"
        self.username = username
        self.key = api_key
        self.url = "https://%s/api/%s/%s" % (url, self.api_ver, "%s")
        self.opener = create_opener("https://%s/*" % url, username, api_key)

    @server_check
    def share(self, secret, passphrase=None, recipient=None, ttl=None):
        """
        Shares given secret and returns Python dictionary, containing server response.

        Useful fields:
         [*] res["secret_key"]      : key for your secret
         [*] res["metadata_key"]    : key for your secret's meta. With it you can see,
                                                    whether secret was revealed or not.
        Other field's meaning you can obtain from https://onetimesecret.com/docs/api/secrets


        @param secret:      secret you want to share
        @param passphrase:  password, if you wish to keep your secret totally confidential
        @param recipient:   recipient's e-mail, if you wish to send him an invitation to see your secret
        @param ttl:         TTL of your secret, in seconds. Set to one day by default

        @type secret:       string
        @type passphrase:   string
        @type recipient:    string
        @type ttl:          int

        @return res:        dict
        """
        if ttl is None:
            ttl = 3600 * 24
        data = {"secret":secret.encode("utf-8"),
                "ttl":ttl}
        if passphrase:
            data.update({"passphrase":passphrase.encode("utf-8")})
        if recipient:
            data.update({"recipient":recipient.encode("utf-8")})

        url = self.url % "share"
        raw = urllib2.urlopen(url, urlencode(data)).read()
        res = json.loads(raw)
        return res

    @server_check
    def generate(self, passphrase=None, recipient=None, ttl=None):
        """
        Generates random secret. Inputs and return are similar to share()'s, except "secret", which is not
        in use here.

        @param passphrase:  password, if you wish to keep your secret totally confidential
        @param recipient:   recipient's e-mail, if you wish to send him an invitation to see your secret
        @param ttl:         TTL of your secret, in seconds. Set to one day by default

        @type passphrase:   string
        @type recipient:    string
        @type ttl:          int

        @return res:        dict
        """
        if ttl is None:
            ttl = 3600 * 24
        data = {"ttl":ttl}
        if passphrase:
            data.update({"passphrase":passphrase.encode("utf-8")})
        if recipient:
            data.update({"recipient":recipient.encode("utf-8")})

        url = self.url % "generate"
        raw = urllib2.urlopen(url, urlencode(data)).read()
        res = json.loads(raw)
        return res

    @server_check
    def retrieve_secret(self, secret_key, passphrase=None):
        """
        Retrieves secret by given secret_key and passphrase (if necessary) and returns
        Python dictionary, containing server response. Raises exception if finds some
        problems with passphrase.

        Usefull fields:
         [*] res["value"] : secret you were looking for
        Other field's meaning you can obtain from https://onetimesecret.com/docs/api/secrets

        @param secret_key:  key of the secret you wish to get
        @param passphrase:  you can specify passphrase if necessary

        @type secret_key:   string
        @type passphrase:   string

        @return res:        dict
        """
        try:
            data = {"SECRET_KEY": secret_key}
            if passphrase:
                data.update({"passphrase":passphrase.encode("utf-8")})

            url = self.url % "secret/%s" % secret_key
            raw = urllib2.urlopen(url, urlencode(data)).read()
            res = json.loads(raw)
            return res
        except urllib2.HTTPError:
            raise Exception("Check key and passphrase")

    @server_check
    def retrieve_meta(self, meta_key):
        """
        Retrieves metadata of secret with given METADATA_KEY.
        Useful fields:
         [*] res["secret_key"]  : key of the secret associated with this meta
         [*] res["received"]    : time (in POSIX format, UTC), the secret
                                  associated with this meta was received. 0 if secret wasn't open.

        @param meta_key : metadata_key of the secret, you want to lookup

        @type meta_key  : string
        """
        data = {"METADATA_KEY":meta_key}

        url = self.url % "private/%s" % meta_key
        raw = urllib2.urlopen(url, urlencode(data)).read()
        res = json.loads(raw)
        if not res.has_key(u"received"):
            res.update({u"received":0})
        return res

    def status(self):
        """
        Checks server's ability to process our request. Also, sets necessary credentials for urllib2.
        Returns True if all is OK, else False.

        @return: bool
        """
        urllib2.install_opener(self.opener)
        url = self.url % "status"
        raw = urllib2.urlopen(url).read()
        return json.loads(raw)[u"status"] == u"nominal"