# Mitteilungen-Scans-Processing
Dies ist ein kleines Tool, um die Scans der [Mitteilungen des Vereins für Geschichte und Heimatpflege Soest e. V.](https://geschichtsverein-soest.de/mitteilungen/) zu ansehnlichen PDFs zu verarbeiten.
Ganz bestimmt gibt es bessere Wege – beispielsweise könnte ich `Pillow` auch verwenden, um `convert` zu ersetzen – aber so ist das Projekt eben gewachsen und [gut genug](https://www.xkcd.com/974/).


## Benutzung
Benötigt werden:
- Kommandozeilen-Tools:
  - `pdftoppm` → Poppler
  - `convert` → ImageMagick
  - `unpaper`
  - `img2pdf`
  - `ocrmypdf`
- Python-Pakete
  - `click`
  - `Pillow`

Dann kann das Tool wie folgt aufgerufen werden:
```bash
./main.py [OPTIONS] input.pdf output.pdf
```


## Ohne dieses Tool: Der Weg über die Kommandozeile
```bash
pdftoppm Scan-PDFs/Mitteilungen_20.pdf PPMs/Mitteilungen_20
convert PPM-orig/Mitteilungen_20-8.ppm -normalize -colorspace HSL -channel lightness -fx 'min(1.0,u.b*1.075)' -colorspace RGB -colorspace Gray PPM-convert/Mitteilungen_20-8.ppm
unpaper --overwrite --layout double --output-pages 2 --no-blackfilter --no-noisefilter --no-blurfilter --no-grayfilter --no-mask-scan --no-mask-center --no-deskew --no-wipe --no-border --no-border-scan --no-border-align PPM-convert/Mitteilungen_20-%d.ppm PPM-unpaper/Mitteilungen_20-%d.ppm
ocrmypdf -l deu PDF-img2pdf/Mitteilungen_20.pdf PDF-OCR/Mitteilungen_20.pdf
```
