import streamlit as st
import pandas as pd
import numpy as np
import io

def perform_matching(hrms_df, db_df, hrms_mass_col, db_mass_col, db_name_col, tolerance_da, mode):
    """
    Core logic for matching HRMS masses to the database.
    Modified to work entirely with pandas DataFrames in memory.
    """
    # Work on copies to prevent altering the original uploaded data
    results_df = hrms_df.copy()
    db_clean = db_df.copy()

    # Clean the database: convert masses to numeric, drop NaNs
    db_clean[db_mass_col] = pd.to_numeric(db_clean[db_mass_col], errors='coerce')
    db_clean = db_clean.dropna(subset=[db_mass_col])
    
    # Calculate proton mass for adduct correction
    h_mass = 1.007825
    matched_names = []
    
    # Set up progress bar
    progress_bar = st.progress(0)
    total_rows = len(results_df)
    
    for index, row in results_df.iterrows():
        experimental_mass = row[hrms_mass_col]
        
        if pd.isnull(experimental_mass):
            matched_names.append("Empty Row")
        else:
            # 1. Convert experimental m/z to neutral exact mass
            if mode == 'Positive [M+H]+':
                neutral_mass = experimental_mass - h_mass
            elif mode == 'Negative [M-H]-':
                neutral_mass = experimental_mass + h_mass
            else: # 'Neutral' mode
                neutral_mass = experimental_mass
                
            # 2. Define the matching window
            min_mass = neutral_mass - tolerance_da
            max_mass = neutral_mass + tolerance_da
            
            # 3. Find matches
            matches = db_clean[(db_clean[db_mass_col] >= min_mass) & (db_clean[db_mass_col] <= max_mass)]
            
            # 4. Record results
            if not matches.empty:
                names = matches[db_name_col].tolist()
                unique_names = list(set(names))
                match_string = " | ".join(str(name) for name in unique_names)
                matched_names.append(match_string)
            else:
                matched_names.append("No Match Found")
                
        # Update progress bar
        if total_rows > 0:
            progress_bar.progress((index + 1) / total_rows)

    # Append results
    results_df['Database_Matches'] = matched_names
    return results_df

# --- Streamlit UI Setup ---
st.set_page_config(page_title="HRMS Database Matcher", page_icon="🧬", layout="wide")

st.title("🧬 HRMS Peak-to-Database Matcher")
st.write("Upload your HRMS experimental data and your local Phytochemical database to find compound matches based on exact mass.")

# --- File Upload Section ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload HRMS Data")
    hrms_file = st.file_uploader("Upload Experimental Data (.xlsx)", type=["xlsx"], key="hrms")

with col2:
    st.subheader("2. Upload Database")
    db_file = st.file_uploader("Upload Compound Database (.xlsx)", type=["xlsx"], key="db")

# --- Processing Section ---
if hrms_file is not None and db_file is not None:
    try:
        # Load dataframes
        hrms_df = pd.read_excel(hrms_file)
        db_df = pd.read_excel(db_file)
        
        st.write("---")
        st.subheader("3. Configuration")
        
        # UI Columns for settings
        cfg_col1, cfg_col2, cfg_col3 = st.columns(3)
        
        with cfg_col1:
            hrms_mass_col = st.selectbox("HRMS Mass Column (m/z):", hrms_df.columns, help="The column in your experimental data containing the peak masses.")
            mode = st.selectbox("Ionization Mode:", ['Positive [M+H]+', 'Negative [M-H]-', 'Neutral (Already Corrected)'])
            
        with cfg_col2:
            db_mass_col = st.selectbox("Database Mass Column:", db_df.columns, help="The column in your database containing the exact Monoisotopic masses.")
            db_name_col = st.selectbox("Database Compound Name Column:", db_df.columns)
            
        with cfg_col3:
            # Added the Slider for Tolerance
            st.write("Mass Tolerance (Da)")
            tolerance_da = st.slider(
                "Select acceptable mass error:", 
                min_value=0.001, 
                max_value=10.000, 
                value=0.010,   # Default value
                step=0.001,    # Fine control for HRMS accuracy
                format="%.3f"
            )
            st.caption(f"Currently matching within ±{tolerance_da:.3f} Da")

        # --- Run Matching ---
        if st.button("Start Matching Process", type="primary"):
            st.write("### Matching in progress...")
            
            # Call the matching function
            matched_df = perform_matching(
                hrms_df=hrms_df, 
                db_df=db_df, 
                hrms_mass_col=hrms_mass_col, 
                db_mass_col=db_mass_col, 
                db_name_col=db_name_col, 
                tolerance_da=tolerance_da, 
                mode=mode
            )
            
            # Calculate metrics
            successful_hits = len(matched_df[matched_df['Database_Matches'] != "No Match Found"])
            
            st.success(f"✅ Matching Complete! Found {successful_hits} peaks that correspond to known compounds.")
            
            # Show preview
            st.write("### Results Preview")
            st.dataframe(matched_df.head(15))
            
            # Convert to Excel in memory for download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                matched_df.to_excel(writer, index=False, sheet_name='Matched_Results')
            
            processed_data = output.getvalue()
            
            # Download Button
            st.download_button(
                label="📥 Download Matched Results",
                data=processed_data,
                file_name="HRMS_Database_Matched.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"An error occurred while reading or processing the files: {e}")
