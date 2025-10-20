import pandas as pd
import glob
import os
# Import libraries needed for Task C early, just in case
import requests
from bs4 import BeautifulSoup
import time

# --- TASK A: DATA INTEGRATION ---

print("Starting Task A: Data Integration...")

# Get the path to the current folder where this script is
folder_path = os.path.dirname(os.path.abspath(__file__))

# Create a path for a new 'output' folder to store our results
output_folder = os.path.join(folder_path, 'output')
os.makedirs(output_folder, exist_ok=True) # This creates the folder if it doesn't exist

# Specifically list our 5 state files to merge
state_files = ['delhi.csv', 'G.csv', 'K.csv', 'mh.csv', 'tamil.csv']
# Create the full file path for each
all_csv_files = [os.path.join(folder_path, file) for file in state_files]

print(f"Found {len(all_csv_files)} state files to merge.")

# --- Load and Combine Data ---
all_dataframes = []  # Create an empty list to hold each state's data

for file in all_csv_files:
    print(f"Reading file: {os.path.basename(file)}...")
    try:
        df = pd.read_csv(file, low_memory=False)
        all_dataframes.append(df) # Add the DataFrame to our list
    except Exception as e:
        print(f"Error reading {file}: {e}")

master_df = pd.concat(all_dataframes, ignore_index=True)
print(f"Combined all files. Total rows: {len(master_df)}")

# --- Clean the Data ---
print("Cleaning data...")

# A. Drop Duplicates:
original_rows = len(master_df)
master_df.drop_duplicates(subset=['CIN'], inplace=True)
print(f"Removed {original_rows - len(master_df)} duplicate rows based on CIN.")

# B. Handle Null/Missing Values (Fixed to remove warnings):
master_df['AuthorizedCapital'] = master_df['AuthorizedCapital'].fillna(0)
master_df['PaidupCapital'] = master_df['PaidupCapital'].fillna(0)
master_df['CompanyStatus'] = master_df['CompanyStatus'].fillna('Unknown')

print("Data cleaning complete.")

# --- Save the Master File ---
master_file_path = os.path.join(output_folder, 'master_dataset.csv')
master_df.to_csv(master_file_path, index=False)

print(f"Success! Master file saved to: {master_file_path}")
print("--- Task A Finished ---")


# --- TASK B: CHANGE DETECTION ---

print("\nStarting Task B: Change Detection...")

def find_changes(old_file_path, new_file_path, log_date):
    """Compares two CSVs and logs the differences."""
    
    try:
        df_old = pd.read_csv(old_file_path, dtype={'CIN': str}).set_index('CIN')
        df_new = pd.read_csv(new_file_path, dtype={'CIN': str}).set_index('CIN')
    except FileNotFoundError as e:
        print(f"Error: Could not find file. {e}")
        print("Please make sure 'day1.csv', 'day2.csv', and 'day3.csv' are in your main MCA_TASK folder.")
        return []
    except KeyError:
        print(f"Error: 'CIN' column not found. Please check files: {old_file_path}, {new_file_path}")
        return []

    changes_list = []

    # 1. Find New Incorporations (in new but not in old)
    new_cins = df_new.index.difference(df_old.index)
    for cin in new_cins:
        changes_list.append({
            'CIN': cin,
            'Change_Type': 'New Incorporation',
            'Field_Changed': 'N/A',
            'Old_Value': 'N/A',
            'New_Value': df_new.loc[cin, 'CompanyName'],
            'Date': log_date
        })

    # 2. Find Deregistrations (in old but not in new)
    gone_cins = df_old.index.difference(df_new.index)
    for cin in gone_cins:
        changes_list.append({
            'CIN': cin,
            'Change_Type': 'Deregistered',
            'Field_Changed': 'N/A',
            'Old_Value': df_old.loc[cin, 'CompanyName'],
            'New_Value': 'N/A',
            'Date': log_date
        })

    # 3. Find Field Updates (in both files but values are different)
    common_cins = df_old.index.intersection(df_new.index)
    
    columns_to_check = ['CompanyStatus', 'AuthorizedCapital', 'PaidupCapital']

    for cin in common_cins:
        for col in columns_to_check:
            old_val = df_old.loc[cin, col]
            new_val = df_new.loc[cin, col]
            
            if old_val != new_val and not (pd.isna(old_val) and pd.isna(new_val)):
                changes_list.append({
                    'CIN': cin,
                    'Change_Type': 'Field Update',
                    'Field_Changed': col,
                    'Old_Value': old_val,
                    'New_Value': new_val,
                    'Date': log_date
                })
                
    return changes_list

# --- Run the comparisons ---
changes_day_2 = find_changes(
    os.path.join(folder_path, 'day1.csv'),
    os.path.join(folder_path, 'day2.csv'),
    'Day 2'
)
changes_day_3 = find_changes(
    os.path.join(folder_path, 'day2.csv'),
    os.path.join(folder_path, 'day3.csv'),
    'Day 3'
)

# --- Save the change logs ---
log_df_2 = pd.DataFrame(changes_day_2)
log_path_2 = os.path.join(output_folder, 'change_log_day2.json')
log_df_2.to_json(log_path_2, orient='records', indent=4)
print(f"Saved Day 2 change log to: {log_path_2}")

log_df_3 = pd.DataFrame(changes_day_3)
log_path_3 = os.path.join(output_folder, 'change_log_day3.json')
log_df_3.to_json(log_path_3, orient='records', indent=4)
print(f"Saved Day 3 change log to: {log_path_3}")

print("--- Task B Finished ---")


# --- TASK E (Part 1): AI SUMMARY GENERATOR ---

print("\nStarting Task E: AI Summary Generation...")

try:
    # Load the change log we want to summarize
    log_df_summary = pd.read_json(os.path.join(output_folder, 'change_log_day3.json')) # Use a different variable name here
    
    # Calculate the stats
    new_corps = len(log_df_summary[log_df_summary['Change_Type'] == 'New Incorporation'])
    deregistered = len(log_df_summary[log_df_summary['Change_Type'] == 'Deregistered'])
    updates = len(log_df_summary[log_df_summary['Change_Type'] == 'Field Update'])
    
    # Create the summary text
    summary_text = (
        f"Daily Summary:\n"
        f"New incorporations: {new_corps}\n"
        f"Deregistered: {deregistered}\n"
        f"Updated records: {updates}"
    )
    
    # Save the summary to a .txt file
    summary_path = os.path.join(output_folder, 'daily_summary.txt')
    with open(summary_path, 'w') as f:
        f.write(summary_text)
        
    print(f"Successfully saved AI summary to: {summary_path}")

except FileNotFoundError:
    print("Could not find change log for summary. Skipping summary generation.")
except Exception as e:
    print(f"An error occurred during summary generation: {e}")

print("--- Task E (Part 1) Finished ---")


# --- TASK C: WEB-BASED CIN ENRICHMENT ---
# **** THIS BLOCK IS NOW AT THE END ****

print("\nStarting Task C: Web-Based Enrichment...")

def enrich_company_data(cin):
    """Scrapes ZaubaCorp for data based on a CIN."""
    
    url = f"https://www.zaubacorp.com/company/{cin}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"  - Failed to fetch {cin}, status code: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- Scrape for data ---
        
        director_names = []
        director_table = soup.find('table', class_='table-striped')
        
        if director_table:
            for row in director_table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) > 1 and cells[0].text.strip().isdigit():
                    director_name = cells[1].get_text(strip=True)
                    if director_name:
                        director_names.append(director_name)

        email = "Not Found"
        website = "Not Found"
        
        details_div = soup.find('div', class_='col-lg-6 col-md-6 col-sm-12 col-xs-12')
        if details_div:
            paragraphs = details_div.find_all('p')
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if "Email:" in p_text:
                    email_tag = p.find_next_sibling('p')
                    if email_tag:
                        email = email_tag.get_text(strip=True)
                if "Website:" in p_text:
                    website_tag = p.find_next_sibling('p')
                    if website_tag:
                        website = website_tag.get_text(strip=True)

        return {
            'CIN': cin,
            'Scraped_Directors': ', '.join(director_names) if director_names else 'Not Found',
            'Scraped_Email': email,
            'Scraped_Website': website
        }

    except Exception as e:
        print(f"  - Error processing {cin}: {e}")
        return None

# --- Run the Enrichment ---

try:
    # Use the same variable name as before, this is okay
    log_df = pd.read_json(os.path.join(output_folder, 'change_log_day3.json')) 
    
    cins_to_enrich = log_df['CIN'].unique()[:25]
    print(f"Found {len(cins_to_enrich)} CINs to enrich from the change log...")

    enriched_results = []
    for cin in cins_to_enrich:
        print(f"Enriching {cin}...")
        data = enrich_company_data(cin)
        if data:
            enriched_results.append(data)
        time.sleep(1) # Wait 1 second

    # --- Save the Enriched Data ---
    enriched_df = pd.DataFrame(enriched_results)
    enriched_path = os.path.join(output_folder, 'enriched_company_data.csv')
    enriched_df.to_csv(enriched_path, index=False)
    
    print(f"Successfully saved enriched data for {len(enriched_results)} companies to: {enriched_path}")

except FileNotFoundError:
    print("Could not find 'change_log_day3.json'. Skipping Task C.")
except Exception as e:
    print(f"An error occurred during Task C: {e}")

print("--- Task C Finished ---")

# --- END OF SCRIPT ---