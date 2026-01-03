# tax_rules.py
"""
Indian Income Tax Rules Implementation for FY 2025-26 (AY 2026-27).
Compliant with Union Budget February 2025.
"""

def calculate_tax(
    gross_income: float, 
    age: int = 30,
    investments_80c: float = 0, 
    medical_80d: float = 0, 
    housing_loan_interest: float = 0, 
    nps_80ccd_1b: float = 0,          
    savings_interest: float = 0,      
    regime: str = "new"
):
    """
    Calculates final tax liability including Surcharge and Cess.
    Returns: int (rounded final tax amount)
    """
    tax = 0
    taxable_income = 0
    
    # --- NEW REGIME (u/s 115BAC) - FY 2025-26 ---
    if regime == "new":
        # Standard Deduction ₹75,000 (unchanged from Budget 2024)
        std_deduction = 75000
        
        # New Regime allows very few deductions (Only Std Ded)
        taxable_income = max(0, gross_income - std_deduction)
        
        # New Tax Slabs (Budget 2025) - Updated slabs
        slab_income = taxable_income
        
        if slab_income <= 400000:
            tax = 0
        elif slab_income <= 800000:
            tax = (slab_income - 400000) * 0.05
        elif slab_income <= 1200000:
            tax = 20000 + (slab_income - 800000) * 0.10
        elif slab_income <= 1600000:
            tax = 20000 + 40000 + (slab_income - 1200000) * 0.15
        elif slab_income <= 2000000:
            tax = 20000 + 40000 + 60000 + (slab_income - 1600000) * 0.20
        elif slab_income <= 2400000:
            tax = 20000 + 40000 + 60000 + 80000 + (slab_income - 2000000) * 0.25
        else:
            tax = 20000 + 40000 + 60000 + 80000 + 100000 + (slab_income - 2400000) * 0.30

        # Rebate u/s 87A (New Regime) - Tax NIL if income <= 12L (Budget 2025)
        if taxable_income <= 1200000:
            tax = 0
        else:
            # Marginal Relief Logic (Simplified)
            if taxable_income <= 1275000:
                tax = min(tax, taxable_income - 1200000)

    # --- OLD REGIME ---
    elif regime == "old":
        std_deduction = 50000
        
        # Deductions
        deduction_80c = min(investments_80c, 150000)
        deduction_80d = min(medical_80d, 50000 if age >= 60 else 25000)
        deduction_nps = min(nps_80ccd_1b, 50000)
        deduction_home_loan = min(housing_loan_interest, 200000)
        limit_savings = 50000 if age >= 60 else 10000
        deduction_savings = min(savings_interest, limit_savings)
        
        total_deductions = (std_deduction + deduction_80c + deduction_80d + 
                            deduction_nps + deduction_home_loan + deduction_savings)
                            
        taxable_income = max(0, gross_income - total_deductions)
        
        # Old Regime Slabs based on Age (unchanged)
        basic_exemption = 250000
        if age >= 80: 
            basic_exemption = 500000
        elif age >= 60: 
            basic_exemption = 300000
            
        slab_income = taxable_income
        
        if slab_income <= basic_exemption:
            tax = 0
        elif slab_income <= 500000:
            tax = (slab_income - basic_exemption) * 0.05
        elif slab_income <= 1000000:
            tax = (500000 - basic_exemption) * 0.05 + (slab_income - 500000) * 0.20
        else:
            tax = (500000 - basic_exemption) * 0.05 + 100000 + (slab_income - 1000000) * 0.30

        # Rebate u/s 87A (Old Regime) - Tax NIL if income <= 5L
        if taxable_income <= 500000:
            tax = 0

    # --- SURCHARGE (Income > 50L) ---
    surcharge_rate = 0
    if taxable_income > 5000000:
        if taxable_income <= 10000000: 
            surcharge_rate = 0.10
        elif taxable_income <= 20000000: 
            surcharge_rate = 0.15
        elif regime == "new" or taxable_income <= 50000000:
            surcharge_rate = 0.25  # Capped at 25% for new regime
        else:
            surcharge_rate = 0.37  # Old regime above 5Cr
    
    surcharge = tax * surcharge_rate
    total_tax = tax + surcharge

    # --- CESS (4%) ---
    cess = total_tax * 0.04
    
    return round(total_tax + cess)


def suggest_savings(data):
    """
    Suggest tax-saving strategies based on extracted data.
    Returns: list of strings
    """
    suggestions = []
    income = data.get('total_income', 0)
    age = data.get('age', 30)
    inv_80c = data.get('investments_80c', 0)
    med_80d = data.get('medical_80d', 0)
    regime = data.get('regime', 'new')
    
    # Calculate tax in current regime
    current_tax = calculate_tax(
        gross_income=income,
        age=age,
        investments_80c=inv_80c if regime == 'old' else 0,
        medical_80d=med_80d if regime == 'old' else 0,
        regime=regime
    )
    
    # Calculate tax in other regime
    other_regime = 'old' if regime == 'new' else 'new'
    other_tax = calculate_tax(
        gross_income=income,
        age=age,
        investments_80c=inv_80c if other_regime == 'old' else 0,
        medical_80d=med_80d if other_regime == 'old' else 0,
        regime=other_regime
    )
    
    # Regime comparison
    if other_tax < current_tax:
        savings = current_tax - other_tax
        suggestions.append(f"💡 **Switch to {other_regime.upper()} Regime** to save ₹{savings:,}!")
    
    # Old Regime specific suggestions
    if regime == 'old':
        if inv_80c < 150000:
            gap = 150000 - inv_80c
            suggestions.append(f"📌 **80C:** Invest ₹{gap:,} more in ELSS/PPF/EPF to max out deduction.")
        
        if med_80d == 0:
            suggestions.append("📌 **Health Insurance (80D):** No premium found. Buy insurance to save up to ₹25k.")
        elif med_80d < 25000:
            gap = 25000 - med_80d
            suggestions.append(f"📌 **80D:** Increase health insurance by ₹{gap:,} to max out benefit.")
    
    # New Regime insights
    if regime == 'new':
        taxable = max(0, income - 75000)
        if taxable > 1200000 and taxable <= 1300000:
            suggestions.append("⚠️ **Just above ₹12L limit:** Consider salary restructuring to reduce taxable income.")
    
    # General insights
    if income > 1500000:
        suggestions.append("💡 **High Income (>15L):** New Regime usually better unless deductions > ₹3.75L.")
    
    if not suggestions:
        suggestions.append("✅ You're already optimized! Keep up the good tax planning.")
    
    return suggestions