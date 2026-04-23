# Collections Intelligence Platform - Frontend

Modern React application for proactive loan collections management with AI-powered features.

## 🚀 Features

### Customer Portal
- **📋 Loan Management**: View loan details with bounce risk indicators
- **🎥 Video AI Agent**: Interactive lip-synced video assistance powered by D-ID
- **🎤 Voice Input**: Speak questions in 9 Indian languages (automatic detection)
- **✅ Auto-Pay Enrollment**: Prevent payment bounces with auto-debit
- **💬 AI Chat Assistant**: Multilingual text-based loan queries
- **🌐 Language Support**: Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, English

### Officer Portal
- **📊 Dashboard**: Real-time bounce risk KPIs with visual progress bars
- **🔍 Customer Search**: 90% faster with instant bounce risk display
- **🎯 Bounce Prevention**: High/Medium/Low risk categorization
- **📢 Bulk Campaigns**: Multi-customer outreach for auto-pay enrollment
- **📈 Risk Analytics**: Portfolio health monitoring
- **✍️ Request Management**: Grace period and loan restructure approvals

## 🛠️ Tech Stack

- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Charts**: Recharts (for analytics visualizations)
- **Audio**: MediaRecorder API (voice input)
- **Video**: HTML5 Video Player (D-ID lip-sync playback)
- **Routing**: React Router v6

## 📦 Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

Development server runs on `http://localhost:5173`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root (not in frontend/):

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# Feature flags (optional)
VITE_ENABLE_VIDEO_AGENT=true
VITE_ENABLE_VOICE_INPUT=true
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── customer/           # Customer-facing pages
│   │   │   ├── ChatAssistant.jsx
│   │   │   ├── CustomerLoans.jsx  # 📹 Video AI Agent
│   │   │   ├── LoanDetail.jsx
│   │   │   ├── Preferences.jsx
│   │   │   └── CustomerLayout.jsx
│   │   ├── officer/            # Officer-facing pages
│   │   │   ├── OfficerDashboard.jsx  # Bounce KPIs
│   │   │   ├── CustomerSearch.jsx    # 90% faster
│   │   │   ├── LoanIntelligence.jsx
│   │   │   ├── GraceManagement.jsx
│   │   │   ├── RestructureManagement.jsx
│   │   │   └── OfficerLayout.jsx
│   │   └── LoginPage.jsx
│   ├── components/
│   │   ├── LoanChat.jsx        # Text chat component
│   │   └── VideoCallAgent.jsx  # Video AI modal (NEW)
│   ├── charts/                 # Dashboard visualizations
│   ├── chatbot/                # Chat interface components
│   ├── assets/                 # Images, icons
│   ├── api.js                  # Axios configuration
│   ├── App.jsx                 # Main app component
│   └── main.jsx                # Entry point
├── public/                     # Static assets
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## 🎨 Key Components

### VideoCallAgent.jsx (NEW)
- D-ID lip-synced video player
- Voice recording with MediaRecorder API
- Automatic language detection
- Loan context display
- Chat history sidebar

### CustomerLoans.jsx (ENHANCED)
- Bounce risk badges (High/Medium/Low)
- Auto-pay enrollment modal
- Video AI Agent button (📹)
- Real-time risk indicators

### OfficerDashboard.jsx (REDESIGNED)
- Consolidated KPI card
- Bounce risk distribution with progress bars
- Auto-pay enrollment tracking
- Color-coded risk metrics

### CustomerSearch.jsx (OPTIMIZED)
- 90% performance improvement
- Instant bounce risk display
- Advanced filters (bounce risk, DPD)
- Sort by risk score

## 🔌 API Integration

The frontend communicates with FastAPI backend via Axios:

```javascript
// Example: Transcribe voice to text
const response = await axios.post(
  '/customer/video-agent/transcribe-audio',
  formData,
  {
    headers: { 'Content-Type': 'multipart/form-data' }
  }
);

// Example: Get bounce risk for loan
const risk = await axios.get(`/officer/loans/${loanId}/bounce-risk`);
```

Key endpoints:
- `/customer/video-agent/*` - Video AI & voice input
- `/officer/bounce-prevention/*` - Bounce risk APIs
- `/customer/chat` - Text chat with AI
- `/officer/dashboard/kpis` - Dashboard metrics

## 🎤 Voice Input Features

**Browser Compatibility**:
- Chrome 49+
- Firefox 25+
- Safari 14+
- Edge 79+

**Supported Audio Formats**:
- WebM (Opus codec) - Chrome/Firefox
- OGG (Opus codec) - Firefox
- MP4 (AAC codec) - Safari

Backend automatically converts to WAV format for Sarvam AI processing.

## 🎥 Video AI Agent

**Features**:
- Click "📹 Ask Video AI Agent" on loan page
- Record voice or type question
- Automatic language detection
- Receive lip-synced video response
- Supports 9 languages

**Technical Details**:
- Video format: MP4 (H.264 codec)
- Response time: 3-5 seconds
- Fallback: Browser TTS if D-ID unavailable

## 🧪 Development Tips

### Running in Dev Mode

```bash
npm run dev
```

**Hot Module Replacement (HMR)** enabled - changes reflect instantly.

### Building for Production

```bash
npm run build
```

Generates optimized build in `dist/` folder.

### Linting

```bash
npm run lint
```

ESLint configured for React best practices.

## 🐛 Troubleshooting

**Voice input not working**:
- Check browser microphone permissions
- Ensure HTTPS (required for MediaRecorder API in production)
- Verify backend ffmpeg installation

**Video not playing**:
- Check D-ID API key in backend `.env`
- Verify internet connection
- Check browser console for errors

**Slow dashboard loading**:
- Clear browser cache
- Check network tab for API response times
- Verify backend database connection

## 📄 License

Part of Collections Intelligence Platform - Production-Ready Prototype

## 🙏 Credits

Built with:
- **React** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **D-ID** - Video AI avatars
- **Sarvam AI** - Voice transcription

---

**For full system documentation, see `../README.md` and `../docs/system_design.md`**
