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

def serialize_buffer(tag_records):
    output = io.BytesIO()
    tag_records = [
        {
            key: value if isinstance(value, (bytes, bytearray)) else str(value).encode()
            for key, value in tag_record.items()
        }
        for tag_record in tag_records
    ]
    fastavro.schemaless_writer(output, schema, tag_records)
    return output.getbuffer()

def deserialize_buffer(data):
    fo = io.BytesIO(data)
    return fastavro.schemaless_reader(fo, schema)
