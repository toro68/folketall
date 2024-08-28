import streamlit as st
import requests
import pandas as pd

# SSB API endpoint
url = "https://data.ssb.no/api/v0/no/table/01222/"

# Default query (for Rogaland municipalities)
query = {
    "query": [
        {
            "code": "Region",
            "selection": {
                "filter": "agg:KommSummer",
                "values": [
                    "K-1101", "K-1103", "K-1106", "K-1108", "K-1111", "K-1112", "K-1114", "K-1119",
                    "K-1120", "K-1121", "K-1122", "K-1124", "K-1127", "K-1130", "K-1133", "K-1134",
                    "K-1135", "K-1144", "K-1145", "K-1146", "K-1149", "K-1151", "K-1160"
                ],
            },
        },
        {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Folketilvekst10", "Folketallet11"]}},
        {"code": "Tid", "selection": {"filter": "item", "values": ["2024K2"]}},
    ],
    "response": {"format": "json-stat2"},
}

# Streamlit app
st.title("SSB Population Data for Rogaland Municipalities")

# Fetch data from SSB API
response = requests.post(url, json=query)
data = response.json()

# Extract data and create DataFrame
try:
    # Get municipality codes and labels
    municipality_codes = data["dimension"]["Region"]["category"]["index"]
    municipality_labels = data["dimension"]["Region"]["category"]["label"]

    # Create lists to store data
    municipalities = []
    population_changes = []
    total_populations = []

    # Iterate through municipalities and extract data
    for code in municipality_codes:
        index = municipality_codes[code]
        population_change = data["value"][index * 2]
        total_population = data["value"][index * 2 + 1]

        municipalities.append(municipality_labels[code])
        population_changes.append(population_change)
        total_populations.append(total_population)

    # Create Pandas DataFrame
    df = pd.DataFrame({"Kommune": municipalities, "Folketall endring": population_changes, "Summer folketall": total_populations})

    # Add total row for Rogaland
    total_change = df["Folketall endring"].sum()
    total_population = df["Summer folketall"].sum()
    df.loc["Totalt Rogaland"] = ["Rogaland", total_change, total_population]

    # Add quarter information
    quarter = data["dimension"]["Tid"]["category"]["label"]["2024K2"]
    st.write(f"Data for {quarter}")

    # Display table
    st.table(df)

    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="rogaland_population_data.csv",
        mime="text/csv",
    )

except (KeyError, IndexError):
    st.error("Error fetching or processing data from SSB API. Please check the query and try again.")