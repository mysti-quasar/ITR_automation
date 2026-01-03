import random
from datetime import datetime, timedelta
from fpdf import FPDF

# --- Configuration ---
FILE_NAME = "Indian_Bank_Statement.pdf"
ACCOUNT_HOLDER = "VIKRAM SINGH RATHORE"
ACCOUNT_NO = "XXXXXX8892"
IFSC_CODE = "HDFC0001234"
BRANCH_NAME = "CONNAUGHT PLACE, NEW DELHI"
CURRENCY = "INR"

# --- PDF Class Definition ---
class BankStatementPDF(FPDF):
    def header(self):
        # Bank Logo/Name Placeholder
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'HDFC BANK', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'We understand your world', 0, 1, 'L')
        self.ln(5)
        
        # Statement Title
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'ACCOUNT STATEMENT', 0, 1, 'C')
        self.ln(5)
        
        # Draw a line
        self.line(10, 35, 200, 35)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- Helper to Format Currency (Indian Format) ---
def format_currency(amount):
    """Formats number to Indian currency style (e.g., 1,50,000.00)"""
    s = "{:.2f}".format(amount)
    parts = s.split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    
    last_three = integer_part[-3:]
    rest = integer_part[:-3]
    
    if rest:
        # Complex logic to add commas every 2 digits for Indian style
        rest = rest[::-1]
        rest = ",".join(rest[i:i+2] for i in range(0, len(rest), 2))
        rest = rest[::-1]
        return f"{rest},{last_three}.{decimal_part}"
    else:
        return f"{integer_part}.{decimal_part}"

# --- Data Generation Logic ---
def generate_transactions(num_transactions=40):
    transactions = []
    # Start with a big opening balance (e.g., 5 Crores)
    balance = 5_00_00_000.00 
    
    start_date = datetime.now() - timedelta(days=num_transactions)
    
    descriptions = [
        "RTGS/DLF BUILDERS/PAYMENT",
        "NEFT/ZOMATO MEDIA/REFUND",
        "IMPS/RAHUL SHARMA/TRANSFER",
        "ACH/SIP/ZERODHA BROKING",
        "SALARY/CREDIT/TCS LTD",
        "DIVIDEND/RELIANCE INDUSTRIES",
        "UPI/SWIGGY/FOOD",
        "POS/APPLE INDIA/STORE",
        "CHEQUE DEPOSIT/CLEARING",
        "INT PAYMENT/HOME LOAN"
    ]

    # Add Opening Balance Row
    transactions.append({
        "date": start_date.strftime("%d-%m-%Y"),
        "desc": "OPENING BALANCE",
        "ref": "-",
        "debit": "",
        "credit": "",
        "balance": balance
    })

    for i in range(num_transactions):
        date = start_date + timedelta(days=i)
        desc = random.choice(descriptions)
        
        # Logic to ensure amounts are in Lakhs and balance stays high (Crores)
        if "SALARY" in desc or "DIVIDEND" in desc or "DEPOSIT" in desc:
            type = "CREDIT"
            amount = random.uniform(5_00_000, 50_00_000) # 5 Lakhs to 50 Lakhs Income
        else:
            type = "DEBIT"
            amount = random.uniform(1_00_000, 20_00_000) # 1 Lakh to 20 Lakhs Expense
            
        ref_no = f"REF{random.randint(100000, 999999)}"
        
        if type == "CREDIT":
            balance += amount
            debit_str = ""
            credit_str = format_currency(amount)
        else:
            balance -= amount
            debit_str = format_currency(amount)
            credit_str = ""

        transactions.append({
            "date": date.strftime("%d-%m-%Y"),
            "desc": desc,
            "ref": ref_no,
            "debit": debit_str,
            "credit": credit_str,
            "balance": balance
        })

    return transactions

# --- Generate PDF ---
def create_bank_statement():
    pdf = BankStatementPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Customer Details
    pdf.set_font('Arial', '', 10)
    pdf.cell(100, 5, f"Name: {ACCOUNT_HOLDER}", 0, 0)
    pdf.cell(0, 5, f"Account No: {ACCOUNT_NO}", 0, 1)
    
    pdf.cell(100, 5, f"Branch: {BRANCH_NAME}", 0, 0)
    pdf.cell(0, 5, f"IFSC Code: {IFSC_CODE}", 0, 1)
    
    pdf.cell(100, 5, f"Currency: {CURRENCY}", 0, 0)
    pdf.cell(0, 5, f"Statement Date: {datetime.now().strftime('%d-%m-%Y')}", 0, 1)
    pdf.ln(10)
    
    # --- Table Header ---
    pdf.set_fill_color(220, 230, 240) # Light Gray/Blue
    pdf.set_font('Arial', 'B', 9)
    
    # Column Widths
    col_w = [25, 65, 30, 25, 25, 25] 
    headers = ["Date", "Description", "Ref No.", "Debit", "Credit", "Balance"]
    
    for i in range(len(headers)):
        pdf.cell(col_w[i], 8, headers[i], 1, 0, 'C', True)
    pdf.ln()
    
    # --- Table Rows ---
    pdf.set_font('Arial', '', 8)
    transactions = generate_transactions(num_transactions=40)
    
    for txn in transactions:
        # Check for page break
        if pdf.get_y() > 270:
            pdf.add_page()
            # Reprint Header
            pdf.set_font('Arial', 'B', 9)
            for i in range(len(headers)):
                pdf.cell(col_w[i], 8, headers[i], 1, 0, 'C', True)
            pdf.ln()
            pdf.set_font('Arial', '', 8)

        pdf.cell(col_w[0], 7, txn['date'], 1)
        pdf.cell(col_w[1], 7, txn['desc'], 1)
        pdf.cell(col_w[2], 7, txn['ref'], 1)
        
        # Align Numbers to Right
        pdf.cell(col_w[3], 7, txn['debit'], 1, 0, 'R')
        pdf.cell(col_w[4], 7, txn['credit'], 1, 0, 'R')
        
        # Format Balance correctly
        bal_str = format_currency(txn['balance'])
        pdf.cell(col_w[5], 7, bal_str, 1, 0, 'R')
        pdf.ln()

    # Save File
    pdf.output(FILE_NAME)
    print(f"✅ Generated PDF: {FILE_NAME}")

if __name__ == "__main__":
    create_bank_statement()