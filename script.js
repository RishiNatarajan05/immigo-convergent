import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.33.2/+esm'

document.addEventListener('DOMContentLoaded', function() {
  // Check which page we're on
  const isMenteePage = document.body.contains(document.getElementById('mentee-quiz'));
  const isMentorPage = document.body.contains(document.getElementById('mentor-quiz'));
  const isHomePage = !isMenteePage && !isMentorPage;
  const isMatchesPage = document.body.contains(document.getElementById('matches-container'));
  
  // Mentee page functionality
  if (isMenteePage) {
    initMenteeQuiz();
  }
  
  // Mentor page functionality
  if (isMentorPage) {
    initMentorQuiz();
  }
  
  // Matches page functionality
  if (isMatchesPage) {
    initMatchesPage();
  }
  
  // Initialize tag input functionality if present on page
  initTagInputs();
  
  // Check authentication status and update UI
  checkAuthStatus();
});

// Add Supabase client initialization
const supabaseUrl = 'https://thcfscypmqopiomlsdab.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRoY2ZzY3lwbXFvcGlvbWxzZGFiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDM1NDU3ODQsImV4cCI6MjA1OTEyMTc4NH0.fzM4bMjwGfO-9r72T8R6j1I7MaivyOZy2lhSd9r5HPk';
const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    persistSession: false
  },
  global: {
    headers: {
      'apikey': supabaseKey,
      'Authorization': `Bearer ${supabaseKey}`
    }
  }
});

// Helper function to safely handle string values
function sanitizeString(value) {
  // If value is already a string, return it; otherwise convert to string
  const str = typeof value === 'string' ? value : String(value);
  // Remove any problematic characters that might cause SQL issues
  return str.replace(/[\{\}\[\]"\\]/g, '');
}

// Helper function to format array data for PostgreSQL
function formatArrayForPostgres(items) {
  if (!items || items.length === 0) {
    return "{}";
  }
  
  // Ensure items are properly formatted for PostgreSQL arrays
  const sanitizedItems = items.map(item => sanitizeString(item));
  return "{" + sanitizedItems.join(",") + "}";
}

// Helper function to format languages for PostgreSQL arrays
function formatLanguagesForPostgres(languagesString) {
  if (!languagesString || languagesString.trim() === '') {
    return "{}";
  }
  
  // Split by comma, sanitize each language, then format as a PostgreSQL array
  const languages = languagesString
    .split(',')
    .map(lang => sanitizeString(lang.trim()))
    .filter(Boolean);
    
  return "{" + languages.join(",") + "}";
}

// Function to handle authentication status
function checkAuthStatus() {
  const userData = JSON.parse(localStorage.getItem("mentorMatchUser"));
  
  // Update nav menu based on auth status
  const authNav = document.getElementById('auth-nav');
  
  if (authNav) {
    if (userData && userData.isLoggedIn) {
      // User is logged in, show logout and dashboard
      authNav.innerHTML = `
        <a href="matches.html">My Matches</a>
        <a href="#" id="logout-btn">Logout</a>
      `;
      
      // Add logout event listener
      document.getElementById('logout-btn').addEventListener('click', function(e) {
        e.preventDefault();
        localStorage.removeItem("mentorMatchUser");
        window.location.href = "index.html";
      });
    } else {
      // User is not logged in, show login/signup
      authNav.innerHTML = `
        <a href="login.html">Login</a>
        <a href="role-select.html" class="btn">Sign Up</a>
      `;
    }
  }
}

// Mentee registration
async function submitMenteeForm() {
  try {
    // Get form fields
    const name = sanitizeString(document.getElementById('mentee-name').value);
    const email = sanitizeString(document.getElementById('mentee-email').value);
    const country = sanitizeString(document.getElementById('mentee-country').value);
    const speakingLanguages = document.getElementById('mentee-speaking-language').value;
    const desiredField = sanitizeString(document.getElementById('mentee-desired-field').value);
    const degree = sanitizeString(document.getElementById('mentee-degree').value);
    const college = sanitizeString(document.getElementById('mentee-college').value);
    const priorWorkExperience = sanitizeString(document.getElementById('mentee-experience').value);
    const age = parseInt(document.getElementById('mentee-age').value) || 0;
    const stemSkills = getTagsFromContainer('mentee-skills-tags');
    const interests = getTagsFromContainer('mentee-interests-tags');
    
    const menteeData = {
      name,
      email,
      country,
      speaking_languages: formatLanguagesForPostgres(speakingLanguages),
      desired_field: desiredField,
      degree,
      college,
      prior_work_experience: priorWorkExperience,
      age,
      stem_skills: formatArrayForPostgres(stemSkills),
      interests: formatArrayForPostgres(interests)
    };
    
    console.log('Submitting mentee data:', menteeData);
    
    // Insert into Supabase
    const { data, error } = await supabase
      .from('mentees')
      .insert([menteeData])
      .select();
    
    if (error) {
      console.error('Supabase insert error:', error);
      alert(`Error submitting form: ${error.message}`);
      return;
    }
    
    console.log('Mentee created successfully:', data);
    
    // Save user info in localStorage to maintain session
    localStorage.setItem("mentorMatchUser", JSON.stringify({
      isLoggedIn: true,
      role: 'mentee',
      id: data[0].id,
      name: data[0].name,
      email: data[0].email
    }));
    
    // Show success step with option to go to matches
    goToStep('mentee', 5, 6);
    
    // Update the success message to include a link to matches
    const successMessage = document.querySelector('#mentee-quiz .quiz-step[data-step="6"] .success-message');
    if (successMessage) {
      successMessage.innerHTML = `
        <h3>Thank You for Signing Up!</h3>
        <p>We've received your information and are excited to help you find the perfect mentor.</p>
        <p>Click below to see your potential mentor matches!</p>
        <button class="quiz-btn" id="mentee-see-matches">See Matches</button>
        <button class="quiz-btn secondary" id="mentee-done" style="margin-top: 10px;">Back to Home</button>
      `;
      
      // Add event listener for the new button
      document.getElementById('mentee-see-matches').addEventListener('click', function() {
        window.location.href = "matches.html";
      });
      
      // Re-add event listener for the done button
      document.getElementById('mentee-done').addEventListener('click', function() {
        window.location.href = "index.html";
      });
    }
    
  } catch (error) {
    console.error('Error creating mentee:', error.message);
    alert('There was an error submitting your information. Please try again: ' + error.message);
  }
}

// Mentor registration
async function submitMentorForm() {
  try {
    // Get form fields
    const name = sanitizeString(document.getElementById('mentor-name').value);
    const email = sanitizeString(document.getElementById('mentor-email').value);
    const country = sanitizeString(document.getElementById('mentor-country').value);
    const speakingLanguages = document.getElementById('mentor-speaking-language').value;
    const field = sanitizeString(document.getElementById('mentor-field').value);
    const degree = sanitizeString(document.getElementById('mentor-degree').value);
    const university = sanitizeString(document.getElementById('mentor-college').value);
    const workExperience = sanitizeString(document.getElementById('mentor-work-experience').value);
    const age = parseInt(document.getElementById('mentor-age').value) || 0;
    const stemSkills = getTagsFromContainer('mentor-skills-tags');
    const interests = getTagsFromContainer('mentor-interests-tags');
    
    const mentorData = {
      name,
      email,
      country,
      speaking_languages: formatLanguagesForPostgres(speakingLanguages),
      field,
      degree,
      university,
      work_experience: workExperience,
      age,
      stem_skills: formatArrayForPostgres(stemSkills),
      interests: formatArrayForPostgres(interests)
    };
    
    console.log('Submitting mentor data:', mentorData);
    
    // Insert into Supabase
    const { data, error } = await supabase
      .from('mentors')
      .insert([mentorData])
      .select();
    
    if (error) {
      console.error('Supabase insert error:', error);
      alert(`Error submitting form: ${error.message}`);
      return;
    }
    
    console.log('Mentor created successfully:', data);
    
    // Save user info in localStorage to maintain session
    localStorage.setItem("mentorMatchUser", JSON.stringify({
      isLoggedIn: true,
      role: 'mentor',
      id: data[0].id,
      name: data[0].name,
      email: data[0].email
    }));
    
    // Show success step with option to go to matches
    goToStep('mentor', 5, 6);
    
    // Update the success message to include a link to matches
    const successMessage = document.querySelector('#mentor-quiz .quiz-step[data-step="6"] .success-message');
    if (successMessage) {
      successMessage.innerHTML = `
        <h3>Thank You for Signing Up as a Mentor!</h3>
        <p>We've received your information and are excited for you to start mentoring.</p>
        <p>Click below to see potential mentees you can help!</p>
        <button class="quiz-btn" id="mentor-see-matches">See Matches</button>
        <button class="quiz-btn secondary" id="mentor-done" style="margin-top: 10px;">Back to Home</button>
      `;
      
      // Add event listener for the new button
      document.getElementById('mentor-see-matches').addEventListener('click', function() {
        window.location.href = "matches.html";
      });
      
      // Re-add event listener for the done button
      document.getElementById('mentor-done').addEventListener('click', function() {
        window.location.href = "index.html";
      });
    }
    
  } catch (error) {
    console.error('Error creating mentor:', error.message);
    alert('There was an error submitting your information. Please try again: ' + error.message);
  }
}

// Function to get tags from container
function getTagsFromContainer(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return [];
  
  const tags = container.querySelectorAll('.tag');
  return Array.from(tags).map(tag => {
    // Extract just the text content, not including the "×" button
    const tagText = tag.textContent.trim();
    return tagText.replace('×', '').trim();
  });
}

// Initialize tag inputs
function initTagInputs() {
  document.querySelectorAll('.tag-input').forEach(input => {
    const containerId = input.id.replace('-input', '-tags');
    const container = document.getElementById(containerId);
    
    if (!container) return;
    
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        const value = this.value.trim();
        if (value) {
          addTag(value, container);
          this.value = '';
        }
      }
    });
  });
}

// Add a tag
function addTag(text, container) {
  const tag = document.createElement('div');
  tag.className = 'tag';
  tag.textContent = text;
  
  const removeBtn = document.createElement('span');
  removeBtn.className = 'tag-remove';
  removeBtn.textContent = '×';
  removeBtn.addEventListener('click', function() {
    container.removeChild(tag);
  });
  
  tag.appendChild(removeBtn);
  container.appendChild(tag);
}

// Quiz navigation - Fixed to handle actual HTML structure
function goToStep(quizType, currentStep, nextStep) {
  // Find current and next step elements
  const currentStepEl = document.querySelector(`#${quizType}-quiz .quiz-step[data-step="${currentStep}"]`);
  const nextStepEl = document.querySelector(`#${quizType}-quiz .quiz-step[data-step="${nextStep}"]`);
  
  if (currentStepEl && nextStepEl) {
    // Hide current step
    currentStepEl.classList.remove('active');
    
    // Show next step
    nextStepEl.classList.add('active');
    
    // Update progress counter
    const currentStepCounter = document.getElementById(`${quizType}-current-step`);
    if (currentStepCounter) {
      currentStepCounter.textContent = nextStep;
    }
    
    // Update progress bar
    const totalSteps = document.getElementById(`${quizType}-total-steps`).textContent;
    const progressBar = document.getElementById(`${quizType}-progress`);
    if (progressBar) {
      const progressPercentage = (nextStep / parseInt(totalSteps)) * 100;
      progressBar.style.width = `${progressPercentage}%`;
    }
    
    // Scroll to top
    window.scrollTo(0, 0);
  } else {
    console.error(`Could not find steps for ${quizType}: current step ${currentStep} or next step ${nextStep}`);
    // Let's add some debugging to help identify the issue
    console.log('Current selector:', `#${quizType}-quiz .quiz-step[data-step="${currentStep}"]`);
    console.log('Next selector:', `#${quizType}-quiz .quiz-step[data-step="${nextStep}"]`);
    console.log('Current element found:', currentStepEl);
    console.log('Next element found:', nextStepEl);
    console.log('All quiz steps:', document.querySelectorAll(`#${quizType}-quiz .quiz-step`));
  }
}

// Initialize mentee quiz
function initMenteeQuiz() {
  // Step 1 next button
  document.getElementById('mentee-next-1').addEventListener('click', function() {
    goToStep('mentee', 1, 2);
  });
  
  // Step 2 buttons
  document.getElementById('mentee-prev-2').addEventListener('click', function() {
    goToStep('mentee', 2, 1);
  });
  
  document.getElementById('mentee-next-2').addEventListener('click', function() {
    goToStep('mentee', 2, 3);
  });
  
  // Step 3 buttons
  document.getElementById('mentee-prev-3').addEventListener('click', function() {
    goToStep('mentee', 3, 2);
  });
  
  document.getElementById('mentee-next-3').addEventListener('click', function() {
    goToStep('mentee', 3, 4);
  });
  
  // Step 4 buttons
  document.getElementById('mentee-prev-4').addEventListener('click', function() {
    goToStep('mentee', 4, 3);
  });
  
  document.getElementById('mentee-next-4').addEventListener('click', function() {
    goToStep('mentee', 4, 5);
  });
  
  // Step 5 buttons
  document.getElementById('mentee-prev-5').addEventListener('click', function() {
    goToStep('mentee', 5, 4);
  });
  
  document.getElementById('mentee-submit').addEventListener('click', function() {
    submitMenteeForm();
  });
  
  // Final done button
  document.getElementById('mentee-done').addEventListener('click', function() {
    window.location.href = "index.html";
  });
  
  // Close button
  document.getElementById('mentee-close').addEventListener('click', function() {
    window.location.href = "index.html";
  });
}

// Initialize mentor quiz
function initMentorQuiz() {
  // Step 1 next button
  document.getElementById('mentor-next-1').addEventListener('click', function() {
    goToStep('mentor', 1, 2);
  });
  
  // Step 2 buttons
  document.getElementById('mentor-prev-2').addEventListener('click', function() {
    goToStep('mentor', 2, 1);
  });
  
  document.getElementById('mentor-next-2').addEventListener('click', function() {
    goToStep('mentor', 2, 3);
  });
  
  // Step 3 buttons
  document.getElementById('mentor-prev-3').addEventListener('click', function() {
    goToStep('mentor', 3, 2);
  });
  
  document.getElementById('mentor-next-3').addEventListener('click', function() {
    goToStep('mentor', 3, 4);
  });
  
  // Step 4 buttons
  document.getElementById('mentor-prev-4').addEventListener('click', function() {
    goToStep('mentor', 4, 3);
  });
  
  document.getElementById('mentor-next-4').addEventListener('click', function() {
    goToStep('mentor', 4, 5);
  });
  
  // Step 5 buttons
  document.getElementById('mentor-prev-5').addEventListener('click', function() {
    goToStep('mentor', 5, 4);
  });
  
  document.getElementById('mentor-submit').addEventListener('click', function() {
    submitMentorForm();
  });
  
  // Final done button
  document.getElementById('mentor-done').addEventListener('click', function() {
    window.location.href = "index.html";
  });
  
  // Close button
  document.getElementById('mentor-close').addEventListener('click', function() {
    window.location.href = "index.html";
  });
}

// Admin function to load CSV data into Supabase
async function loadCSVDataToSupabase() {
  try {
    // Check if we're on the admin page or have admin rights
    if (!confirm('This will upload CSV data to Supabase. Continue?')) {
      return;
    }
    
    // Upload mentors
    const mentorsCount = await uploadCSVToSupabase('mentordataconvergent.csv', 'mentors');
    
    // Upload mentees
    const menteesCount = await uploadCSVToSupabase('menteedataconvergent.csv', 'mentees');
    
    alert(`CSV data uploaded successfully to Supabase!\nMentors: ${mentorsCount}\nMentees: ${menteesCount}`);
    
  } catch (error) {
    console.error('Error uploading CSV data:', error);
    alert(`Error uploading CSV data: ${error.message}`);
  }
}

// Add admin function to window for console access
window.loadCSVDataToSupabase = loadCSVDataToSupabase;

// Initialize matches page
function initMatchesPage() {
  // Get user info from localStorage
  const userData = JSON.parse(localStorage.getItem("mentorMatchUser"));
  
  if (!userData || !userData.isLoggedIn) {
    // User is not logged in, show error message
    const matchesContainer = document.getElementById('matches-container');
    if (matchesContainer) {
      matchesContainer.innerHTML = `
        <div class="error-message">
          <h2>Not Logged In</h2>
          <p>You need to be logged in to view your matches.</p>
          <div class="action-buttons">
            <a href="login.html" class="btn primary-btn">Login</a>
            <a href="role-select.html" class="btn secondary-btn">Sign Up</a>
          </div>
        </div>
      `;
    }
    return;
  }
  
  // User is logged in, load their matches based on role
  loadMatches(userData);
}

// Load matches for the current user
async function loadMatches(userData) {
  const matchesContainer = document.getElementById('matches-container');
  if (!matchesContainer) return;
  
  try {
    // Show loading state
    matchesContainer.innerHTML = '<p class="loading">Loading your matches...</p>';
    
    let matches = [];
    
    if (userData.role === 'mentee') {
      // This mentee is looking for mentors
      // 1. Get the mentee's data
      const { data: menteeData, error: menteeError } = await supabase
        .from('mentees')
        .select('*')
        .eq('id', userData.id)
        .single();
        
      if (menteeError) throw menteeError;
      
      if (!menteeData) {
        matchesContainer.innerHTML = '<p class="error">Unable to find your profile. Please try again later.</p>';
        return;
      }
      
      // 2. Find potential mentor matches
      const { data: mentors, error: mentorsError } = await supabase
        .from('mentors')
        .select('*');
        
      if (mentorsError) throw mentorsError;
      
      // 3. Calculate match scores
      matches = calculateMatches(menteeData, mentors, 'mentee');
      
    } else if (userData.role === 'mentor') {
      // This mentor is looking for mentees
      // 1. Get the mentor's data
      const { data: mentorData, error: mentorError } = await supabase
        .from('mentors')
        .select('*')
        .eq('id', userData.id)
        .single();
        
      if (mentorError) throw mentorError;
      
      if (!mentorData) {
        matchesContainer.innerHTML = '<p class="error">Unable to find your profile. Please try again later.</p>';
        return;
      }
      
      // 2. Find potential mentee matches
      const { data: mentees, error: menteesError } = await supabase
        .from('mentees')
        .select('*');
        
      if (menteesError) throw menteesError;
      
      // 3. Calculate match scores
      matches = calculateMatches(mentorData, mentees, 'mentor');
    }
    
    // Display matches
    displayMatches(matches);
    
  } catch (error) {
    console.error('Error loading matches:', error);
    matchesContainer.innerHTML = `
      <p class="error">Error loading matches: ${error.message}</p>
      <button class="btn primary-btn" onclick="window.location.reload()">Try Again</button>
    `;
  }
}

// Calculate match scores between a user and potential matches
function calculateMatches(userData, potentialMatches, userRole) {
  // Make a copy of the potential matches to avoid modifying the originals
  const matches = JSON.parse(JSON.stringify(potentialMatches));
  
  // Determine field names based on role
  const userDesiredField = userRole === 'mentee' ? userData.desired_field : userData.field;
  const matchFieldName = userRole === 'mentee' ? 'field' : 'desired_field';
  
  // Process arrays if they're stored as PostgreSQL array strings
  const userSkills = processPgArray(userData.stem_skills);
  const userInterests = processPgArray(userData.interests);
  const userLanguages = processPgArray(userData.speaking_languages);
  
  // Calculate match scores
  matches.forEach(match => {
    let score = 0;
    
    // Field match (most important)
    const matchField = match[matchFieldName];
    if (userDesiredField && matchField && 
        userDesiredField.toLowerCase() === matchField.toLowerCase()) {
      score += 40;
    }
    
    // Skills match
    const matchSkills = processPgArray(match.stem_skills);
    const skillOverlap = countOverlap(userSkills, matchSkills);
    if (skillOverlap > 0) {
      score += Math.min(skillOverlap * 10, 30); // Max 30 points
    }
    
    // Interests match
    const matchInterests = processPgArray(match.interests);
    const interestOverlap = countOverlap(userInterests, matchInterests);
    if (interestOverlap > 0) {
      score += Math.min(interestOverlap * 5, 15); // Max 15 points
    }
    
    // Language match
    const matchLanguages = processPgArray(match.speaking_languages);
    const languageOverlap = countOverlap(userLanguages, matchLanguages);
    if (languageOverlap > 0) {
      score += 10;
    }
    
    // Country match (small bonus)
    if (userData.country && match.country && 
        userData.country.toLowerCase() === match.country.toLowerCase()) {
      score += 5;
    }
    
    // Add the score to the match
    match.match_score = score;
  });
  
  // Sort by match score (highest first)
  matches.sort((a, b) => b.match_score - a.match_score);
  
  // Return top match (limiting to 1)
  return matches.slice(0, 1);
}

// Helper function to process PostgreSQL array strings
function processPgArray(pgArray) {
  if (!pgArray) return [];
  
  // If it's already an array, return it
  if (Array.isArray(pgArray)) return pgArray.map(item => item.toLowerCase());
  
  // If it's a PostgreSQL array string like "{item1,item2}"
  if (typeof pgArray === 'string' && pgArray.startsWith('{') && pgArray.endsWith('}')) {
    // Extract items between the braces and split by comma
    const content = pgArray.substring(1, pgArray.length - 1);
    if (!content) return [];
    
    return content.split(',')
      .map(item => item.trim().toLowerCase())
      .filter(item => item.length > 0);
  }
  
  // If it's a regular string (comma or semicolon-separated)
  if (typeof pgArray === 'string') {
    const separator = pgArray.includes(';') ? ';' : ',';
    return pgArray.split(separator)
      .map(item => item.trim().toLowerCase())
      .filter(item => item.length > 0);
  }
  
  return [];
}

// Helper function to count overlapping items between two arrays
function countOverlap(array1, array2) {
  const set1 = new Set(array1.map(item => item.toLowerCase()));
  return array2.filter(item => set1.has(item.toLowerCase())).length;
}

// Display matches on the page
function displayMatches(matches) {
  const matchesContainer = document.getElementById('matches-container');
  if (!matchesContainer) return;
  if (!matches || matches.length === 0) {
    matchesContainer.innerHTML = `
      <p class="no-matches">No matches found. Try updating your profile to find better matches.</p>
    `;
    return;
  }
  // Get user data to determine role
  const userData = JSON.parse(localStorage.getItem("mentorMatchUser"));
  const userRole = userData?.role || 'mentee';
  matchesContainer.innerHTML = '';
  const match = matches[0];
  const matchPercentage = Math.min(100, Math.round(match.match_score));
  let roleText = '';
  if (userRole === 'mentee') {
    roleText = `${match.field || 'Mentor'} • ${matchPercentage}% Match`;
  } else {
    roleText = `${match.desired_field || 'Mentee'} • ${matchPercentage}% Match`;
  }
  const countryFlag = '🌎';
  const matchCard = document.createElement('div');
  matchCard.className = 'match-card';
  matchCard.innerHTML = `
    <div class="match-image-placeholder">
      <img src="abcd.jpg" alt="Profile picture" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;" />
    </div>
    <h3 class="match-name">${match.name}</h3>
    <p class="match-role">${roleText}</p>
    <p class="match-country">
      <span>${countryFlag}</span>
      <span>${match.country || 'Not specified'}</span>
    </p>
    <button class="btn btn-primary match-action-button" data-match-id="${match.id}">
      ${userRole === 'mentee' ? 'Learn More' : 'Contact Mentee'}
    </button>
  `;
  matchesContainer.appendChild(matchCard);
  matchCard.querySelector('.match-action-button').addEventListener('click', handleMatchAction);
}

// Format arrays for display
function formatArrayForDisplay(array) {
  const processedArray = processPgArray(array);
  
  if (!processedArray || processedArray.length === 0) {
    return 'None';
  }
  
  return processedArray.join(', ');
}

// Handle match action button clicks
function handleMatchAction(event) {
  const button = event.target;
  const matchId = button.getAttribute('data-match-id');
  const userData = JSON.parse(localStorage.getItem("mentorMatchUser"));

  if (!userData || !userData.isLoggedIn) {
    alert('You need to be logged in to perform this action.');
    return;
  }

  // Always redirect to the dashboard, no alert or popup
  if (userData.role === 'mentee') {
    // Save the mentor request info to localStorage (optional, as before)
    localStorage.setItem("requestedMentorId", matchId);
    // Redirect to mentee dashboard
    window.location.href = "mentee-dashboard.html";
  } else {
    // For mentors, redirect to mentor dashboard (if exists)
    localStorage.setItem("requestedMenteeId", matchId);
    window.location.href = "mentor-dashboard.html";
  }
}