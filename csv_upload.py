import os
import csv
import json
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv('keys.env')

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def format_pg_array(value):
    """Convert various Python types to PostgreSQL array format"""
    # Handle empty or None values
    if value is None or pd.isna(value) or value == '' or value == '[]' or value == '{}':
        return "{}"
    
    # Extract list items based on the input type
    items = []
    if isinstance(value, str):
        # Clean the string of any problematic characters
        cleaned_value = value.strip()
        
        # Remove outer brackets/braces if present
        if (cleaned_value.startswith('[') and cleaned_value.endswith(']')) or \
           (cleaned_value.startswith('{') and cleaned_value.endswith('}')):
            cleaned_value = cleaned_value[1:-1].strip()
        
        # Split by common delimiters
        if ';' in cleaned_value:
            items = [item.strip() for item in cleaned_value.split(';') if item.strip()]
        elif ',' in cleaned_value:
            items = [item.strip() for item in cleaned_value.split(',') if item.strip()]
        elif cleaned_value:  # Single value
            items = [cleaned_value]
    elif isinstance(value, list):
        items = [str(item).strip() for item in value if item is not None and str(item).strip()]
    else:
        # Single non-string, non-list value
        items = [str(value).strip()]
    
    # Format each item properly for PostgreSQL array
    formatted_items = []
    for item in items:
        # Clean the string
        item_str = str(item).strip()
        
        # Remove quotes at beginning and end
        if (item_str.startswith("'") and item_str.endswith("'")) or \
           (item_str.startswith('"') and item_str.endswith('"')):
            item_str = item_str[1:-1].strip()
        
        # Skip empty items
        if not item_str:
            continue
            
        # Remove any remaining special characters that might cause SQL issues
        item_str = item_str.replace("'", "")
        item_str = item_str.replace("\\", "")
        
        # Format for PostgreSQL
        if '"' in item_str or ',' in item_str or ' ' in item_str or '{' in item_str or '}' in item_str:
            formatted_items.append('"' + item_str.replace('"', '') + '"')
        else:
            formatted_items.append(item_str)
    
    # Return properly formatted PostgreSQL array
    if not formatted_items:
        return "{}"
    return "{" + ",".join(formatted_items) + "}"

def process_csv_mentees(csv_path):
    """Process mentee CSV file and transform it to match Supabase schema"""
    df = pd.read_csv(csv_path)
    
    # Standardize column names (lowercase, replace spaces with underscores)
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Basic data cleaning
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip().fillna('')
    
    # Convert age to integer
    if 'age' in df.columns:
        df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0).astype(int)
    
    # Handle stem_skills as PostgreSQL array format
    if 'stem_skills' in df.columns:
        df['stem_skills'] = df['stem_skills'].apply(
            lambda x: format_pg_array(x) if pd.notna(x) else "{}"
        )
    else:
        df['stem_skills'] = df.apply(lambda row: "{}", axis=1)
    
    # Handle interests as PostgreSQL array format
    if 'interests' in df.columns:
        df['interests'] = df['interests'].apply(
            lambda x: format_pg_array(x) if pd.notna(x) else "{}"
        )
    else:
        df['interests'] = df.apply(lambda row: "{}", axis=1)
    
    # Ensure all required fields exist
    required_fields = ['name', 'email', 'age', 'country', 'speaking_languages', 
                      'desired_field', 'degree', 'college', 'stem_skills', 
                      'interests', 'prior_work_experience']
    
    for field in required_fields:
        if field not in df.columns:
            # Map similar fields or create empty ones
            if field == 'desired_field' and 'field' in df.columns:
                df['desired_field'] = df['field']
            elif field == 'college' and 'university' in df.columns:
                df['college'] = df['university']
            elif field == 'prior_work_experience' and 'work_experience' in df.columns:
                df['prior_work_experience'] = df['work_experience']
            else:
                df[field] = '' if field not in ['age', 'stem_skills', 'interests'] else 0 if field == 'age' else "{}"
    
    # Select only required columns in correct order
    df = df[required_fields]
    
    # Convert dictionary to JSON string for json fields
    records = df.to_dict('records')
    for record in records:
        # If stem_skills and interests are already in PostgreSQL array format, keep them as is
        # Otherwise, ensure they're strings for json compatibility
        if isinstance(record['stem_skills'], str) and not record['stem_skills'].startswith('{'):
            record['stem_skills'] = "{}"
        if isinstance(record['interests'], str) and not record['interests'].startswith('{'):
            record['interests'] = "{}"
    
    return records

def process_csv_mentors(csv_path):
    """Process mentor CSV file and transform it to match Supabase schema"""
    df = pd.read_csv(csv_path)
    
    # Standardize column names (lowercase, replace spaces with underscores)
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Basic data cleaning
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip().fillna('')
    
    # Convert age to integer
    if 'age' in df.columns:
        df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0).astype(int)
    
    # Handle stem_skills as PostgreSQL array format
    if 'stem_skills' in df.columns:
        df['stem_skills'] = df['stem_skills'].apply(
            lambda x: format_pg_array(x) if pd.notna(x) else "{}"
        )
    else:
        df['stem_skills'] = df.apply(lambda row: "{}", axis=1)
    
    # Handle interests as PostgreSQL array format
    if 'interests' in df.columns:
        df['interests'] = df['interests'].apply(
            lambda x: format_pg_array(x) if pd.notna(x) else "{}"
        )
    else:
        df['interests'] = df.apply(lambda row: "{}", axis=1)
    
    # Ensure all required fields exist
    required_fields = ['name', 'email', 'age', 'country', 'speaking_languages', 
                      'field', 'degree', 'university', 'stem_skills', 
                      'interests', 'work_experience']
    
    for field in required_fields:
        if field not in df.columns:
            # Map similar fields or create empty ones
            if field == 'field' and 'desired_field' in df.columns:
                df['field'] = df['desired_field']
            elif field == 'university' and 'college' in df.columns:
                df['university'] = df['college']
            elif field == 'work_experience' and 'prior_work_experience' in df.columns:
                df['work_experience'] = df['prior_work_experience']
            else:
                df[field] = '' if field not in ['age', 'stem_skills', 'interests'] else 0 if field == 'age' else "{}"
    
    # Select only required columns in correct order
    df = df[required_fields]
    
    # Convert dictionary to JSON string for json fields
    records = df.to_dict('records')
    for record in records:
        # If stem_skills and interests are already in PostgreSQL array format, keep them as is
        # Otherwise, ensure they're strings for json compatibility
        if isinstance(record['stem_skills'], str) and not record['stem_skills'].startswith('{'):
            record['stem_skills'] = "{}"
        if isinstance(record['interests'], str) and not record['interests'].startswith('{'):
            record['interests'] = "{}"
    
    return records

def upload_to_supabase(data, table_name):
    """Upload data to Supabase in batches"""
    batch_size = 20
    success_count = 0
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        try:
            # Debug print statements
            print(f"Preparing batch {i//batch_size + 1}")
            
            # Make a clean copy to prevent issues with dict objects
            cleaned_batch = []
            for item in batch:
                cleaned_item = {}
                for key, value in item.items():
                    # Make sure values are of the right type
                    if key in ['stem_skills', 'interests']:
                        # Ensure array fields are properly formatted
                        if isinstance(value, str) and not value.startswith('{'):
                            cleaned_item[key] = "{}"
                        else:
                            cleaned_item[key] = value
                    else:
                        cleaned_item[key] = value
                cleaned_batch.append(cleaned_item)
            
            # Insert the cleaned batch
            result = supabase.table(table_name).insert(cleaned_batch).execute()
            
            if hasattr(result, 'data'):
                success_count += len(result.data)
                print(f"Batch {i//batch_size + 1}: Inserted {len(result.data)} rows successfully")
            else:
                print(f"Batch {i//batch_size + 1}: Error, no data returned")
        except Exception as e:
            print(f"Error inserting batch {i//batch_size + 1}: {str(e)}")
            # Try one-by-one insertion for this batch to skip problematic records
            for item in batch:
                try:
                    # Clean the item for insertion
                    cleaned_item = {}
                    for key, value in item.items():
                        if key in ['stem_skills', 'interests']:
                            # Ensure array fields are properly formatted
                            if isinstance(value, str) and not value.startswith('{'):
                                cleaned_item[key] = "{}"
                            else:
                                cleaned_item[key] = value
                        else:
                            cleaned_item[key] = value
                            
                    result = supabase.table(table_name).insert([cleaned_item]).execute()
                    if hasattr(result, 'data'):
                        success_count += len(result.data)
                except Exception as e:
                    print(f"  Failed to insert item: {str(e)}")
        
    return success_count

def main():
    """Main function to process and upload CSV data"""
    try:
        # Process and upload mentee data
        mentees_data = process_csv_mentees('menteedataconvergent.csv')
        print(f"Processed {len(mentees_data)} mentee records")
        mentees_count = upload_to_supabase(mentees_data, 'mentees')
        print(f"Successfully uploaded {mentees_count}/{len(mentees_data)} mentees")
        
        # Process and upload mentor data
        mentors_data = process_csv_mentors('mentordataconvergent.csv')
        print(f"Processed {len(mentors_data)} mentor records")
        mentors_count = upload_to_supabase(mentors_data, 'mentors')
        print(f"Successfully uploaded {mentors_count}/{len(mentors_data)} mentors")
        
        print("\nCSV data upload completed!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()