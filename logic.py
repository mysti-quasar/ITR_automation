# logic.py
import os
import pypdf
from dotenv import load_dotenv
from typing import List

# --- Imports ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# 1. Load Environment
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# --- 2. Schemas ---
class TransactionItem(BaseModel):
    description: str = Field(description="Description of transaction e.g., 'UPI Zomato', 'Salary'")
    amount: float = Field(description="Transaction amount in number")
    type: str = Field(description="Type: 'Credit' (Income) or 'Debit' (Expense)")
    category: str = Field(description="Category: 'Salary', 'Business', '80C', 'Health Insurance', 'Rent', 'Other'")

class StatementData(BaseModel):
    transactions: List[TransactionItem] = Field(description="List of all extracted transactions")

# --- 3. Calculation Logic (Python Side) ---
def calculate_from_list(transactions: List[dict]):
    totals = {
        "total_income": 0.0,
        "investments_80c": 0.0,
        "medical_80d": 0.0,
        "expenses": 0.0
    }
    
    # Safety Check
    if not transactions:
        return totals

    for t in transactions:
        try:
            if not isinstance(t, dict):
                continue

            amt = float(t.get('amount', 0))
            typ = t.get('type', '').lower()
            cat = t.get('category', '').lower()
            
            if 'credit' in typ:
                totals['total_income'] += amt
            elif 'debit' in typ:
                totals['expenses'] += amt
                
                if '80c' in cat or 'lic' in cat or 'ppf' in cat:
                    totals['investments_80c'] += amt
                elif 'health' in cat or 'medic' in cat:
                    totals['medical_80d'] += amt
        except:
            continue
            
    return {k: round(v, 2) for k, v in totals.items()}

# --- 4. PDF Logic ---
def extract_text_from_pdf(file_bytes):
    temp_filename = "temp_statement.pdf"
    try:
        with open(temp_filename, "wb") as f:
            f.write(file_bytes)
        text = ""
        with pdfplumber.open(temp_filename) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted: text += extracted + "\n"
        if os.path.exists(temp_filename): os.remove(temp_filename)
        return text
    except Exception as e:
        print(f"❌ PDF Error: {e}")
        return ""

# --- 5. Main Analysis ---
def analyze_with_ai(text_data):
    if not api_key:
        return {"total_income": 0, "error": "API Key Missing"}

    if not text_data or len(text_data.strip()) < 50:
        return {"total_income": 0, "error": "Empty PDF"}

    try:
        # Using gemini-2.5-flash because 2.5 causes 404 errors currently
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=api_key,
            temperature=0
        )

        parser = JsonOutputParser(pydantic_object=StatementData)

        prompt = PromptTemplate(
            template="""
            You are an expert Chartered Accountant. Analyze this bank statement text.
            
            Task:
            1. Extract every transaction into a list.
            2. Categorize strictly as: 'Salary', 'Business', '80C', 'Health Insurance', 'Rent', 'Other'.
            3. Do NOT sum up totals. Just list the items.
            
            Bank Statement:
            {text_data}
            
            Format Instructions:
            {format_instructions}
            """,
            input_variables=["text_data"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        chain = prompt | llm | parser

        print("🦜🔗 LangChain processing list...")
        
        result = chain.invoke({"text_data": text_data[:30000]})
        
        # FIX FOR LIST/DICT
        raw_list = []
        if isinstance(result, list):
            raw_list = result
        elif isinstance(result, dict):
            raw_list = result.get("transactions", [])
        
        # Calculate using Python
        final_calculated_data = calculate_from_list(raw_list)
        
        return final_calculated_data

    except Exception as e:
        print(f"❌ LangChain Error: {e}")
        return {
            "total_income": 0, "investments_80c": 0, 
            "medical_80d": 0, "expenses": 0, 
            "error": str(e)
        }

# --- 6. ITR Recommendation (Updated for ITR 1-7) ---
def get_itr_recommendation(user_profile_text):
    """
    Hybrid ITR Recommender (Ticks + Text) for ITR 1 to 7
    """
    if not api_key:
        return "API Key Missing."

    try:
        # Use Stable Model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=api_key,
            temperature=0
        )

        prompt = f"""
        Act as a Senior Indian Tax Expert (FY 2025-26).
        Analyze the user's financial profile based on their selection and notes.
        Suggest the BEST ITR Form (ITR-1 to ITR-7).

        USER INPUT:
        {user_profile_text}

        LOGIC RULES (Strictly Follow):
        1. **ITR-1 (Sahaj):** Resident Individual, Total Income <= 50L, Salary/Pension/One House/Interest. (NOT for Director, Unlisted Shares, Business, Capital Gains).
        2. **ITR-2:** Individual/HUF, Capital Gains (Stocks), Foreign Assets, Income > 50L, Director, Unlisted Shares. (NO Business Income).
        3. **ITR-3:** Individual/HUF having Business/Profession Income (Intraday, F&O, Doctor, CA) NOT opting for presumptive scheme.
        4. **ITR-4 (Sugam):** Individual/HUF/Firm (excluding LLP) with Presumptive Business (Sec 44AD/ADA) & Income <= 50L.
        5. **ITR-5:** For Firms, LLPs, AOPs, BOIs (Entities that are NOT Individual/HUF/Company).
        6. **ITR-6:** For Companies (Private Ltd, Public Ltd) not claiming exemption u/s 11.
        7. **ITR-7:** For Persons/Companies under section 139(4A/4B/4C/4D) - Trusts, Political Parties, NGOs, Colleges claiming exemptions.

        OUTPUT FORMAT:
        "**[ITR Form Name]** - [Short Reason]"
        Example: "**ITR-2** - Because you have Capital Gains from Stocks."
        If multiple apply (e.g. Business + Salary), prioritize the higher form (ITR-3 covers Salary too).
        Keep it concise.
        """
        
        response = llm.invoke(prompt)
        return response.content

    except Exception as e:
        return f"Error: {str(e)}"
