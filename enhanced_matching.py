import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.neighbors import NearestNeighbors
import matplotlib.pyplot as plt
from itertools import chain
import os
from typing import List, Dict, Any, Tuple, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Constants for feature weighting
WEIGHTS = {
    'skills': 0.20,
    'interests': 0.075,
    'field': 0.30,
    'age': 0.10,
    'languages': 0.175,
    'country': 0.15
}

def load_from_database() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load mentee and mentor data from Supabase database.
    Returns processed dataframes for mentees and mentors.
    """
    try:
        # Connect to Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL or key not found in environment variables")
            
        supabase = create_client(url, key)
        
        # Fetch data from Supabase
        mentee_response = supabase.table('mentees').select('*').execute()
        mentor_response = supabase.table('mentors').select('*').execute()
        
        if len(mentee_response.data) == 0 or len(mentor_response.data) == 0:
            raise ValueError("No data found in Supabase tables")
            
        mentee_data = pd.DataFrame(mentee_response.data)
        mentor_data = pd.DataFrame(mentor_response.data)
        
        print(f"[INFO] Successfully loaded {len(mentee_data)} mentees and {len(mentor_data)} mentors from Supabase")
    
    except Exception as e:
        print(f"[ERROR] Failed to load data from Supabase: {str(e)}")
        print("[DEBUG] Falling back to CSV files")
        
        # Fallback to CSV files for development
        mentee_data = pd.read_csv("mentee_data.csv")
        mentor_data = pd.read_csv("mentor_data.csv")
        
        print(f"[DEBUG] Loaded {len(mentee_data)} mentees and {len(mentor_data)} mentors from CSV")
    
    # Preprocess the data
    mentee_data["Speaking Language"] = mentee_data["Speaking Language"].fillna("")
    mentor_data["speaking_language"] = mentor_data["speaking_language"].fillna("")

    # Process STEM Skills and Interests
    mentee_data['STEM Skills'] = mentee_data['STEM Skills'].apply(
        lambda x: str(x).split(', ') if isinstance(x, str) else [])
    mentor_data['stem_skills'] = mentor_data['stem_skills'].apply(
        lambda x: str(x).split(', ') if isinstance(x, str) else [])
    mentee_data['Interests'] = mentee_data['Interests'].apply(
        lambda x: str(x).split(', ') if isinstance(x, str) else [])
    mentor_data['interests'] = mentor_data['interests'].apply(
        lambda x: str(x).split(', ') if isinstance(x, str) else [])

    # Process Languages
    mentee_data['languages'] = mentee_data['Speaking Language'].apply(
        lambda x: [lang.strip().lower() for lang in (x.replace("/", ",") if isinstance(x, str) else "").split(",") if lang.strip()]
    )
    mentor_data['languages'] = mentor_data['speaking_language'].apply(
        lambda x: [lang.strip().lower() for lang in str(x).split() if lang.strip()]
    )

    # Process Country
    mentee_data['country_clean'] = mentee_data['Country'].apply(lambda x: str(x).lower().strip())
    mentor_data['country_clean'] = mentor_data['country'].apply(lambda x: str(x).lower().strip())
    
    return mentee_data, mentor_data

def save_match_to_database(mentee_id: str, mentor_id: str, match_score: float) -> bool:
    """
    Save a mentor-mentee match to the database
    
    Args:
        mentee_id: The ID of the mentee
        mentor_id: The ID of the mentor
        match_score: The calculated match score
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Connect to Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL or key not found in environment variables")
            
        supabase = create_client(url, key)
        
        # Prepare match data
        match_data = {
            'mentee_id': mentee_id,
            'mentor_id': mentor_id,
            'match_score': match_score,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Insert into matches table
        response = supabase.table('matches').insert(match_data).execute()
        
        print(f"[INFO] Match saved: Mentee {mentee_id} + Mentor {mentor_id} = {match_score:.1f}%")
        return len(response.data) > 0
        
    except Exception as e:
        print(f"[ERROR] Failed to save match to database: {str(e)}")
        return False

def create_feature_vectors(mentee_data: pd.DataFrame, mentor_data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create feature vectors for matching algorithm using the union of classes for skills, interests, and languages.
    
    Args:
        mentee_data: Preprocessed mentee dataframe
        mentor_data: Preprocessed mentor dataframe
        
    Returns:
        Tuple containing feature vectors for mentees and mentors
    """
    # Ensure languages columns are lists
    mentee_data['languages'] = mentee_data['languages'].apply(lambda x: x if isinstance(x, list) else [])
    mentor_data['languages'] = mentor_data['languages'].apply(lambda x: x if isinstance(x, list) else [])
    
    mentee_data['STEM Skills'] = mentee_data['STEM Skills'].apply(lambda skills: [s.lower() for s in skills])
    mentor_data['stem_skills'] = mentor_data['stem_skills'].apply(lambda skills: [s.lower() for s in skills])
    mentee_data['Interests'] = mentee_data['Interests'].apply(lambda interests: [i.lower() for i in interests])
    mentor_data['interests'] = mentor_data['interests'].apply(lambda interests: [i.lower() for i in interests])
    
    all_skills = set(chain.from_iterable(mentee_data['STEM Skills'])) | set(chain.from_iterable(mentor_data['stem_skills']))
    all_interests = set(chain.from_iterable(mentee_data['Interests'])) | set(chain.from_iterable(mentor_data['interests']))
    all_languages = set(chain.from_iterable(mentee_data['languages'])) | set(chain.from_iterable(mentor_data['languages']))

    # Encode STEM Skills
    mlb_skills = MultiLabelBinarizer(classes=sorted(all_skills))
    mentee_skills = mlb_skills.fit_transform(mentee_data['STEM Skills'])
    mentor_skills = mlb_skills.transform(mentor_data['stem_skills'])

    # Encode Interests
    mlb_interests = MultiLabelBinarizer(classes=sorted(all_interests))
    mentee_interests = mlb_interests.fit_transform(mentee_data['Interests'])
    mentor_interests = mlb_interests.transform(mentor_data['interests'])

    # Encode Fields
    mentee_fields = pd.get_dummies(mentee_data['Desired Field'])
    mentor_fields = pd.get_dummies(mentor_data['field'])
    all_fields = list(set(mentee_fields.columns) | set(mentor_fields.columns))
    for col in all_fields:
        if col not in mentee_fields.columns:
            mentee_fields[col] = 0
        if col not in mentor_fields.columns:
            mentor_fields[col] = 0
    mentee_fields = mentee_fields[all_fields]
    mentor_fields = mentor_fields[all_fields]

    # Normalize Age
    mentee_age = mentee_data[['Age']].values / 100.0
    mentor_age = mentor_data[['age']].values / 100.0

    # Encode Languages
    mlb_languages = MultiLabelBinarizer(classes=sorted(all_languages))
    mentee_languages = mlb_languages.fit_transform(mentee_data['languages'])
    mentor_languages = mlb_languages.transform(mentor_data['languages'])

    # Encode Country
    mentee_country = pd.get_dummies(mentee_data['country_clean'])
    mentor_country = pd.get_dummies(mentor_data['country_clean'])
    all_countries = list(set(mentee_country.columns) | set(mentor_country.columns))
    for col in all_countries:
        if col not in mentee_country.columns:
            mentee_country[col] = 0
        if col not in mentor_country.columns:
            mentor_country[col] = 0
    mentee_country = mentee_country[all_countries]
    mentor_country = mentor_country[all_countries]

    # Combine features with weights
    mentee_features = np.hstack([
        mentee_skills * WEIGHTS['skills'],
        mentee_interests * WEIGHTS['interests'],
        mentee_fields.values * WEIGHTS['field'],
        mentee_age * WEIGHTS['age'],
        mentee_languages * WEIGHTS['languages'],
        mentee_country.values * WEIGHTS['country']
    ])
    mentor_features = np.hstack([
        mentor_skills * WEIGHTS['skills'],
        mentor_interests * WEIGHTS['interests'],
        mentor_fields.values * WEIGHTS['field'],
        mentor_age * WEIGHTS['age'],
        mentor_languages * WEIGHTS['languages'],
        mentor_country.values * WEIGHTS['country']
    ])
    
    return mentee_features, mentor_features

def build_knn_model(mentor_features: np.ndarray, n_neighbors: int = 5) -> NearestNeighbors:
    """
    Build a KNN model based on mentor features.
    
    Args:
        mentor_features: Feature vector for mentors
        n_neighbors: Number of nearest neighbors to find
        
    Returns:
        Fitted KNN model
    """
    actual_neighbors = min(n_neighbors, mentor_features.shape[0])
    knn = NearestNeighbors(n_neighbors=actual_neighbors, metric='euclidean')
    knn.fit(mentor_features)
    return knn

def find_mentors_for_mentee_id(mentee_id: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Main API function: Find matching mentors for a given mentee ID
    
    Args:
        mentee_id: The ID of the mentee to match
        k: Number of matches to return
        
    Returns:
        List of mentor matches with scores and details
    """
    # Load data
    mentee_data, mentor_data = load_from_database()
    
    # Find mentee index by ID
    try:
        mentee_idx = mentee_data[mentee_data['id'] == mentee_id].index[0]
    except (IndexError, KeyError):
        print(f"[ERROR] Mentee with ID {mentee_id} not found")
        return []
    
    # Create features and build model
    mentee_features, mentor_features = create_feature_vectors(mentee_data, mentor_data)
    knn_model = build_knn_model(mentor_features, n_neighbors=k)
    
    # Get matches
    mentee_vector = mentee_features[mentee_idx].reshape(1, -1)
    distances, indices = knn_model.kneighbors(mentee_vector)
    match_scores = 100 * (1.0 / (1.0 + distances[0]))
    
    # Build result objects
    matched_mentors = []
    for idx, score in zip(indices[0], match_scores):
        mentor = mentor_data.iloc[idx]
        mentor_id = mentor.get('id', f"mentor_{idx}")
        
        matched_mentors.append({
            'mentor_id': mentor_id,
            'name': mentor['name'],
            'field': mentor['field'],
            'skills': mentor['stem_skills'],
            'interests': mentor['interests'],
            'experience': mentor['work_experience'],
            'match_score': float(score),
            'languages': mentor['languages'],
            'country': mentor['country']
        })
        
        # Save match to database
        save_match_to_database(mentee_id, mentor_id, float(score))
    
    return matched_mentors

def find_mentors_for_new_mentee(mentee_data: Dict[str, Any], k: int = 5) -> List[Dict[str, Any]]:
    """
    Find matching mentors for a new mentee that isn't in the database yet
    
    Args:
        mentee_data: Dictionary with mentee information
        k: Number of matches to return
        
    Returns:
        List of mentor matches with scores and details
    """
    # Load existing data
    existing_mentees, mentor_data = load_from_database()
    
    # Create a DataFrame for the new mentee
    new_mentee = pd.DataFrame({
        'Name': [mentee_data.get('name', '')],
        'Country': [mentee_data.get('country', '')],
        'Speaking Language': [mentee_data.get('speaking_language', '')],
        'Desired Field': [mentee_data.get('desired_field', '')],
        'Degree': [mentee_data.get('degree', '')],
        'College': [mentee_data.get('college', '')],
        'STEM Skills': [mentee_data.get('stem_skills', [])],
        'Interests': [mentee_data.get('interests', [])],
        'Prior Work Experience': [mentee_data.get('prior_work_experience', '')],
        'Age': [mentee_data.get('age', 20)],
        'languages': [mentee_data.get('languages', [])],
        'country_clean': [mentee_data.get('country', '').lower().strip()]
    })
    
    # Combine with existing mentees for feature calculation
    combined_mentees = pd.concat([existing_mentees, new_mentee], ignore_index=True)
    
    # Create features and build model
    mentee_features, mentor_features = create_feature_vectors(combined_mentees, mentor_data)
    knn_model = build_knn_model(mentor_features, n_neighbors=k)
    
    # Get index of the new mentee (last row)
    new_mentee_idx = len(combined_mentees) - 1
    
    # Get matches
    mentee_vector = mentee_features[new_mentee_idx].reshape(1, -1)
    distances, indices = knn_model.kneighbors(mentee_vector)
    match_scores = 100 * (1.0 / (1.0 + distances[0]))
    
    # Build result objects
    matched_mentors = []
    for idx, score in zip(indices[0], match_scores):
        mentor = mentor_data.iloc[idx]
        mentor_id = mentor.get('id', f"mentor_{idx}")
        
        matched_mentors.append({
            'mentor_id': mentor_id,
            'name': mentor['name'],
            'field': mentor['field'],
            'skills': mentor['stem_skills'],
            'interests': mentor['interests'],
            'experience': mentor['work_experience'],
            'match_score': float(score),
            'languages': mentor['languages'],
            'country': mentor['country']
        })
    
    return matched_mentors

def create_mentee(mentee_data: Dict[str, Any]) -> str:
    """
    Create a new mentee in the database
    
    Args:
        mentee_data: Dictionary with mentee information
        
    Returns:
        ID of the newly created mentee
    """
    try:
        # Connect to Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL or key not found in environment variables")
            
        supabase = create_client(url, key)
        
        # Insert mentee data
        response = supabase.table('mentees').insert(mentee_data).execute()
        
        if response.data and len(response.data) > 0:
            new_id = response.data[0]['id']
            print(f"[INFO] Created new mentee: {mentee_data.get('name', 'Unknown')} with ID {new_id}")
            return new_id
        else:
            raise ValueError("No data returned from insert operation")
            
    except Exception as e:
        print(f"[ERROR] Failed to create mentee: {str(e)}")
        return f"mentee_{id(mentee_data)}"  # Fallback to dummy ID for development

def create_mentor(mentor_data: Dict[str, Any]) -> str:
    """
    Create a new mentor in the database
    
    Args:
        mentor_data: Dictionary with mentor information
        
    Returns:
        ID of the newly created mentor
    """
    try:
        # Connect to Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL or key not found in environment variables")
            
        supabase = create_client(url, key)
        
        # Insert mentor data
        response = supabase.table('mentors').insert(mentor_data).execute()
        
        if response.data and len(response.data) > 0:
            new_id = response.data[0]['id']
            print(f"[INFO] Created new mentor: {mentor_data.get('name', 'Unknown')} with ID {new_id}")
            return new_id
        else:
            raise ValueError("No data returned from insert operation")
            
    except Exception as e:
        print(f"[ERROR] Failed to create mentor: {str(e)}")
        return f"mentor_{id(mentor_data)}"  # Fallback to dummy ID for development

def get_all_mentees() -> List[Dict[str, Any]]:
    """
    Get all mentees from the database
    
    Returns:
        List of mentee data objects
    """
    try:
        # Connect to Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL or key not found in environment variables")
            
        supabase = create_client(url, key)
        
        # Fetch all mentees
        response = supabase.table('mentees').select('*').execute()
        
        return response.data
        
    except Exception as e:
        print(f"[ERROR] Failed to get mentees: {str(e)}")
        # Fallback to local data
        mentee_data, _ = load_from_database()
        return mentee_data.to_dict('records')

def get_all_mentors() -> List[Dict[str, Any]]:
    """
    Get all mentors from the database
    
    Returns:
        List of mentor data objects
    """
    try:
        # Connect to Supabase
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL or key not found in environment variables")
            
        supabase = create_client(url, key)
        
        # Fetch all mentors
        response = supabase.table('mentors').select('*').execute()
        
        return response.data
        
    except Exception as e:
        print(f"[ERROR] Failed to get mentors: {str(e)}")
        # Fallback to local data
        _, mentor_data = load_from_database()
        return mentor_data.to_dict('records')

def visualize_matches(mentee_name: str, matched_mentors: List[Dict[str, Any]], save_path: Optional[str] = None) -> str:
    """
    Create a bar chart visualization for mentor matches
    
    Args:
        mentee_name: Name of the mentee
        matched_mentors: List of matched mentors with scores
        save_path: Path to save the visualization (optional)
        
    Returns:
        Path to the saved visualization file
    """
    if not save_path:
        save_path = f"{mentee_name.replace(' ', '_')}_matches.png"
        
    names = [m['name'] for m in matched_mentors]
    scores = [m['match_score'] for m in matched_mentors]
    
    plt.figure(figsize=(12, 6))
    plt.barh(range(len(names)), scores, color='skyblue')
    plt.yticks(range(len(names)), names)
    plt.xlabel('Match Score (%)')
    plt.title(f'Top Mentor Matches for {mentee_name}')
    
    for i, score in enumerate(scores):
        plt.text(score + 1, i, f'{score:.1f}%', va='center')
        
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    
    return save_path

# Example usage:
if __name__ == "__main__":
    # This would be called by your frontend
    print("Mentor Matching Service - API Example")
    
    # Example: Get matches for an existing mentee
    # matches = find_mentors_for_mentee_id("mentee_123", k=5)
    
    # Example: Get matches for a new mentee
    new_mentee = {
        "name": "Jane Smith",
        "country": "United States",
        "speaking_language": "English, Spanish",
        "desired_field": "Data Science",
        "degree": "Bachelor's",
        "college": "MIT",
        "stem_skills": ["Python", "Machine Learning", "Statistics"],
        "interests": ["AI Ethics", "Research"],
        "prior_work_experience": "Internship at Google",
        "age": 22
    }
    
    # matches = find_mentors_for_new_mentee(new_mentee, k=3)
    # print(f"Found {len(matches)} matches for {new_mentee['name']}")