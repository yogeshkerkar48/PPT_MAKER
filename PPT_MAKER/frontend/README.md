# Vue.js Frontend - HTML to PowerPoint Converter

Modern, responsive Vue 3 frontend for the HTML to PowerPoint converter.

## Features

- 🎨 Modern glassmorphism UI design
- 📤 Drag & drop file upload
- 🎨 Color picker with presets
- 📝 Large text area for content
- ⚡ Real-time validation
- 🚀 Automatic file download
- 📱 Fully responsive

## Setup

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

### Build for Production

```bash
npm run build
```

## Configuration

Edit `.env` to change the API URL:

```
VITE_API_URL=http://localhost:8000
```

## Usage

1. **Upload Image**: Click or drag & drop a PNG/JPG image
2. **Enter Content**: Paste HTML or plain text
3. **Choose Color**: Select a background color
4. **Generate**: Click the button to create your presentation
5. **Download**: The PPTX file will download automatically

## Tech Stack

- **Vue 3** - Progressive JavaScript framework
- **Vite** - Next generation frontend tooling
- **Axios** - HTTP client for API calls
- **Vanilla CSS** - Custom styling with glassmorphism

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── pptxService.js    # API integration
│   ├── styles/
│   │   └── main.css          # Global styles
│   ├── App.vue               # Main component
│   └── main.js               # App initialization
├── index.html                # HTML entry point
├── vite.config.js            # Vite configuration
└── package.json              # Dependencies
```

## API Integration

The frontend communicates with the backend via:
- **Endpoint**: `POST /generate-pptx`
- **Content-Type**: `multipart/form-data`
- **Response**: Binary PPTX file

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
