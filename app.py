# app.py
# MBA Tax Optimizer - Streamlit single-file MVP
# Paste this entire file into your GitHub repo as app.py

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import date

st.set_page_config(page_title="MBA Tax Optimizer", layout="wide")

# -------------------------
# EDITABLE RULES / PARAMETERS
# -------------------------
RULES = {
    "fy": "2025-26",
    "standard_deduction": 50000,
    "80c_limit": 150000,
    "80ccd_1b_limit": 50000,
    "hra_metro_pct": 0.50,
    "hra_nonmetro_pct": 0.40,
    "cess_rate": 0.04,
    # tax slabs (example) - edit these numbers if government changes slabs
    "tax_slabs_old": [
        {"upto": 250000, "rate": 0.0},
        {"upto": 500000, "rate": 0.05},
        {"upto": 1000000, "rate": 0.20},
        {"upto": 999999999, "rate": 0.30}
    ],
    # Example new regime slab structure (editable)
    "tax_slabs_new": [
        {"upto": 300000, "rate": 0.0},
        {"upto": 600000, "rate": 0.05},
        {"upto": 900000, "rate": 0.10},
        {"upto": 1200000, "rate": 0.15},
        {"upto": 1500000, "rate": 0.20},
        {"upto": 999999999, "rate": 0.30}
    ],
    "allowed_reimbursements": ["internet", "phone", "books", "conveyance", "meal_voucher"]
}

# -------------------------
# Utility tax functions
# -------------------------
def compute_hra_exemption(basic, da, hra_received, rent_paid, is_metro):
    salary_for_hra = basic + da
    pct = RULES["hra_metro_pct"] if is_metro else RULES["hra_nonmetro_pct"]
    limit_pct = pct * salary_for_hra
    rent_minus_10pct = max(0, rent_paid - 0.10 * salary_for_hra)
    hra_exemption = min(hra_received, limit_pct, rent_minus_10pct)
    return round(max(0, hra_exemption), 0)

def tax_from_slabs(taxable_income, slabs):
    tax = 0.0
    previous = 0
    for slab in slabs:
        upto = slab["upto"]
        rate = slab["rate"]
        if taxable_income <= previous:
            break
        taxable_here = min(taxable_income, upto) - previous
        if taxable_here > 0:
            tax += taxable_here * rate
        previous = upto
    tax = tax * (1 + RULES["cess_rate"])
    return round(tax, 0)

def compute_old_regime_tax(gross_income, hra_exempt, deductions):
    # deductions is a dict including standard_deduction, 80c, nps, health_insurance, home_loan_interest, etc.
    taxable = gross_income - hra_exempt - deductions.get("standard_deduction",0)
    taxable -= deductions.get("80c",0)
    taxable -= deductions.get("80ccd_1b",0)
    taxable -= deductions.get("80d",0)
    taxable -= deductions.get("home_loan_interest",0)
    taxable = max(0, taxable)
    tax = tax_from_slabs(taxable, RULES["tax_slabs_old"])
    return int(tax), int(taxable)

def compute_new_regime_tax(gross_income, allowed_deductions=None):
    # In new regime only few deductions allowed; we will allow standard deduction optionally (editable)
    allowed_deductions = allowed_deductions or {}
    taxable = gross_income - allowed_deductions.get("standard_deduction",0) - allowed_deductions.get("80ccd_1b",0)
    taxable = max(0, taxable)
    tax = tax_from_slabs(taxable, RULES["tax_slabs_new"])
    return int(tax), int(taxable)

# -------------------------
# UI helper: sidebar and header
# -------------------------
st.title("MBA Tax Optimizer — Salary structuring & deduction suggestions")
st.caption(f"Financial Year: {RULES['fy']}  •  Editable rules in code (top of app.py)")

with st.expander("Why this tool? (short)"):
    st.write(
        """
        This tool compares Old vs New tax regimes, calculates HRA exemption, highlights missed deductions (80C, NPS, 80D etc.),
        and gives practical salary-structuring suggestions (move special allowance -> HRA, increase NPS, convert allowances to reimbursements).
        """
    )

# Left column: questionnaire
col1, col2 = st.columns([2,3])

with col1:
    st.header("1. Personal & Accommodation")
    age = st.selectbox("Age bracket", ["<60", "60-80", ">80"])
    is_senior = (age != "<60")
    city = st.text_input("City (type city or 'metro'/'non-metro')", value="metro")
    is_metro = st.radio("City type", ["Metro", "Non-Metro"]) == "Metro"
    lives_rented = st.radio("Do you live in rented accommodation?", ["Yes","No"]) == "Yes"
    rent_annual = 0
    if lives_rented:
        rent_annual = st.number_input("Annual rent paid (₹)", min_value=0, value=240000, step=1000)

    st.markdown("---")
    st.header("2. Salary breakup (annual amounts)")
    ctc = st.number_input("Total CTC (₹)", min_value=0, value=1800000, step=10000)
    basic = st.number_input("Basic salary (₹)", min_value=0, value=720000, step=10000)
    da = st.number_input("Dearness Allowance (DA) (₹) — if none put 0", min_value=0, value=0, step=1000)
    hra = st.number_input("HRA received (₹)", min_value=0, value=288000, step=1000)
    special_allowance = st.number_input("Special allowance (taxable) (₹)", min_value=0, value=200000, step=1000)
    variable_pay = st.number_input("Bonus / variable components (₹)", min_value=0, value=200000, step=1000)
    employer_pf = st.number_input("Employer PF contribution (₹)", min_value=0, value=86400, step=1000)
    employee_pf = st.number_input("Employee PF contribution (₹)", min_value=0, value=86400, step=1000)
    employer_nps = st.number_input("Employer NPS contribution (₹) if any", min_value=0, value=60000, step=1000)
    gratuity = st.number_input("Gratuity (if defined) (₹)", min_value=0, value=0, step=1000)

    st.markdown("---")
    st.header("3. Investments & Deductions")
    invest_80c = st.number_input("Total 80C investments this FY (₹)", min_value=0, value=150000, step=1000)
    nps_employee = st.number_input("NPS (employee contribution) (₹)", min_value=0, value=50000, step=1000)
    health_insurance = st.number_input("Health insurance premium claimed under 80D (₹)", min_value=0, value=25000, step=1000)
    home_loan_interest = st.number_input("Home loan interest paid this FY (₹)", min_value=0, value=0, step=1000)
    donations_80g = st.number_input("Donations (80G) this FY (₹)", min_value=0, value=0, step=1000)

    st.markdown("---")
    st.header("4. Preferences")
    willing_restructure = st.radio("Are you willing to restructure salary (ask HR)?", ["Yes","No"]) == "Yes"
    hr_flexibility = st.selectbox("HR flexibility (your guess)", ["High","Medium","Low"])
    priority = st.selectbox("What's your priority?", ["Maximize immediate take-home", "Maximize tax savings", "Balance"])

# Right column: compute and results
with col2:
    st.header("Results and Suggestions")
    if st.button("Run full analysis"):
        # Compute HRA exemption
        hra_exempt = compute_hra_exemption(basic, da, hra, rent_annual, is_metro)

        # Build deductions dict
        deductions = {
            "standard_deduction": RULES["standard_deduction"],
            "80c": min(invest_80c, RULES["80c_limit"]),
            "80ccd_1b": min(nps_employee, RULES["80ccd_1b_limit"]),
            "80d": health_insurance,
            "home_loan_interest": home_loan_interest
        }

        gross_income = ctc  # for simplicity; we treat CTC ~ gross for this MVP

        old_tax, old_taxable = compute_old_regime_tax(gross_income, hra_exempt, deductions)
        allowed_new_deductions = {
            "standard_deduction": 0,  # new regime usually doesn't have standard deduction for salaried? (editable)
            "80ccd_1b": min(nps_employee, RULES["80ccd_1b_limit"])
        }
        new_tax, new_taxable = compute_new_regime_tax(gross_income, allowed_new_deductions)

        # Results summary table
        summary = pd.DataFrame({
            "Component": ["Gross Income","Exemptions (HRA)","Deductions (applied)","Taxable Income","Estimated Tax"],
            "Old Regime":[gross_income, hra_exempt, 
                          deductions["standard_deduction"] + deductions["80c"] + deductions["80ccd_1b"] + deductions["80d"],
                          old_taxable, old_tax],
            "New Regime":[gross_income, 0,
                          allowed_new_deductions["standard_deduction"] + allowed_new_deductions["80ccd_1b"],
                          new_taxable, new_tax]
        })

        st.subheader("Side-by-side: Old vs New regime")
        st.table(summary.set_index("Component"))

        # Best regime
        if old_tax < new_tax:
            st.success(f"Old regime looks better here — Estimated annual tax: ₹{old_tax:,} vs New regime: ₹{new_tax:,}")
        elif new_tax < old_tax:
            st.success(f"New regime looks better here — Estimated annual tax: ₹{new_tax:,} vs Old regime: ₹{old_tax:,}")
        else:
            st.info(f"Both regimes give similar tax: ₹{old_tax:,}")

        # Missed deductions suggestions
        st.markdown("### Missed / Partially used deductions")
        missed = []
        # 80C check
        if invest_80c < RULES["80c_limit"]:
            missing_80c = RULES["80c_limit"] - invest_80c
            missed.append({"Deduction":"80C (investments)", "Current":invest_80c, "Max":RULES["80c_limit"], "Opportunity (₹)": missing_80c})
        # NPS check
        if nps_employee < RULES["80ccd_1b_limit"]:
            missed.append({"Deduction":"80CCD(1B) - NPS", "Current":nps_employee, "Max":RULES["80ccd_1b_limit"], "Opportunity (₹)": RULES["80ccd_1b_limit"] - nps_employee})
        # 80D check
        if health_insurance == 0:
            missed.append({"Deduction":"80D - Health insurance", "Current":0, "Max":"Varies(25k)", "Opportunity (₹)": RULES["80d_max"] if "80d_max" in RULES else "Up to ₹25,000 (edit rules)"})

        if missed:
            missed_df = pd.DataFrame(missed)
            st.table(missed_df)
        else:
            st.write("Everything looks optimized from these common deductions. Good job!")

        # Salary restructuring suggestions (simple heuristics)
        st.markdown("### Salary restructuring suggestions (quick wins)")

        suggestions = []
        # Suggest moving special allowance to HRA (if user pays rent and special allowance > 0)
        if lives_rented and special_allowance > 0:
            # suggest move up to special_allowance or enough to cover rent-exempt gap
            hypothetical_move = min(special_allowance, max(0, rent_annual - hra_exempt))
            if hypothetical_move > 0:
                # very rough tax impact estimate: marginal tax rate approach
                # compute marginal rate by seeing which slab current taxable resides in
                _, current_taxable = compute_old_regime_tax(gross_income, hra_exempt, deductions)
                # estimate marginal rate
                marginal = estimate_marginal_rate(current_taxable)
                est_tax_saved = int(hypothetical_move * marginal)
                suggestions.append({
                    "Action": f"Move ₹{hypothetical_move:,} from Special Allowance → HRA (ask HR)",
                    "Estimated Tax Saving (₹/yr)": est_tax_saved,
                    "Notes":"Requires actual rent receipts & HR policy"
                })

        # Suggest increasing NPS if under 80ccd limit
        if nps_employee < RULES["80ccd_1b_limit"]:
            to_invest = RULES["80ccd_1b_limit"] - nps_employee
            est_saving = int(to_invest * marginal_tax_rate_for_income(old_taxable if 'old_taxable' in locals() else new_taxable) )
            suggestions.append({
                "Action": f"Invest additional ₹{to_invest:,} in NPS (80CCD(1B))",
                "Estimated Tax Saving (₹/yr)": "See note",
                "Notes": f"NPS gives additional tax benefit up to ₹{RULES['80ccd_1b_limit']:,} (employee). Employer contributions treated differently."
            })

        # Display suggestions table
        if suggestions:
            sugg_df = pd.DataFrame(suggestions)
            st.table(sugg_df)
        else:
            st.write("No safe restructuring suggestions available automatically.")

        # Generate HR email template
        st.markdown("### HR Email / Talking points")
        hr_email = generate_hr_email(name="[Your Name]", emp_id="[Employee ID]", changes=[
            {"what":"Increase HRA component", "why":"I live in rented accommodation and can provide rent receipts"},
            {"what":"Convert part of Special Allowance to reimbursements (internet/phone)","why":"Company already has proof-based reimbursement policy"},
            {"what":"Consider employer NPS contribution / increase employer NPS","why":"To improve long-term retirement savings & tax efficient"}
        ])
        st.code(hr_email, language="markdown")
        st.download_button("Download HR email (text)", hr_email, file_name="hr_email.txt")

        # Downloadable summary CSV
        summary_csv = summary.to_csv(index=False)
        st.download_button("Download summary (CSV)", summary_csv, file_name="tax_summary.csv", mime="text/csv")

        # Short notes
        st.markdown("#### Notes & next steps")
        st.write("""
            - This is an educational tool (not legal advice). For complex cases (ESOPs, foreign income, expatriate taxation), consult a CA.
            - Admins: change rules at the top of app.py when Budget changes occur.
            - If HR flexibility is high, pick the actions with the largest savings and lowest paperwork friction first.
        """)


# -------------------------
# Helper functions used inside main body
# (placed here to keep top logic readable)
# -------------------------

def estimate_marginal_rate(taxable_income):
    """Estimate marginal rate used for quick saving estimates (no cess)."""
    for slab in RULES["tax_slabs_old"]:
        if taxable_income <= slab["upto"]:
            return slab["rate"]
    # default highest slab
    return RULES["tax_slabs_old"][-1]["rate"]

def marginal_tax_rate_for_income(taxable_income):
    # return effective marginal including cess
    base = estimate_marginal_rate(taxable_income)
    return base * (1 + RULES["cess_rate"])

def generate_hr_email(name="[Your Name]", emp_id="[ID]", changes=None):
    if changes is None:
        changes = []
    lines = []
    lines.append(f"Subject: Request to review salary structure for FY {RULES['fy']}")
    lines.append("")
    lines.append(f"Hi HR Team,")
    lines.append("")
    lines.append(f"I would like to request a review of my salary structure for the upcoming financial year to optimize tax efficiency while remaining aligned with company policy.")
    lines.append("")
    lines.append("Proposed items for discussion:")
    for c in changes:
        lines.append(f"- {c['what']}: {c.get('why','')}")
    lines.append("")
    lines.append("Purpose: These changes help align my in-hand salary and retirement savings while being fully compliant with tax rules. Happy to meet and discuss feasibility or provide required documents.")
    lines.append("")
    lines.append("Thanks & regards,")
    lines.append(name)
    lines.append(emp_id)
    return "\n".join(lines)

# --------------
# Footer: quick test button & sample cases
# --------------
st.markdown("---")
st.write("Need help? Share one sample salary profile (you can also paste anonymized numbers) and I’ll run it and suggest exact changes.")
st.caption("Built by your batchmate — Edit constants at top of app.py to update tax rules after Budget announcements.")
