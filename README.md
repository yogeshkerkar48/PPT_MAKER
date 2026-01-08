# 🎬 Cinematic PPT Generator (v4.2)

A powerful, AI-driven command-line tool designed to transform raw text, PDFs, or DOCX files into high-impact, professional PowerPoint presentations automatically.

## 🌟 Key Features

### 1. **Cinematic Design Engine**
- **Precision Layout**: Alternating side-by-side layouts (Image Left/Text Right and vice versa) for a dynamic presentation flow.
- **Aspect Ratio Mastery**: Automatically scales images to fill vertical height while preserving their original proportions (no stretching).
- **Readability Pro**: Uses semi-transparent (85% opaque) dark text backdrops to ensure perfect legibility over even the most complex maps or bright photos.

### 2. **Intelligent Content Structuring**
- **AI-Powered Parsing**: Uses Groq (LLaMA 3) to convert messy raw data into structured, punchy bullet points.
- **One-to-One Mapping**: Ensures every numbered point in your input gets exactly one dedicated slide.
- **Problem Solving & Q&A**: Automatically formats numerical problems to show both the question and the step-by-step solution.

### 3. **Robust Image Acquisition**
- **Triple Fallback System**: Searches Google Images (via Serper.dev) first, then falls back to multiple AI image generators (Pollinations.ai) if no results are found.
- **Deduplication Logic**: A custom post-processing system intercepts duplicate image requests (common in math problems) and replaces them with unique, context-aware alternatives.
- **Integrity Validation**: Strictly blocks corrupt downloads and rate-limit error images by checking exact pixel resolutions (1280x720).

---

## 🏗️ Project Architecture

| File | Role |
| :--- | :--- |
| `generate_ppt.py` | **Main Orchestrator**: Handles CLI arguments, file ingestion, and the step-by-step generation workflow. |
| `groq_client.py` | **AI Brain**: Manages the complex prompts sent to Groq for content structuring and visual query generation. |
| `pptx_generator.py` | **Design Engine**: The physical builder that converts AI data into a styled `.pptx` file. |
| `html_parser.py` | **Data Safety**: Cleans raw HTML inputs and truncates massive documents to fit AI limits safely. |
| `config.py` | **Configuration**: Central hub for API keys, model selection, and image search parameters. |

---

## 🚀 Get Started

### 1. Prerequisites
- Python 3.10+
- A [Groq API Key](https://console.groq.com/)
- A [Serper.dev API Key](https://serper.dev/) (for Google Image search)

### 2. Setup
Clone the project and install dependencies:
```powershell
pip install -r requirements.txt
```
Create a `.env` file in the `backend` directory and add your keys:
```env
GROQ_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
```

---

## 💻 Final Running Command

To generate a presentation from a text file with a specific limit on slides, use the following command from the `backend` directory:

```powershell
python generate_ppt.py --input your_filename.txt --output result_presentation.pptx --max-slides 70
```

### Command Arguments:
- `--input`: Path to your source file (.txt, .pdf, .docx).
- `--output`: Desired name for the generated PowerPoint file.
- `--max-slides`: (Optional) Limit the AI to a certain number of slides.
- `--text`: (Optional) Provide raw text/HTML directly instead of a file.

---

## 🎨 Visual Example
The generator produces a professional "Broadcast/Documentary" style:
- **Slide 1**: Image Left | Text Right (Pure White on Dark Backdrop)
- **Slide 2**: Text Left (Pure White on Dark Backdrop) | Image Right
- *...and so on.*

---

## 📝 Sample Command for Quick Start

To generate a high-quality presentation using the provided sample data, simply copy and paste this command into your terminal:

```powershell
python generate_ppt.py --input ppt_data.txt --output sample_presentation.pptx --max-slides 50
```
