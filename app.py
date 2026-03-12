import streamlit as st

st.title("MBA Tax Optimizer")

st.write("This tool helps you compare tax under Old vs New regime.")

st.header("Enter Salary Details")

ctc = st.number_input("Annual CTC (₹)", value=2000000)

basic = st.number_input("Basic Salary (₹)", value=800000)

hra = st.number_input("HRA (₹)", value=300000)

rent = st.number_input("Annual Rent Paid (₹)", value=240000)

invest_80c = st.number_input("Total 80C Investments (₹)", value=150000)

nps = st.number_input("NPS Contribution (₹)", value=50000)

health_insurance = st.number_input("Health Insurance Premium (₹)", value=25000)

metro = st.selectbox("City Type", ["Metro", "Non-Metro"])


if st.button("Calculate Tax"):

    salary = basic

    if metro == "Metro":
        hra_limit = 0.5 * salary
    else:
        hra_limit = 0.4 * salary

    rent_minus_10 = rent - 0.1 * salary

    hra_exemption = min(hra, hra_limit, rent_minus_10)

    taxable_old = (
        ctc
        - hra_exemption
        - 50000
        - invest_80c
        - nps
        - health_insurance
    )

    tax = 0

    if taxable_old <= 250000:
        tax = 0
    elif taxable_old <= 500000:
        tax = (taxable_old - 250000) * 0.05
    elif taxable_old <= 1000000:
        tax = 12500 + (taxable_old - 500000) * 0.2
    else:
        tax = 112500 + (taxable_old - 1000000) * 0.3

    tax = tax * 1.04

    st.subheader("Results")

    st.write("HRA Exemption:", round(hra_exemption))

    st.write("Taxable Income:", round(taxable_old))

    st.write("Estimated Tax (Old Regime): ₹", round(tax))
