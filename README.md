# DoItNow Interview Preparation Bot 🤖

![Interview Preparation](https://images.unsplash.com/photo-1553877522-43269d4ea984?auto=format&fit=crop&w=1200&q=80)

## 📋 Overview

DoItNow is an intelligent Telegram bot designed to help job seekers prepare for interviews by providing personalized interview practice based on actual job postings. Simply share a job listing URL, and the bot will create a customized interview simulation experience.

## ✨ Features

- 🔍 **Smart Job Analysis**: Automatically extracts key information from job postings including:
  - Job title and requirements
  - Key responsibilities
  - Required qualifications
  - Experience level

- 💡 **Customized Questions**: Generates relevant interview questions based on the job posting:
  - Technical questions aligned with required skills
  - Behavioral questions based on job responsibilities
  - Situational questions related to the role

- 🎙️ **Voice Support**: Practice answering interview questions using:
  - Voice messages (recommended for realistic practice)
  - Text responses

- 📊 **Instant Feedback**: Receive immediate, constructive feedback on your answers:
  - Strengths analysis
  - Areas for improvement
  - Tailored suggestions

- 📑 **Performance Report**: Get a comprehensive PDF report including:
  - Question-by-question analysis
  - Response evaluation
  - Overall performance summary

## 🚀 Getting Started

### Prerequisites

```
python 3.x
selenium
beautifulsoup4
python-telegram-bot
google-generativeai
reportlab
SpeechRecognition
ffmpeg (for voice processing)
```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/DoItNow-bot.git
   cd DoItNow-bot
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - TELEGRAM_TOKEN: Your Telegram bot token
   - GEMINI_API_KEY: Your Google Gemini API key

4. Run the bot:
   ```bash
   python bot.py
   ```

## 🎯 How to Use

1. Start a chat with the bot on Telegram
2. Send the bot a job listing URL (LinkedIn, Indeed, etc.)
3. The bot will analyze the job posting and generate relevant interview questions
4. Answer each question using voice messages or text
5. Receive instant feedback on your responses
6. Get a detailed PDF report after completing all questions

## 🛠️ Technical Details

- Built with Python 3.x
- Uses Selenium for web scraping job listings
- Implements Google's Gemini AI for intelligent feedback
- Supports voice message processing using SpeechRecognition
- Generates professional PDF reports using ReportLab

## 📝 Note

- Ensure you have a stable internet connection
- Some job posting websites may have anti-scraping measures
- Voice recognition works best in a quiet environment
- PDF generation requires sufficient system memory

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini AI for intelligent response analysis
- Telegram Bot API for the messaging interface
- All the open-source libraries that made this project possible