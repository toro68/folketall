import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# SSB API endpoint
url = "https://data.ssb.no/api/v0/no/table/01222/"

# Function to get available quarters
def get_available_quarters(num_quarters=20):
    quarters = []
    current_date = datetime.now() - timedelta(days=90)  # Start from previous quarter
    for _ in range(num_quarters):
        year = current_date.year
        quarter = (current_date.month - 1) // 3 + 1
        quarters.append(f"{year}K{quarter}")
        current_date -= timedelta(days=90)
    return quarters[::-1]  # Reverse to get most recent first

# Streamlit app
st.title("SSB Folketall i Rogaland")

# Sidebar for navigation
analysis_type = st.sidebar.radio("Velg analyse", ["Alle kommuner", "Enkelt kommune over tid"])

# Rogaland municipality codes and names
municipality_codes = [
    "1101", "1103", "1106", "1108", "1111", "1112", "1114", "1119",
    "1120", "1121", "1122", "1124", "1127", "1130", "1133", "1134",
    "1135", "1144", "1145", "1146", "1149", "1151", "1160"
]

municipality_names = [
    "Eigersund", "Stavanger", "Haugesund", "Sandnes", "Sokndal", "Lund", "Bjerkreim", "Hå",
    "Klepp", "Time", "Gjesdal", "Sola", "Randaberg", "Strand", "Hjelmeland", "Suldal",
    "Sauda", "Kvitsøy", "Bokn", "Tysvær", "Karmøy", "Utsira", "Vindafjord"
]

if analysis_type == "Alle kommuner":
    # Existing code for all municipalities
    available_quarters = get_available_quarters(4)  # Last 4 quarters
    selected_quarters = available_quarters[-2:]  # Last 2 quarters

    # Query for Rogaland municipalities
    query = {
        "query": [
            {
                "code": "Region",
                "selection": {"filter": "item", "values": municipality_codes},
            },
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Folketallet11"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": selected_quarters}},
        ],
        "response": {"format": "json-stat2"},
    }

    try:
        response = requests.post(url, json=query)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            st.error(f"API Error: {data['error']}")
            st.stop()

        # Get municipality labels
        municipality_labels = data["dimension"]["Region"]["category"]["label"]
        
        # Create DataFrame
        df = pd.DataFrame(data["value"], columns=["Folketall"])
        df["Kommune"] = [municipality_labels[code] for code in municipality_codes for _ in selected_quarters]
        df["Kvartal"] = selected_quarters * len(municipality_codes)
        
        # Pivot the DataFrame for easier change calculation
        df_pivot = df.pivot(index="Kommune", columns="Kvartal", values="Folketall")
        
        # Calculate change
        df_pivot["Endring"] = df_pivot[selected_quarters[-1]] - df_pivot[selected_quarters[-2]]
        df_pivot["Endring %"] = (df_pivot["Endring"] / df_pivot[selected_quarters[-2]] * 100).round(2)
        
        # Reset index to make Kommune a column again
        df_final = df_pivot.reset_index()
        
        # Rename columns for clarity
        df_final = df_final.rename(columns={selected_quarters[-1]: "Folketall"})
        
        # Sort by population
        df_final = df_final.sort_values("Folketall", ascending=False)
        
        # Display table for municipalities
        st.write(f"Data for kommuner i Rogaland, {selected_quarters[-1]} (endring fra {selected_quarters[-2]})")
        st.table(df_final[["Kommune", "Folketall", "Endring", "Endring %"]])
        
        # Create bar plot for population
        fig_pop = px.bar(df_final, x="Kommune", y="Folketall", 
                         title="Befolkning i Rogaland kommuner")
        st.plotly_chart(fig_pop)
        
        # Create bar plot for change
        fig_change = px.bar(df_final, x="Kommune", y="Endring", 
                            title="Befolkningsendring i Rogaland kommuner")
        st.plotly_chart(fig_change)
        
        # Calculate summary for Rogaland
        rogaland_summary = pd.DataFrame({
            "Kommune": ["Rogaland totalt"],
            "Folketall": [df_final["Folketall"].sum()],
            "Endring": [df_final["Endring"].sum()],
            "Endring %": [(df_final["Endring"].sum() / df_final[selected_quarters[-2]].sum() * 100).round(2)]
        })
        
        # Display summary table for Rogaland
        st.write(f"Oppsummering for hele Rogaland, {selected_quarters[-1]} (endring fra {selected_quarters[-2]})")
        st.table(rogaland_summary)
        
        # Combine municipal data and Rogaland summary for download
        df_download = pd.concat([df_final, rogaland_summary])
        
        # Download button
        csv = df_download.to_csv(index=False)
        st.download_button(
            label="Last ned data som CSV",
            data=csv,
            file_name=f"rogaland_population_data_{selected_quarters[-1]}.csv",
            mime="text/csv",
        )

    except requests.RequestException as e:
        st.error(f"Feil ved henting av data fra SSB API: {str(e)}")
    except KeyError as e:
        st.error(f"Feil ved behandling av data fra SSB API: Manglende nøkkel i datastrukturen: {str(e)}")
    except IndexError as e:
        st.error(f"Feil ved behandling av data fra SSB API: Indekseringsfeil: {str(e)}")
    except Exception as e:
        st.error(f"Uventet feil: {str(e)}")

else:  # Single municipality analysis
    st.header("Analyse av enkelt kommune over tid")

    # Select municipality
    selected_municipality = st.selectbox("Velg kommune", municipality_names)
    selected_code = municipality_codes[municipality_names.index(selected_municipality)]

    # Select time range
    available_quarters = get_available_quarters(20)  # Increased to 20 quarters for more historical data
    start_quarter = st.selectbox("Velg startkvartalet", available_quarters, index=len(available_quarters)-8)
    
    # Determine the index of the start quarter
    start_index = available_quarters.index(start_quarter)
    
    # Create a list of quarters from the start quarter to the end of available quarters
    end_quarter_options = available_quarters[start_index:]
    
    # Select end quarter
    end_quarter = st.selectbox("Velg sluttkvartalet", end_quarter_options, index=len(end_quarter_options)-1)

    selected_quarters = available_quarters[start_index:available_quarters.index(end_quarter)+1]

    # Query for single municipality
    query = {
        "query": [
            {
                "code": "Region",
                "selection": {"filter": "item", "values": [selected_code]},
            },
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["Folketallet11"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": selected_quarters}},
        ],
        "response": {"format": "json-stat2"},
    }

    try:
        response = requests.post(url, json=query)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            st.error(f"API Error: {data['error']}")
            st.stop()

        # Create DataFrame
        df = pd.DataFrame({
            "Kvartal": selected_quarters,
            "Folketall": data["value"]
        })

        # Calculate change
        df["Endring"] = df["Folketall"].diff()
        df["Endring %"] = (df["Endring"] / df["Folketall"].shift(1) * 100).round(2)

        # Display line chart
        fig = px.line(df, x="Kvartal", y="Folketall", 
                      title=f"Befolkningsutvikling i {selected_municipality}")
        st.plotly_chart(fig)

        # Display table
        st.write(f"Befolkningsdata for {selected_municipality}")
        st.table(df)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Last ned data som CSV",
            data=csv,
            file_name=f"{selected_municipality}_population_data_{start_quarter}-{end_quarter}.csv",
            mime="text/csv",
        )

    except requests.RequestException as e:
        st.error(f"Feil ved henting av data fra SSB API: {str(e)}")
    except KeyError as e:
        st.error(f"Feil ved behandling av data fra SSB API: Manglende nøkkel i datastrukturen: {str(e)}")
    except IndexError as e:
        st.error(f"Feil ved behandling av data fra SSB API: Indekseringsfeil: {str(e)}")
    except Exception as e:
        st.error(f"Uventet feil: {str(e)}")

st.write(f"Forespurte kvartaler: {', '.join(selected_quarters)}")