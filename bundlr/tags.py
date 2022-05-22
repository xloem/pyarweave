import io
import fastavro

schema = fastavro.parse_schema({
  "type": "array",
  "items": {
    "type": "record",
    "name": "Tag",
    "fields": [
      { "name": "name", "type": "bytes" },
      { "name": "value", "type": "bytes" }
    ]
  }  
})

def serialize_buffer(tags_obj):
    output = io.BytesIO()
    if isinstance(tags_obj, dict):
        tags_obj = tags_obj.items()
    tag_records = [
        {
            'name': name if isinstance(name,(bytes,bytearray)) else str(name).encode(),
            'value': value if isinstance(value,(bytes,bytearray)) else str(value).encode()
        }
        for name, value in tags_obj
    ]
    fastavro.schemaless_writer(output, schema, tag_records)
    return output.getbuffer()

def deserialize_buffer(data):
    fo = io.BytesIO(data)
    records = fastavro.schemaless_reader(fo, schema)
    return [
        (record['name'], record['value'])
        for record in records
    ]
