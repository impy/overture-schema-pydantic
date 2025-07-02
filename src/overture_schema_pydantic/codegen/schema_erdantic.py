import erdantic
from rich.pretty import pprint

from overture_schema_pydantic.divisions import Division


diagram = erdantic.create(Division)
pprint(diagram)

with open("../../../out/division.gv", "w") as file:
    file.write(diagram.to_dot())

diagram.draw("../../../out/division.png", format="png")
