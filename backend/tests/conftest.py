import sys
import os
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "测试用例")
NATIVE_PDF_DIR = os.path.join(TEST_DATA_DIR, "原生PDF")
IMAGE_PDF_DIR = os.path.join(TEST_DATA_DIR, "图片型PDF")


def get_native_pdfs():
    if not os.path.isdir(NATIVE_PDF_DIR):
        return []
    return sorted([f for f in os.listdir(NATIVE_PDF_DIR) if f.endswith(".pdf")])


def get_image_pdfs():
    if not os.path.isdir(IMAGE_PDF_DIR):
        return []
    return sorted([f for f in os.listdir(IMAGE_PDF_DIR) if f.endswith(".pdf")])


def native_pdf_path(name):
    return os.path.join(NATIVE_PDF_DIR, name)


def image_pdf_path(name):
    return os.path.join(IMAGE_PDF_DIR, name)
