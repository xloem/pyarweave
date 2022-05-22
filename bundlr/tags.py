import io
import fastavro

schema = fastavro.parse_schema({
  "type": "array",
  "items": {
    "type": "record",
    "name": "Tag",
    "fields": [
      { "name": "name", "type": "string" },
      { "name": "value", "type": "string" }
    ]
  }  
})

def serialize_buffer(tags_dict):
    output = io.BytesIO()
    tag_records = [{'name':name,'value':value} for name, value in tags_dict.items()]
    fastavro.schemaless_writer(output, schema, tag_records)
    return output.getbuffer()

def deserialize_buffer(data):
    fo = io.BytesIO(data)
    records = fastavro.schemaless_reader(fo, schema)
    return {
        record['name']: record['value']
        for record in records
    }
