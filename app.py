import streamlit as st
import pandas as pd
import tempfile
import os
import re

from pdf2image import convert_from_path
from PIL import Image

import pytesseract
import cv2
import numpy as np

from datetime import datetime


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Standard Bank Statement Converter",
    layout="wide"
)

st.title("Standard Bank Statement → CSV")

st.write(
    "Upload scanned Standard Bank PDF statements"
)


# =========================
# OCR IMAGE CLEANING
# =========================


def preprocess_image(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    gray = cv2.fastNlMeansDenoising(gray)

    thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    processed_path = image_path.replace(
        ".jpg",
        "_processed.jpg"
    )

    cv2.imwrite(processed_path, thresh)

    return processed_path


# =========================
# TEXT CLEANING
# =========================


def clean_description(text):

    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# =========================
# DATE NORMALIZATION
# =========================


def normalize_date(date_str, current_year="2024"):

    patterns = [
        "%d/%m",
        )
