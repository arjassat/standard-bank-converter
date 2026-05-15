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
import easyocr

from datetime import datetime


# =========================================
# PAGE CONFIG
# =========================================

st.set_page_config(
    page_title="Standard Bank Statement Converter",
    layout="wide"
)

st.title("Standard Bank Statement → CSV")

st.write(
    "Upload scanned Standard Bank PDF statements"
)


# =========================================
# OCR ENGINE
# =========================================

reader = easyocr.Reader(
    ['en'],
    gpu=False
)


# =========================================
# IMAGE PREPROCESSING
# =========================================

def preprocess_image(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.fastNlMeansDenoising(gray)

    gray = cv2.convertScaleAbs(
        gray,
        alpha=1.5,
        beta=10
    )

    thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    kernel = np.ones((1, 1), np.uint8)

    thresh = cv2.morphologyEx(
        thresh,
        cv2.MORPH_CLOSE,
        kernel
    )

    processed_path = image_path.replace(
        ".jpg",
        "_processed.jpg"
    )

    cv2.imwrite(
        processed_path,
        thresh
    )

    return processed_path


# =========================================
# TEXT CLEANING
# =========================================

def clean_description(text):

    text = re.sub(
        r'\s+',
        ' ',
        text
    )

    return text.strip()


# =========================================
# DATE NORMALIZATION
# =========================================

def normalize_date(
    date_str,
    current_year="2024"
):

    patterns = [
        "%d/%m",
        "%d-%m",
        "%d.%m"
    ]

    for pattern in patterns:

        try:

            dt = datetime.strptime(
                date_str,
                pattern
            )

            dt = dt.replace(
                year=int(current_year)
            )

            return dt.strftime(
                "%d/%m/%Y"
            )

        except:
            pass

    return date_str


# =========================================
# AMOUNT NORMALIZATION
# =========================================

def normalize_amount(amount_str):

    amount_str = amount_str.replace(
        ",",
        ""
    )

    amount_str = amount_str.strip()

    match = re.search(
        r'([0-9]+\.[0-9]{2})',
        amount_str
    )

    if not match:
        return ""

    value = match.group(1)

    if "DR" in amount_str.upper():
        return f"-{value}"

    return value


# =========================================
# TRANSACTION DETECTION
# =========================================

def looks_like_transaction(line):

    date_match = re.search(
        r'\b\d{1,2}[\/\-.]\d{1,2}\b',
        line
    )

    amount_match = re.search(
        r'\d+[.,]\d{2}',
        line
    )

    keywords = [
        'ATM',
        'POS',
        'TRANSFER',
        'PAYMENT',
        'PURCHASE',
        'DEBIT',
        'CREDIT',
        'CARD'
    ]

    keyword_match = any(
        keyword in line.upper()
        for keyword in keywords
    )

    return (
        (date_match and amount_match)
        or
        (keyword_match and amount_match)
    )


# =========================================
# TRANSACTION PARSER
# =========================================

def extract_transactions(text):

    transactions = []

    lines = text.split("\n")

    current_year = "2024"

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if not looks_like_transaction(line):
            continue

        date_match = re.search(
            r'(\d{1,2}[\/\-.]\d{1,2})',
            line
        )

        amount_match = re.findall(
            r'([0-9,]+\.\d{2}\s*(?:DR|CR)?)',
            line,
            re.IGNORECASE
        )

        if not date_match:
            continue

        if not amount_match:
            continue

        raw_date = date_match.group(1)

        raw_amount = amount_match[-1]

        description = line

        description = description.replace(
            raw_date,
            ""
        )

        description = description.replace(
            raw_amount,
            ""
        )

        description = clean_description(
            description
        )

        transaction = {
            "Date": normalize_date(
                raw_date,
                current_year
            ),
            "Description": description,
            "Amount": normalize_amount(
                raw_amount
            )
        }

        transactions.append(
            transaction
        )

    return transactions


# =========================================
# FILE UPLOAD
# =========================================

uploaded_files = st.file_uploader(
    "Upload PDF Statements",
    type=["pdf"],
    accept_multiple_files=True
)


# =========================================
# PROCESS FILES
# =========================================

if uploaded_files:

    all_transactions = []

    progress_bar = st.progress(0)

    total_files = len(uploaded_files)

    for file_index, uploaded_file in enumerate(uploaded_files):

        st.write(
            f"Processing: {uploaded_file.name}"
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf"
        ) as tmp:

            tmp.write(
                uploaded_file.read()
            )

            pdf_path = tmp.name

        try:

            images = convert_from_path(
                pdf_path,
                dpi=350
            )

            full_text = ""

            for idx, image in enumerate(images):

                image_path = (
                    f"temp_{file_index}_{idx}.jpg"
                )

                image.save(
                    image_path,
                    "JPEG"
                )

                processed_path = preprocess_image(
                    image_path
                )

                # =================================
                # OCR PASS 1 — TESSERACT
                # =================================

                tesseract_text = pytesseract.image_to_string(
                    Image.open(processed_path),
                    config='--psm 6'
                )

                # =================================
                # OCR PASS 2 — EASYOCR
                # =================================

                easyocr_results = reader.readtext(
                    processed_path,
                    detail=0,
                    paragraph=True
                )

                easyocr_text = "\n".join(
                    easyocr_results
                )

                # =================================
                # COMBINE OCR OUTPUTS
                # =================================

                extracted_text = (
                    tesseract_text
                    + "\n"
                    + easyocr_text
                )

                full_text += (
                    extracted_text + "\n"
                )

                if os.path.exists(image_path):
                    os.remove(image_path)

                if os.path.exists(processed_path):
                    os.remove(processed_path)

            transactions = extract_transactions(
                full_text
            )

            all_transactions.extend(
                transactions
            )

        except Exception as e:

            st.error(
                f"Error processing {uploaded_file.name}: {str(e)}"
            )

        finally:

            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        progress_bar.progress(
            (file_index + 1) / total_files
        )

    if len(all_transactions) == 0:

        st.warning(
            "No transactions found."
        )

    else:

        df = pd.DataFrame(
            all_transactions
        )

        st.success(
            f"Found {len(df)} transactions"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="standard_bank_transactions.csv",
            mime="text/csv"
        )
