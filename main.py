"""
Workflow
========
- pdftoppm |                             | PDF → PPM
- convert  | Kurvenfilter/…              | PPM → PPM
- unpaper  | Doppelseiten → Einzelseiten | ??? → PPM
- img2pdf  |                             | PPM → PDF
- ocrmypdf | OCR                         | PDF → PDF
"""

from PIL import Image
import numpy as np
from subprocess import run
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile


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


def unpaper(input_file: Path, output_file_pattern: Path) -> Path:
    """
    Separates two-page scans into single pages (and more).
    """
    assert input_file.suffix == '.ppm'
    assert '%d' in output_file_pattern.name

    args = [
        '--layout', 'double',
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
        '--output-pages', '2',
        # '--overwrite',
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
    print(page_path, mean)
    return mean < 0.01  # TODO: adjust threshold


def main():
    input_file = Path('input.pdf')
    output_file = Path('output.pdf')

    assert input_file.suffix == '.pdf'
    assert output_file.suffix == '.pdf'
    assert output_file.parent.exists()

    # TODO: option to overwrite
    # assert not output_file.exists(), "Output file already exists"

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print(tmpdir)

        # tmpdir.mkdir(777, False, '1')
        pages = pdftoppm(input_file, tmpdir / f"1-{input_file.stem}")

        # tmpdir.mkdir(777, False, '2')
        pages = [
            convert(page, tmpdir / f"2-{page.name}")
            for page in pages
        ]

        # tmpdir.mkdir(777, False, '3')
        pages = [
            single_page
            for double_page in pages
            for single_page in unpaper(double_page, tmpdir / f"3-{double_page.stem}-%d.ppm")
        ]

        # tmpdir.mkdir(777, False, '4')
        pdf = img2pdf(pages, tmpdir / f"4-{input_file.name}")

        ocrmypdf(pdf, output_file)

        assert output_file.exists()

        print("Output file size is", output_file.stat().st_size, "bytes")


if __name__ == '__main__':
    main()
