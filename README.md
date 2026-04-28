# 🎯 CV Job Matcher

An AI-powered job matching platform that analyses your CV, recommends tailored career paths, and aggregates real-time job listings—ranked by how well they match your profile.

Built with **Streamlit, Python, and AI-driven analysis**, this tool helps you identify high-fit opportunities faster and make smarter career decisions.

### 🌐 Try the Live App
[![Live Demo](https://img.shields.io/badge/Live-Demo-green?style=for-the-badge)](https://danielakbank-cv-job-matcher-app-xacssg.streamlit.app/)
---

## 🚀 Key Features

### 📄 CV Upload & Intelligent Analysis
- Upload CVs in **PDF or DOCX**
- Automatic text extraction
- AI-powered analysis of skills, experience, and background
- Generates personalised role recommendations

---

### 💡 Smart Role Suggestions
Roles are grouped into:

- 🎯 **Obvious Matches** – Directly aligned roles  
- 🚀 **Stretch Roles** – Slightly above your current level  
- 💎 **Hidden Gems** – Less obvious but high-potential roles  

Each role includes:
- Match explanation
- Estimated salary range

---

### 📍 Location-Based Search
- Search via UK postcode (postcodes.io)
- IP-based fallback location detection
- Adjustable radius (5km – 150km)
- Nationwide search option

---

### 🔎 Multi-Source Job Aggregation
- Adzuna API  
- Reed API  
- Remotive API (remote roles)

---

### 🧠 AI Job Matching Engine
Each job is scored against your CV:

- 🟢 70–100% → Strong Match  
- 🟡 45–69% → Partial Match  
- 🔴 0–44% → Weak Match  

---

### 🤖 AI Job Insights
- Why you're a match
- Relevant existing skills
- Skill gaps to improve

---

### 🎛 Filters & Controls
- Filter by minimum match score
- Sort by match or salary
- Filter by role categories

---

## 🏗 Tech Stack

- **Frontend:** Streamlit  
- **Backend:** Python  

### AI Modules:
- CV parsing
- Role suggestion engine
- Job scoring system
- Job analysis engine

### APIs:
- Adzuna Jobs API  
- Reed Jobs API  
- Remotive API  
- postcodes.io  
- ip-api  

---

## 📂 Project Structure

```
project/
│
├── app.py
├── utils/
│   ├── cv_parser.py
│   ├── job_fetcher.py
│   ├── scorer.py
│   ├── analyzer.py
│   ├── job_suggester.py
│
├── .env
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Setup

### 1. Clone repository
```bash
git clone https://github.com/your-username/cv-job-matcher.git
cd cv-job-matcher
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
REED_API_KEY=your_reed_api_key
```

### 5. Run the app
```bash
streamlit run app.py
```

---

## 📍 Location Filtering Logic

| Source        | Behaviour                          |
|--------------|-----------------------------------|
| Postcode     | Precise geolocation               |
| IP Detection | Approximate fallback              |
| Adzuna       | Uses postcode + radius (km)       |
| Reed         | Uses location + radius (miles)    |
| Remotive     | Global remote jobs only           |

---

## 🧠 How It Works

1. Upload your CV  
2. AI analyses your experience  
3. Suggested roles are generated  
4. Jobs are fetched via APIs  
5. Each job is scored against your CV  
6. Results are ranked and explained  

---

## ⚠️ Limitations

- IP-based location is approximate  
- API rate limits may apply  
- Job descriptions vary in quality  
- CV parsing depends on formatting  

---

## 🔮 Future Improvements

- ✉️ AI-generated cover letters  
- 💾 Save/bookmark jobs  
- 📊 Skill gap dashboard  
- 🌍 More job sources  
- 📱 Mobile optimisation  

---

## 👤 Author

**Daniel Akinbankole**  
Data Analyst | AI Builder | Flutter Developer  

---

## ⭐ Support

If you like this project:

- ⭐ Star the repo  
- 🍴 Fork it  
- 🚀 Contribute  

---

## 📌 License

Open-source for learning and personal use.
