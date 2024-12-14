import json
from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import click
from build123d_ease import show
from loguru import logger


@dataclass(kw_only=True)
class BushingSpec:
    """Specification for the bushing."""

    bushing_id: float = 3.2
    bushing_od: float = 6.4
    bushing_length: float

    bushing_each_time: int = 4

    flag_thickness: float = 2.8
    flag_length: float = 15
    flag_height: float = 12

    text_font_size: float = 5
    text_thickness: float = 1

    # Border around the standoff holes.
    flag_stem_length_radial: float = 4
    flag_stem_od: float = 3.5

    text_top: str = ""
    text_bottom: str = ""

    def __post_init__(self) -> None:
        """Post initialization checks."""
        assert (
            self.bushing_od > self.bushing_id
        ), f"OD {self.bushing_od} < ID {self.bushing_id}"

        assert self.flag_stem_od < self.bushing_od, (
            f"Flag stem OD {self.flag_stem_od} > "
            f"Bushing OD {self.bushing_od}"
        )


def make_bushing(base_spec: BushingSpec) -> bd.Part:
    """Create a CAD model of bushing."""
    p = bd.Part(None)

    p += bd.Cylinder(
        radius=base_spec.bushing_od / 2,
        height=base_spec.bushing_length,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    if len(base_spec.text_top) <= len(base_spec.text_bottom):
        text_top = base_spec.text_top + " to"
        text_bottom = base_spec.text_bottom
    else:
        text_top = base_spec.text_top
        text_bottom = "to " + base_spec.text_bottom

    text_2d_top = bd.Text(
        text_top,
        font_size=base_spec.text_font_size,
        align=(bd.Align.CENTER, bd.Align.MIN),
    ).translate((0, 0.6))
    text_2d_bottom = bd.Text(
        text_bottom,
        font_size=base_spec.text_font_size,
        align=(bd.Align.CENTER, bd.Align.MAX),
    ).translate((0, -0.6))

    max_text_width = max(
        text_2d_top.bounding_box().size.X, text_2d_bottom.bounding_box().size.X
    )

    flag_length = max_text_width + 2

    # Create the flag stem (in +X direction).
    p += (
        bd.Cone(
            top_radius=base_spec.flag_thickness / 2,
            bottom_radius=min(
                base_spec.bushing_od / 2, base_spec.bushing_length / 2
            ),
            height=(
                base_spec.flag_stem_length_radial + base_spec.bushing_od / 2
            ),
            align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
        )
        .rotate(bd.Axis.Y, 90)
        .translate(
            (
                0,
                0,
                min(base_spec.bushing_length / 2, base_spec.flag_height / 2),
            )
        )
    )

    # Create the flag body for text (in +X direction).
    p += (
        flag_body_box := bd.Box(
            flag_length,
            base_spec.flag_thickness,
            base_spec.flag_height,
            align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.MIN),
        ).translate(
            (
                base_spec.flag_stem_length_radial + base_spec.bushing_od / 2,
                0,
                0,
            )
        )
    )

    # Add text to the flag (front side).
    for text_2d in (text_2d_top, text_2d_bottom):
        text_sketch = bd.Plane.XZ * text_2d.translate(
            (flag_body_box.center().X, flag_body_box.center().Z)
        )
        assert isinstance(text_sketch, bd.Sketch)
        p += bd.extrude(
            text_sketch,
            amount=base_spec.text_thickness + base_spec.flag_thickness / 2,
        )

    # Add text to the flag (back side).
    for text_2d in (text_2d_top, text_2d_bottom):
        text_sketch = bd.Plane.XZ * text_2d.translate(
            (-flag_body_box.center().X, flag_body_box.center().Z)
        )
        assert isinstance(text_sketch, bd.Sketch)
        p += bd.extrude(
            text_sketch,
            amount=(base_spec.text_thickness + base_spec.flag_thickness / 2),
        ).rotate(axis=bd.Axis.Z, angle=180)

    p -= bd.Cylinder(
        radius=base_spec.bushing_id / 2,
        height=base_spec.bushing_length,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )

    return p


@click.command()
@click.argument(
    "bushing_list_file_path",
    type=click.Path(exists=True, dir_okay=False),
    default=Path(__file__).parent.parent / "bushing_parts_list.json",
)
def make_many_bushings(bushing_list_file_path: Path | str) -> bd.Part:
    """Create a CAD model of many bushings."""
    bushing_list_file_path = Path(bushing_list_file_path)
    bushing_list = json.loads(bushing_list_file_path.read_text())

    (
        export_folder := Path(__file__).parent.parent
        / "build"
        / bushing_list_file_path.stem
    ).mkdir(exist_ok=True, parents=True)

    for i, bushing_overrides in enumerate(bushing_list):
        spec = BushingSpec(**bushing_overrides)

        part = make_bushing(spec).translate((0, i * spec.bushing_od + 5, 0))
        show(part)
        # breakpoint()
        assert isinstance(
            part, bd.Part | bd.Compound | bd.Solid
        ), f"part is not a Part: {part}"

        file_stem = f"bushing_{i}"
        if (
            "text_top" in bushing_overrides
            and "text_bottom" in bushing_overrides
        ):
            file_stem += (
                f" - {bushing_overrides['text_top']} "
                f"to {bushing_overrides['text_bottom']}"
            )

        bd.export_stl(part, str(export_folder / f"{file_stem}.stl"))
        logger.info(f"Exported '{file_stem}.stl'")

    return part


if __name__ == "__main__":
    make_many_bushings()
