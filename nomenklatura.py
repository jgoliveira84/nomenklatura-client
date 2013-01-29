import requests
import json


class NKObject(object):
 
 def __init__(self,data):
  for k,v in data.items():
    setattr(self,k,v)

def apply_attrs(obj, data):
    for k, v in data.items():
        setattr(obj, k, v)


class NKException(Exception):

    def __init__(self, data):
        apply_attrs(self, data)


class NKDatasetException(NKException):

    def __repr__(self):
        return "<NKDatasetException(%s:%s)>" % (self,
                                               getattr(self, 'message', None))


class NKNoMatch(NKException):

    def __repr__(self):
        return "<NKNoMatch(%s:%s)>" % (self.dataset,
                                       self.key)


class NKInvalid(NKException):

    def __repr__(self):
        return "<NKInvalid(%s:%s)>" % (self.dataset,
                                       self.key)


class Value(NKObject):

    def __init__(self, dataset, data):
        self._dataset = dataset
        apply_attrs(self, data)

    def __repr__(self):
        return "<Value(%s:%s:%s)>" % (self._dataset.name,
                                        self.id, self.value)


class Link(NKObject):

    INVALID = "INVALID"
    NEW = "NEW"

    def __init__(self, dataset, data):
        self._dataset = dataset
        super(NKLink,self).__init__(data)

    def __repr__(self):
        return "<Link(%s:%s:%s:%s)>" % (self._dataset.name,
                                       self.id, self.key, self.is_matched)


class Dataset(object):

    def __init__(self, dataset,
                 host='http://nomenklatura.okfnlabs.org',
                 api_key=None):
        self.host = host
        self.name = dataset
        self.api_key = api_key
        self._fetch()

    @property
    def _session(self):
        if not hasattr(self, '_session_obj'):
            headers = {'Accept': 'application/json',
                       'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = self.api_key
            self._session_obj = requests.Session()
            self._session_obj.headers.update(headers)
        return self._session_obj

    def _get(self, path, params={}, retry=True):
        response = self._session.get(self.host + '/' + self.name + path,
                                     params=params)
        if not response.ok:
            #print [response.status_code, response.content]
            del self._session_obj
        return response.status_code, response.json()

    def _post(self, path, data={}, retry=True):
        data = json.dumps(data)
        response = self._session.post(self.host + '/' + self.name + path,
                                      allow_redirects=True,
                                      data=data)
        if not response.ok:
            #print [response.status_code, response.content]
            del self._session_obj
        return (response.status_code,
                json.loads(response.content) if response.content else {})

    def _fetch(self):
        code, data = self._get('')
        if not (code == 200 and data):
            data = data or {'code': code}
            raise NKDatasetException(data)
        apply_attrs(self, data)

    def get_value(self, id=None, value=None):
        assert id or value, "Need to give an ID or a value!"
        if id is not None:
            code, val = self._get('/values/%s' % id)
        else:
            code, val = self._get('/value', params={'value': value})
        if code != 200:
            raise NKException(val or {})
        return Value(self, val)

    def add_value(self, value, data={}):
        code, val = self._post('/values',
                               data={'value': value, 'data': data})
        if code == 400:
            raise NKException(val)
        return Value(self, val)

    def ensure_value(self, value, data={}):
        try:
            return self.get_value(value=value)
        except NKException:
            return self.add_value(value=value, data=data)

    def values(self):
        code, vals = self._get('/values')
        return [Value(self, v) for v in vals]

    def get_link(self, id=None, key=None):
        assert id or key, "Need to give an ID or a key!"
        if id is not None:
            code, val = self._get('/links/%s' % id)
        else:
            code, val = self._get('/link', params={'key': key})
        if code != 200:
            raise NKException(val)
        return Link(self, val)

    def links(self):
        code, vals = self._get('/links')
        return [Link(self, v) for v in vals]

    def lookup(self, key, context={}, readonly=False):
        code, val = self._post('/lookup',
                               data={'key': key,
                                     'readonly': readonly})
        if code == 404:
            raise NKNoMatch(val)
        elif code == 418:
            raise NKInvalid(val)
        else:
            return Value(self, val.get('value'))

    def match(self, link_id, value_id):
        code, val = self._post('/links/%s/match' % link_id,
                               data={'choice': value_id,
                                     'value': ''})
        if code != 200:
            raise NKException(val)
        return None

    def __repr__(self):
        return "<Dataset(%s)>" % self.name


if __name__ == "__main__":
    ds = Dataset('offenesparlament', 'http://localhost:5000')
