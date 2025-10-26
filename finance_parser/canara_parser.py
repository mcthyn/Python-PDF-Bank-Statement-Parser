import re
import pandas as pd
import pdfplumber



def extract_pdf_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        text_string = ""
        for page in pdf.pages:
            text_string += page.extract_text_simple()

    return text_string.replace("\n", "")



def extract_transactions(text: str) -> list:
    pattern = re.compile(
        r"(?P<type>UPI/(?:DR|CR))/(?P<txn_id>[^/]+)"                    # UPI/DR/xxxx
        r"/(?P<party>[A-Za-z0-9\s]+)"                                   # Party name
        r".{0,30}?"                                                     # tolerate small junk
        r"(?P<bank_code>[A-Z]{4})"                                      # Bank code like SBIN, YESB
        r"/(?P<upi_id>[\w*\-]+@[\w]+)"                                  # UPI ID like abc@okaxis
        r".*?"                                                          # skip filler till date
        r"(?P<date>\d{2}-\d{2}-\d{4}).*?"                               # DD-MM-YYYY
        r"(?P<amount>[\d,]+\.\d{2})\s+"                                 # 100.00
        r"(?P<balance>[\d,]+\.\d{2}).*?"                                # 10,000.00
        r"(?P<time>\d{2}:\d{2}:\d{2}).*?"                               # HH:MM:SS
        r"Chq\s*:\s*(?P<cheque>[0-9]+)",                                # Chq: 5658XXXXX8817
        re.DOTALL | re.IGNORECASE
    )

    transactions = [m.groupdict() for m in pattern.finditer(text)]
    return transactions



def to_structured_df(transactions) -> pd.DataFrame:
    df = pd.DataFrame(transactions)

    df['party'] = df['party'].str.replace("\n", "")

    df[["transaction", "type"]] = df['type'].str.split("/", expand=True)
    col = df.pop("transaction")
    df.insert(0, "transaction", col)

    df_reordered = df.reindex(columns=[
        'date', 'time', 'transaction', 'type', 'txn_id',
        'party', 'bank_code', 'upi_id', 'amount', 'balance', 'cheque'
    ])

    return df_reordered



def canara_parser(pdf_path: str) -> pd.DataFrame:
    text = extract_pdf_text(pdf_path)
    transactions = extract_transactions(text)
    return to_structured_df(transactions)


