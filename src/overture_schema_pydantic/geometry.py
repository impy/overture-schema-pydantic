from typing import Any, Optional

from pydantic import (
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    ValidationError,
    ValidationInfo,
)
from pydantic_core import core_schema, InitErrorDetails

from shapely.geometry import shape, mapping
from shapely.geometry.base import BaseGeometry

# Note: It would be better to model this as a string enumeration class GeometryType(Enum, str)
#       and then you get GeometryType(str) with a ValueError on unrecognized type as a freebie.
_GEOMETRY_TYPES = (
    "GeometryCollection",
    "LineString",
    "Point",
    "Polygon",
    "MultiLineString",
    "MultiPoint",
    "MultiPolygon",
)


class GeometryTypeConstraint:
    def __init__(self, *allowed_types: str):
        self.__allowed_types = self.__class__._validate_geometry_types(allowed_types)

    @property
    def allowed_types(self) -> tuple[str, ...]:
        return self.__allowed_types

    def validate(self, value: "Geometry", info: ValidationInfo):
        geometry_type = value.geom.geom_type
        if geometry_type not in self.allowed_types:
            context = info.context or {}
            loc = context.get("loc_prefix", ()) + ("value",)
            raise ValidationError.from_exception_data(
                title=self.__class__.__name__,
                line_errors=[
                    InitErrorDetails(
                        type="value_error",
                        loc=loc,
                        input=value,
                        ctx={
                            "error": f"geometry type not allowed: {repr(geometry_type)} (allowed values: {repr(self.allowed_types)})"
                        },
                    )
                ],
            )

    @classmethod
    def _validate_geometry_types(cls, a: list[str]) -> tuple[str]:
        if not a:
            raise ValueError(
                f"allowed_types is empty (it must contain at least one of: {_GEOMETRY_TYPES})"
            )

        if not all(item in _GEOMETRY_TYPES for item in a):
            invalid = [item for item in a if item not in _GEOMETRY_TYPES]
            raise ValueError(
                f"allowed_types contains invalid values: {invalid} (allowed: {_GEOMETRY_TYPES})"
            )

        if len(set(a)) != len(a):
            raise ValueError(f"allowed_types contains duplicate(s)")

        return tuple(sorted(a))

    def __get_pydantic_core_schema__(
        self, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        if not issubclass(source, Geometry):
            raise TypeError(
                f"{GeometryTypeConstraint.__name__} can only be applied to {Geometry.__name__}; but it was applied to {source.__name__}"
            )
        schema = handler(source)
        return core_schema.with_info_after_validator_function(self.validate, schema)

    def __get_pydantic_json_schema__(
        self, source: type[Any], handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        if len(self.allowed_types) == 1:
            return _GEOMETRY_JSON_SCHEMA[self.allowed_types[0]]
        else:
            allowed_schemas = tuple(
                map(
                    lambda x: _GEOMETRY_JSON_SCHEMA[x],
                    self.allowed_types,
                )
            )
            return {
                "oneOf": allowed_schemas,
            }


_ALL_GEOMETRY_ALLOWED = GeometryTypeConstraint(*_GEOMETRY_TYPES)


class Geometry:
    geom: BaseGeometry

    def __init__(self, geom: BaseGeometry):
        self.geom = geom

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Geometry) and self.geom == other.geom

    def __hash__(self) -> int:
        return hash(self.geom)

    def __repr__(self) -> str:
        return f"<{repr(self.geom)}>"

    def __str__(self) -> str:
        return self.wkt

    def to_geo_json(self) -> dict[str, Any]:
        return mapping(self.geom)

    @classmethod
    def from_geo_json(cls, value: Any) -> "Geometry":
        if not isinstance(value, dict):
            raise TypeError(
                f"value must be a dict; but {repr(value)} has type {type(value).__name__}"
            )

        type_ = value.get("type")

        if type_ not in _GEOMETRY_TYPES:
            raise ValueError(
                f"allowed_types contains invalid value {repr(type_)} (allowed: {_GEOMETRY_TYPES})"
            )

        return cls(shape(value))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validator(value: Any, info: ValidationInfo) -> Geometry:
            try:
                return cls.from_geo_json(value)
            except Exception as e:
                context = info.context or {}
                loc = context.get("loc_prefix", ()) + ("value",)
                raise ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        InitErrorDetails(
                            type="value_error",
                            loc=loc,
                            input=value,
                            ctx={"error": f"invalid geometry value: {str(e)}"},
                        )
                    ],
                )

        return core_schema.with_info_plain_validator_function(
            validator,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: v.to_geojson()
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        return _ALL_GEOMETRY_ALLOWED.__get_pydantic_json_schema__(core_schema, handler)


########################################################################
# JSON Schema primitives for GeoJSON geometry
########################################################################

_BBOX_JSON_SCHEMA = {
    "type": "array",
    "minItems": 4,
    "items": {
        "type": "number",
    },
}

_POINT_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 2,
    "items": {
        "type": "number",
    },
}

########################################################################
# JSON Schema for GeoJSON geometry `coordinates`
########################################################################

_LINE_STRING_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 2,
    "items": _POINT_COORDINATES_JSON_SCHEMA,
}

_MULTI_LINE_STRING_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _LINE_STRING_COORDINATES_JSON_SCHEMA,
}

_MULTI_POINT_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _POINT_COORDINATES_JSON_SCHEMA,
}

_LINEAR_RING_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 4,
    "items": _POINT_COORDINATES_JSON_SCHEMA,
}

_POLYGON_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _LINEAR_RING_COORDINATES_JSON_SCHEMA,
}

_MULTI_POLYGON_COORDINATES_JSON_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": _POLYGON_COORDINATES_JSON_SCHEMA,
}

########################################################################
# JSON Schema for GeoJSON geometry types
########################################################################


def geometry_json_schema(
    geometry_type: str,
    coordinates: Optional[dict[str, Any]] = None,
    geometries: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    properties = {
        "type": {
            "type": "string",
            "const": geometry_type,
        },
        "bbox": _BBOX_JSON_SCHEMA,
    }
    required = ["type"]
    if coordinates:
        required.append("coordinates")
        properties["coordinates"] = coordinates
    if geometries:
        required.append("geometries")
        properties["geometries"] = geometries
    return {
        "type": "object",
        "required": required,
        "properties": properties,
    }


_LINE_STRING_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "LineString", coordinates=_LINE_STRING_COORDINATES_JSON_SCHEMA
)

_POINT_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "Point", coordinates=_POINT_COORDINATES_JSON_SCHEMA
)

_POLYGON_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "Polygon", coordinates=_POLYGON_COORDINATES_JSON_SCHEMA
)

_MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "MultiLineString", coordinates=_MULTI_LINE_STRING_COORDINATES_JSON_SCHEMA
)

_MULTI_POINT_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "MultiPoint", coordinates=_MULTI_POINT_COORDINATES_JSON_SCHEMA
)

_MULTI_POLYGON_GEOMETRY_JSON_SCHEMA = geometry_json_schema(
    "MultiPolygon", coordinates=_MULTI_POLYGON_COORDINATES_JSON_SCHEMA
)

_GEOMETRY_COLLECTION_JSON_SCHEMA = geometry_json_schema(
    "GeometryCollection",
    geometries={
        "oneOf": (
            _LINE_STRING_GEOMETRY_JSON_SCHEMA,
            _POINT_GEOMETRY_JSON_SCHEMA,
            _POLYGON_GEOMETRY_JSON_SCHEMA,
            _MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA,
            _MULTI_POINT_GEOMETRY_JSON_SCHEMA,
            _MULTI_POLYGON_GEOMETRY_JSON_SCHEMA,
        )
    },
)

########################################################################
# Lookup table for all the JSON Schema
########################################################################

_GEOMETRY_JSON_SCHEMA = {
    "GeometryCollection": _GEOMETRY_COLLECTION_JSON_SCHEMA,
    "LineString": _LINE_STRING_GEOMETRY_JSON_SCHEMA,
    "Point": _POINT_GEOMETRY_JSON_SCHEMA,
    "Polygon": _POLYGON_GEOMETRY_JSON_SCHEMA,
    "MultiLineString": _MULTI_LINE_STRING_GEOMETRY_JSON_SCHEMA,
    "MultiPoint": _MULTI_POINT_GEOMETRY_JSON_SCHEMA,
    "MultiPolygon": _MULTI_POLYGON_GEOMETRY_JSON_SCHEMA,
}
