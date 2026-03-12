import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="MBA Tax Optimizer", layout="wide")

# -----------------------------
# TAX RULES (EDIT WHEN NEEDED)
# -----------------------------

STANDARD_DEDUCTION = 50000
LIMIT_80C = 150000
LIMIT_NPS = 50000
CESS = 0.04


OLD_SLABS = [
    (250000,0),
    (500000,0.05),
    (1000000,0.20),
    (999999999,0.30)
]


NEW_SLABS = [
    (300000,0),
    (600000,0.05),
    (900000,0.10),
    (1200000,0.15),
    (1500000,0.20),
    (999999999,0.30)
]

# -----------------------------
# TAX FUNCTION
# -----------------------------

def calculate_tax(income, slabs):

    tax=0
    prev=0

    for limit,rate in slabs:

        if income>limit:
            tax+=(limit-prev)*rate
            prev=limit

        else:
            tax+=(income-prev)*rate
            break

    tax=tax*(1+CESS)

    return int(tax)


# -----------------------------
# HRA CALCULATION
# -----------------------------

def hra_exemption(hra,basic,rent,metro):

    if metro:
        limit=0.5*basic
    else:
        limit=0.4*basic

    rent_cond=rent-0.1*basic

    return max(0,min(hra,limit,rent_cond))


# -----------------------------
# UI
# -----------------------------

st.title("MBA Salary Tax Optimizer")

st.write(
"""
Compare **Old vs New tax regimes**  
and simulate **salary restructuring strategies**.
"""
)

col1,col2=st.columns([2,3])

# --------------------------------
# SECTION 1 COMPENSATION
# --------------------------------

with col1:

    st.header("Compensation")

    fixed_salary=st.number_input("Fixed Salary",value=2000000)

    joining_bonus=st.number_input("Joining Bonus",value=0)

    relocation_bonus=st.number_input("Relocation Bonus",value=0)

    performance_bonus=st.number_input("Annual Incentive / Bonus",value=0)

    gross_income=(
        fixed_salary
        +joining_bonus
        +relocation_bonus
        +performance_bonus
    )

    st.success(f"Gross Income = ₹{gross_income:,}")


# --------------------------------
# SALARY BREAKDOWN
# --------------------------------

with col1:

    st.header("Salary Breakdown")

    basic=st.number_input("Basic Salary",value=800000)

    hra=st.number_input("HRA Received",value=300000)

    special_allowance=st.number_input("Special Allowance",value=400000)

    employer_pf=st.number_input("Employer PF",value=0)

    employer_nps=st.number_input("Employer NPS",value=0)

    gratuity=st.number_input("Gratuity",value=0)


# --------------------------------
# ALLOWANCES
# --------------------------------

with col1:

    st.header("Allowances / Reimbursements")

    rent=st.number_input("Annual Rent Paid",value=240000)

    metro=st.checkbox("Metro City")

    internet=st.number_input("Internet Reimbursement",value=0)

    phone=st.number_input("Phone Reimbursement",value=0)

    conveyance=st.number_input("Conveyance",value=0)

    meal=st.number_input("Meal Vouchers",value=0)

    lta=st.number_input("LTA Claimed",value=0)

# --------------------------------
# DEDUCTIONS
# --------------------------------

with col2:

    st.header("Deductions")

    st.subheader("80C Investments")

    st.write(
    """
    Examples of 80C investments:

    EPF  
    PPF  
    ELSS mutual funds  
    Life insurance  
    Home loan principal
    """
    )

    invest_80c=st.number_input("Total 80C Investments",value=150000)

    nps=st.number_input("NPS Contribution (80CCD1B)",value=50000)

    health=st.number_input("Health Insurance (80D)",value=25000)

    edu_loan=st.number_input("Education Loan Interest (80E)",value=0)

    home_interest=st.number_input("Home Loan Interest",value=0)


# --------------------------------
# RUN ANALYSIS
# --------------------------------

if st.button("Run Analysis"):

    hra_exempt=hra_exemption(hra,basic,rent,metro)

    reimbursements=internet+phone+conveyance+meal

    exemptions_old=hra_exempt+reimbursements+lta


    deductions_old=(
        STANDARD_DEDUCTION
        +min(invest_80c,LIMIT_80C)
        +min(nps,LIMIT_NPS)
        +health
        +edu_loan
        +home_interest
    )


    taxable_old=gross_income-exemptions_old-deductions_old

    tax_old=calculate_tax(taxable_old,OLD_SLABS)


# ---------------------------
# NEW REGIME FIX
# ---------------------------

    taxable_new=gross_income-STANDARD_DEDUCTION

    tax_new=calculate_tax(taxable_new,NEW_SLABS)


# --------------------------------
# TABLE OUTPUT
# --------------------------------

    df=pd.DataFrame({

        "Component":[
        "Gross Income",
        "Exemptions (Old only)",
        "Deductions",
        "Taxable Income",
        "Estimated Tax"
        ],

        "Old Regime":[
        gross_income,
        exemptions_old,
        deductions_old,
        taxable_old,
        tax_old
        ],

        "New Regime":[
        gross_income,
        0,
        STANDARD_DEDUCTION,
        taxable_new,
        tax_new
        ]

    })

    st.subheader("Side-by-side: Old vs New Regime")

    st.table(df)


# --------------------------------
# RECOMMENDATION
# --------------------------------

    if tax_old<tax_new:

        st.success(f"Old Regime Recommended — Save ₹{tax_new-tax_old:,}")

    else:

        st.success(f"New Regime Recommended — Save ₹{tax_old-tax_new:,}")


# --------------------------------
# MISSED DEDUCTIONS
# --------------------------------

    st.subheader("Missed Deduction Opportunities")

    if invest_80c<LIMIT_80C:

        st.write(
        f"Invest ₹{LIMIT_80C-invest_80c:,} more under 80C."
        )

    if nps<LIMIT_NPS:

        st.write(
        f"Invest ₹{LIMIT_NPS-nps:,} more in NPS."
        )

    if edu_loan>0:

        st.write("Education loan interest fully deductible under 80E.")


# --------------------------------
# OPTIMIZATION SIMULATOR
# --------------------------------

    st.subheader("Salary Optimization Simulator")

    move_hra=st.slider(
        "Move Special Allowance → HRA",
        0,
        int(special_allowance),
        0
    )

    convert_reimb=st.slider(
        "Convert Allowance → Reimbursements",
        0,
        int(special_allowance),
        0
    )

    invest_more_80c=st.slider(
        "Increase 80C Investment",
        0,
        LIMIT_80C,
        0
    )

    invest_more_nps=st.slider(
        "Increase NPS",
        0,
        LIMIT_NPS,
        0
    )


    new_hra=hra+move_hra

    new_special=special_allowance-move_hra-convert_reimb

    hra_new=hra_exemption(new_hra,basic,rent,metro)


    exemptions_sim=hra_new+reimbursements+lta+convert_reimb

    deductions_sim=(
        STANDARD_DEDUCTION
        +min(invest_80c+invest_more_80c,LIMIT_80C)
        +min(nps+invest_more_nps,LIMIT_NPS)
        +health
        +edu_loan
        +home_interest
    )


    taxable_sim=gross_income-exemptions_sim-deductions_sim

    tax_sim=calculate_tax(taxable_sim,OLD_SLABS)

    savings=tax_old-tax_sim


    st.write(f"Optimized Tax = ₹{tax_sim:,}")

    st.success(f"Potential Savings = ₹{savings:,}")
