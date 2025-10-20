import streamlit as st
import pandas as pd
import os

# --- Page Configuration ---
# Set the page title and layout
st.set_page_config(
    page_title="MCA Insights Engine",
    page_icon="🚀",
    layout="wide"
)

# --- Data Loading ---
# We use @st.cache_data to load the data only once
@st.cache_data
def load_data():
    """Loads all our processed data files."""
    base_path = "output"
    master_data_path = os.path.join(base_path, "master_dataset.csv")
    enriched_data_path = os.path.join(base_path, "enriched_company_data.csv")
    
    master_df = pd.read_csv(master_data_path, low_memory=False)
    enriched_df = pd.read_csv(enriched_data_path)
    
    # --- Data Merging ---
    # Merge the master data with our scraped (fake) enriched data
    # We use a 'left' merge to keep all companies from the master list
    final_df = pd.merge(
        master_df, 
        enriched_df, 
        on="CIN", 
        how="left"
    )
    
    # Fill in "Not Found" for companies that weren't in our enriched sample
    final_df['Scraped_Directors'].fillna('Not Scraped', inplace=True)
    final_df['Scraped_Email'].fillna('Not Scraped', inplace=True)
    final_df['Scraped_Website'].fillna('Not Scraped', inplace=True)
    
    return final_df

print("Loading data...")
df = load_data()
print("Data loading complete.")

# --- UI Layout ---

st.title("🚀 MCA Insights Engine")
st.write("A dashboard to search, filter, and analyze company data.")

# --- 1. Sidebar for Filters ---
st.sidebar.header("Filter Companies")

# Get unique values for filters
states = df['CompanyStateCode'].unique()
statuses = df['CompanyStatus'].unique()

# Create filter widgets
selected_state = st.sidebar.selectbox("Filter by State", options=["All"] + sorted(states))
selected_status = st.sidebar.selectbox("Filter by Status", options=["All"] + sorted(statuses))

# --- 2. Main Page for Search and Display ---

# Create columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Search Companies")
    search_query = st.text_input("Search by Company Name or CIN")

# --- Filtering Logic ---
# Start with the full dataframe
filtered_df = df

# Apply filters
if selected_state != "All":
    filtered_df = filtered_df[filtered_df['CompanyStateCode'] == selected_state]

if selected_status != "All":
    filtered_df = filtered_df[filtered_df['CompanyStatus'] == selected_status]

if search_query:
    filtered_df = filtered_df[
        filtered_df['CompanyName'].str.contains(search_query, case=False) |
        filtered_df['CIN'].str.contains(search_query, case=False)
    ]

# --- Display the Data ---
st.header("Search Results")
st.dataframe(filtered_df.head(50)) # Show the first 50 results
st.write(f"Showing **{len(filtered_df)}** matching companies.")

# --- Display Enriched Data (Details on demand) ---
st.header("View Enriched Company Details")
# Create a dropdown to select a company from the filtered results
company_list = filtered_df['CompanyName'].tolist()
selected_company_name = st.selectbox("Select a company to view details", options=company_list)

if selected_company_name:
    # Get the data for the selected company
    company_data = filtered_df[filtered_df['CompanyName'] == selected_company_name].iloc[0]
    
    st.subheader(f"Details for: {company_data['CompanyName']}")
    
    # Display in columns
    c1, c2, c3 = st.columns(3)
    c1.metric("CIN", company_data['CIN'])
    c2.metric("Company Status", company_data['CompanyStatus'])
    c3.metric("State", company_data['CompanyStateCode'])
    
    st.subheader("Enriched Data (from ZaubaCorp)")
    st.text(f"Directors: {company_data['Scraped_Directors']}")
    st.text(f"Email: {company_data['Scraped_Email']}")
    st.text(f"Website: {company_data['Scraped_Website']}")

    # --- TASK E (Part 2): CHATBOT ---

st.header("Chat with MCA Data")

# Load the change logs for the chatbot to use
@st.cache_data
def load_change_logs():
    try:
        log_day2 = pd.read_json("output/change_log_day2.json")
        log_day3 = pd.read_json("output/change_log_day3.json")
        return log_day2, log_day3
    except FileNotFoundError:
        st.error("Could not load change logs for chatbot.")
        return pd.DataFrame(), pd.DataFrame()

log_day2, log_day3 = load_change_logs()

# Get user input using Streamlit's chat input widget
prompt = st.chat_input("Ask a question about the data...")

if prompt:
    # Display the user's message in the chat interface
    st.chat_message("user").write(prompt)

    # --- Simple Rule-Based AI Logic ---
    # Convert the prompt to lowercase for easier matching
    prompt_lower = prompt.lower()

    # Check for keywords to determine the user's question
    if "how many new incorporations" in prompt_lower:
        # Check the 'day 3' log (which compares day 2 vs day 3 data)
        new_corps = len(log_day3[log_day3['Change_Type'] == 'New Incorporation'])
        # Display the answer in the chat interface as the assistant
        st.chat_message("assistant").write(f"There were {new_corps} new incorporations in the last update.")

    elif "how many companies were struck off" in prompt_lower or "deregistered" in prompt_lower:
        # Check the 'day 2' log for status changes to 'Strike Off'
        struck_off_logs = log_day2[log_day2['Change_Type'] == 'Field Update']
        # Count how many of those changes had 'Strike Off' as the new value
        struck_off = len(struck_off_logs[struck_off_logs['New_Value'] == 'Strike Off'])
        st.chat_message("assistant").write(f"There were {struck_off} companies marked as 'Strike Off' in the Day 2 update.")

    elif "show companies in" in prompt_lower:
        # Example: "show companies in Delhi"
        # Extract the state name after "in " and convert to uppercase
        state = prompt_lower.split("in ")[-1].upper().strip()
        # Filter the main dataframe (df) for the requested state
        state_df = df[df['CompanyStateCode'] == state]
        # Display the result
        st.chat_message("assistant").write(f"Found {len(state_df)} companies in {state}. Here are the first 5:")
        st.dataframe(state_df.head()) # Show the first 5 companies

    else:
        # If the question doesn't match known patterns, give help text
        st.chat_message("assistant").write("Sorry, I can only answer simple questions about:\n"
                                          "- 'how many new incorporations'\n"
                                          "- 'how many companies were struck off'\n"
                                          "- 'show companies in [State]'\n")
