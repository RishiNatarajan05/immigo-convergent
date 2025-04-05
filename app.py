from flask import Flask, request, jsonify, send_from_directory
import os
import json
import csv

app = Flask(__name__, static_folder='.', static_url_path='')

# Enable CORS manually
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Serve static files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_file(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    else:
        return send_from_directory('.', 'index.html')

# Load mentee data from CSV
def load_mentees():
    mentees = []
    try:
        with open('menteedataconvergent.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Process the data
                mentee = {
                    'id': row.get('id', f"mentee_{len(mentees)}"),
                    'name': row.get('Name', ''),
                    'country': row.get('Country', ''),
                    'speaking_language': row.get('Speaking Language', ''),
                    'desired_field': row.get('Desired Field', ''),
                    'degree': row.get('Degree', ''),
                    'college': row.get('College', ''),
                    'prior_work_experience': row.get('Prior Work Experience', ''),
                    'age': int(row.get('Age', 0)) if row.get('Age', '').isdigit() else 0,
                    'stem_skills': row.get('STEM Skills', '').split(', ') if row.get('STEM Skills') else [],
                    'interests': row.get('Interests', '').split(', ') if row.get('Interests') else []
                }
                mentees.append(mentee)
        print(f"Loaded {len(mentees)} mentees from CSV")
    except Exception as e:
        print(f"Error loading mentees: {str(e)}")
    return mentees

# Load mentor data from CSV
def load_mentors():
    mentors = []
    try:
        with open('mentordataconvergent.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Process the data
                mentor = {
                    'id': row.get('id', f"mentor_{len(mentors)}"),
                    'name': row.get('name', ''),
                    'country': row.get('country', ''),
                    'speaking_language': row.get('speaking_language', ''),
                    'field': row.get('field', ''),
                    'degree': row.get('degree', ''),
                    'university': row.get('university', ''),
                    'work_experience': row.get('work_experience', ''),
                    'age': int(row.get('age', 0)) if row.get('age', '').isdigit() else 0,
                    'stem_skills': row.get('stem_skills', '').split(', ') if row.get('stem_skills') else [],
                    'interests': row.get('interests', '').split(', ') if row.get('interests') else []
                }
                mentors.append(mentor)
        print(f"Loaded {len(mentors)} mentors from CSV")
    except Exception as e:
        print(f"Error loading mentors: {str(e)}")
    return mentors

# Simple matching algorithm
def match_algorithm(mentee, mentors, k=5):
    matches = []
    
    for mentor in mentors:
        score = 0
        
        # Match field (most important)
        if mentee['desired_field'].lower() == mentor['field'].lower():
            score += 40
            
        # Match skills
        mentee_skills = set(s.lower() for s in mentee['stem_skills'])
        mentor_skills = set(s.lower() for s in mentor['stem_skills'])
        skill_overlap = len(mentee_skills.intersection(mentor_skills))
        if skill_overlap > 0:
            score += min(skill_overlap * 10, 30)  # Max 30 points for skills
            
        # Match interests
        mentee_interests = set(i.lower() for i in mentee['interests'])
        mentor_interests = set(i.lower() for i in mentor['interests'])
        interest_overlap = len(mentee_interests.intersection(mentor_interests))
        if interest_overlap > 0:
            score += min(interest_overlap * 5, 15)  # Max 15 points for interests
            
        # Match language
        if mentee['speaking_language'] and mentor['speaking_language']:
            mentee_languages = set(lang.strip().lower() for lang in mentee['speaking_language'].split(','))
            mentor_languages = set(lang.strip().lower() for lang in mentor['speaking_language'].split(','))
            if mentee_languages.intersection(mentor_languages):
                score += 10
                
        # Match country (small bonus)
        if mentee['country'].lower() == mentor['country'].lower():
            score += 5
            
        matches.append({
            'mentor_id': mentor['id'],
            'name': mentor['name'],
            'field': mentor['field'],
            'skills': mentor['stem_skills'],
            'interests': mentor['interests'],
            'experience': mentor['work_experience'],
            'match_score': score,
            'languages': mentor['speaking_language'].split(',') if mentor['speaking_language'] else [],
            'country': mentor['country']
        })
    
    # Sort by score and return top k
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches[:k]

# Keep track of matches in memory
matches_db = []

@app.route('/api/matching/mentee/<mentee_id>', methods=['GET'])
def get_matches(mentee_id):
    """Get mentor matches for a specific mentee."""
    try:
        # Get number of matches to return
        k = int(request.args.get('limit', 5))
        
        # Load data
        mentees = load_mentees()
        mentors = load_mentors()
        
        # Find mentee
        mentee = next((m for m in mentees if m['id'] == mentee_id), None)
        
        if not mentee:
            return jsonify({
                "success": False,
                "message": f"Mentee with ID {mentee_id} not found",
                "data": [],
                "mentee_id": mentee_id
            }), 404
        
        # Get matches
        matches = match_algorithm(mentee, mentors, k=k)
        
        # Save matches to in-memory DB
        for match in matches:
            match_record = {
                'id': f"match_{len(matches_db)}",
                'mentee_id': mentee_id,
                'mentor_id': match['mentor_id'],
                'match_score': match['match_score'],
                'status': 'pending',
                'created_at': 'now'
            }
            matches_db.append(match_record)
        
        # Return the matches
        return jsonify({
            "success": True,
            "message": f"Found {len(matches)} matches for mentee {mentee_id}",
            "data": matches,
            "mentee_id": mentee_id
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error finding matches: {str(e)}",
            "data": [],
            "mentee_id": mentee_id
        }), 500

@app.route('/api/mentees', methods=['POST'])
def create_mentee():
    """Create a new mentee."""
    try:
        # Get mentee data from request
        mentee_data = request.json
        
        if not mentee_data:
            return jsonify({
                "success": False,
                "message": "No mentee data provided",
                "data": None
            }), 400
        
        # Generate a new ID
        mentee_id = f"mentee_{len(load_mentees()) + 1}"
        
        # Add to our in-memory mentees for now
        # In a real application, we would save to a database
        
        # Return success response with mentee ID
        return jsonify({
            "success": True,
            "message": "Mentee created successfully",
            "data": {
                "mentee_id": mentee_id
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating mentee: {str(e)}",
            "data": None
        }), 500

@app.route('/api/mentors', methods=['POST'])
def create_mentor():
    """Create a new mentor."""
    try:
        # Get mentor data from request
        mentor_data = request.json
        
        if not mentor_data:
            return jsonify({
                "success": False,
                "message": "No mentor data provided",
                "data": None
            }), 400
        
        # Generate a new ID
        mentor_id = f"mentor_{len(load_mentors()) + 1}"
        
        # Add to our in-memory mentors for now
        # In a real application, we would save to a database
        
        # Return success response with mentor ID
        return jsonify({
            "success": True,
            "message": "Mentor created successfully",
            "data": {
                "mentor_id": mentor_id
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating mentor: {str(e)}",
            "data": None
        }), 500

@app.route('/api/mentees/<mentee_id>/match', methods=['POST'])
def generate_matches(mentee_id):
    """Generate matches for a specific mentee."""
    try:
        # Get number of matches to return
        k = int(request.args.get('limit', 5))
        
        # Load data
        mentees = load_mentees()
        mentors = load_mentors()
        
        # Find mentee
        mentee = next((m for m in mentees if m['id'] == mentee_id), None)
        
        if not mentee:
            return jsonify({
                "success": False,
                "message": f"Mentee with ID {mentee_id} not found",
                "data": None
            }), 404
        
        # Generate matches
        matches = match_algorithm(mentee, mentors, k=k)
        
        # Return success response with matches
        return jsonify({
            "success": True,
            "message": f"Generated {len(matches)} matches for mentee {mentee_id}",
            "data": matches
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating matches: {str(e)}",
            "data": None
        }), 500

@app.route('/api/matches/<match_id>/update-status', methods=['PUT'])
def update_match_status(match_id):
    """Update the status of a match."""
    try:
        # Get status from request
        status = request.json.get('status')
        
        if not status:
            return jsonify({
                "success": False,
                "message": "No status provided",
                "data": None
            }), 400
        
        # Valid statuses
        valid_statuses = ['pending', 'requested', 'accepted', 'rejected']
        if status not in valid_statuses:
            return jsonify({
                "success": False,
                "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                "data": None
            }), 400
        
        # Find the match in our in-memory DB
        match = next((m for m in matches_db if m['id'] == match_id), None)
        
        if not match:
            return jsonify({
                "success": False,
                "message": f"Match with ID {match_id} not found",
                "data": None
            }), 404
            
        # Update status
        match['status'] = status
            
        # Return success response
        return jsonify({
            "success": True,
            "message": f"Match status updated to {status}",
            "data": match
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating match status: {str(e)}",
            "data": None
        }), 500

@app.route('/api/mentee/<mentee_id>/matches', methods=['GET'])
def get_mentee_matches(mentee_id):
    """Get all matches for a specific mentee."""
    try:
        # Find matches for this mentee in our in-memory DB
        mentee_matches = [m for m in matches_db if m['mentee_id'] == mentee_id]
        
        # Get mentor details for each match
        mentors = load_mentors()
        
        for match in mentee_matches:
            mentor = next((m for m in mentors if m['id'] == match['mentor_id']), None)
            if mentor:
                match['mentor'] = mentor
        
        # Return matches
        return jsonify({
            "success": True,
            "message": f"Found {len(mentee_matches)} matches for mentee {mentee_id}",
            "data": mentee_matches
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting mentee matches: {str(e)}",
            "data": []
        }), 500

@app.route('/api/mentor/<mentor_id>/matches', methods=['GET'])
def get_mentor_matches(mentor_id):
    """Get all matches for a specific mentor."""
    try:
        # Find matches for this mentor in our in-memory DB
        mentor_matches = [m for m in matches_db if m['mentor_id'] == mentor_id]
        
        # Get mentee details for each match
        mentees = load_mentees()
        
        for match in mentor_matches:
            mentee = next((m for m in mentees if m['id'] == match['mentee_id']), None)
            if mentee:
                match['mentee'] = mentee
        
        # Return matches
        return jsonify({
            "success": True,
            "message": f"Found {len(mentor_matches)} matches for mentor {mentor_id}",
            "data": mentor_matches
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting mentor matches: {str(e)}",
            "data": []
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')