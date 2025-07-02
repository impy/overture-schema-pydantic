POC goals

1) ~~Model geometry.~~
2) ~~Model an arbitrary custom constraint. (Geometry type)~~
3) ~~Model feature type.~~
4) ~~Override feature type JSON Schema to make it GeoJSON.~~
5) ~~Generate a typed ID reference.~~
6) ~~Model common names with language tags as dictionary keys.~~
7) ~~Model sources~~ with JSON Pointer value.
8) Annotate `int` type with a "hard range" annotation for Parquet.
9) Figure out how this would propagate through Spark into Parquet file.
10) ~~Generate a Spark schema.~~

Some observations of base types needed:

- A non-empty string type that has no leading or trailing whitespace.
- A floating-point number [0,1] representing a percentage, used for both
  confidence and linear referencing.
- A `UniqueItems` constraint may not be needed because in Pydantic you
  can just declare the field type to be `set`/`Set` and this will
  generate the right `uniqeItems` constraint in JSON Schema.

CODE GENERATION:

- Python has a native AST manipulation module, `ast`. This would be good for
  parsing the schema source code into a Python AST.
- ~~Either the `ast` module by itself or that plus `astor` could be used to
  traverse the schema source code as a syntax tree and generate other code
  from it.~~
- It might be useful to use LibCST to *generate* the code because you can
  make a "concrete syntax tree" that contains comments etc.
- It appears that the Pydantic artifact that we REALLY care about in terms
  of an AST-like structure is the core schema. So we probably don't want to
  parse the code, we just want to find a way to:
    - Discover all the things that derive from BaseModel (or Feature?),
      either by parsing the code or by requiring some kind of schema
      manifest. But note that even with a manifest we still have to
      parse the code.
    - From all the BaseModel and/or Feature derived classes, get their
      core schema from `__get_pydantic_core_schema__`.
      
# ERD Diagram 

Using Erdantic, we can generate an ER Diagram from the Pydantic models.
Below is an example using the Divisions pydantic mode with the generated ERD 
both as a Python object and as a rendered graph.

```
EntityRelationshipDiagram(
   models={
      'overture_schema_pydantic.divisions.Division': ModelInfo(...),
      'overture_schema_pydantic.names.Names': ModelInfo(...),
      'overture_schema_pydantic.source.Source': ModelInfo(...)
   },
   edges={
      'overture_schema_pydantic.divisions.Division-names-overture_schema_pydantic.names.Names': Edge(...),
      'overture_schema_pydantic.divisions.Division-sources-overture_schema_pydantic.source.Source': Edge(...)
   }
)
```

![ERD Diagram generatd by Erdantic](/out/division.png)
