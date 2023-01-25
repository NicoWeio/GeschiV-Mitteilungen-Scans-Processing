#!/usr/bin/env python3
"""
Workflow
========
- pdftoppm |                             | PDF → PPM
- convert  | Kurvenfilter/…              | PPM → PPM
- unpaper  | Doppelseiten → Einzelseiten | ??? → PPM
- img2pdf  |                             | PPM → PDF
- ocrmypdf | OCR                         | PDF → PDF
"""

from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

import click
import numpy as np
from PIL import Image


def check_empty_outputdir(func):
    def wrapper(*args, **kwargs):
        assert args[1].parent.exists()
        if len(list(args[1].parent.iterdir())) > 0:
            raise Exception("Directory not empty")
        return func(*args, **kwargs)
    return wrapper


def pdftoppm(input_file: Path, output_file_base: Path) -> list[Path]:
    assert input_file.suffix == '.pdf'
    assert output_file_base.suffix == ''

    run(['pdftoppm', input_file, output_file_base], check=True)

    output_files = sorted(output_file_base.parent.glob(f'{output_file_base.name}-*.ppm'))
    assert len(output_files) > 0
    return output_files


def convert(input_file: Path, output_file: Path) -> Path:
    """
    Applies a curve filter to the image using ImageMagick.
    """
    assert input_file.suffix == '.ppm'
    assert output_file.suffix == '.ppm'

    args = [
        '-normalize',
        '-colorspace', 'HSL',
        '-channel', 'lightness',
        '-fx', 'min(1.0,u.b*1.075)',  # TODO?
        '-colorspace', 'RGB',
        '-colorspace', 'Gray',
    ]

    run(['convert', input_file, *args, output_file], check=True)
    return output_file


def unpaper(input_file: Path, output_file_pattern: Path, double_page: bool) -> list[Path]:
    """
    Separates two-page scans into single pages (and more).
    """
    assert input_file.suffix == '.ppm'
    # use a pattern even if we only have one output file
    assert '%d' in output_file_pattern.name

    args = [
        '--no-blackfilter',
        '--no-blurfilter',
        '--no-border-align',
        '--no-border-scan',
        '--no-border',
        '--no-deskew',
        '--no-grayfilter',
        '--no-mask-center',
        '--no-mask-scan',
        '--no-noisefilter',
        '--no-wipe',
        # '--overwrite',
    ]
    if double_page:
        args += [
            '--layout', 'double',
            '--output-pages', '2',
        ]

    run(['unpaper', *args, input_file, output_file_pattern], check=True)

    output_files = sorted(output_file_pattern.parent.glob(output_file_pattern.name.replace('%d', '*')))
    assert len(output_files) > 0
    return output_files


def img2pdf(input_files: list[Path], output_file: Path) -> Path:
    assert all(f.suffix == '.ppm' for f in input_files)
    assert output_file.suffix == '.pdf'

    run(['img2pdf', *input_files, '-o', output_file], check=True)
    return output_file


def ocrmypdf(input_file: Path, output_file: Path) -> Path:
    assert input_file.suffix == '.pdf'
    assert output_file.suffix == '.pdf'

    args = [
        '--language', 'deu',
        # COPILOT '--optimize', '3',
        # COPILOT '--output-type', 'pdfa',
    ]

    run(['ocrmypdf', *args, input_file, output_file], check=True)
    return output_file


def is_blank(page_path: Path) -> bool:
    """
    Checks if a page is (mostly) blank.
    """
    assert page_path.suffix == '.ppm'
    image = np.array(Image.open(page_path))
    # average over RGB channels
    image = np.mean(image, axis=2)
    # average over all pixels
    mean = np.mean(image)
    mean_blackness = 255 - mean
    print(page_path, mean_blackness)
    return mean_blackness < 1  # TODO: adjust threshold


@click.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument('output_file', type=click.Path(dir_okay=False, path_type=Path))
@click.option('double_page', '--double-page/--single-page', default=True)
def main(input_file, output_file, double_page):
    assert input_file.suffix == '.pdf'
    assert output_file.suffix == '.pdf'
    assert output_file.parent.exists()

    # TODO: option to overwrite
    assert not output_file.exists(), "Output file already exists"

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print(tmpdir)

        pages = pdftoppm(input_file, tmpdir / f"1-{input_file.stem}")

        pages = [
            convert(page, tmpdir / f"2-{page.name}")
            for page in pages
        ]

        pages = [
            out_page
            for in_page in pages
            for out_page in unpaper(in_page, tmpdir / f"3-{in_page.stem}-%d.ppm", double_page)
        ]

        pages = [
            page
            for page in pages
            if not is_blank(page)
        ]

        pdf = img2pdf(pages, tmpdir / f"4-{input_file.name}")

        ocrmypdf(pdf, output_file)

        assert output_file.exists()

        print("Output file size is", output_file.stat().st_size, "bytes")


if __name__ == '__main__':
    main()
