import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
import io

def get_monoisotopic_mass(compound_name):
    """
    Queries PubChem by chemical name to retrieve the exact monoisotopic mass.
    Tries the exact name first; if not found, tries the lowercase version.
    """
    if pd.isnull(compound_name) or str(compound_name).strip() == "":
        return "Empty Name"
        
    clean_name = str(compound_name).strip()
    
    def fetch_from_api(name_to_search):
        encoded_name = urllib.parse.quote(name_to_search)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_name}/property/MonoisotopicMass/JSON"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                props = data.get('PropertyTable', {}).get('Properties', [])
                if props and 'MonoisotopicMass' in props[0]:
                    return props[0]['MonoisotopicMass']
                return "Mass Not Listed"
            elif response.status_code == 404:
                return "NOT_FOUND" 
            else:
                return f"API Error: {response.status_code}"
        except Exception as e:
            return "Connection Failed"

    # 1. Try original case
    result = fetch_from_api(clean_name)
    
    # 2. Fallback to lowercase if not found
    if result == "NOT_FOUND":
        time.sleep(0.3) 
        lowercase_result = fetch_from_api(clean_name.lower())
        if lowercase_result == "NOT_FOUND":
            return "Name Not Found"
        return lowercase_result
        
    return result

# --- Streamlit UI Setup ---
st.set_page_config(page_title="PubChem Mass Fetcher", page_icon="🧪")

st.title("🧪 PubChem Monoisotopic Mass Fetcher")
st.write("Upload an Excel file containing compound names. This app will query PubChem and append a new column with the monoisotopic mass for each compound.")

# File uploader widget
uploaded_file = st.file_uploader("Upload your Excel file (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Read the file into a Pandas DataFrame
        df = pd.read_excel(uploaded_file)
        
        st.write("### Data Preview")
        st.dataframe(df.head(5)) # Show first 5 rows
        
        # Let the user select which column contains the compound names
        name_col = st.selectbox("Select the column containing the compound names:", df.columns)
        
        # Start processing button
        if st.button("Fetch Masses"):
            st.write("---")
            st.write(f"Fetching masses for **{len(df)}** compounds. Please wait...")
            
            # Setup UI elements for progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            masses = []
            total_rows = len(df)
            
            for i, name in enumerate(df[name_col]):
                mass = get_monoisotopic_mass(name)
                masses.append(mass)
                
                # Update progress bar and text dynamically
                progress_percentage = (i + 1) / total_rows
                progress_bar.progress(progress_percentage)
                status_text.text(f"Processed {i + 1}/{total_rows}: {name} -> {mass}")
                
                # Crucial delay to prevent IP bans from NCBI
                time.sleep(0.3)

            # Add the new data to the dataframe
            df['Monoisotopic_Mass'] = masses
            
            st.success("✅ Processing complete!")
            st.write("### Updated Data Preview")
            st.dataframe(df.head(10))
            
            # Convert the updated DataFrame back to an Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Mass_Data')
            
            processed_data = output.getvalue()
            
            # Create a download button for the new file
            st.download_button(
                label="📥 Download Updated Excel File",
                data=processed_data,
                file_name="Updated_Compound_Masses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"An error occurred while reading the file: {e}")
