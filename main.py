import csv
import io
from fastapi.responses import StreamingResponse
import os
import uvicorn
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel 

# Imports
from logic import extract_text_from_pdf, analyze_with_ai
from tax_rules import calculate_tax, suggest_savings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from logic import get_itr_recommendation # Import update karna mat bhulna

load_dotenv()

app = FastAPI(title="TaxAI Professional 2025")

# --- Global Variable to store PDF Data (Temporary Memory) ---
# Note: Real app mein Database use karein, ye prototype ke liye hai.
user_data_store = {"analysis": "No PDF uploaded yet."}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schema for Chat (To fix 422 Error) ---
class ChatRequest(BaseModel):
    query: str
class ITRHelpRequest(BaseModel):
    history: str
class ManualEntryRequest(BaseModel):
    description: str
    amount: float
    category: str  # values: 'income', '80c', '80d', 'expense'

# Aur ye endpoint
@app.post("/recommend-itr")
async def recommend_itr(request: ITRHelpRequest):
    try:
        from logic import get_itr_recommendation
        reply = get_itr_recommendation(request.history)
        return {"reply": reply}
    except Exception as e:
        return {"reply": "Sorry, could not process request."}


@app.get("/")
async def serve_frontend():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"error": "index.html not found"})



@app.post("/chat-with-ca")
async def chat(request: ChatRequest):
    """
    Chatbot jo ab PDF Data bhi janta hai.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"bot_reply": "⚠️ Error: API Key missing in .env"}

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key=api_key
        )

        # Context ko string mein convert karein
        context_data = str(user_data_store["analysis"])

        system_instruction = f"""
        You are an expert CA. Answer based on Indian Tax Laws (FY 2024-25).
        
        USER'S UPLOADED FINANCIAL DATA: 
        {context_data}

        INSTRUCTIONS:
        1. If the user asks about their income/tax, use the DATA provided above.
        2. If data is 'No PDF uploaded yet', tell them to upload a statement first.
        3. Keep answers short and professional.
        """

        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=request.query)
        ]

        response = llm.invoke(messages)
        
        # Ensure we always return 'bot_reply' key
        return {"bot_reply": response.content}

    except Exception as e:
        print(f"Chat Error: {e}")
        return {"bot_reply": f"⚠️ Technical Error: {str(e)}"}
    
# main.py ke imports mein 'json' jodein
import json 

# --- COMBINED ANALYSIS ENDPOINT ---
@app.post("/analyze-combined")
async def analyze_combined(
    file: UploadFile = File(None),        # File Optional hai
    manual_entries: str = Form("[]")      # JSON String aayega list ka
):
    try:
        # 1. Initialize Base Data
        ai_data = {
            "total_income": 0.0, "investments_80c": 0.0, 
            "medical_80d": 0.0, "expenses": 0.0, "raw_transactions": []
        }

        # 2. Process PDF (If uploaded)
        if file:
            content = await file.read()
            text = extract_text_from_pdf(content)
            extracted_data = analyze_with_ai(text)
            
            if "error" not in extracted_data:
                ai_data = extracted_data
                # AI ke transactions me flag laga do
                for t in ai_data.get("raw_transactions", []):
                    t["is_manual"] = False

        # 3. Process Manual Entries (from JSON string)
        manual_list = json.loads(manual_entries) # String to List convert
        
        for entry in manual_list:
            amt = float(entry.get("amount", 0))
            cat = entry.get("category", "")
            
            # Update Totals
            if cat == "income":
                ai_data["total_income"] = ai_data.get("total_income", 0) + amt
            elif cat == "80c":
                ai_data["investments_80c"] = ai_data.get("investments_80c", 0) + amt
                ai_data["expenses"] = ai_data.get("expenses", 0) + amt
            elif cat == "80d":
                ai_data["medical_80d"] = ai_data.get("medical_80d", 0) + amt
                ai_data["expenses"] = ai_data.get("expenses", 0) + amt
            elif cat == "expense":
                ai_data["expenses"] = ai_data.get("expenses", 0) + amt
            
            # Add to Transactions List
            new_txn = {
                "description": f"(Manual) {entry.get('description')}",
                "amount": amt,
                "type": "Credit" if cat == "income" else "Debit",
                "category": f"Manual-{cat.upper()}",
                "is_manual": True
            }
            # List ke upar add karein
            if "raw_transactions" not in ai_data: ai_data["raw_transactions"] = []
            ai_data["raw_transactions"].insert(0, new_txn)

        # 4. Save to Memory (For Chatbot)
        user_data_store["analysis"] = ai_data

        # 5. Calculate Tax
        income = float(ai_data.get('total_income', 0))
        inv_80c = float(ai_data.get('investments_80c', 0))
        med_80d = float(ai_data.get('medical_80d', 0))
        
        tax_new = calculate_tax(income, regime="new")
        tax_old = calculate_tax(income, investments_80c=inv_80c, medical_80d=med_80d, regime="old")
        
        advice = suggest_savings(ai_data)
        diff = abs(tax_new - tax_old)
        rec = "New Regime" if tax_new < tax_old else "Old Regime"
        advice.insert(0, f"✅ **Recommendation:** Choose **{rec}**. Save ₹{diff:,.0f}")

        return {
            "analysis": ai_data,
            "estimated_tax": {"new_regime": tax_new, "old_regime": tax_old},
            "ca_suggestions": advice
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# main.py ke end mein download_report function replace karein

@app.get("/download-report")
async def download_report():
    """
    Generates a CSV report (Lightweight alternative to Excel).
    """
    if "analysis" not in user_data_store or user_data_store["analysis"] == "No PDF uploaded yet.":
        return JSONResponse(status_code=400, content={"error": "No data available."})

    data = user_data_store["analysis"]
    
    # Calculate Data
    income = float(data.get('total_income', 0))
    inv_80c = float(data.get('investments_80c', 0))
    med_80d = float(data.get('medical_80d', 0))
    expenses = float(data.get('expenses', 0))

    tax_new = calculate_tax(income, regime="new")
    tax_old = calculate_tax(income, investments_80c=inv_80c, medical_80d=med_80d, regime="old")
    
    rec = "New Regime" if tax_new < tax_old else "Old Regime"
    
    # --- CSV GENERATION ---
    output = io.StringIO()
    writer = csv.writer(output)

    # Section 1: Summary
    writer.writerow(["--- TAX SUMMARY REPORT ---"])
    writer.writerow(["Total Income", income])
    writer.writerow(["Total Expenses", expenses])
    writer.writerow(["Investments (80C)", inv_80c])
    writer.writerow(["Medical (80D)", med_80d])
    writer.writerow([]) # Empty Line
    writer.writerow(["--- TAX CALCULATION ---"])
    writer.writerow(["New Regime Tax", tax_new])
    writer.writerow(["Old Regime Tax", tax_old])
    writer.writerow(["Recommendation", rec])
    writer.writerow([])

    # Section 2: Suggestions
    writer.writerow(["--- CA SUGGESTIONS ---"])
    suggestions = suggest_savings(data)
    for s in suggestions:
        writer.writerow([s])
    writer.writerow([])

    # Section 3: Transactions
    writer.writerow(["--- DETAILED TRANSACTIONS ---"])
    writer.writerow(["Description", "Category", "Amount", "Type"])
    
    raw_txns = data.get("raw_transactions", [])
    for t in raw_txns:
        writer.writerow([
            t.get("description", ""),
            t.get("category", ""),
            t.get("amount", 0),
            t.get("type", "")
        ])

    # Return CSV File
    output.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename="TaxAI_Report.csv"'
    }
    return StreamingResponse(
        iter([output.getvalue()]), 
        headers=headers, 
        media_type='text/csv'
    )



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
