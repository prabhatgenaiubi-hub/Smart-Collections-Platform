import { useState, useEffect, useRef } from 'react';
import api from '../api';

export default function VideoCallAgent({ loanId, onClose }) {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [loanSummary, setLoanSummary] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentVideo, setCurrentVideo] = useState(null); // ← D-ID video URL
  const [videoStatus, setVideoStatus] = useState('idle'); // idle / playing / ended
  const [isRecording, setIsRecording] = useState(false); // ← Voice recording state
  const [mediaRecorder, setMediaRecorder] = useState(null); // ← MediaRecorder instance
  
  const chatEndRef = useRef(null);
  const speechSynthRef = useRef(null);
  const videoRef = useRef(null); // ← Video element reference

  // Fetch loan summary on mount
  useEffect(() => {
    fetchLoanSummary();
  }, [loanId]);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // Handle video playback when currentVideo changes
  useEffect(() => {
    console.log('currentVideo state changed:', currentVideo);
    if (currentVideo && videoRef.current) {
      console.log('Video URL updated, loading:', currentVideo);
      videoRef.current.src = currentVideo;
      videoRef.current.load();
      videoRef.current.play().catch(err => {
        console.error('Auto-play failed:', err);
      });
    }
  }, [currentVideo]);

  const fetchLoanSummary = async () => {
    try {
      const res = await api.get(`/customer/video-agent/loan-summary/${loanId}`);
      setLoanSummary(res.data);
    } catch (err) {
      console.error('Failed to fetch loan summary:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    // Add user message (text input, not voice)
    const userMessage = { type: 'user', text: question, timestamp: new Date(), isVoice: false };
    setConversation(prev => [...prev, userMessage]);
    
    const questionText = question;
    setQuestion(''); // Clear input immediately
    
    // Call the shared submission logic
    await handleSubmitQuestion(questionText, language);
  };

  const playVideo = (videoUrl) => {
    console.log('Setting video URL:', videoUrl);
    // Set video URL - useEffect will handle playback
    setCurrentVideo(videoUrl);
    setVideoStatus('playing');
    setIsPlaying(true);
  };

  const handleVideoEnded = () => {
    setVideoStatus('ended');
    setIsPlaying(false);
    // Keep showing last frame instead of hiding video
  };

  const stopVideo = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    setVideoStatus('idle');
    setIsPlaying(false);
  };

  const speakText = (text, lang) => {
    if ('speechSynthesis' in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = getVoiceLang(lang);
      utterance.rate = 0.9;
      utterance.pitch = 1.0;

      utterance.onstart = () => setIsPlaying(true);
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);

      speechSynthRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    }
  };

  const getVoiceLang = (lang) => {
    const langMap = {
      'en': 'en-IN',
      'hi': 'hi-IN',
      'ta': 'ta-IN',
      'te': 'te-IN',
      'kn': 'kn-IN',
      'ml': 'ml-IN',
      'bn': 'bn-IN',
      'gu': 'gu-IN',
      'mr': 'mr-IN'
    };
    return langMap[lang] || 'en-IN';
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
    }
    
    // Also stop video if playing
    if (videoRef.current && !videoRef.current.paused) {
      stopVideo();
    }
  };

  const handleQuickQuestion = (q) => {
    setQuestion(q);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,  // Mono
          sampleRate: 16000,  // 16kHz is standard for STT
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      // Use MediaRecorder with best available format
      // Sarvam supports: WAV, MP3, FLAC, OGG
      let options = {};
      
      // Try different formats in order of preference
      if (MediaRecorder.isTypeSupported('audio/wav')) {
        options = { mimeType: 'audio/wav' };
      } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        options = { mimeType: 'audio/webm;codecs=opus' };
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        options = { mimeType: 'audio/ogg;codecs=opus' };
      } else {
        options = { mimeType: 'audio/webm' };
      }
      
      console.log('Recording with options:', options);
      
      const recorder = new MediaRecorder(stream, options);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
          console.log('Chunk received:', e.data.size, 'bytes');
        }
      };

      recorder.onstop = async () => {
        console.log('Total chunks:', chunks.length);
        const audioBlob = new Blob(chunks, { type: recorder.mimeType });
        console.log('Audio recorded:', {
          size: audioBlob.size,
          type: audioBlob.type,
          mimeType: recorder.mimeType
        });
        
        if (audioBlob.size === 0) {
          alert('No audio was recorded. Please try again.');
          return;
        }
        
        if (audioBlob.size < 5000) {
          alert('Recording too short. Please speak for at least 3 seconds.');
          return;
        }
        
        await transcribeAudio(audioBlob);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      // Start recording
      recorder.start(100); // Collect data every 100ms
      setMediaRecorder(recorder);
      setIsRecording(true);
      
      console.log('Recording started with format:', recorder.mimeType);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone. Please allow microphone access.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      console.log('Recording stopped...');
    }
  };

  const transcribeAudio = async (audioBlob) => {
    setLoading(true);
    
    try {
      // Create form data with audio file
      const formData = new FormData();
      
      // Determine filename based on mime type
      let filename = 'recording.webm';
      if (audioBlob.type.includes('ogg')) {
        filename = 'recording.ogg';
      } else if (audioBlob.type.includes('wav')) {
        filename = 'recording.wav';
      } else if (audioBlob.type.includes('mp3')) {
        filename = 'recording.mp3';
      }
      
      formData.append('audio_file', audioBlob, filename);

      console.log('Transcribing audio...');
      console.log('Sending to API:', '/customer/video-agent/transcribe-audio');
      console.log('Audio blob size:', audioBlob.size, 'bytes');
      console.log('Audio blob type:', audioBlob.type);
      console.log('Filename:', filename);
      
      const res = await api.post('/customer/video-agent/transcribe-audio', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      const transcribed = res.data.text;
      const detectedLang = res.data.language;

      console.log('Transcribed:', transcribed, 'Language:', detectedLang);

      // Auto-set detected language
      if (detectedLang && detectedLang !== language) {
        setLanguage(detectedLang);
        console.log('Language auto-switched to:', detectedLang);
      }

      // Set transcribed text as question
      setQuestion(transcribed);
      
      // Show user message
      const userMessage = { 
        type: 'user', 
        text: transcribed, 
        timestamp: new Date(),
        isVoice: true 
      };
      setConversation(prev => [...prev, userMessage]);

      // Auto-submit after small delay
      setTimeout(() => {
        if (transcribed.trim()) {
          handleSubmitQuestion(transcribed, detectedLang);
        }
      }, 500);

    } catch (err) {
      console.error('Transcription failed:', err);
      console.error('Error response:', err.response?.data);
      console.error('Error status:', err.response?.status);
      setLoading(false);
      
      let errorText = 'Sorry, I could not understand your voice. Please try typing or speaking again.';
      if (err.response?.data?.detail) {
        errorText = err.response.data.detail;
        console.error('Backend error detail:', err.response.data.detail);
      }
      
      const errorMessage = {
        type: 'agent',
        text: errorText,
        timestamp: new Date()
      };
      setConversation(prev => [...prev, errorMessage]);
    }
  };

  const handleSubmitQuestion = async (questionText, lang) => {
    if (!questionText.trim()) return;

    setLoading(true);

    try {
      const res = await api.post('/customer/video-agent/chat', {
        loan_id: loanId,
        question: questionText,
        language: lang || language
      });

      console.log('Backend response:', {
        video_url: res.data.answer_video_url,
        video_status: res.data.video_status,
        has_audio: !!res.data.answer_audio_url
      });

      const agentMessage = {
        type: 'agent',
        text: res.data.answer_text,
        audio_url: res.data.answer_audio_url,
        video_url: res.data.answer_video_url,
        video_status: res.data.video_status,
        timestamp: new Date()
      };

      setConversation(prev => [...prev, agentMessage]);

      // If D-ID video is available, play it instead of browser TTS
      if (res.data.answer_video_url && res.data.video_status === 'ready') {
        console.log('Playing D-ID video');
        playVideo(res.data.answer_video_url);
      } else {
        console.log('Using browser TTS fallback, video_status:', res.data.video_status);
        speakText(res.data.answer_text, lang || language);
      }

    } catch (err) {
      console.error('Failed to get response:', err);
      console.error('Error details:', err.response?.data);
      
      let errorText = 'Sorry, I encountered an error. Please try again.';
      if (err.response?.data?.detail) {
        errorText = `Error: ${err.response.data.detail}`;
      }
      
      const errorMessage = {
        type: 'agent',
        text: errorText,
        timestamp: new Date()
      };
      setConversation(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      setQuestion('');
    }
  };


  const languages = [
    { code: 'en', label: 'English', flag: '🇬🇧' },
    { code: 'hi', label: 'हिन्दी', flag: '🇮🇳' },
    { code: 'ta', label: 'தமிழ்', flag: '🇮🇳' },
    { code: 'te', label: 'తెలుగు', flag: '🇮🇳' },
    { code: 'kn', label: 'ಕನ್ನಡ', flag: '🇮🇳' },
    { code: 'ml', label: 'മലയാളം', flag: '🇮🇳' },
  ];

  console.log('VideoCallAgent rendering, currentVideo:', currentVideo, 'loanId:', loanId);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col">
        
        {/* Header - Professional Banking Style */}
        <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white px-6 py-4 rounded-t-2xl flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-white bg-opacity-20 rounded-full flex items-center justify-center backdrop-blur-sm">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-tight">Banking AI Assistant</h2>
              <p className="text-sm opacity-90 font-medium">Professional Loan Advisory Service</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2 transition-all duration-200 hover:rotate-90"
            title="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Video Agent - EXPANDED TO 60% */}
          <div className="w-3/5 bg-gradient-to-b from-gray-50 to-gray-100 p-8 flex flex-col border-r">
            {/* Video/Avatar Container */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '500px' }}>
              {/* Default Avatar - Shows when no video */}
              {!currentVideo ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
                  {/* Avatar Circle - Professional Woman Image */}
                  <div 
                    style={{
                      width: '384px',
                      height: '384px',
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 20px 60px rgba(102, 126, 234, 0.4)',
                      border: '6px solid white',
                      flexShrink: 0,
                      position: 'relative',
                      overflow: 'hidden',
                      backgroundColor: '#f3f4f6'
                    }}
                  >
                    {/* Professional Woman Avatar Image */}
                    <img 
                      src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=400&fit=crop"
                      alt="AI Banking Assistant"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        display: 'block'
                      }}
                    />
                    {/* Fallback icon if image fails to load */}
                    <div style={{
                      display: 'none',
                      width: '100%',
                      height: '100%',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    }}>
                      <svg 
                        style={{ color: 'white' }}
                        width="200" 
                        height="200" 
                        fill="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <circle cx="12" cy="8" r="4" />
                        <path d="M12 14c-6 0-8 3-8 6v2h16v-2c0-3-2-6-8-6z" />
                      </svg>
                    </div>
                  </div>
                  
                  {/* Professional Label */}
                  <div style={{ marginTop: '24px', textAlign: 'center' }}>
                    <p style={{ fontSize: '24px', fontWeight: '600', color: '#1f2937' }}>Banking Assistant</p>
                    <p style={{ fontSize: '18px', color: '#6b7280', marginTop: '8px' }}>AI-Powered Support</p>
                  </div>
                  
                  {/* Speaking indicator when playing audio without video */}
                  {isPlaying && (
                    <div className="mt-4">
                      <div className="flex gap-1 justify-center">
                        <div className="w-1.5 h-8 bg-blue-500 rounded animate-pulse"></div>
                        <div className="w-1.5 h-12 bg-purple-500 rounded animate-pulse" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-1.5 h-10 bg-blue-500 rounded animate-pulse" style={{animationDelay: '0.2s'}}></div>
                        <div className="w-1.5 h-14 bg-purple-500 rounded animate-pulse" style={{animationDelay: '0.3s'}}></div>
                        <div className="w-1.5 h-8 bg-blue-500 rounded animate-pulse" style={{animationDelay: '0.4s'}}></div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* D-ID Video Player - Shows when video is ready */
                <div className="w-full max-w-2xl">
                  <div className="relative rounded-2xl overflow-hidden shadow-2xl bg-black">
                    <video
                      ref={videoRef}
                      className="w-full h-auto"
                      onEnded={handleVideoEnded}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      playsInline
                      controls={false}
                    />
                    {/* Speaking indicator overlay on video */}
                    {isPlaying && videoStatus === 'playing' && (
                      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
                        <div className="flex gap-1 bg-black bg-opacity-50 rounded-lg px-3 py-2">
                          <div className="w-1 h-8 bg-white rounded animate-pulse"></div>
                          <div className="w-1 h-12 bg-white rounded animate-pulse" style={{animationDelay: '0.1s'}}></div>
                          <div className="w-1 h-10 bg-white rounded animate-pulse" style={{animationDelay: '0.2s'}}></div>
                          <div className="w-1 h-14 bg-white rounded animate-pulse" style={{animationDelay: '0.3s'}}></div>
                          <div className="w-1 h-8 bg-white rounded animate-pulse" style={{animationDelay: '0.4s'}}></div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            
            <div className="mt-6 text-center">
              <p className="text-sm font-semibold text-gray-700">
                {isPlaying ? '🔊 Speaking...' : '👂 Listening'}
              </p>
              {isPlaying && (
                <button
                  onClick={stopSpeaking}
                  className="mt-3 px-4 py-2 bg-red-500 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition-colors"
                >
                  ⏹ Stop
                </button>
              )}
            </div>

            {/* Language Selector */}
            <div className="mt-8 w-full">
              <p className="text-xs font-semibold text-gray-600 mb-2">🌐 Language</p>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {languages.map(lang => (
                  <option key={lang.code} value={lang.code}>
                    {lang.flag} {lang.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Right: Chat & Loan Summary - REDUCED TO 40% */}
          <div className="w-2/5 flex flex-col">
            
            {/* Loan Summary */}
            {loanSummary && (
              <div className="bg-blue-50 border-b border-blue-200 p-4">
                <h3 className="text-sm font-bold text-gray-800 mb-2">🏦 Loan Summary</h3>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <p className="text-gray-600">Type</p>
                    <p className="font-semibold text-gray-900">{loanSummary.loan.loan_type}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">EMI Amount</p>
                    <p className="font-semibold text-gray-900">₹{loanSummary.loan.emi_amount?.toLocaleString('en-IN')}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Due Date</p>
                    <p className="font-semibold text-gray-900">{loanSummary.loan.emi_due_date}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Outstanding</p>
                    <p className="font-semibold text-gray-900">₹{loanSummary.loan.outstanding_balance?.toLocaleString('en-IN')}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Days Past Due</p>
                    <p className={`font-semibold ${loanSummary.loan.days_past_due > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {loanSummary.loan.days_past_due}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Payments Made</p>
                    <p className="font-semibold text-gray-900">{loanSummary.loan.total_payments_made}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {conversation.length === 0 && (
                <div className="text-center text-gray-500 mt-8">
                  <p className="text-2xl mb-2">👋</p>
                  <p className="text-sm">Hi! I'm your AI loan assistant.</p>
                  <p className="text-xs mt-1">Ask me anything about your loan!</p>
                </div>
              )}

              {conversation.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                    msg.type === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    {/* Voice indicator for user messages */}
                    {msg.type === 'user' && msg.isVoice && (
                      <span className="inline-block mr-2 text-xs">🎤</span>
                    )}
                    <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                    <p className={`text-xs mt-1 ${msg.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                      {msg.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Quick Questions */}
            {loanSummary && conversation.length === 0 && (
              <div className="px-6 pb-4">
                <p className="text-xs font-semibold text-gray-600 mb-2">💡 Quick Questions:</p>
                <div className="flex flex-wrap gap-2">
                  {loanSummary.quick_questions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleQuickQuestion(q)}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs rounded-lg transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="bg-gray-50 border-t p-4">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask a question about your loan..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
                
                {/* Microphone Button */}
                <button
                  type="button"
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={loading}
                  className={`px-4 py-3 rounded-xl font-semibold transition-all flex items-center justify-center ${
                    isRecording 
                      ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
                      : 'bg-purple-600 hover:bg-purple-700'
                  } text-white disabled:bg-gray-300 disabled:cursor-not-allowed`}
                  title={isRecording ? 'Stop Recording' : 'Start Voice Recording'}
                >
                  {isRecording ? '⏹' : '🎤'}
                </button>
                
                {/* Send Button */}
                <button
                  type="submit"
                  disabled={loading || !question.trim()}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold rounded-xl transition-colors"
                >
                  {loading ? '...' : '📤'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
