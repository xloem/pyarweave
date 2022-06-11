import io, time, uuid
import json
from .utils import tags_to_dict

class Entity:
    def __init__(self, **kwparams):
        kwparams['content_type'] = 'application/json' if kwparams.get('cipher') is None else 'application/octet-stream'
        if kwparams.get('unix_time') is None:
            kwparams['unix_time'] = str(time.time())
        self._tags_props = {
            name : value
            for name, value in kwparams.items()
            if name in self.tagspec
            and value is not None
        }
        self._data_props = {
            name : value
            for name, value in kwparams.items()
            if name in self.dataspec
            and value is not None
        }

    def __getattr__(self, name):
        if name in self.tagspec:
            return self._tags_props.get(name)
        elif name in self.dataspec:
            return self._data_props.get(name)
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in self.tagspec:
            self._tags_props[name] = value
        elif name in self.dataspec:
            self._data_props[name] = value
        else:
            super().__setattr__(name, value)

    @classmethod
    def from_tags_stream(cls, tags, stream):
        return cls(**cls.tags_to_props(tags), **cls.stream_to_props(stream))

    def to_tags_bytes(self):
        return self.props_to_tags(self._props_dict), self.props_to_bytes(self._data_dict)

    @classmethod
    def tags_to_props(cls, tags):
        tags_dict = tags_to_dict(tags)
        props_dict = {
            prop: tags_dict[tag]
            for prop, tag
            in cls.tagspec.items()
            if tags_dict.get(tag) is not None
        }
        assert len(tags_dict) == len(props_dict)
        return props_dict

    @classmethod
    def props_to_tags(cls, props):
        tags_dict = {
            tag: props[prop]
            for prop, tag
            in cls.tagspec.items()
            if props.get(prop) is not None
        }
        assert len(tags_dict) == len(props)
        return tags_dict

    @classmethod
    def stream_to_props(cls, stream):
        data_dict = json.load(stream)
        props_dict = {
            prop: data_dict[key]
            for prop, key
            in cls.dataspec.items()
            if data_dict.get(key) is not None
        }
        assert len(data_dict) == len(props_dict)
        return props_dict
        
    @classmethod
    def props_to_bytes(cls, props):
        bytes = io.BytesIO()
        data_dict = {
            key: props[prop]
            for prop, key
            in cls.dataspec.items()
            if props.get(prop) is not None
        }
        assert len(data_dict) == len(props)
        json.dump(data_dict, bytes)
        return bytes.getvalue()

    tagspec = dict(
        version = 'ArFS',
        cipher = 'Cipher',
        cipher_iv = 'Cipher-IV',
        content_type = 'Content-Type',
        drive_id = 'Drive-ID',
        entity_type = 'Entity-Type',
        unix_time = 'Unix-Time',
    )

class Drive(Entity):
    tagspec = dict(
        **Entity.tagspec,
        privacy = 'Drive-Privacy',
        auth_mode = 'Drive-Auth-Mode',
    )
    dataspec = dict(
        name = 'name',
        root = 'rootFolderId'
    )
    def __init__(self, name, root = None, privacy = 'public', unix_time = None, drive_id = None, cipher = None, cipher_iv = None, auth_mode = None, version = '0.11'):
        if root is None:
            root = str(uuid.uuid4())
        if drive_id is None:
            drive_id = str(uuid.uuid4())

        super.__init__(entity_type = 'drive', version = version, cipher = cipher,
              cipher_iv = cipher_iv, drive_id = drive_id, privacy = privacy, auth_mode = auth_mode,
              content_type = content_type, unix_time = unix_time, name = name,
              root_folder_id = root_folder_id)

class Folder(Entity):
    tagspec = dict(
        **Entity.tagspec,
        id = 'Folder-Id',
        parent = 'Parent-Folder-Id',
    )
    dataspec = dict(
        name = 'name',
    )
    def __init__(self, drive_id, name, id = None, parent = None, unix_time = None, cipher = None, cipher_iv = None, version = '0.11'):
        if id is None:
            id = str(uuid.uuid4())
        super.__init__(entity_type = 'folder', version = version, cipher = cipher,
              cipher_iv = cipher_iv, drive_id = drive_id, privacy = privacy, auth_mode = auth_mode,
              unix_time = unix_time, name = name, id = id, parent = parent)

class FileMetadata(Entity):
    tagspec = dict(
        **Entity.tagspec,
        id = 'File-Id',
        parent = 'Parent-Folder-Id',
    )
    dataspec = dict(
        name = 'name',
        size = 'size',
        last_modified_date = 'lastModifiedDate',
        data_txid = 'dataTxId',
        data_content_type = 'dataContentType',
    )
    def __init__(self, drive_id, parent, name, size, data_txid, data_content_type, id = None, unix_time = None, cipher = None, cipher_iv = None, version = '0.11'):
        if id is None:
            id = str(uuid.uuid4())
        super.__init__(entity_type = 'file', version = version, cipher = cipher,
              cipher_iv = cipher_iv, drive_id = drive_id, privacy = privacy, auth_mode = auth_mode,
              unix_time = unix_time, name = name, id = id, parent = parent)

class FileData(Entity):
    tagspec = dict(
        cipher = 'Cipher',
        cipher_iv = 'Cipher-IV',
        content_type = 'Content-Type'
    )
    dataspec = {}
    def __init__(self, cipher = None, cipher_iv = None, content_type = None):
        super().__init__(cipher, cipher_iv)
        self.content_type = content_type

    @classmethod
    def from_tags(cls, tags):
        return cls(**cls.tags_to_props(tags))

    @classmethod
    def from_tags_stream(cls, tags, stream):
        return cls.from_tags(cls), stream

    def to_tags(self):
        return self.props_to_tags(self._props_dict)
    
    def to_tags_bytes(self, stream):
        return self.to_tags(), stream.read()
