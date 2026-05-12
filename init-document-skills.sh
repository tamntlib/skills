#!/bin/bash

uv run --with python-docx --with python-pptx --with openpyxl --with pandas --with xlrd --with pypdf --with pdfplumber --with "markitdown[pptx]" python -c "import docx, pptx, openpyxl, pandas, xlrd, pypdf, pdfplumber, markitdown; print('ok')"

brew install poppler pandoc

brew install --cask libreoffice

# If you need OCR scanned PDFs/images
brew install tesseract
uv run --with pytesseract --with pdf2image python -c "import pytesseract, pdf2image; print('ok')"
