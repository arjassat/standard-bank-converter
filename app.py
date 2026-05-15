import streamlit as st
import pandas as pd
import tempfile
import os
import re

from pdf2image import convert_from_path
from PIL import Image

import pytesseract
import cv2

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

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

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

    cv2.imwrite(
        processed_path,
        thresh
    )

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
                date_str,
                pattern
            )

            dt = dt.replace(year=2024)

            return dt.strftime(
                "%d/%m/%Y"
            )

        except:
            pass

    return date_str


# =====================================
# AMOUNT
# =====================================

def normalize_amount(amount_str):

    amount_str = amount_str.replace(
        ",",
        ""
    )

    amount_str = amount_str.strip()

    number_match = re.search(
        r'([0-9]+\.[0-9]{2})',
        amount_str
    )

    if not number_match:
        return ""

    value = number_match.group(1)

    if "DR" in amount_str.upper():
        return f"-{value}"

    return value


# =====================================
# PARSER
# =====================================

def extract_transactions(text):

    transactions = []

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
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

        description = re.sub(
            r'\s+',
            ' ',
            description
        ).strip()

        transactions.append({
            "Date": normalize_date(raw_date),
            "Description": description,
            "Amount": normalize_amount(raw_amount)
        })

    return transactions


# =====================================
# UPLOAD
# =====================================

uploaded_files = st.file_uploader(
    "Upload PDF Statements",
    type=["pdf"],
    accept_multiple_files=True
)


# =====================================
# PROCESS
# =====================================

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
                dpi=300
            )

            full_text = ""

            for idx, image in enumerate(images):

                image_path = f"temp_{idx}.jpg"

                image.save(
                    image_path,
                    "JPEG"
                )

                processed_path = preprocess_image(
                    image_path
                )

                extracted_text = pytesseract.image_to_string(
                    Image.open(processed_path),
                    config='--psm 6'
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
                str(e)
            )

        finally:

            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        progress_bar.progress(
            (file_index + 1) / total_files
        )

    if len(all_transactions) == 0:

        st.warning(
            "No transactions found"
        )

    else:

        df = pd.DataFrame(
            all_transactions
        )

        st.success(
            f"Found {len(df)} transactions"
        )

        st.dataframe(df)

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="transactions.csv",
            mime="text/csv"
        )
