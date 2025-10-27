import re
import pandas as pd
import pdfplumber



def clean_text(text: str) -> str:
    return re.sub(
        r'Page\s*\d+\s*Date\s+Particulars\s+Deposits\s+Withdrawals\s+Balance',
        '',
        text,
        flags=re.IGNORECASE
    )



def extract_transaction_blocks(pdf_path: str) -> list:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)

    # Extract only the text between Opening Balance  and Closing Balance
    pattern = r'Opening Balance\s+[\d,]+\.\d+\s*(.*?)\s*Closing Balance\s+[\d,]+\.\d+'
    match = re.search(pattern, text, re.DOTALL)
    transaction_block = match.group(1).strip() if match else ""
    cleaned_transactions = clean_text(transaction_block)

    pattern = r'(Chq:\s*\d*)'
    parts = re.split(pattern, cleaned_transactions)

    # Capture the Chq: pattern in parentheses, then rejoin it into the previous chunk.
    transactions = []
    for i in range(0, len(parts) - 1, 2):
        before = parts[i].strip()
        chq = parts[i + 1].strip()
        transactions.append(f"{before} {chq}".strip())

    return transactions



def parse_transaction(block: str) -> dict:
    """
    Parse a Canara Bank transaction block into structured data.
    """

    # --- Extract date ---
    date_match = re.search(r'\b(\d{2}-\d{2}-\d{4})\b', block)
    date = date_match.group(1) if date_match else None

    # --- Extract cheque number ---
    chq_match = re.search(r'Chq:\s*(\S+)', block)
    cheque_no = chq_match.group(1) if chq_match else None

    # --- Extract balance (always last number) ---
    balance_match = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', block)
    balance = balance_match[-1] if balance_match else None

    # --- Extract amount ---
    if len(balance_match) >= 2:
        amount = balance_match[-2]

    # --- Extract transaction type ---
    txn_type_match = re.search(
        r'\b(UPI/DR|UPI/CR|NEFT CR|NEFT DR|SBINT|IMPS/CR|IMPS/DR|ATM/DR|POS/DR|INT/CR)\b',
        block
    )
    txn_type = txn_type_match.group(1) if txn_type_match else "UNKNOWN"

    # --- Extract time ---
    time_match = re.search(r'\d{2}:\d{2}:\d{2}', block)
    time = time_match.group(0) if time_match else None

    # --- Extract particulars (the messy middle) ---
    particulars = re.sub(
        r'\b\d{2}-\d{2}-\d{4}\b|Chq:\s*\S+|(\d{1,3}(?:,\d{3})*\.\d{2})',
        '',
        block
    ).strip()

    particulars = re.sub(r'\s+', ' ', particulars)  # normalize spaces

    # --- Extract Party name ---
    party = None
    if txn_type.startswith("UPI"):
        party = block.split("/")[3].replace("\n", "")

    elif txn_type.startswith("NEFT"):
        party = particulars.split("-")[-2]

    return {
        "date": date,
        "time": time,
        "txn_type": txn_type,
        "party": party,
        "particulars": particulars,
        "amount": amount,
        "balance": balance,
        "cheque_no": cheque_no,
    }



def to_table(transactions: list, save=False, output_path="output.csv") -> pd.DataFrame:
    df = pd.DataFrame(transactions)

    if save:
        df.to_csv(output_path)

    return df





transaction_blocks = extract_transaction_blocks("media/canara_statement.pdf")
transactions = [parse_transaction(block) for block in transaction_blocks]
transactions_df = to_table(transactions, save=True)
