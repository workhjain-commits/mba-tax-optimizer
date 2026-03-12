# app.py
# MBA Tax Optimizer — Added 80C breakup, employer PF field, and recommendations

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import date

st.set_page_config(page_title="MBA Tax Optimizer", layout="wide")

# -------------------------
# RULES
# -------------------------

RULES = {
    "fy": "2025-26",
    "standard_deduction": 50000,
    "80c_limit": 150000,
    "80ccd_1b_limit": 50000,
    "hra_metro_pct": 0.50,
    "hra_nonmetro_pct": 0.40,
    "cess_rate": 0.04,
    "tax_slabs_old": [
        {"upto":250000,"rate":0},
        {"upto":500000,"rate":0.05},
        {"upto":1000000,"rate":0.20},
        {"upto":999999999,"rate":0.30}
    ],
    "tax_slabs_new":[
        {"upto":300000,"rate":0},
        {"upto":600000,"rate":0.05},
        {"upto":900000,"rate":0.10},
        {"upto":1200000,"rate":0.15},
        {"upto":1500000,"rate":0.20},
        {"upto":999999999,"rate":0.30}
    ],
    "new_regime_allowed":{
        "standard_deduction":True,
        "80ccd_1b":True
    }
}

# -------------------------
# FUNCTIONS
# -------------------------

def compute_hra_exemption(basic,da,hra_received,rent_paid,is_metro):

    salary_for_hra=basic+da
    pct=RULES["hra_metro_pct"] if is_metro else RULES["hra_nonmetro_pct"]
    limit_pct=pct*salary_for_hra
    rent_minus_10pct=max(0,rent_paid-0.10*salary_for_hra)

    hra_exemption=min(hra_received,limit_pct,rent_minus_10pct)

    return round(max(0,hra_exemption),0)


def tax_from_slabs(taxable_income,slabs):

    tax=0
    previous=0

    for slab in slabs:

        upto=slab["upto"]
        rate=slab["rate"]

        if taxable_income<=previous:
            break

        taxable_here=min(taxable_income,upto)-previous

        if taxable_here>0:
            tax+=taxable_here*rate

        previous=upto

    tax=tax*(1+RULES["cess_rate"])

    return round(tax,0)


def compute_old_regime_tax(gross_income,exemptions_sum,deductions):

    taxable=gross_income-exemptions_sum

    taxable-=deductions.get("standard_deduction",0)
    taxable-=deductions.get("80c",0)
    taxable-=deductions.get("80ccd_1b",0)
    taxable-=deductions.get("80d",0)
    taxable-=deductions.get("80e",0)
    taxable-=deductions.get("home_loan_interest",0)

    taxable=max(0,round(taxable))

    tax=tax_from_slabs(taxable,RULES["tax_slabs_old"])

    return int(tax),int(taxable)


def compute_new_regime_tax(gross_income,allowed_deductions):

    taxable=gross_income

    if RULES["new_regime_allowed"]["standard_deduction"]:
        taxable-=allowed_deductions.get("standard_deduction",0)

    if RULES["new_regime_allowed"]["80ccd_1b"]:
        taxable-=allowed_deductions.get("80ccd_1b",0)

    taxable=max(0,round(taxable))

    tax=tax_from_slabs(taxable,RULES["tax_slabs_new"])

    return int(tax),int(taxable)


def estimate_marginal_rate_old(taxable_income):

    for slab in RULES["tax_slabs_old"]:
        if taxable_income<=slab["upto"]:
            return slab["rate"]

    return RULES["tax_slabs_old"][-1]["rate"]


def marginal_with_cess(taxable_income):

    base=estimate_marginal_rate_old(taxable_income)

    return base*(1+RULES["cess_rate"])


def money(x):
    return f"₹{int(x):,}"

# -------------------------
# UI
# -------------------------

st.title("MBA Tax Optimizer — Expanded Questionnaire")

st.caption(f"FY {RULES['fy']}")

col_left,col_right=st.columns([2,3])

with col_left:

    st.header("Section A — Compensation Structure")

    fixed_pay=st.number_input("Fixed Pay",value=1800000)

    joining_bonus=st.number_input("Joining Bonus",value=0)

    relocation_bonus=st.number_input("Relocation Bonus",value=0)

    performance_bonus=st.number_input("Annual Incentive / Performance Bonus",value=200000)

    gross_income=(
        fixed_pay
        +joining_bonus
        +relocation_bonus
        +performance_bonus
    )

    st.info(f"Calculated Gross Income = {money(gross_income)}")

    st.header("Section B — Accommodation")

    is_metro=st.radio("City Type",["Metro","Non-Metro"])=="Metro"

    lives_rented=st.radio("Live in rented house?",["Yes","No"])=="Yes"

    rent_annual=0

    if lives_rented:
        rent_annual=st.number_input("Annual Rent Paid",value=240000)

    st.header("Section C — Salary Breakdown")

    basic=st.number_input("Basic",value=720000)

    da=st.number_input("DA",value=0)

    hra=st.number_input("HRA",value=288000)

    special_allowance=st.number_input("Special Allowance",value=200000)

    employer_pf=st.number_input("Employer PF contribution",value=86400)

    st.header("Allowances")

    internet_allowance=st.number_input("Internet",value=0)

    phone_allowance=st.number_input("Phone",value=0)

    conveyance_allowance=st.number_input("Conveyance",value=0)

    meal_voucher=st.number_input("Meal Voucher",value=0)

    lta_claimed=st.number_input("LTA",value=0)

with col_right:

    st.header("Section D — 80C Breakup")

    epf=st.number_input("EPF (Employee PF)",value=86400)

    ppf=st.number_input("PPF",value=0)

    elss=st.number_input("ELSS",value=0)

    life_ins=st.number_input("Life Insurance Premium",value=0)

    tax_fd=st.number_input("Tax Saving FD",value=0)

    principal_home=st.number_input("Home Loan Principal",value=0)

    sukanya=st.number_input("Sukanya / Other",value=0)

    invest_80c=epf+ppf+elss+life_ins+tax_fd+principal_home+sukanya

    st.header("Other Deductions")

    nps_employee=st.number_input("NPS 80CCD(1B)",value=50000)

    health_insurance=st.number_input("Health Insurance 80D",value=25000)

    education_loan_interest=st.number_input("Education Loan Interest 80E",value=0)

    home_loan_interest=st.number_input("Home Loan Interest",value=0)

# -------------------------
# ANALYSIS
# -------------------------

if st.button("Run full analysis"):

    hra_exempt=compute_hra_exemption(basic,da,hra,rent_annual,is_metro) if lives_rented else 0

    reimbursements=internet_allowance+phone_allowance+conveyance_allowance+meal_voucher

    exemptions_old=hra_exempt+reimbursements+lta_claimed

    deductions={
        "standard_deduction":RULES["standard_deduction"],
        "80c":min(invest_80c,RULES["80c_limit"]),
        "80ccd_1b":min(nps_employee,RULES["80ccd_1b_limit"]),
        "80d":health_insurance,
        "80e":education_loan_interest,
        "home_loan_interest":home_loan_interest
    }

    old_tax,old_taxable=compute_old_regime_tax(gross_income,exemptions_old,deductions)

    allowed_new={
        "standard_deduction":RULES["standard_deduction"],
        "80ccd_1b":min(nps_employee,RULES["80ccd_1b_limit"])
    }

    new_tax,new_taxable=compute_new_regime_tax(gross_income,allowed_new)

    summary = pd.DataFrame({

"Component":[
"Gross Income",

"Exemptions (Old only)",
"  ↳ HRA Exemption",
"  ↳ Internet Reimbursement",
"  ↳ Phone Reimbursement",
"  ↳ Conveyance",
"  ↳ Meal Voucher",
"  ↳ LTA",

"Deductions",
"  ↳ Standard Deduction",
"  ↳ 80C",
"  ↳ NPS 80CCD(1B)",
"  ↳ Health Insurance 80D",
"  ↳ Education Loan Interest 80E",
"  ↳ Home Loan Interest",

"Taxable Income",
"Estimated Tax"
],

"Old Regime":[
gross_income,

exemptions_old,
hra_exempt,
internet_allowance,
phone_allowance,
conveyance_allowance,
meal_voucher,
lta_claimed,

deductions["standard_deduction"]
+ deductions["80c"]
+ deductions["80ccd_1b"]
+ deductions["80d"]
+ deductions["80e"]
+ deductions["home_loan_interest"],

deductions["standard_deduction"],
deductions["80c"],
deductions["80ccd_1b"],
deductions["80d"],
deductions["80e"],
deductions["home_loan_interest"],

old_taxable,
old_tax
],

"New Regime":[
gross_income,

0,
0,
0,
0,
0,
0,
0,

allowed_new["standard_deduction"] + allowed_new["80ccd_1b"],

allowed_new["standard_deduction"],
0,
allowed_new["80ccd_1b"],
0,
0,
0,

new_taxable,
new_tax
]

})

    st.subheader("Old vs New")

    st.table(summary)

# -------------------------
# RECOMMENDATIONS
# -------------------------

    st.subheader("Recommendations")

    marginal=marginal_with_cess(old_taxable)

    if invest_80c<RULES["80c_limit"]:

        gap=RULES["80c_limit"]-invest_80c

        est_save=int(gap*marginal)

        st.write(f"Invest additional {money(gap)} in 80C to save approx {money(est_save)} tax")

    if nps_employee<RULES["80ccd_1b_limit"]:

        gap=RULES["80ccd_1b_limit"]-nps_employee

        est_save=int(gap*marginal)

        st.write(f"Invest additional {money(gap)} in NPS to save approx {money(est_save)} tax")

    if lives_rented and special_allowance>0:

        st.write("Consider restructuring part of Special Allowance into HRA")

    if reimbursements>0:

        st.write("Convert allowances into proof-based reimbursements if company policy allows")

    if old_tax<new_tax:

        st.success(f"Old Regime Better — Save {money(new_tax-old_tax)}")

    else:

        st.success(f"New Regime Better — Save {money(old_tax-new_tax)}")
