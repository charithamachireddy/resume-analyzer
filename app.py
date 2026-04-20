from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import google.generativeai as genai
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import nltk
from collections import Counter
import string

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploaded_resumes'
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure Gemini AI
GEMINI_API_KEY = "AIzaSyBiOtuIccMk17G9SojG0HpyUTqB2I55A2M"  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

def extract_text_from_txt(file_path):
    text = ""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    except Exception as e:
        print(f"Error reading TXT: {e}")
    return text

def calculate_nlp_score(resume_text):
    # Basic NLP analysis
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(resume_text.lower())
    words = [word for word in words if word.isalpha() and word not in stop_words]
    
    # Key skills and keywords for ATS
    technical_skills = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'html', 'css', 
                       'machine learning', 'data science', 'aws', 'docker', 'git', 'agile']
    
    soft_skills = ['leadership', 'communication', 'teamwork', 'problem solving', 'analytical',
                   'project management', 'collaboration', 'creative', 'innovative']
    
    # Count skill occurrences
    skill_count = 0
    for skill in technical_skills + soft_skills:
        if skill.replace(' ', '') in resume_text.lower().replace(' ', ''):
            skill_count += 1
    
    # Basic scoring algorithm
    word_count = len(words)
    unique_words = len(set(words))
    
    # Score calculation (0-100)
    base_score = min(50, word_count / 10)  # Base score from word count
    skill_score = min(30, skill_count * 2)  # Skill score
    diversity_score = min(20, unique_words / 20)  # Word diversity score
    
    total_score = base_score + skill_score + diversity_score
    return min(100, max(0, total_score))

def analyze_resume_with_gemini(resume_text):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
        Analyze this resume and provide a comprehensive ATS (Applicant Tracking System) analysis:

        Resume Text: {resume_text}

        Please provide:
        1. ATS Score (0-100) with brief justification
        2. Top 5 specific improvements to increase ATS score
        3. Missing keywords that should be added
        4. Formatting suggestions
        5. Overall strengths and weaknesses

        Format your response as JSON with the following structure:
        {{
            "ats_score": <number>,
            "score_justification": "<brief explanation>",
            "improvements": ["<improvement1>", "<improvement2>", ...],
            "missing_keywords": ["<keyword1>", "<keyword2>", ...],
            "formatting_suggestions": ["<suggestion1>", "<suggestion2>", ...],
            "strengths": ["<strength1>", "<strength2>", ...],
            "weaknesses": ["<weakness1>", "<weakness2>", ...]
        }}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def get_youtube_videos(query, count=4):
    # This is a simplified version - you might want to use YouTube API for better results
    videos = [
        {
            "title": "How to Write a Resume That Gets Noticed",
            "url": "https://www.youtube.com/watch?v=Tt08KmFfIYQ",
            "thumbnail": "https://img.youtube.com/vi/Tt08KmFfIYQ/maxresdefault.jpg"
        },
        {
            "title": "ATS Resume Tips - How to Pass Applicant Tracking Systems",
            "url": "https://www.youtube.com/watch?v=sN19aNmjBoU",
            "thumbnail": "https://img.youtube.com/vi/sN19aNmjBoU/maxresdefault.jpg"
        },
        {
            "title": "Resume Keywords - How to Use Them Effectively",
            "url": "https://www.youtube.com/watch?v=j0Zm6TMr-eI",
            "thumbnail": "https://img.youtube.com/vi/j0Zm6TMr-eI/maxresdefault.jpg"
        },
        {
            "title": "Common Resume Mistakes to Avoid",
            "url": "https://www.youtube.com/watch?v=BYUy1yvjHxE",
            "thumbnail": "https://img.youtube.com/vi/BYUy1yvjHxE/maxresdefault.jpg"
        }
    ]
    return videos

def get_placement_videos():
    videos = [
        {
            "title": "How to get Tech Placement in 6 Months?",
            "url": "https://www.youtube.com/watch?v=m7VcIH_N9ZY",
            "thumbnail": "https://img.youtube.com/vi/KdXAUst8bIc/maxresdefault.jpg"
        },
        {
            "title": "Campus Placement Preparation Strategy",
            "url": "https://www.youtube.com/watch?v=2cf9xo1S134",
            "thumbnail": "https://img.youtube.com/vi/2cf9xo1S134/maxresdefault.jpg"
        },
        {
            "title": "Mock Interview Tips and Tricks",
            "url": "https://www.youtube.com/watch?v=1qw5ITr3k9E",
            "thumbnail": "https://img.youtube.com/vi/1qw5ITr3k9E/maxresdefault.jpg"
        },
        {
            "title": "Aptitude Test Preparation for Placements",
            "url": "https://www.youtube.com/watch?v=7Z0mLf3ufDM",
            "thumbnail": "https://img.youtube.com/vi/7Z0mLf3ufDM/maxresdefault.jpg"
        }
    ]
    return videos



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jobs')
def jobs():
    return render_template('jobs.html')

@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text based on file type
        if filename.lower().endswith('.pdf'):
            resume_text = extract_text_from_pdf(filepath)
        elif filename.lower().endswith('.docx'):
            resume_text = extract_text_from_docx(filepath)
        else:
            resume_text = extract_text_from_txt(filepath)
        
        if not resume_text.strip():
            return jsonify({'error': 'Could not extract text from resume'}), 400
        
        # Analyze with Gemini AI
        gemini_analysis = analyze_resume_with_gemini(resume_text)
        
        # Calculate NLP score as backup
        nlp_score = calculate_nlp_score(resume_text)
        
        # Parse Gemini response
        analysis_data = {}
        if gemini_analysis:
            try:
                # Clean the response to extract JSON
                json_start = gemini_analysis.find('{')
                json_end = gemini_analysis.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = gemini_analysis[json_start:json_end]
                    analysis_data = json.loads(json_str)
            except:
                pass
        
        # Fallback analysis if Gemini fails
        if not analysis_data:
            analysis_data = {
                "ats_score": nlp_score,
                "score_justification": "Score based on keyword analysis and resume structure",
                "improvements": [
                    "Add more industry-specific keywords",
                    "Include quantifiable achievements",
                    "Optimize resume format for ATS",
                    "Add relevant technical skills",
                    "Include action verbs in descriptions"
                ],
                "missing_keywords": ["python", "javascript", "project management", "analytical", "communication"],
                "formatting_suggestions": ["Use standard headings", "Avoid graphics", "Use bullet points", "Keep consistent formatting"],
                "strengths": ["Clear structure", "Relevant experience"],
                "weaknesses": ["Missing keywords", "Needs quantifiable results"]
            }
        
        # Get YouTube videos
        videos = get_youtube_videos("resume improvement")
        
        return jsonify({
            'success': True,
            'analysis': analysis_data,
            'videos': videos,
            'filename': filename
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/get_jobs')
def get_jobs():
    city = request.args.get('city', '').strip()
    job_title = request.args.get('job_title', '').strip()
    
    if not city or not job_title:
        return jsonify({'error': 'City and job title are required'}), 400
    
    # Generate job search links
    job_links = {
        'LinkedIn': f"https://www.linkedin.com/jobs/search/?keywords={job_title.replace(' ', '%20')}&location={city.replace(' ', '%20')}",
        'Indeed': f"https://www.indeed.com/jobs?q={job_title.replace(' ', '+')}&l={city.replace(' ', '+')}",
        'Glassdoor': f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={job_title.replace(' ', '+')}&locT=C&locId={city.replace(' ', '+')}",
        'Naukri': f"https://www.naukri.com/{job_title.replace(' ', '-')}-jobs-in-{city.replace(' ', '-')}",
        'Monster': f"https://www.monster.com/jobs/search/?q={job_title.replace(' ', '+')}&where={city.replace(' ', '+')}",
        'AngelList': f"https://angel.co/jobs?keywords={job_title.replace(' ', '%20')}&location={city.replace(' ', '%20')}"
    }
    
    return jsonify({
        'city': city,
        'job_title': job_title,
        'job_links': job_links
    })

if __name__ == '__main__':
    app.run(debug=True)