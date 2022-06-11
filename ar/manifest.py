import json

from .utils import create_tag

CONTENT_TYPE = 'application/x.arweave-manifest+json'

class Manifest:
    def __init__(self, path_txids, index = None, version = '0.1.0'):
        self.path_txids = path_txids
        self.index = index
        self.version = version
    @classmethod
    def fromjson(cls, json):
        return cls(
            path_txids = { key: value['id'] for key, value in json['paths'].items() },
            index = json['index']['path'] if 'index' in json else None,
            version = json['version']
        )
    def tojson(self):
        return dict(
            manifest = 'arweave/paths',
            version = self.version,
            **(
                dict(
                    index = dict(
                        path = self.index
                    )
                ) if self.index is not None
                else {}
            ),
            paths = {
                path: dict(id=txid)
                for path, txid in self.path_txids.items()
            }
        )
    def tobytes(self):
        return json.dumps(self.tojson()).encode()
    @staticmethod
    def totags():
        return [create_tag('Content-Type', CONTENT_TYPE, True)]
