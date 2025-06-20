from overture_schema_pydantic.geometry import Geometry, GeometryTypeConstraint

from dataclasses import dataclass
from itertools import chain, combinations
from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError


def test_geometry_type_constraint_empty():
    with pytest.raises(ValueError):

        class EmptyGeometryTypeConstraintModel(BaseModel):
            geometry: Annotated[Geometry, GeometryTypeConstraint()]


def test_geometry_type_constraint_invalid():
    with pytest.raises(ValueError):

        class InvalidGeometryTypeConstraintModel(BaseModel):
            geometry: Annotated[Geometry, GeometryTypeConstraint("foo")]


@dataclass
class GeometryTypeCase:
    geometry_type: str
    examples: tuple[dict] = ()
    counterexamples: tuple[dict] = ()


TEST_GEOMETRY_TYPE_CASES: tuple[GeometryTypeCase] = (
    GeometryTypeCase(
        geometry_type="Point",
        examples=(
            {"type": "Point", "coordinates": [0, 0]},
            {"type": "Point", "coordinates": [-90, 131.5]},
        ),
        counterexamples=(
            {},
            {"type": "Point"},
            {"coordinates": [0, 0]},
            {"type": "Point", "coordinates": "foo"},
            {"type": "Point", "coordinates": [0]},
            {"type": "Point", "coordinates": [[0, 0], [1, 1]]},
        ),
    ),
)


def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


TEST_GEOMETRY_TYPE_CASE_SUBSETS = tuple(
    s for s in powerset(TEST_GEOMETRY_TYPE_CASES) if len(s) > 0
)


@pytest.mark.parametrize("geometry_type_case_subset", TEST_GEOMETRY_TYPE_CASE_SUBSETS)
def test_geometry_type_constraint_valid(geometry_type_case_subset, subtests):
    allowed_types = tuple(g.geometry_type for g in geometry_type_case_subset)

    class ConstrainedModel(BaseModel):
        geometry: Annotated[Geometry, GeometryTypeConstraint(*allowed_types)]

    for geometry_type_case in geometry_type_case_subset:
        with subtests.test(geometry_type=geometry_type_case.geometry_type):
            for example in geometry_type_case.examples:
                with subtests.test(example=example):
                    model_instance = ConstrainedModel(geometry=example)
            for counterexample in geometry_type_case.counterexamples:
                with subtests.test(counterexample=counterexample):
                    with pytest.raises(ValidationError):
                        model_instance = ConstrainedModel(geometry=counterexample)
