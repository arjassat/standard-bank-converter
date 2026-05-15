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


# =====================================
# PAGE
# =====================================

st.set_page_config(
    page_title="Standard Bank Converter",
    layout="wide"
)

st.title("Standard Bank Statement → CSV")


# =====================================
# IMAGE CLEANING
# =====================================


def preprocess_image(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    gray = cv2.GaussianBlur(gray, (5, 5), 0)

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


# =====================================
# DATE
# =====================================


def normalize_date(date_str):

    patterns = [
        "%d/%m",
        "%d-%m",
        "%d.%m"
    ]

    for pattern in patterns:

        try:

            dt = datetime.strptime(
        )
