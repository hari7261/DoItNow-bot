import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import asyncio
import tempfile
import speech_recognition as sr
import time

# Configuration
TELEGRAM_TOKEN = "YOUR-TELEGRAM-API"
GEMINI_API_KEY = "YOUR-GEMINI-API"

# Initialize AI models
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# Voice recognizer
recognizer = sr.Recognizer()

# User session storage
user_sessions = {}

class UserSession:
    def __init__(self):
        self.job_data = None
        self.questions = []
        self.current_question = 0
        self.answers = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_sessions[user_id] = UserSession()
    await update.message.reply_text(
        "🚀 Welcome to Interview Prep Bot!\n"
        "Send me a job listing URL (LinkedIn, Indeed, etc.) to begin."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession()

    if update.message.text and ("http://" in update.message.text or "https://" in update.message.text):
        await handle_job_url(update, context)
    elif update.message.text:
        await handle_text_answer(update, context)

async def handle_job_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = update.message.text
    
    await update.message.reply_text("🔍 Analyzing the job posting...")
    
    try:
        job_data = scrape_job_details(url)
        user_sessions[user_id].job_data = job_data
        
        # Format requirements and responsibilities more cleanly
        requirements = job_data['requirements'][:3] if job_data['requirements'] else []
        responsibilities = job_data['responsibilities'][:3] if job_data['responsibilities'] else []
        
        # Remove any items that are too short or look like placeholders
        requirements = [r for r in requirements if len(r) > 30 and 'job' not in r.lower()[:10]]
        responsibilities = [r for r in responsibilities if len(r) > 30 and 'job' not in r.lower()[:10]]
        
        # Create an elegant job summary with better spacing and formatting
        job_summary = f"""✨ Position Overview

📋 Role
{job_data['title']}

📑 Key Requirements"""

        if requirements:
            for req in requirements:
                # Clean and format each requirement
                summary = req[:150] + "..." if len(req) > 150 else req
                summary = summary.replace("*", "").replace("#", "").replace("`", "")
                job_summary += f"\n• {summary}"
        else:
            job_summary += "\n• Requirements not specified in the job posting"

        job_summary += "\n\n💼 Core Responsibilities"
        
        if responsibilities:
            for resp in responsibilities:
                # Clean and format each responsibility
                summary = resp[:150] + "..." if len(resp) > 150 else resp
                summary = summary.replace("*", "").replace("#", "").replace("`", "")
                job_summary += f"\n• {summary}"
        else:
            job_summary += "\n• Responsibilities not specified in the job posting"

        if job_data['experience_level']:
            job_summary += f"\n\n⭐ Experience Required\n{job_data['experience_level']}"
        
        job_summary += "\n\n🎯 Next Steps\nI'll generate targeted interview questions based on this role. Get ready to practice!"
        
        await update.message.reply_text(job_summary)
        
        if requirements or responsibilities or job_data['description']:
            questions = generate_questions(job_data)
            user_sessions[user_id].questions = questions
            user_sessions[user_id].current_question = 0
            await ask_question(update, context)
        else:
            await update.message.reply_text("❌ I couldn't find enough details in this job posting. Please try with a different job URL that contains more information.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def scrape_job_details(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")  # Avoid detection
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)  # Increased wait time
    
    try:
        driver.get(url)
        time.sleep(5)  # Increased wait time for dynamic content
        
        # Get the page source after JavaScript execution
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Initialize job details
        job_details = {
            "title": "",
            "url": url,
            "responsibilities": [],
            "requirements": [],
            "experience_level": "",
            "description": ""
        }
        
        # Extract title using multiple methods
        possible_title_elements = (
            soup.find('h1') or 
            soup.find(class_=lambda x: x and ('job-title' in x.lower() or 'jobtitle' in x.lower())) or
            soup.find('title') or
            soup.find(['h1', 'h2'], string=lambda x: x and ('job' in x.lower() or 'position' in x.lower()))
        )
        
        if possible_title_elements:
            job_details["title"] = possible_title_elements.get_text(strip=True)
        
        # Look for job description and requirements in common patterns
        description_keywords = ['job-description', 'description', 'job-details', 'about-job', 'job-summary']
        requirement_keywords = ['requirements', 'qualifications', 'skills', 'what-we-need']
        responsibility_keywords = ['responsibilities', 'duties', 'what-you-will-do', 'day-to-day']
        
        # Function to clean text
        def clean_text(text):
            return ' '.join(text.strip().split())
        
        # Extract content by sections
        for section in soup.find_all(['div', 'section']):
            section_text = section.get_text(' ', strip=True).lower()
            section_id = section.get('id', '').lower()
            section_class = ' '.join(section.get('class', [])).lower()
            
            # Check if section contains relevant content
            if any(keyword in section_id or keyword in section_class or keyword in section_text 
                  for keyword in description_keywords):
                job_details["description"] = clean_text(section.get_text())
            
            if any(keyword in section_id or keyword in section_class or keyword in section_text 
                  for keyword in requirement_keywords):
                # Look for bullet points or numbered lists
                requirements = []
                for item in section.find_all(['li', 'p']):
                    text = clean_text(item.get_text())
                    if len(text) > 20:  # Avoid very short items
                        requirements.append(text)
                if requirements:
                    job_details["requirements"].extend(requirements)
            
            if any(keyword in section_id or keyword in section_class or keyword in section_text 
                  for keyword in responsibility_keywords):
                responsibilities = []
                for item in section.find_all(['li', 'p']):
                    text = clean_text(item.get_text())
                    if len(text) > 20:  # Avoid very short items
                        responsibilities.append(text)
                if responsibilities:
                    job_details["responsibilities"].extend(responsibilities)
            
            # Look for experience requirements
            if 'experience' in section_text:
                import re
                experience_pattern = r'\b(\d+[-\s]?(?:\d+)?\+?\s*(?:year|yr)s?)\b'
                experience_matches = re.findall(experience_pattern, section_text)
                if experience_matches:
                    job_details["experience_level"] = experience_matches[0]
        
        # If no structured data found, try to extract from general content
        if not any([job_details["requirements"], job_details["responsibilities"], job_details["description"]]):
            # Get all text content
            main_content = soup.find(['main', 'article']) or soup.find('body')
            if main_content:
                content_text = main_content.get_text(' ', strip=True)
                # Split into paragraphs and analyze each
                paragraphs = [p for p in content_text.split('\n') if len(p.strip()) > 50]
                for para in paragraphs:
                    para_lower = para.lower()
                    if any(keyword in para_lower for keyword in requirement_keywords):
                        job_details["requirements"].append(clean_text(para))
                    elif any(keyword in para_lower for keyword in responsibility_keywords):
                        job_details["responsibilities"].append(clean_text(para))
                    else:
                        job_details["description"] = clean_text(para)
        
        # Ensure we have some content
        if not job_details["title"]:
            raise Exception("Could not find job title")
        
        if not any([job_details["requirements"], job_details["responsibilities"], job_details["description"]]):
            raise Exception("Could not find job details")
        
        return job_details
        
    except Exception as e:
        raise Exception(f"Error scraping job details: {str(e)}")
    finally:
        driver.quit()

def generate_questions(job_data):
    # Prepare detailed context for question generation
    context = f"""
    Job Title: {job_data['title']}
    
    Key Responsibilities:
    {chr(10).join(f'- {r}' for r in job_data['responsibilities'][:5]) if job_data['responsibilities'] else 'Not specified'}
    
    Requirements/Qualifications:
    {chr(10).join(f'- {r}' for r in job_data['requirements'][:5]) if job_data['requirements'] else 'Not specified'}
    
    Experience Level: {job_data['experience_level'] if job_data['experience_level'] else 'Not specified'}
    """
    
    if job_data['description']:
        context += f"\nAdditional Context:\n{job_data['description'][:1000]}"
    
    prompt = f"""
    Generate 5 targeted interview questions for this role:
    {context}
    
    Requirements:
    - Include 2 technical questions based on the specific skills/requirements
    - Include 2 behavioral questions relevant to the responsibilities
    - Include 1 situational question related to the role's challenges
    - Questions should be specific to this role, not generic
    - Format as a numbered list
    """
    
    response = gemini_model.generate_content(prompt)
    questions = [q for q in response.text.split('\n') if q.strip() and q[0].isdigit()]
    return questions[:5]

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    
    if session.current_question < len(session.questions):
        question = session.questions[session.current_question]
        message = (
            f"📝 Interview Question {session.current_question + 1} of {len(session.questions)}\n\n"
            f"{question}\n\n"
            "🎙️ You can:\n"
            "• Send a voice message (recommended for practice)\n"
            "• Type your answer\n"
            "\nTake your time to think and structure your response!"
        )
        await update.message.reply_text(message)
    else:
        await generate_report(update, context)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_sessions or not user_sessions[user_id].questions:
        await update.message.reply_text("Please send a job URL first!")
        return
    
    session = user_sessions[user_id]
    
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_audio:
        await voice_file.download_to_drive(temp_audio.name)
        audio_path = temp_audio.name
    
    await update.message.reply_text("🔄 Processing your answer...")
    
    try:
        # Convert OGG to WAV
        wav_path = audio_path.replace('.ogg', '.wav')
        os.system(f"ffmpeg -i {audio_path} {wav_path}")
        
        # Transcribe using Google Speech Recognition
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            transcript = recognizer.recognize_google(audio)
        
        session.answers.append({
            "question": session.questions[session.current_question],
            "answer": transcript
        })
        
        feedback = generate_feedback(
            session.questions[session.current_question],
            transcript,
            session.job_data
        )
        
        await send_long_message(update.message, f"📝 Feedback:\n\n{feedback}")
        
        session.current_question += 1
        await ask_question(update, context)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing answer: {str(e)}")
    finally:
        os.unlink(audio_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)

def generate_feedback(question, answer, job_data):
    prompt = f"""
    Analyze this interview response briefly:
    Position: {job_data['title']}
    Question: {question}
    Answer: {answer}
    
    Provide concise feedback (2-3 lines total) following this format:
    ✓ Strength: One key strong point
    △ Improve: One specific suggestion
    
    Be direct and constructive.
    """
    
    response = gemini_model.generate_content(prompt)
    feedback = response.text.strip()
    
    # Clean up the feedback format
    feedback = (feedback
               .replace('**', '')
               .replace('*', '')
               .replace('#', '')
               .replace('Strength:', '✓ Strength:')
               .replace('Improve:', '△ Improve:'))
    
    return feedback

async def handle_text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_sessions or not user_sessions[user_id].questions:
        await update.message.reply_text("Please send a job URL first!")
        return
    
    session = user_sessions[user_id]
    answer = update.message.text
    
    session.answers.append({
        "question": session.questions[session.current_question],
        "answer": answer
    })
    
    feedback = generate_feedback(
        session.questions[session.current_question],
        answer,
        session.job_data
    )
    
    await send_long_message(update.message, f"📝 Feedback:\n\n{feedback}")
    
    session.current_question += 1
    await ask_question(update, context)

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session = user_sessions[user_id]
    
    await update.message.reply_text("📊 Creating your interview performance report...")
    
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch
    
    pdf_path = f"report_{user_id}.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Create the story (content) for the PDF
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8
    )
    
    # Add title
    story.append(Paragraph("Interview Performance Report", title_style))
    
    # Add job details
    story.append(Paragraph(f"Position: {session.job_data['title']}", heading_style))
    story.append(Spacer(1, 12))
    
    # Add performance summary
    story.append(Paragraph("Performance Analysis", heading_style))
    story.append(Spacer(1, 12))
    
    # Process each Q&A
    for i, qa in enumerate(session.answers, 1):
        # Question section
        story.append(Paragraph(f"Question {i}:", subheading_style))
        story.append(Paragraph(qa['question'], styles['Normal']))
        story.append(Spacer(1, 8))
        
        # Create a table for answer and feedback
        feedback = generate_feedback(qa['question'], qa['answer'], session.job_data)
        data = [
            ['Your Response:', 'Feedback:'],
            [Paragraph(qa['answer'], styles['Normal']), Paragraph(feedback, styles['Normal'])]
        ]
        
        t = Table(data, colWidths=[doc.width/2.0-6]*2)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0,0), (-1,-1), 2, colors.black),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 20))
    
    # Build the PDF
    doc.build(story)
    
    await update.message.reply_document(
        document=open(pdf_path, 'rb'),
        caption="✨ Here's your detailed interview performance report!",
        filename=f"Interview_Report_{session.job_data['title']}.pdf"
    )
    
    os.unlink(pdf_path)
    del user_sessions[user_id]

async def send_long_message(message, text):
    # Clean up formatting and make feedback more readable
    text = (text
           .replace('**', '')
           .replace('*', '')
           .replace('📝 Feedback:\n\n', '')
           .replace('Strength:', '✓ Strength:')
           .replace('Improve:', '△ Improve:'))
    
    # Add a decorative border to the feedback
    formatted_text = f"""
╭──────────────────────╮
  Feedback
╰──────────────────────╯

{text}"""
    
    await message.reply_text(formatted_text)

def main():
    print("Starting bot...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    app.run_polling()

if __name__ == "__main__":
    main()
